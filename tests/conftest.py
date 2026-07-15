"""Test configuration and fixtures for skill-retriever."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def tmp_flat_index(tmp_path):
    """Create a temporary flat index for testing."""
    index = [
        {
            "name": "test-skill-alpha",
            "description": "A test skill for alpha scenarios with Docker and testing keywords",
            "path": "/tmp/test-skills/alpha",
            "tags": ["testing", "devops"],
            "skill_id": "test-alpha-001",
        },
        {
            "name": "test-skill-beta",
            "description": "A test skill for beta scenarios with React and frontend keywords",
            "path": "/tmp/test-skills/beta",
            "tags": ["frontend", "react"],
            "skill_id": "test-beta-002",
        },
        {
            "name": "test-skill-gamma",
            "description": "A test skill for gamma scenarios with FastAPI and backend",
            "path": "/tmp/test-skills/gamma",
            "tags": ["backend", "api"],
            "skill_id": "test-gamma-003",
        },
    ]
    index_path = tmp_path / "flat_index.json"
    index_path.write_text(json.dumps(index))
    return index_path


@pytest.fixture
def sample_skills_dir(tmp_path):
    """Create a skills directory for integration tests."""
    skills = tmp_path / "test_skills"
    skills.mkdir()
    docker = skills / "docker-patterns"
    docker.mkdir()
    docker.joinpath("SKILL.md").write_text("---\nname: docker-patterns\n---\nDocker patterns")
    return skills


@pytest.fixture
def mock_flat_index(tmp_flat_index):
    """Patch flat index path to use the test fixture."""
    from skill_retriever.compose import FLAT_INDEX_PATH

    with patch.object(FLAT_INDEX_PATH, "exists", return_value=True):
        with patch("skill_retriever.compose.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = lambda *args: None
            mock_open.return_value.read.return_value = tmp_flat_index.read_text()
            yield tmp_flat_index
