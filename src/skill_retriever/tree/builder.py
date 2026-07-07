"""
Tree Builder - Build capability tree from skills using LLM classification.

Two-phase build process:
1. Structure Discovery: Sample skills to discover domain/type structure
2. Anchored Classification: Classify remaining skills into discovered structure
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from typing import Optional

import litellm
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.tree import Tree as RichTree

from ..config import (
    LLM_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    BRANCHING_FACTOR,
    TREE_BUILD_MAX_WORKERS,
    TREE_BUILD_CACHING,
    TREE_BUILD_NUM_RETRIES,
    TREE_BUILD_TIMEOUT,
    MAX_DEPTH,
    ensure_cache,
)
from .schema import DynamicTreeConfig, TreeNode, Skill, FIXED_ROOT_CATEGORIES
from .skill_scanner import SkillScanner
from .prompts import RECURSIVE_SPLIT_PROMPT, FIXED_CATEGORY_ASSIGNMENT_PROMPT

# litellm._turn_on_debug()

console = Console()

# Default output path
DEFAULT_TREE_PATH = Path(__file__).parent.parent / "capability_tree" / "tree.yaml"


class TreeBuilder:
    """
    Unified tree builder with auto-selection and node splitting.

    Features:
    - Auto-selects build method based on skill count
    - Splits oversized nodes (> max_skills_per_node)
    - Simple tree visualization
    """

    def __init__(
        self,
        skills_dir: Path | str | None = None,
        output_path: Path | str | None = None,
        config: Optional[DynamicTreeConfig] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_workers: Optional[int] = None,
    ):
        self.scanner = SkillScanner(skills_dir)
        self.output_path = Path(output_path) if output_path else DEFAULT_TREE_PATH
        self.config = config or DynamicTreeConfig(branching_factor=BRANCHING_FACTOR, max_depth=MAX_DEPTH)
        self.model = model or LLM_MODEL
        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.max_workers = max_workers or TREE_BUILD_MAX_WORKERS

        self._llm_calls = 0
        self._leaf_skills = 0  # Skills that have reached leaf nodes
        self._progress = None  # Rich progress bar
        self._progress_task = None
        ensure_cache()

    def build(self, verbose: bool = False, show_tree: bool = True, generate_html: bool = True) -> dict:
        """
        Build capability tree from skill_seeds.

        Args:
            verbose: Print detailed progress
            show_tree: Display tree after building
            generate_html: Generate HTML visualization

        Returns:
            Tree dict structure
        """
        console.print(Panel.fit(
            "[bold cyan]Building Capability Tree[/bold cyan]",
            border_style="cyan",
        ))

        # Step 1: Scan skills
        console.print("\n[bold]Step 1: Scanning skills...[/bold]")
        skills = self.scanner.to_dict_list()

        if not skills:
            console.print("[red]No skills found.[/red]")
            return {}

        console.print(f"[green]Found {len(skills)} skills[/green]")

        # Step 2: Build tree with auto-selection
        console.print("\n[bold]Step 2: Building tree structure...[/bold]")
        tree = self._build_tree(skills, verbose)

        # Step 3: Convert to dict and write
        console.print("\n[bold]Step 3: Writing to file...[/bold]")
        tree_dict = self._tree_to_dict(tree)
        self._write_yaml(tree_dict)

        # Step 4: Generate HTML visualization
        if generate_html:
            from .visualizer import generate_html as gen_html
            html_path = self.output_path.with_suffix('.html')
            gen_html(tree_dict, html_path)
            console.print(f"[green]Generated HTML: {html_path}[/green]")

        # Show tree
        if show_tree:
            console.print("\n[bold]Tree Structure:[/bold]")
            self._print_tree(tree_dict)

        console.print(Panel.fit(
            f"[bold green]Done![/bold green] ({self._llm_calls} LLM calls)\n"
            f"Output: {self.output_path}",
            border_style="green",
        ))

        return tree_dict

    def _build_tree(self, skills: list[dict], verbose: bool = False) -> TreeNode:
        """Build tree using queue-based parallel approach (no recursion)."""
        root = TreeNode(id="root", name="Root", description="Skill capability tree root")

        # Queue: (node, skills, depth, parent_context)
        queue = [(root, skills, 0, None)]
        futures_map = {}  # future -> (node, depth)

        total_skills = len(skills)
        self._leaf_skills = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("({task.fields[leaf]}/{task.fields[total_count]} skills done, {task.fields[llm]} LLM, {task.fields[pending]} pending)"),
            console=console,
            transient=False,
        ) as progress:
            self._progress = progress
            self._progress_task = progress.add_task("Building tree...", total=total_skills, pending=0, leaf=0, llm=0, total_count=total_skills)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while queue or futures_map:
                    # Submit all queued tasks
                    while queue:
                        node, node_skills, depth, parent_context = queue.pop(0)
                        future = executor.submit(
                            self._process_node,
                            node=node,
                            skills=node_skills,
                            depth=depth,
                            parent_context=parent_context,
                            verbose=verbose,
                        )
                        futures_map[future] = (node, depth)

                    # Update pending count
                    if self._progress and self._progress_task is not None:
                        self._progress.update(self._progress_task, pending=len(futures_map))

                    if not futures_map:
                        break

                    # Wait for at least one to complete
                    done, _ = wait(futures_map.keys(), return_when=FIRST_COMPLETED)

                    # Process completed futures
                    for future in done:
                        node, depth = futures_map.pop(future)
                        try:
                            children_to_process = future.result()
                            # Add children to queue
                            for child_node, child_skills in children_to_process:
                                parent_ctx = {"name": child_node.name, "description": child_node.description}
                                queue.append((child_node, child_skills, depth + 1, parent_ctx))
                        except Exception as e:
                            console.print(f"[red]Error processing {node.id}: {e}[/red]")

            self._progress = None

        return root

    def _process_node(
        self,
        node: TreeNode,
        skills: list[dict],
        depth: int,
        parent_context: Optional[dict],
        verbose: bool = False,
    ) -> list[tuple[TreeNode, list[dict]]]:
        """
        Process a single node: split skills and create children.
        Returns list of (child_node, child_skills) tuples for further processing.
        """
        # Special handling for root node: use fixed categories
        if depth == 0 and node.id == "root":
            return self._process_root_with_fixed_categories(node, skills, verbose)

        # Terminal condition: skills count within threshold
        if len(skills) <= self.config.max_skills_per_node:
            for skill_data in skills:
                skill = Skill(
                    id=skill_data["id"],
                    name=skill_data.get("name", skill_data["id"]),
                    description=skill_data.get("description", ""),
                    path=node.id,
                    skill_path=skill_data.get("skill_path", ""),
                    content=skill_data.get("content", ""),
                    github_url=skill_data.get("github_url", ""),
                    stars=skill_data.get("stars", 0),
                    is_official=skill_data.get("is_official", False),
                    author=skill_data.get("author", ""),
                )
                node.skills.append(skill)
            # Update leaf skills count
            self._leaf_skills += len(skills)
            if self._progress and self._progress_task is not None:
                self._progress.update(self._progress_task, leaf=self._leaf_skills, completed=self._leaf_skills)
            if verbose:
                console.print(f"[dim]  Leaf: {node.id} ({len(skills)} skills)[/dim]")
            return []

        # Depth limit check
        if depth >= self.config.max_depth:
            if verbose:
                console.print(f"[yellow]Warning: max depth reached at {node.id}, forcing leaf[/yellow]")
            for skill_data in skills:
                skill = Skill(
                    id=skill_data["id"],
                    name=skill_data.get("name", skill_data["id"]),
                    description=skill_data.get("description", ""),
                    path=node.id,
                    skill_path=skill_data.get("skill_path", ""),
                    content=skill_data.get("content", ""),
                    github_url=skill_data.get("github_url", ""),
                    stars=skill_data.get("stars", 0),
                    is_official=skill_data.get("is_official", False),
                    author=skill_data.get("author", ""),
                )
                node.skills.append(skill)
            # Update leaf skills count
            self._leaf_skills += len(skills)
            if self._progress and self._progress_task is not None:
                self._progress.update(self._progress_task, leaf=self._leaf_skills, completed=self._leaf_skills)
            return []

        # LLM grouping
        if self._progress and self._progress_task is not None:
            self._progress.update(self._progress_task, description=f"Splitting: {node.id} ({len(skills)} skills)")
        if verbose:
            console.print(f"[cyan]Splitting: {node.id} ({len(skills)} skills, depth={depth})[/cyan]")

        groups = self._split_skills(skills, parent_context, verbose)

        if not groups:
            # Grouping failed, make it a leaf
            if verbose:
                console.print(f"[yellow]Grouping failed for {node.id}, forcing leaf[/yellow]")
            for skill_data in skills:
                skill = Skill(
                    id=skill_data["id"],
                    name=skill_data.get("name", skill_data["id"]),
                    description=skill_data.get("description", ""),
                    path=node.id,
                    skill_path=skill_data.get("skill_path", ""),
                    content=skill_data.get("content", ""),
                    github_url=skill_data.get("github_url", ""),
                    stars=skill_data.get("stars", 0),
                    is_official=skill_data.get("is_official", False),
                    author=skill_data.get("author", ""),
                )
                node.skills.append(skill)
            return []

        # Build skill map
        skill_map = {s["id"]: s for s in skills}

        # Create child nodes
        children_to_process = []
        for group_id, group_data in groups.items():
            child_skill_ids = group_data.get("skill_ids", [])
            child_skills = [skill_map[sid] for sid in child_skill_ids if sid in skill_map]

            if len(child_skills) < 2:
                continue

            child_node = TreeNode(
                id=group_id,
                name=group_data.get("name", group_id),
                description=group_data.get("description", ""),
                depth=depth + 1,
                parent_id=node.id,
            )

            node.children.append(child_node)

            # Mark assigned skills
            for sid in child_skill_ids:
                skill_map.pop(sid, None)

            children_to_process.append((child_node, child_skills))

        # Handle unassigned skills (assign to largest child group)
        if skill_map and children_to_process:
            # Find the child with most skills
            largest_idx = max(range(len(children_to_process)), key=lambda i: len(children_to_process[i][1]))
            unassigned = list(skill_map.values())
            if verbose:
                console.print(f"[yellow]  {len(unassigned)} unassigned skills -> {children_to_process[largest_idx][0].id}[/yellow]")

            # Add unassigned to largest child
            child_node, child_skills = children_to_process[largest_idx]
            children_to_process[largest_idx] = (child_node, child_skills + unassigned)

        return children_to_process

    def _process_root_with_fixed_categories(
        self,
        node: TreeNode,
        skills: list[dict],
        verbose: bool = False,
    ) -> list[tuple[TreeNode, list[dict]]]:
        """
        Process root node using fixed categories.
        Uses LLM to assign skills to predefined categories, then creates child nodes.

        Returns list of (child_node, child_skills) tuples for further processing.
        """
        if self._progress and self._progress_task is not None:
            self._progress.update(self._progress_task, description=f"Assigning skills to fixed categories ({len(skills)} skills)")
        if verbose:
            console.print(f"[cyan]Assigning {len(skills)} skills to fixed categories[/cyan]")

        # Build categories list for prompt
        categories_list = []
        for cat_id, cat_data in FIXED_ROOT_CATEGORIES.items():
            categories_list.append(f"- {cat_id}: {cat_data['name']}")
            categories_list.append(f"  {cat_data['description']}")
        categories_list_str = "\n".join(categories_list)

        # Build skills list for prompt
        skills_list = self._format_skills_list(skills)

        # Call LLM to assign skills to categories
        prompt = FIXED_CATEGORY_ASSIGNMENT_PROMPT.format(
            count=len(skills),
            categories_list=categories_list_str,
            skills_list=skills_list,
        )

        response = self._call_llm(prompt)
        result = self._parse_json(response)
        assignments = result.get("assignments", {})

        # Build skill map
        skill_map = {s["id"]: s for s in skills}

        # Create child nodes for non-empty categories
        children_to_process = []
        for cat_id, cat_data in FIXED_ROOT_CATEGORIES.items():
            assignment = assignments.get(cat_id, {})
            # Support both new format (dict with skill_ids/description) and old format (list of skill_ids)
            if isinstance(assignment, dict):
                assigned_skill_ids = assignment.get("skill_ids", [])
                # Use LLM-generated description if available, otherwise fallback to default
                description = assignment.get("description", cat_data["description"])
            else:
                # Backward compatibility: old format is a list of skill IDs
                assigned_skill_ids = assignment
                description = cat_data["description"]

            child_skills = [skill_map[sid] for sid in assigned_skill_ids if sid in skill_map]

            # Skip empty categories
            if not child_skills:
                if verbose:
                    console.print(f"[dim]  Skipping empty category: {cat_id}[/dim]")
                continue

            child_node = TreeNode(
                id=cat_id,
                name=cat_data["name"],
                description=description,  # Use dynamically generated description
                depth=1,
                parent_id=node.id,
            )

            node.children.append(child_node)

            # Mark assigned skills
            for sid in assigned_skill_ids:
                skill_map.pop(sid, None)

            if verbose:
                console.print(f"[green]  {cat_id}: {len(child_skills)} skills[/green]")

            children_to_process.append((child_node, child_skills))

        # Handle unassigned skills (assign to largest category)
        if skill_map and children_to_process:
            largest_idx = max(range(len(children_to_process)), key=lambda i: len(children_to_process[i][1]))
            unassigned = list(skill_map.values())
            if verbose:
                console.print(f"[yellow]  {len(unassigned)} unassigned skills -> {children_to_process[largest_idx][0].id}[/yellow]")

            child_node, child_skills = children_to_process[largest_idx]
            children_to_process[largest_idx] = (child_node, child_skills + unassigned)

        return children_to_process

    def _split_skills(
        self,
        skills: list[dict],
        parent_context: Optional[dict],
        verbose: bool = False,
    ) -> dict:
        """
        Call LLM to split skills into groups.

        Args:
            skills: Skills to group
            parent_context: Parent node context for coherence
            verbose: Print progress

        Returns:
            Dict of groups: {"group-id": {"name": ..., "description": ..., "skill_ids": [...]}}
        """
        # Build context section
        if parent_context:
            context_section = f'''## Parent Context
You are creating sub-categories under "{parent_context["name"]}": {parent_context["description"]}
Ensure sub-categories are coherent with this parent context.'''
        else:
            context_section = "## Context\nYou are creating top-level categories for all skills."

        # Calculate group range (relaxed)
        min_groups = max(2, self.config.branching_factor - 3)
        max_groups = self.config.branching_factor + 2

        skills_list = self._format_skills_list(skills)

        prompt = RECURSIVE_SPLIT_PROMPT.format(
            count=len(skills),
            context_section=context_section,
            skills_list=skills_list,
            min_groups=min_groups,
            max_groups=max_groups,
        )

        response = self._call_llm(prompt)
        result = self._parse_json(response)

        groups = result.get("groups", {})

        # Optional: quality validation
        issues = self._validate_split_quality(groups, len(skills))
        if issues and verbose:
            for issue in issues:
                console.print(f"[yellow]  Split quality issue: {issue}[/yellow]")

        return groups

    def _validate_split_quality(self, groups: dict, total_skills: int) -> list[str]:
        """Detect split quality issues."""
        issues = []

        if not groups:
            return ["No groups returned"]

        sizes = [len(g.get("skill_ids", [])) for g in groups.values()]
        avg = sum(sizes) / len(sizes) if sizes else 0

        for name, g in groups.items():
            size = len(g.get("skill_ids", []))
            if size > 2.5 * avg and size > 5:
                issues.append(f"Group '{name}' too large ({size} vs avg {avg:.1f})")
            if size == 1:
                issues.append(f"Group '{name}' is singleton")
            if not g.get("description"):
                issues.append(f"Group '{name}' missing description")

        # Check coverage
        total_assigned = sum(sizes)
        if total_assigned < total_skills * 0.9:
            issues.append(f"Low coverage: {total_assigned}/{total_skills} skills assigned")

        return issues

    # =========================================================================
    # Helper methods
    # =========================================================================

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response."""
        self._llm_calls += 1
        if self._progress and self._progress_task is not None:
            self._progress.update(self._progress_task, llm=self._llm_calls)
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                api_base=self.base_url,
                caching=TREE_BUILD_CACHING,
                num_retries=TREE_BUILD_NUM_RETRIES,
                timeout=TREE_BUILD_TIMEOUT,
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]LLM call failed: {e}[/red]")
            return "{}"

    def _parse_json(self, response: str) -> dict | list:
        """Parse JSON from LLM response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        match = re.search(r'[\[{][\s\S]*[\]}]', response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}

    def _format_skills_list(self, skills: list[dict]) -> str:
        """Format skills list for prompt."""
        lines = []
        for skill in skills:
            desc = skill.get("description", "")
            lines.append(f"- {skill['id']}: {skill.get('name', skill['id'])}")
            if desc:
                lines.append(f"  {desc}")
        return "\n".join(lines)

    def _tree_to_dict(self, tree: TreeNode) -> dict:
        """Convert TreeNode to dict format for YAML (supports arbitrary depth)."""
        return self._node_to_dict(tree)

    def _node_to_dict(self, node: TreeNode) -> dict:
        """Recursively convert a node to dict."""
        result = {
            "id": node.id,
            "name": node.name,
            "description": node.description,
        }

        if node.children:
            result["children"] = [self._node_to_dict(child) for child in node.children]

        if node.skills:
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
                for s in node.skills
            ]

        return result

    def _write_yaml(self, tree_dict: dict) -> None:
        """Write tree to YAML file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                tree_dict,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )

    def _print_tree(self, tree_dict: dict) -> None:
        """Print tree structure using rich (supports arbitrary depth)."""
        total_skills = self._count_skills_in_dict(tree_dict)
        rich_tree = RichTree(f"[bold]{tree_dict.get('name', 'Skill Tree')}[/bold] ({total_skills} skills)")

        for child in tree_dict.get("children", []):
            self._add_node_to_rich_tree(rich_tree, child)

        console.print(rich_tree)

    def _add_node_to_rich_tree(self, parent_branch, node_dict: dict) -> None:
        """Recursively add nodes to rich tree."""
        node_skills = self._count_skills_in_dict(node_dict)
        node_id = node_dict.get("id", "unknown")

        # Color based on depth (alternating)
        has_children = bool(node_dict.get("children"))
        if has_children:
            label = f"[yellow]{node_id}[/yellow] ({node_skills} skills)"
        else:
            label = f"[green]{node_id}[/green] ({node_skills} skills)"

        branch = parent_branch.add(label)

        # Add children recursively
        for child in node_dict.get("children", []):
            self._add_node_to_rich_tree(branch, child)

        # Add skills (leaf node)
        skills = node_dict.get("skills", [])
        for skill in skills[:3]:
            branch.add(f"[blue]{skill['id']}[/blue]")
        if len(skills) > 3:
            branch.add(f"[dim]... +{len(skills) - 3} more[/dim]")

    def _count_skills_in_dict(self, node_dict: dict) -> int:
        """Recursively count skills in a node dict."""
        count = len(node_dict.get("skills", []))
        for child in node_dict.get("children", []):
            count += self._count_skills_in_dict(child)
        return count


# Convenience function
def build_tree(
    skills_dir: Path | str | None = None,
    output_path: Path | str | None = None,
    verbose: bool = False,
    show_tree: bool = True,
) -> dict:
    """Build capability tree."""
    builder = TreeBuilder(skills_dir, output_path)
    return builder.build(verbose=verbose, show_tree=show_tree)
