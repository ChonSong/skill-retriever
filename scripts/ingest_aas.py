#!/usr/bin/env python3
"""
Ingest AAS (Agentic Awesome Skills) into skill-retriever corpus.

Usage:
    python scripts/ingest_aas.py                          # dry-run: report what would happen
    python scripts/ingest_aas.py --execute                # actually copy skills
    python scripts/ingest_aas.py --execute --safe-only    # only permissively-licensed (MIT/Apache/BSD)
    python scripts/ingest_aas.py --execute --all          # copy all AAS skills (even unlicensed)
    python scripts/ingest_aas.py --execute --dry-run      # show what would happen without writing

Output:
    - data/aas_ingest_report.json  — full report of what was ingested/skipped
    - src/skill_retriever/community_skills/<name>/SKILL.md  — copied skills
    - Updates ship_safe_manifest.json
"""

import argparse
import json
import os
import shutil
import sys
import yaml
from collections import Counter
from datetime import datetime
from pathlib import Path

# Paths
REPO_DIR = Path(__file__).parent.parent.resolve()
AAS_DIR = REPO_DIR.parent / "aas-skills" / "skills"
OUR_SKILLS_DIR = REPO_DIR / "src" / "skill_retriever" / "community_skills"
HERMES_SKILLS_DIR = Path.home() / ".hermes" / "skills"
SHIP_MANIFEST = REPO_DIR / "data" / "ship_safe_manifest.json"
OUT_REPORT = REPO_DIR / "data" / "aas_ingest_report.json"

# License classifications
PERMISSIVE = {"mit", "apache-2.0", "bsd-3-clause", "bsd-3-clause license",
              "3-clause bsd license", "mit-0", "cc-by-4.0",
              "mit license", "apache-2.0 license", "bsd-3-clause license?"}
CAUTIOUS = {"unknown", "not declared"}


def load_existing_skills():
    """Build a set of (name_lower, source_lower) already in our corpus."""
    names = set()
    
    # From community skills
    if OUR_SKILLS_DIR.exists():
        for d in os.listdir(OUR_SKILLS_DIR):
            dpath = OUR_SKILLS_DIR / d
            smd = dpath / "SKILL.md"
            if dpath.is_dir() and smd.exists():
                names.add(d.lower())
                # Also check the frontmatter name
                meta = parse_frontmatter(smd)
                if meta and meta.get("name"):
                    names.add(meta["name"].strip().lower())
    
    # From hermes skills
    if HERMES_SKILLS_DIR.exists():
        for root, dirs, files in os.walk(HERMES_SKILLS_DIR):
            for f in files:
                if f == "SKILL.md":
                    rel = os.path.relpath(root, HERMES_SKILLS_DIR)
                    names.add(rel.lower())
                    meta = parse_frontmatter(Path(root) / "SKILL.md")
                    if meta and meta.get("name"):
                        names.add(meta["name"].strip().lower())
    
    return names


def parse_frontmatter(smd_path):
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        with open(smd_path) as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
    except Exception:
        pass
    return {}


def scan_aas_skills():
    """Scan AAS skills directory and return metadata for each skill."""
    skills = []
    errors = []
    
    for entry in sorted(os.listdir(AAS_DIR)):
        epath = AAS_DIR / entry
        if not epath.is_dir():
            continue
        
        # Check for SKILL.md in this directory
        smd = epath / "SKILL.md"
        if not smd.exists():
            # Check nested
            for sub in os.listdir(epath):
                subpath = epath / sub
                if subpath.is_dir() and (subpath / "SKILL.md").exists():
                    meta = parse_frontmatter(subpath / "SKILL.md")
                    skills.append({
                        "name": meta.get("name", entry) if meta else entry,
                        "dir_name": f"{entry}/{sub}",
                        "path": str(subpath / "SKILL.md"),
                        "license": (meta.get("license", "unknown") if meta else "unknown").lower(),
                        "source": meta.get("source", "community") if meta else "community",
                        "source_repo": meta.get("source_repo", "") if meta else "",
                        "risk": meta.get("risk", "unknown") if meta else "unknown",
                        "description": (meta.get("description", "") or "")[:200],
                    })
            continue
        
        meta = parse_frontmatter(smd)
        skills.append({
            "name": meta.get("name", entry) if meta else entry,
            "dir_name": entry,
            "path": str(smd),
            "license": (meta.get("license", "unknown") if meta else "unknown").lower(),
            "source": meta.get("source", "community") if meta else "community",
            "source_repo": meta.get("source_repo", "") if meta else "",
            "risk": meta.get("risk", "unknown") if meta else "unknown",
            "description": (meta.get("description", "") or "")[:200],
        })
    
    return skills, errors


def classify_license(license_str):
    """Return 'safe', 'cautious', or 'restricted' based on license string."""
    ls = license_str.strip().lower()
    if ls in PERMISSIVE:
        return "safe"
    if ls in CAUTIOUS or not ls:
        return "cautious"
    return "restricted"


def main():
    parser = argparse.ArgumentParser(description="Ingest AAS skills into skill-retriever")
    parser.add_argument("--execute", action="store_true", help="Actually copy files (default: dry-run)")
    parser.add_argument("--safe-only", action="store_true", help="Only copy permissively-licensed skills")
    parser.add_argument("--all", action="store_true", help="Copy all skills regardless of license")
    parser.add_argument("--dry-run", action="store_true", help="Print report without writing")
    args = parser.parse_args()
    
    if not args.execute and not args.dry_run:
        print("🔍 DRY RUN — pass --execute to actually ingest, or --dry-run for explicit dry-run")
        print()
    
    if not AAS_DIR.exists():
        print(f"❌ AAS skills directory not found at {AAS_DIR}")
        print("   Clone it first: git clone --depth 1 https://github.com/sickn33/agentic-awesome-skills.git aas-skills")
        sys.exit(1)
    
    print("=" * 60)
    print("📊 AAS Ingestion Analysis")
    print("=" * 60)
    
    # Load existing
    print("\n📂 Scanning existing corpus...")
    existing = load_existing_skills()
    print(f"   {len(existing)} existing skill names (community + hermes)")
    
    # Scan AAS
    print("\n📂 Scanning AAS skills...")
    aas_skills, errors = scan_aas_skills()
    print(f"   {len(aas_skills)} AAS skills found")
    if errors:
        print(f"   ⚠️  {len(errors)} errors: {errors[:3]}")
    
    # Classify
    deduped = 0
    new_safe = []
    new_cautious = []
    new_restricted = []
    
    for skill in aas_skills:
        name_lower = skill["name"].lower().strip()
        dir_lower = skill["dir_name"].lower().strip()
        
        # Dedup: check both name and dir_name
        if name_lower in existing or dir_lower in existing:
            deduped += 1
            continue
        
        lic_class = classify_license(skill["license"])
        if lic_class == "safe":
            new_safe.append(skill)
        elif lic_class == "cautious":
            new_cautious.append(skill)
        else:
            new_restricted.append(skill)
    
    print(f"\n📊 Dedup: {deduped} already in our corpus")
    print(f"📊 New skills: {len(new_safe) + len(new_cautious) + len(new_restricted)}")
    print(f"   ✅ Safe (MIT/Apache/BSD/CC-BY): {len(new_safe)}")
    print(f"   ⚠️  Cautious (unknown license): {len(new_cautious)}")
    print(f"   ❌ Restricted: {len(new_restricted)}")
    
    # Report per-license counts for new skills
    lic_counts = Counter()
    for skill in new_safe + new_cautious + new_restricted:
        lic_counts[skill["license"]] += 1
    print(f"\n📊 License breakdown for new skills:")
    for lic, count in lic_counts.most_common():
        tag = "✅" if classify_license(lic) == "safe" else "⚠️" if classify_license(lic) == "cautious" else "❌"
        print(f"   {tag} {lic}: {count}")
    
    # Source breakdown
    src_counts = Counter()
    for skill in new_safe + new_cautious + new_restricted:
        src = skill["source"][:40] if len(skill["source"]) > 40 else skill["source"]
        src_counts[src] += 1
    print(f"\n📊 Source breakdown for new skills:")
    for src, count in src_counts.most_common(10):
        print(f"   {src}: {count}")
    
    # === Ingestion ===
    copied = 0
    if args.execute and not args.dry_run:
        print(f"\n{'='*60}")
        print("📝 Ingestion phase")
        print(f"{'='*60}")
        
        # Determine which skills to copy
        if args.all:
            to_copy = new_safe + new_cautious + new_restricted
            print(f"   Mode: ALL (including unlicensed)")
        elif args.safe_only:
            to_copy = new_safe
            print(f"   Mode: SAFE ONLY (MIT/Apache/BSD)")
        else:
            to_copy = new_safe + new_cautious
            print(f"   Mode: SAFE + CAUTIOUS (skipping restricted)")
        
        print(f"   Copying {len(to_copy)} skills to community_skills/...")
        
        copied = 0
        skipped_existing = 0
        errors_copy = []
        
        for skill in to_copy:
            target_dir = OUR_SKILLS_DIR / skill["dir_name"]
            if target_dir.exists():
                skipped_existing += 1
                continue
            
            # Read the actual SKILL.md content from AAS
            src_path = REPO_DIR.parent / "aas-skills" / skill["path"]
            if not src_path.exists():
                errors_copy.append(f"Source not found: {skill['path']}")
                continue
            
            # Create target dir and copy
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, target_dir / "SKILL.md")
            copied += 1
        
        print(f"   ✅ Copied: {copied}")
        print(f"   ⏭️  Skipped (already exists): {skipped_existing}")
        if errors_copy:
            print(f"   ❌ Errors: {len(errors_copy)}")
            for e in errors_copy[:3]:
                print(f"       {e}")
        
        # Update manifest
        print(f"\n📝 Updating ship_safe_manifest.json...")
        manifest = {}
        if SHIP_MANIFEST.exists():
            with open(SHIP_MANIFEST) as f:
                manifest = json.load(f)
        
        manifest["aas_ingested_at"] = datetime.utcnow().isoformat()
        manifest["aas_ingested_count"] = copied
        manifest["aas_mode"] = "all" if args.all else ("safe_only" if args.safe_only else "safe+cautious")
        
        with open(SHIP_MANIFEST, "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"   ✅ Manifest updated")
    
    # Write report
    print(f"\n📝 Writing report to {OUT_REPORT}...")
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "existing_skill_names": len(existing),
        "aas_total": len(aas_skills),
        "deduped": deduped,
        "new_safe": len(new_safe),
        "new_cautious": len(new_cautious),
        "new_restricted": len(new_restricted),
        "new_total": len(new_safe) + len(new_cautious) + len(new_restricted),
        "license_breakdown": dict(lic_counts),
        "source_breakdown": dict(src_counts.most_common(20)),
        "safe_skills": [{"name": s["name"], "dir": s["dir_name"], "license": s["license"], "source": s["source"]} for s in new_safe],
        "cautious_skills": [{"name": s["name"], "dir": s["dir_name"], "license": s["license"], "source": s["source"]} for s in new_cautious],
        "restricted_skills": [{"name": s["name"], "dir": s["dir_name"], "license": s["license"], "source": s["source"]} for s in new_restricted],
    }
    
    with open(OUT_REPORT, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"   ✅ Report written")
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 SUMMARY")
    print(f"{'='*60}")
    print(f"   Current corpus: ~{len(existing)} skill names")
    print(f"   AAS total:      {len(aas_skills)} skills")
    print(f"   New to us:      {len(new_safe) + len(new_cautious) + len(new_restricted)}")
    print(f"     - Safe:       {len(new_safe)}")
    print(f"     - Cautious:   {len(new_cautious)}")
    print(f"     - Restricted: {len(new_restricted)}")
    print(f"   Already have:   {deduped}")
    
    if args.execute and not args.dry_run:
        print(f"\n   ✅ Ingestion complete — {copied} skills copied to community_skills/")
        print(f"   ⏭️  Next: rebuild embedding index + capability tree")
    else:
        print(f"\n   💡 Run with --execute --safe-only to copy permissively-licensed skills")
        print(f"      Or --execute --all to copy everything including unlicensed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
