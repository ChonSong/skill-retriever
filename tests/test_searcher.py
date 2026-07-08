"""Tests for skill_retriever searcher — tree loading and search basics."""
from pathlib import Path
import sys

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from skill_retriever.search.searcher import Searcher, SearchResult


def test_searcher_imports():
    """Verify Searcher and SearchResult are importable."""
    assert Searcher is not None
    assert SearchResult is not None


def test_searcher_init():
    """Verify searcher initializes without tree (tree loads lazily on search)."""
    s = Searcher(tree_path="/nonexistent/tree.yaml")
    assert s is not None
    assert s.model is not None
    assert s.max_parallel >= 1


def test_searcher_load_tree_bundled():
    """Verify the bundled tree.yaml is loadable."""
    tree_path = (
        Path(__file__).parent.parent
        / "src"
        / "skill_retriever"
        / "capability_tree"
        / "tree.yaml"
    )
    if not tree_path.exists():
        # Try top1000 as fallback
        tree_path = (
            Path(__file__).parent.parent
            / "src"
            / "skill_retriever"
            / "capability_tree"
            / "tree_top1000.yaml"
        )

    if not tree_path.exists():
        # No bundled tree — skip this test
        return

    s = Searcher(tree_path=str(tree_path))
    tree = s._load_tree()
    assert tree is not None
    assert tree.id is not None
    # Tree should have at least root with some children or skills
    assert tree.count_all_skills() > 0 or len(tree.children) > 0


def test_searcher_load_tree_nonexistent():
    """Verify searcher handles missing tree gracefully."""
    s = Searcher(tree_path="/tmp/nonexistent-tree-abc123.yaml")
    tree = s._load_tree()
    assert tree is None


def test_searcher_search_no_tree():
    """Verify search on missing tree returns empty result, doesn't crash."""
    s = Searcher(tree_path="/tmp/nonexistent-tree-abc123.yaml")
    result = s.search("test query")
    assert isinstance(result, SearchResult)
    assert result.selected_skills == []


def test_searcher_search_empty_query():
    """Verify search handles empty query."""
    bundle_tree = (
        Path(__file__).parent.parent
        / "src"
        / "skill_retriever"
        / "capability_tree"
        / "tree.yaml"
    )
    if not bundle_tree.exists():
        bundle_tree = (
            Path(__file__).parent.parent
            / "src"
            / "skill_retriever"
            / "capability_tree"
            / "tree_top1000.yaml"
        )

    if not bundle_tree.exists():
        return

    s = Searcher(tree_path=str(bundle_tree))
    result = s.search("")
    assert isinstance(result, SearchResult)
    # Empty query should return empty results
    assert result.selected_skills == []


def test_event_callback():
    """Verify event callback is invoked during search lifecycle."""
    tree_path = (
        Path(__file__).parent.parent
        / "src"
        / "skill_retriever"
        / "capability_tree"
        / "tree.yaml"
    )
    if not tree_path.exists():
        tree_path = (
            Path(__file__).parent.parent
            / "src"
            / "skill_retriever"
            / "capability_tree"
            / "tree_top1000.yaml"
        )
    if not tree_path.exists():
        return

    events = []

    def callback(event_type, data):
        events.append((event_type, data))

    s = Searcher(tree_path=str(tree_path), event_callback=callback)
    s.search("test")
    assert len(events) > 0
    event_types = [e[0] for e in events]
    assert "search_start" in event_types
    assert "search_complete" in event_types
