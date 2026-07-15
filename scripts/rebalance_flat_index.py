#!/usr/bin/env python3
"""Rebalance — rebuild flat index from actual ~/.hermes/skills/ including all active canonical skills."""
import json
import os
import re
from pathlib import Path

SKILLS_DIR = Path.home() / ".hermes/skills"
ARCHIVED_DIR = SKILLS_DIR / "_archived"
FLAT_PATH = Path.home() / ".hermes/skill-retriever-cache/flat_index.json"


def extract_meta_from_skill_md(skill_dir):
    """Extract name + description from SKILL.md frontmatter."""
    md_path = skill_dir / "SKILL.md"
    if not md_path.exists():
        md_path = skill_dir / "skill.md"
    if not md_path.exists():
        name = skill_dir.name
        desc = ""
        # Try README.md as fallback
        readme = skill_dir / "README.md"
        if readme.exists():
            try:
                text = readme.read_text()[:1000]
                desc = text.split('\n\n')[0][:300] if text else ""
            except Exception:
                pass
        return name, desc, []

    try:
        text = md_path.read_text()
    except Exception:
        return skill_dir.name, "", []

    name = skill_dir.name
    desc = []
    tags = []
    in_desc = False
    desc_buf = []

    for line in text.split('\n'):
        line = line.strip()
        if line == '---':
            if in_desc:
                break
            in_desc = True
            continue
        if in_desc:
            m = re.match(r'^name:\s*(.*)', line)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                continue
            m = re.match(r'^description:\s*(.*)', line)
            if m:
                desc_buf.append(m.group(1).strip().strip('"').strip("'"))
                continue
            m = re.match(r'^tags?:\s*\[(.*)\]', line)
            if m:
                tags = [t.strip() for t in m.group(1).split(',') if t.strip()]
                continue
            m = re.match(r'^-\s*(.*)', line)
            if m:
                tags.append(m.group(1).strip())
                continue

    # Fallback: first non-empty non-header line
    if not desc_buf:
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                desc_buf.append(line)
                break

    return name, ' '.join(desc_buf)[:500], tags


def main():
    # Walk active skills
    skills = []
    for entry in sorted(os.listdir(SKILLS_DIR)):
        if entry.startswith('.') or entry == '_archived':
            continue
        skill_dir = SKILLS_DIR / entry
        if not skill_dir.is_dir():
            continue
        name, desc, tags = extract_meta_from_skill_md(skill_dir)
        skills.append({
            "name": name,
            "description": desc or f"Skill: {entry}",
            "path": str(skill_dir.relative_to(SKILLS_DIR.parent)),
            "tags": tags or entry.split('-'),
        })

    # Deduplicate
    by_name = {}
    for s in skills:
        n = s["name"]
        if n not in by_name or len(s["description"]) > len(by_name[n]["description"]):
            by_name[n] = s

    # Write flat index
    flat = sorted(by_name.values(), key=lambda x: x["name"])
    FLAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FLAT_PATH, "w") as f:
        json.dump(flat, f, indent=2)

    print(f"Rebalanced: {len(by_name)} skills → {FLAT_PATH}")

    # Report
    archived = set(os.listdir(ARCHIVED_DIR)) if ARCHIVED_DIR.exists() else set()
    archived_bases = {n.replace('affaan-m-', '').replace('sickn33-', '') for n in archived}
    active = set(by_name.keys())
    overlap = active & archived_bases
    print(f"  Overlap with archived (reversible): {len(overlap)}")


if __name__ == "__main__":
    main()
