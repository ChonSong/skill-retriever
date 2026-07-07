"""
Dynamic Tree Schema - Generic tree node structure for multi-level hierarchy.
"""

from dataclasses import dataclass, field
from typing import Optional


# Fixed root categories for the first level of the capability tree
FIXED_ROOT_CATEGORIES = {
    "content-creation": {
        "name": "Content Creation",
        "description": "Content authoring tools including documents, images, presentations, and copywriting."
    },
    "data-processing": {
        "name": "Data Processing",
        "description": "Data analysis, visualization, and transformation tools."
    },
    "development": {
        "name": "Development",
        "description": "Developer tools including code generation, testing, and APIs."
    },
    "automation": {
        "name": "Automation",
        "description": "Browser automation, workflows, and integrations."
    },
    "domain-specific": {
        "name": "Domain Specific",
        "description": "Vertical domain tools for healthcare, finance, research, and other specialized fields."
    },
}


@dataclass
class DynamicTreeConfig:
    """
    Configuration for dynamic tree building and searching.

    Single parameter (branching_factor) derives all others using multiplicative factors.
    This ensures proper scaling as tree size grows.
    """

    branching_factor: int = 8  # Core parameter (5-12 recommended)
    max_depth: int = 6         # Soft limit, warn if exceeded

    # Incremental update settings
    rebalance_interval: int = 50  # Rebalance every N new skills

    # Derived properties - ALL use multiplication for proper scaling
    @property
    def max_skills_per_node(self) -> int:
        """Max skills before splitting. ~1.5x branching factor."""
        return int(self.branching_factor * 1.5)

    @property
    def expand_threshold(self) -> int:
        """Children <= this: expand all, else LLM select. ~0.7x branching factor."""
        return int(self.branching_factor * 0.7)

    @property
    def early_stop_skill_count(self) -> int:
        """If only 1 child selected and skills <= this, stop recursion. ~1.7x branching factor."""
        return int(self.branching_factor * 1.7)

    @property
    def lazy_split_threshold(self) -> int:
        """Immediate split if skills > this. ~1.3x max_skills_per_node."""
        return int(self.max_skills_per_node * 1.3)

    @property
    def classification_batch_size(self) -> int:
        """Skills per batch in scalable build. ~6x branching factor."""
        return self.branching_factor * 6

    @property
    def structure_sample_size(self) -> int:
        """Sample size for structure discovery. ~12x branching factor."""
        return self.branching_factor * 12


@dataclass
class Skill:
    """Skill information."""
    id: str
    name: str
    description: str = ""
    path: str = ""  # Path in tree, e.g., "content-creation/visual/design"
    skill_path: str = ""  # File path to SKILL.md
    content: str = ""  # Body content of SKILL.md
    selection_reason: str = ""  # Reason why this skill was selected
    # Metadata from skills.json
    github_url: str = ""
    stars: int = 0
    is_official: bool = False
    author: str = ""


@dataclass
class TreeNode:
    """
    Generic tree node that can represent any level in the hierarchy.

    - Intermediate nodes have children (no skills directly)
    - Leaf nodes have skills (no children)
    """
    id: str
    name: str
    description: str = ""

    # Children nodes (for intermediate nodes)
    children: list['TreeNode'] = field(default_factory=list)

    # Skills (for leaf nodes)
    skills: list[Skill] = field(default_factory=list)

    # Metadata
    depth: int = 0
    parent_id: Optional[str] = None

    # For lazy splitting
    pending_split: bool = False

    @property
    def is_leaf(self) -> bool:
        """Leaf node: has skills, no children."""
        return len(self.children) == 0

    @property
    def is_intermediate(self) -> bool:
        """Intermediate node: has children."""
        return len(self.children) > 0

    def count_all_skills(self) -> int:
        """Recursively count all skills in this subtree."""
        if self.is_leaf:
            return len(self.skills)
        return sum(child.count_all_skills() for child in self.children)

    def collect_all_skills(self) -> list[Skill]:
        """Recursively collect all skills in this subtree."""
        if self.is_leaf:
            return list(self.skills)

        result = []
        for child in self.children:
            result.extend(child.collect_all_skills())
        return result

    def get_leaf_nodes(self) -> list['TreeNode']:
        """Get all leaf nodes in this subtree."""
        if self.is_leaf:
            return [self]

        result = []
        for child in self.children:
            result.extend(child.get_leaf_nodes())
        return result

    def get_pending_split_nodes(self) -> list['TreeNode']:
        """Get all nodes marked for pending split."""
        result = []
        if self.pending_split:
            result.append(self)
        for child in self.children:
            result.extend(child.get_pending_split_nodes())
        return result

    def clear_pending_splits(self) -> None:
        """Clear all pending_split flags in this subtree."""
        self.pending_split = False
        for child in self.children:
            child.clear_pending_splits()

    def get_path(self) -> str:
        """Get path from root to this node."""
        # This is set during tree construction
        return self.id

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }

        if self.children:
            result["children"] = [c.to_dict() for c in self.children]

        if self.skills:
            result["skills"] = [
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
                for s in self.skills
            ]

        return result

    @classmethod
    def from_recursive_tree(cls, tree_dict: dict, depth: int = 0, parent_id: Optional[str] = None) -> 'TreeNode':
        """
        Convert from recursive tree format (id/name/description/children/skills)
        to TreeNode structure.
        """
        node = cls(
            id=tree_dict.get("id", "unknown"),
            name=tree_dict.get("name", ""),
            description=tree_dict.get("description", ""),
            depth=depth,
            parent_id=parent_id,
        )

        # Add children recursively
        for child_dict in tree_dict.get("children", []):
            child_node = cls.from_recursive_tree(child_dict, depth + 1, node.id)
            node.children.append(child_node)

        # Add skills
        for skill_dict in tree_dict.get("skills", []):
            skill = Skill(
                id=skill_dict.get("id", ""),
                name=skill_dict.get("name", ""),
                description=skill_dict.get("description", ""),
                path=node.id,
                skill_path=skill_dict.get("skill_path", ""),
                content=skill_dict.get("content", ""),
                github_url=skill_dict.get("github_url", ""),
                stars=skill_dict.get("stars", 0),
                is_official=skill_dict.get("is_official", False),
                author=skill_dict.get("author", ""),
            )
            node.skills.append(skill)

        return node

    @classmethod
    def from_capability_tree(cls, tree_dict: dict) -> 'TreeNode':
        """
        Convert from legacy capability tree format (domains/types/skills)
        to generic TreeNode structure.
        """
        root = cls(id="root", name="Root", description="Skill Tree Root")

        domains = tree_dict.get("domains", {})
        for domain_id, domain_data in domains.items():
            domain_node = cls(
                id=domain_id,
                name=domain_data.get("name", domain_id),
                description=domain_data.get("description", ""),
                depth=1,
                parent_id="root",
            )

            types = domain_data.get("types", {})
            for type_id, type_data in types.items():
                type_node = cls(
                    id=type_id,
                    name=type_data.get("name", type_id),
                    description=type_data.get("description", ""),
                    depth=2,
                    parent_id=domain_id,
                )

                # Add skills to type node
                for skill_data in type_data.get("skills", []):
                    skill = Skill(
                        id=skill_data.get("id", ""),
                        name=skill_data.get("name", ""),
                        description=skill_data.get("description", ""),
                        path=f"{domain_id}/{type_id}",
                        github_url=skill_data.get("github_url", ""),
                        stars=skill_data.get("stars", 0),
                        is_official=skill_data.get("is_official", False),
                        author=skill_data.get("author", ""),
                    )
                    type_node.skills.append(skill)

                domain_node.children.append(type_node)

            root.children.append(domain_node)

        return root


@dataclass
class SearchStep:
    """Record of a single search step."""
    level: int
    node_id: str
    options: list[str]  # Node IDs that were considered
    selected: list[str]  # Node IDs that were selected
    is_parallel: bool = False


@dataclass
class MultiLevelSearchResult:
    """Result from multi-level search."""
    query: str
    selected_skills: list[dict]

    # Search trace
    steps: list[SearchStep] = field(default_factory=list)

    # Statistics
    llm_calls: int = 0
    parallel_rounds: int = 0
    early_stops: int = 0
