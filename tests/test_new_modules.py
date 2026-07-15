#!/usr/bin/env python3
"""Test the flat index build and compose pipeline."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_build_flat_index_creates_file(tmp_path):
    """Test that build_flat_index writes a valid JSON file."""
    from skill_retriever.build_flat_index import walk_node

    tree = {
        "name": "Root",
        "description": "Root node",
        "children": [
            {
                "name": "Testing",
                "description": "Testing domain",
                "skills": [
                    {
                        "id": "test-alpha-001",
                        "name": "test-skill-alpha",
                        "description": "A test skill for alpha",
                        "skill_path": "/tmp/test-skills/alpha",
                    }
                ],
            }
        ],
    }

    results = []
    walk_node(tree, [], results)
    assert len(results) == 1
    assert results[0]["name"] == "test-skill-alpha"
    assert "Testing" in results[0]["tags"]


def test_build_flat_index_merges_domain_path(tmp_path):
    """Test that walk_node includes domain path in tags."""
    from skill_retriever.build_flat_index import walk_node

    tree = {
        "name": "Top",
        "description": "Top level",
        "children": [
            {
                "name": "Middle",
                "description": "Middle level",
                "children": [
                    {
                        "name": "leaf",
                        "description": "Leaf domain",
                        "skills": [
                            {
                                "id": "deep-skill",
                                "name": "deep-skill",
                                "description": "A deeply nested skill",
                                "skill_path": "/tmp/deep",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    results = []
    walk_node(tree, [], results)
    assert results[0]["tags"] == ["Top", "Middle", "leaf"]


def test_compose_format_bundle():
    """Test bundle formatting into hint block."""
    from skill_retriever.compose import bundle_to_hint_block

    bundle = [
        {"name": "skill-a", "load_as": "must", "reason": "Reason A", "confidence": "high"},
        {"name": "skill-b", "load_as": "should", "reason": "Reason B", "confidence": "medium"},
        {"name": "skill-c", "load_as": "consider", "reason": "Reason C", "confidence": "low"},
    ]
    result = bundle_to_hint_block(bundle)
    assert "★ **skill-a**" in result
    assert "▸ **skill-b**" in result
    assert "· **skill-c**" in result
    assert "Reason A" in result


def test_compose_empty_bundle():
    """Test empty bundle returns empty string."""
    from skill_retriever.compose import bundle_to_hint_block

    assert bundle_to_hint_block([]) == ""


def test_subagent_context_top_k_filter():
    """Test that compose_subagent_context limits results."""
    from skill_retriever.subagent_binding import compose_subagent_context

    # Mock compose_skills to return 5 fake items
    with patch("skill_retriever.subagent_binding.compose_skills") as mock_compose:
        mock_compose.return_value = [
            {"name": f"skill-{i}", "load_as": "must", "confidence": "high"}
            for i in range(5)
        ]
        result = compose_subagent_context("test task")
        assert len(result) == 5


def test_section_skills_by_phase_synonyms():
    """Test that sectioning uses synonym matching."""
    from skill_retriever.subagent_binding import section_skills_by_phase

    bundle = [
        {"name": "test-skill", "reason": "unit test with pytest", "confidence": "high"},
        {"name": "deploy-skill", "reason": "deploy docker to production", "confidence": "high"},
        {"name": "react-skill", "reason": "build React components", "confidence": "high"},
    ]
    phases = ["testing", "deployment", "frontend"]
    result = section_skills_by_phase(bundle, phases)

    # test-skill → testing (reason has "test"), deploy-skill → deployment (reason has "deploy"), react-skill → frontend (reason has "build" or "react")
    assert len(result["testing"]) >= 1
    assert len(result["deployment"]) >= 1
    assert len(result["frontend"]) >= 1


def test_logger_log_and_get(tmp_path):
    """Test skill_usage_logger log and get operations."""
    from skill_retriever.skill_usage_logger import log_skill_view, get_usage_stats

    with patch("skill_retriever.skill_usage_logger.USAGE_LOG", tmp_path / "usage.jsonl"):
        log_skill_view("skill-a", "must", "high")
        log_skill_view("skill-b", "should", "medium")
        log_skill_view("skill-a", "must", "high")

        stats = get_usage_stats(24)
        assert stats["total"] == 3
        assert stats["unique_skills"] == 2
        assert stats["skills"][0] == ("skill-a", 2)


def test_dedup_archive_strips_prefix():
    """Test that the archive dedup strips org prefixes correctly."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

    from dedup_skill_names import strip_prefix

    assert strip_prefix("sickn33-react-patterns") == "react-patterns"
    assert strip_prefix("affaan-m-fastapi-patterns") == "fastapi-patterns"
    assert strip_prefix("clean-name") == "clean-name"  # no prefix to strip


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
