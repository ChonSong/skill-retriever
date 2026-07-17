#!/home/sc/.hermes/venv/bin/python3
"""Enrich flat index with quality signals from SKILL.md files.

Run this after rebalance to tag skills with has_steps, has_verification, has_pitfalls.
This enables the quality floor penalty in compose_skills().
"""
import json
import re
from pathlib import Path

FLAT_PATH = Path.home() / ".hermes/skill-retriever-cache/flat_index.json"
SKILLS_DIR = Path.home() / ".hermes/skills"


def check_quality(skill_dir):
    """Check quality signals from a SKILL.md file."""
    md = skill_dir / "SKILL.md"
    if not md.exists():
        md = skill_dir / "skill.md"
    if not md.exists():
        return {}
    try:
        content = md.read_text(errors="ignore")
    except Exception:
        return {}

    has_steps = bool(re.search(r"(?i)##?\s*(steps?|how|usage|example)", content))
    has_pitfalls = bool(re.search(r"(?i)##?\s*(pitfall|warning|caution|troubleshoot)", content))
    has_verification = bool(re.search(r"(?i)##?\s*(verify|test|check|validate)", content))
    return {"has_steps": has_steps, "has_pitfalls": has_pitfalls, "has_verification": has_verification}


def main():
    if not FLAT_PATH.exists():
        print(f"Flat index not found: {FLAT_PATH}")
        return 1

    with open(FLAT_PATH) as f:
        flat = json.load(f)

    enriched = 0
    for entry in flat:
        name = entry.get("name", "")
        # Find matching skill dir (try direct match first, then case-insensitive)
        skill_dir = None
        direct = SKILLS_DIR / name
        if direct.is_dir():
            skill_dir = direct
        else:
            for d in SKILLS_DIR.iterdir():
                if not d.is_dir() or d.name.startswith(".") or d.name == "_archived":
                    continue
                if d.name.lower() == name.lower():
                    skill_dir = d
                    break

        if skill_dir:
            quality = check_quality(skill_dir)
            if any(quality.values()):
                entry["_quality"] = quality
                enriched += 1

    with open(FLAT_PATH, "w") as f:
        json.dump(flat, f, indent=2)

    print(f"Enriched {enriched}/{len(flat)} skills with quality signals")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
