#!/usr/bin/env python3
"""
Deduplicate org-prefixed skill names in skill-retriever capability trees and index files.

Known prefixes: sickn33-, affaan-m-
Rule: Strip the known prefix. If the stripped name already exists -> drop the prefixed variant.
       If it doesn't exist -> rename to the stripped form (most canonical name).

This script uses text-based (regex) manipulation on YAML and JSON files to preserve
original formatting and avoid introducing line-wrapping noise from yaml.dump().

Usage:
    python scripts/dedup_skill_names.py               # dry-run: report only
    python scripts/dedup_skill_names.py --execute      # write deduplicated trees
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_DIR = Path(__file__).parent.resolve()
CAP_TREE_DIR = REPO_DIR / "src" / "skill_retriever" / "capability_tree"
DATA_DIR = REPO_DIR / "data"
COMMUNITY_DIR = REPO_DIR / "src" / "skill_retriever" / "community_skills"

# Known org prefixes to strip (order matters: longest match first)
KNOWN_PREFIXES = ("affaan-m-", "sickn33-")


def strip_prefix(name):
    """Return (stripped_name, prefix) if name starts with a known prefix, else (name, None)."""
    for prefix in KNOWN_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):], prefix
    return name, None


# Regex patterns for matching prefixed names in YAML text
# Match lines like: "      name: sickn33-foo bar"  (with leading whitespace)
YAML_NAME_RE = re.compile(
    r'^(?P<indent>[ \t]*)name:\s*(?P<prefix>' +
    '|'.join(re.escape(p) for p in KNOWN_PREFIXES) +
    r')(?P<rest>.*?)$',
    re.MULTILINE,
)
YAML_ID_RE = re.compile(
    r'^(?P<indent>[ \t]*)id:\s*(?P<prefix>' +
    '|'.join(re.escape(p) for p in KNOWN_PREFIXES) +
    r')(?P<rest>.*?)$',
    re.MULTILINE,
)


def dedup_yaml_file(filepath, stats):
    """Deduplicate a YAML capability tree file using regex substitutions.

    Returns (was_modified, new_text).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Collect all unique names present in the file
    all_names = set()
    for m in re.finditer(r'^[ \t]*name:\s*(.+?)\s*$', text, re.MULTILINE):
        all_names.add(m.group(1).strip())

    # Determine which prefixed names have a base equivalent present
    renames = {}  # old -> new
    removes = set()  # old names to drop

    for m in YAML_NAME_RE.finditer(text):
        old = m.group('prefix') + m.group('rest').strip()
        stripped, prefix = strip_prefix(old)
        stats["prefixed_found"] += 1
        if stripped in all_names:
            removes.add(old)
            stats["deduped_removed"] += 1
        else:
            renames[old] = stripped
            stats["renamed"] += 1

    # Apply substitutions: renames first (so we don't accidentally remove something
    # that was just renamed)
    def replace_name(m):
        prefix = m.group('prefix')
        rest = m.group('rest').strip()
        full = prefix + rest
        if full in renames:
            stats["applied_renames"] += 1
            return f"{m.group('indent')}name: {renames[full]}"
        return m.group(0)

    new_text = YAML_NAME_RE.sub(replace_name, text)

    # Apply id substitutions
    def replace_id(m):
        prefix = m.group('prefix')
        rest = m.group('rest').strip()
        full = prefix + rest
        if full in renames:
            return f"{m.group('indent')}id: {renames[full].lower().replace(' ', '-')}"
        return m.group(0)

    new_text = YAML_ID_RE.sub(replace_id, new_text)

    was_modified = (new_text != text)
    return was_modified, new_text


def dedup_skills_json_text(text, stats):
    """Deduplicate a skills.json index file using JSON parse/dump (compact)."""
    data = json.loads(text)
    skills = data.get("skills", [])
    if not isinstance(skills, list):
        return False, text

    seen = set()
    new_skills = []
    modified = False
    for sk in skills:
        name = sk.get("name", "").strip()
        stripped, prefix = strip_prefix(name)
        if prefix:
            stats["prefixed_found"] += 1
            if stripped.lower() in seen:
                stats["deduped_removed"] += 1
                modified = True
                continue
            sk["name"] = stripped
            sk["id"] = stripped.lower().replace(" ", "-")
            stats["renamed"] += 1
            stats["applied_renames"] += 1
            name = stripped
            modified = True

        key = name.lower()
        if key in seen:
            stats["deduped_removed"] += 1
            modified = True
            continue
        seen.add(key)
        new_skills.append(sk)

    data["skills"] = new_skills
    return modified, json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def dedup_community_skill(filepath, stats):
    """Fix prefixed name in a SKILL.md frontmatter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if not content.startswith("---"):
        return False

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False

    head = parts[1]
    # Find name line
    lines = head.split('\n')
    modified = False
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*name:\s*)(.+)$', line)
        if m:
            name = m.group(2).strip()
            stripped, prefix = strip_prefix(name)
            if prefix:
                lines[i] = f"{m.group(1)}{stripped}"
                stats["prefixed_found"] += 1
                stats["renamed"] += 1
                stats["applied_renames"] += 1
                modified = True
            break

    if not modified:
        return False

    new_content = "---" + "\n".join(lines) + "---" + parts[2]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(description="Dedup prefixed skill names in capability trees")
    parser.add_argument("--execute", action="store_true", help="Write deduplicated files")
    ns = parser.parse_args()
    execute = ns.execute

    stats = defaultdict(int)

    # 1. Process YAML tree files
    tree_files = sorted(CAP_TREE_DIR.glob("tree*.yaml"))
    if not tree_files:
        print("❌ No tree files found in", CAP_TREE_DIR)
        sys.exit(1)

    print("=" * 60)
    print("📊 Skill Name Deduplication")
    print("=" * 60)
    print(f"   Prefixes: {KNOWN_PREFIXES}")
    print(f"   Tree files: {len(tree_files)}")
    print()

    for tf in tree_files:
        modified, new_text = dedup_yaml_file(tf, stats)
        status = "📄"
        if modified:
            status = "✏️"
        print(f"{status} {tf.name} (names: {stats['prefixed_found']} found so far)")

        if modified and execute:
            with open(tf, 'w', encoding='utf-8') as f:
                f.write(new_text)
            print(f"   ✅ Written")

    # 2. Process skills.json index files
    print()
    json_dirs = [DATA_DIR / "skill_top500", DATA_DIR / "skill_top1000"]
    for jd in json_dirs:
        sj = jd / "skills.json"
        if not sj.exists():
            continue
        with open(sj) as f:
            text = f.read()
        modified, new_text = dedup_skills_json_text(text, stats)
        print(f"📄 {sj.relative_to(REPO_DIR)}")
        if modified and execute:
            with open(sj, 'w') as f:
                f.write(new_text)
            print(f"   ✅ Written")

    # 3. Check community_skills/ frontmatter
    print()
    print("📂 community_skills/ frontmatter scan")
    cf_count = 0
    if COMMUNITY_DIR.exists():
        for d in sorted(os.listdir(COMMUNITY_DIR)):
            smd = COMMUNITY_DIR / d / "SKILL.md"
            if not smd.exists():
                continue
            if dedup_community_skill(smd, stats):
                print(f"   ✏️  {d}/SKILL.md")
                cf_count += 1
    if cf_count == 0:
        print("   ✅ No prefixed names found")

    # Summary
    print()
    print("=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(f"   Prefixed names found:   {stats['prefixed_found']}")
    print(f"   Deduped (dup removed):  {stats.get('deduped_removed', 0)}")
    print(f"   Renamed to canonical:   {stats.get('renamed', 0)}")
    print(f"   Applied renames:        {stats.get('applied_renames', 0)}")

    if not execute:
        print()
        print("   💡 Run with --execute to write deduplicated files")
    else:
        print()
        print("   ✅ All files updated")


if __name__ == "__main__":
    main()
