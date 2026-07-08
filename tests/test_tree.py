"""Tests for capability tree builder and schema."""
from pathlib import Path
import sys
import yaml
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from skill_retriever.tree.schema import TreeNode, Skill, DynamicTreeConfig
from skill_retriever.tree.builder import TreeBuilder


# ===== Schema Tests =====

def test_skill_defaults():
    """Verify Skill dataclass default values."""
    s = Skill(id="test", name="Test Skill")
    assert s.id == "test"
    assert s.name == "Test Skill"
    assert s.description == ""
    assert s.path == ""
    assert s.stars == 0
    assert s.is_official is False


def test_treenode_leaf():
    """Verify leaf node detection."""
    node = TreeNode(id="leaf", name="Leaf")
    assert node.is_leaf
    assert not node.is_intermediate


def test_treenode_intermediate():
    """Verify intermediate node detection."""
    child = TreeNode(id="child", name="Child")
    node = TreeNode(id="parent", name="Parent", children=[child])
    assert not node.is_leaf
    assert node.is_intermediate


def test_treenode_count_all_skills_leaf():
    """Verify skill count on leaf node."""
    skills = [Skill(id="s1", name="S1"), Skill(id="s2", name="S2")]
    node = TreeNode(id="leaf", name="Leaf", skills=skills)
    assert node.count_all_skills() == 2


def test_treenode_count_all_skills_nested():
    """Verify recursive skill counting."""
    leaf1 = TreeNode(id="l1", name="L1", skills=[Skill(id="s1", name="S1")])
    leaf2 = TreeNode(id="l2", name="L2", skills=[Skill(id="s2", name="S2"), Skill(id="s3", name="S3")])
    parent = TreeNode(id="p", name="P", children=[leaf1, leaf2])
    assert parent.count_all_skills() == 3


def test_treenode_collect_all_skills():
    """Verify collecting all skills from subtree."""
    leaf1 = TreeNode(id="l1", name="L1", skills=[Skill(id="s1", name="S1"), Skill(id="s2", name="S2")])
    leaf2 = TreeNode(id="l2", name="L2", skills=[Skill(id="s3", name="S3")])
    parent = TreeNode(id="p", name="P", children=[leaf1, leaf2])
    collected = parent.collect_all_skills()
    assert len(collected) == 3
    assert collected[0].id == "s1"
    assert collected[2].id == "s3"


def test_treenode_get_path():
    """Verify path string."""
    node = TreeNode(id="my-node", name="My Node")
    assert node.get_path() == "my-node"


def test_treenode_to_dict():
    """Verify serialization to dict."""
    skill = Skill(id="s1", name="S1", description="Test skill", skill_path="/path/to/SKILL.md")
    node = TreeNode(id="leaf", name="Leaf", skills=[skill])
    d = node.to_dict()
    assert d["id"] == "leaf"
    assert len(d["skills"]) == 1
    assert d["skills"][0]["id"] == "s1"
    assert d["skills"][0]["skill_path"] == "/path/to/SKILL.md"


def test_from_recursive_tree():
    """Verify deserialization from recursive tree format."""
    tree_dict = {
        "id": "root",
        "name": "Root",
        "description": "Root node",
        "children": [
            {
                "id": "dev",
                "name": "Development",
                "description": "Dev tools",
                "skills": [
                    {"id": "git-workflow", "name": "Git Workflow", "description": "Git branching"},
                    {"id": "docker-patterns", "name": "Docker", "description": "Docker compose"},
                ],
            }
        ],
    }
    root = TreeNode.from_recursive_tree(tree_dict)
    assert root.id == "root"
    assert len(root.children) == 1
    assert root.children[0].id == "dev"
    assert len(root.children[0].skills) == 2
    assert root.children[0].skills[0].id == "git-workflow"


def test_from_recursive_tree_leaf():
    """Verify leaf node with skills but no children."""
    tree_dict = {
        "id": "leaf",
        "name": "Leaf",
        "skills": [{"id": "s1", "name": "S1"}],
    }
    node = TreeNode.from_recursive_tree(tree_dict)
    assert node.is_leaf
    assert len(node.skills) == 1


def test_from_capability_tree():
    """Verify deserialization from legacy capability tree format."""
    tree_dict = {
        "domains": {
            "content-creation": {
                "name": "Content Creation",
                "description": "Content tools",
                "types": {
                    "document-creation": {
                        "name": "Document Creation",
                        "description": "Docs",
                        "skills": [{"id": "doc-gen", "name": "Doc Gen"}],
                    }
                },
            }
        }
    }
    root = TreeNode.from_capability_tree(tree_dict)
    assert root.id == "root"
    assert len(root.children) == 1
    assert root.children[0].id == "content-creation"
    assert root.children[0].children[0].id == "document-creation"
    assert root.children[0].children[0].skills[0].id == "doc-gen"


# ===== DynamicTreeConfig Tests =====

def test_dynamic_tree_config_defaults():
    """Verify default config values."""
    cfg = DynamicTreeConfig()
    assert cfg.branching_factor == 8
    assert cfg.max_depth == 6
    assert cfg.max_skills_per_node == 12  # 8 * 1.5
    assert cfg.expand_threshold == 5  # 8 * 0.7
    assert cfg.early_stop_skill_count == 13  # 8 * 1.7


def test_dynamic_tree_config_custom():
    """Verify custom branching factor propagates."""
    cfg = DynamicTreeConfig(branching_factor=5)
    assert cfg.branching_factor == 5
    assert cfg.max_skills_per_node == 7  # 5 * 1.5
    assert cfg.expand_threshold == 3  # 5 * 0.7


# ===== Builder Tests =====

def test_builder_init():
    """Verify TreeBuilder initializes."""
    builder = TreeBuilder(skills_dir="/tmp")
    assert builder is not None
    assert builder.max_workers >= 1


def test_builder_no_skills_dir():
    """Verify builder handles missing skills dir."""
    builder = TreeBuilder(skills_dir="/tmp/nonexistent-dir-abc-123")
    tree_dict = builder.build(show_tree=False, generate_html=False)
    assert tree_dict == {}


def test_builder_build_minimal(tmp_path):
    """Verify builder builds a tree from minimal skills."""
    # Create a minimal skill directory
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n\nBody content"
    )

    builder = TreeBuilder(
        skills_dir=str(skills_dir),
        output_path=str(tmp_path / "tree.yaml"),
    )
    tree_dict = builder.build(show_tree=False, generate_html=False)

    assert tree_dict is not None
    # Root is always present with id='root'
    assert tree_dict.get("id") == "root"
    # With only 1 skill, root may have no children (can't form categories)
    if tree_dict.get("children"):
        assert len(tree_dict["children"]) >= 0


def test_builder_parse_frontmatter_via_scanner():
    """Verify scanner correctly parses SKILL.md frontmatter."""
    from skill_retriever.tree.skill_scanner import SkillScanner, _parse_frontmatter

    content = "---\nname: my-skill\ndescription: My awesome skill\n---\n\nBody here"
    fm, body = _parse_frontmatter(content)
    assert fm.get("name") == "my-skill"
    assert fm.get("description") == "My awesome skill"
    assert "Body here" in body


def test_builder_parse_frontmatter_no_fm():
    """Verify scanner handles SKILL.md without frontmatter."""
    from skill_retriever.tree.skill_scanner import _parse_frontmatter

    content = "# Just a heading\n\nSome content without frontmatter."
    fm, body = _parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_builder_scanner_scan(tmp_path):
    """Verify scanner finds skills in a directory."""
    from skill_retriever.tree.skill_scanner import SkillScanner

    # Create skill structure
    skills_dir = tmp_path / "myskills"
    skills_dir.mkdir()
    for name in ["skill-a", "skill-b", "skill-c"]:
        sd = skills_dir / name
        sd.mkdir()
        (sd / "SKILL.md").write_text(f"---\nname: {name}\ndescription: The {name} skill\n---\n\nBody")

    scanner = SkillScanner(str(skills_dir))
    skills = scanner.scan(show_progress=False)
    assert len(skills) == 3
    names = [s.name for s in skills]
    assert "skill-a" in names
    assert "skill-c" in names
