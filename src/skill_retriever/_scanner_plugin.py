"""Skill scanner — reads Hermes ~/.hermes/skills/ and produces skill_retriever-compatible metadata.

Usage:
    from skill_scanner import scan_hermes_skills
    skills = scan_hermes_skills()
    # Returns list[dict] with keys: id, name, description, category, path
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)

EXCLUDED_SKILL_DIRS = frozenset((
    ".git", ".github", ".hub", ".archive",
    ".venv", "venv", "node_modules",
    "__pycache__", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
))


def scan_hermes_skills(skills_dir: Path | None = None) -> List[Dict[str, Any]]:
    """Scan Hermes skill directories and extract metadata.

    Reads every SKILL.md in ~/.hermes/skills/ and
    ~/.hermes/hermes-agent/skills/ (when installed from source),
    extracting name, description, and category from YAML frontmatter.

    Args:
        skills_dir: Optional override for testing. When None, scans
                    ~/.hermes/skills/ and ~/.hermes/hermes-agent/skills/.

    Returns:
        List of skill metadata dicts with keys:
        - id: skill directory name (unique identifier)
        - name: skill name from frontmatter or dir name
        - description: one-line description
        - category: parent directory name
        - path: absolute path to SKILL.md
        - triggers: list of trigger keywords (from frontmatter, if any)
    """
    if skills_dir is not None:
        skill_dirs = [skills_dir]
    else:
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        skill_dirs = [
            hermes_home / "skills",
            hermes_home / "hermes-agent" / "skills",
        ]

    skills: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for base_dir in skill_dirs:
        if not base_dir.exists():
            logger.debug("skill_scanner: dir not found: %s", base_dir)
            continue

        for cat_dir in sorted(base_dir.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue
            if cat_dir.name in EXCLUDED_SKILL_DIRS:
                continue

            category = cat_dir.name

            for skill_dir in sorted(cat_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue

                # Look for SKILL.md (supports both top-level and category-nested layouts)
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue

                name = skill_dir.name
                if name in seen:
                    continue
                seen.add(name)

                content = skill_md.read_text(encoding="utf-8")
                description, triggers = _parse_frontmatter(content)

                skills.append({
                    "id": name,
                    "name": name,
                    "description": description or "",
                    "category": category,
                    "path": str(skill_md),
                    "triggers": triggers,
                })

    logger.info("skill_scanner: found %d skills in %d directories", len(skills), len(skill_dirs))
    return skills


def _parse_frontmatter(content: str) -> tuple[str, list[str]]:
    """Parse YAML frontmatter from SKILL.md content.

    Returns:
        (description, triggers) tuple. description is empty string if not found.
    """
    if not content.startswith("---"):
        return "", []

    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", []

    try:
        fm = yaml.safe_load(parts[1])
        if not fm or not isinstance(fm, dict):
            return "", []

        description = fm.get("description", "")
        triggers = fm.get("triggers", [])
        if not isinstance(triggers, list):
            triggers = []

        return description, triggers
    except yaml.YAMLError:
        logger.debug("skill_scanner: failed to parse frontmatter")
        return "", []


def scan_skill_content(skill_name: str, skills_dir: Path | None = None) -> str | None:
    """Read the full SKILL.md content for a named skill.

    Args:
        skill_name: Skill directory name (e.g. 'docker-patterns')
        skills_dir: Optional override for testing.

    Returns:
        Full SKILL.md text, or None if not found.
    """
    if skills_dir is not None:
        search_dirs = [skills_dir]
    else:
        hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        search_dirs = [
            hermes_home / "skills",
            hermes_home / "hermes-agent" / "skills",
        ]

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for cat_dir in base_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            skill_md = cat_dir / skill_name / "SKILL.md"
            if skill_md.exists():
                return skill_md.read_text(encoding="utf-8")

    return None
