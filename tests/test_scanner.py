"""Tests for skill_scanner.py — Hermes skill directory scanning."""

import tempfile
from pathlib import Path

# Ensure src/ is importable
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# The scanner is bundled inside the skill_retriever package
from skill_retriever._scanner_plugin import scan_hermes_skills, scan_skill_content


def test_scan_sample_skills():
    """Verify scanner extracts correct metadata from SKILL.md files."""
    fixtures = Path(__file__).parent / "fixtures" / "sample_skills"

    skills = scan_hermes_skills(fixtures)
    assert len(skills) == 1

    skill = skills[0]
    assert skill["name"] == "docker-patterns"
    assert skill["category"] == "devops"
    assert "Docker and Docker Compose patterns" in skill["description"]
    assert skill["id"] == "docker-patterns"
    assert skill["path"].endswith("SKILL.md")


def test_scan_empty_directory():
    """Verify scanner handles empty dirs gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills = scan_hermes_skills(Path(tmpdir))
        assert skills == []


def test_scan_missing_frontmatter():
    """Verify scanner handles SKILL.md without YAML frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "test-cat" / "no-fm"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Just markdown\n\nNo frontmatter here.\n")

        skills = scan_hermes_skills(Path(tmpdir))
        assert len(skills) == 1
        assert skills[0]["description"] == ""


def test_scan_dedup_duplicate_names():
    """Verify scanner deduplicates by name across categories."""
    fixtures = Path(__file__).parent / "fixtures" / "sample_skills"

    skills = scan_hermes_skills(fixtures)
    names = [s["name"] for s in skills]
    assert len(names) == len(set(names)), f"Duplicate names found: {names}"


def test_scan_skill_content():
    """Verify we can read full SKILL.md content for a named skill."""
    fixtures = Path(__file__).parent / "fixtures" / "sample_skills"

    content = scan_skill_content("docker-patterns", fixtures)
    assert content is not None
    assert "When to Use" in content
    assert content.startswith("---")


def test_scan_skill_content_missing():
    """Verify scan_skill_content returns None for missing skill."""
    fixtures = Path(__file__).parent / "fixtures" / "sample_skills"

    content = scan_skill_content("nonexistent-skill", fixtures)
    assert content is None
