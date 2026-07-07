"""
Skill Scanner - Scan skill_seeds directory and extract skill metadata.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ..config import PROJECT_ROOT

console = Console()


@dataclass
class ScannedSkill:
    """Scanned skill data from SKILL.md"""
    id: str
    name: str
    description: str
    skill_path: str
    content: str = ""  # Body content after frontmatter
    # Metadata from skills.json
    github_url: str = ""
    stars: int = 0
    is_official: bool = False
    author: str = ""


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from SKILL.md content.

    Returns: (frontmatter_dict, body_content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    # Simple YAML parsing (key: value format)
    frontmatter = {}
    for line in frontmatter_str.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            frontmatter[key] = value

    return frontmatter, body


class SkillScanner:
    """Scan skill_seeds directory and extract skill metadata."""

    def __init__(self, skills_dir: Path | str | None = None):
        """
        Initialize scanner.

        Args:
            skills_dir: Path to skill_seeds directory.
                       If None, uses default from config.
        """
        if skills_dir is None:
            from ..config import SKILLS_DIR
            self.skills_dir = SKILLS_DIR
        else:
            self.skills_dir = Path(skills_dir)

        # Load metadata from skills.json if available
        self._metadata: dict[str, dict] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """
        Load metadata from skills.json in skills directory if it exists.

        Populates self._metadata as dict mapping skill_id -> metadata dict.
        """
        metadata_path = self.skills_dir / "skills.json"
        if not metadata_path.exists():
            return

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for skill in data.get("skills", []):
                skill_id = skill.get("id", "")
                if skill_id:
                    self._metadata[skill_id] = {
                        "github_url": skill.get("github_url", ""),
                        "stars": skill.get("stars", 0),
                        "is_official": skill.get("is_official", False),
                        "author": skill.get("author", ""),
                    }
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load skills.json: {e}[/yellow]")

    def scan(self, show_progress: bool = True) -> list[ScannedSkill]:
        """
        Scan skills directory and extract name + description from each SKILL.md.

        Returns:
            List of ScannedSkill objects with id, name, description, skill_path
        """
        skills = []

        if not self.skills_dir.exists():
            console.print(f"[red]Skills directory not found: {self.skills_dir}[/red]")
            return skills

        # Get all subdirectories (excluding hidden)
        subdirs = [
            d for d in self.skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        if show_progress:
            skills = self._scan_with_progress(subdirs)
        else:
            skills = self._scan_simple(subdirs)

        # Sort by name
        skills.sort(key=lambda x: x.name.lower())

        if show_progress:
            console.print(f"[green]Found {len(skills)} skills in {self.skills_dir}[/green]")

        return skills

    def _scan_with_progress(self, subdirs: list[Path]) -> list[ScannedSkill]:
        """Scan with progress bar."""
        skills = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Scanning skill files..."),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total})"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning", total=len(subdirs))

            for skill_dir in subdirs:
                skill = self._scan_skill_dir(skill_dir)
                if skill:
                    skills.append(skill)
                progress.update(task, advance=1)

        return skills

    def _scan_simple(self, subdirs: list[Path]) -> list[ScannedSkill]:
        """Scan without progress bar (for testing)."""
        skills = []
        for skill_dir in subdirs:
            skill = self._scan_skill_dir(skill_dir)
            if skill:
                skills.append(skill)
        return skills

    def _scan_skill_dir(self, skill_dir: Path) -> ScannedSkill | None:
        """
        Scan a single skill directory.

        Returns:
            ScannedSkill if SKILL.md found, None otherwise
        """
        # Look for SKILL.md (case-insensitive)
        skill_file = None
        for name in ["SKILL.md", "skill.md", "Skill.md"]:
            candidate = skill_dir / name
            if candidate.exists():
                skill_file = candidate
                break

        if not skill_file:
            return None

        # Read and parse
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            console.print(f"[yellow]Failed to read {skill_file}: {e}[/yellow]")
            return None

        frontmatter, body = _parse_frontmatter(content)

        # Extract name (from frontmatter or directory name)
        name = frontmatter.get("name", skill_dir.name)

        # Extract description
        description = frontmatter.get("description", "")

        # If no description in frontmatter, use first paragraph of body
        if not description and body.strip():
            first_para = body.strip().split('\n\n')[0]
            # Clean up markdown formatting
            first_para = re.sub(r'^#+\s*', '', first_para)  # Remove headers
            first_para = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', first_para)  # Remove links
            description = first_para[:500]  # Limit length

        # Get metadata from skills.json if available
        skill_id = skill_dir.name
        meta = self._metadata.get(skill_id, {})

        # Always use absolute path for consistency
        skill_path_str = str(skill_file.resolve())

        return ScannedSkill(
            id=skill_id,  # Use directory name as ID
            name=name,
            description=description,
            skill_path=skill_path_str,
            content=body.strip(),  # Body content after frontmatter
            github_url=meta.get("github_url", ""),
            stars=meta.get("stars", 0),
            is_official=meta.get("is_official", False),
            author=meta.get("author", ""),
        )

    def to_dict_list(self, skills: list[ScannedSkill] | None = None) -> list[dict]:
        """
        Convert scanned skills to list of dicts.

        Args:
            skills: List of ScannedSkill objects. If None, scan first.

        Returns:
            List of dicts with id, name, description, skill_path
        """
        if skills is None:
            skills = self.scan()

        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "skill_path": s.skill_path,
                "content": s.content,
                "github_url": s.github_url,
                "stars": s.stars,
                "is_official": s.is_official,
                "author": s.author,
            }
            for s in skills
        ]


# Convenience function
def scan_skills(skills_dir: Path | str | None = None) -> list[dict]:
    """
    Convenience function to scan skills directory.

    Returns:
        List of dicts with id, name, description, skill_path
    """
    scanner = SkillScanner(skills_dir)
    return scanner.to_dict_list()
