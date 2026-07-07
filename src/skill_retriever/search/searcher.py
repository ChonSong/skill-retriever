"""
Skill Searcher - Multi-level tree search with LLM selection.

Recursively descends the tree, using LLM to select relevant branches
at each level, with parallel queries for sibling branches.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Any

import litellm
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree as RichTree

from ..config import (
    LLM_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    BRANCHING_FACTOR,
    PRUNE_ENABLED,
    SEARCH_MAX_PARALLEL,
    SEARCH_TEMPERATURE,
    SEARCH_TIMEOUT,
    SEARCH_CACHING,
    PROJECT_ROOT,
    ensure_cache,
)
from ..tree.schema import TreeNode, Skill, DynamicTreeConfig
from ..tree.prompts import NODE_SELECTION_PROMPT, SKILL_SELECTION_PROMPT, SKILL_PRUNE_PROMPT

console = Console()

# Default tree path
DEFAULT_TREE_PATH = Path(__file__).parent.parent / "capability_tree" / "tree.yaml"

# Event callback type: (event_type: str, data: dict) -> None
EventCallback = Callable[[str, dict], None]


@dataclass
class SearchResult:
    """Result from skill search."""
    query: str
    selected_skills: list[dict]
    llm_calls: int = 0
    parallel_rounds: int = 0
    explored_nodes: list[str] = field(default_factory=list)
    selected_paths: list[str] = field(default_factory=list)


class Searcher:
    """
    Multi-level tree searcher with parallel support.

    Recursively descends the tree, using LLM to select relevant branches
    at each level, with parallel queries for sibling branches.
    """

    def __init__(
        self,
        tree_path: Path | str | None = None,
        config: Optional[DynamicTreeConfig] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_parallel: Optional[int] = None,
        prune: Optional[bool] = None,
        event_callback: Optional[EventCallback] = None,
    ):
        self.tree_path = Path(tree_path) if tree_path else DEFAULT_TREE_PATH
        self.config = config or DynamicTreeConfig(branching_factor=BRANCHING_FACTOR)
        self.model = model or LLM_MODEL
        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.max_parallel = max_parallel if max_parallel is not None else SEARCH_MAX_PARALLEL
        self.prune_enabled = prune if prune is not None else PRUNE_ENABLED
        self.event_callback = event_callback

        self._tree: Optional[TreeNode] = None
        self._llm_calls = 0
        self._parallel_rounds = 0
        self._explored_nodes: list[str] = []
        self._selected_paths: list[str] = []

        ensure_cache()

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Emit an event to the callback if set."""
        if self.event_callback:
            try:
                self.event_callback(event_type, data)
            except Exception as e:
                console.print(f"[yellow]Event callback error: {e}[/yellow]")

    def search(self, query: str, verbose: bool = False) -> SearchResult:
        """
        Execute multi-level search.

        Args:
            query: User's task description
            verbose: Print detailed search process

        Returns:
            SearchResult with selected skills
        """
        self._llm_calls = 0
        self._parallel_rounds = 0
        self._explored_nodes = []
        self._selected_paths = []

        # Emit search_start event
        self._emit_event("search_start", {"query": query})

        # Load tree if not loaded
        if self._tree is None:
            self._tree = self._load_tree()
            if self._tree is None:
                self._emit_event("search_complete", {"skills": [], "error": "Tree not found"})
                return SearchResult(query=query, selected_skills=[])

        if verbose:
            console.print(Panel.fit(
                f"[bold cyan]Searching: {query}[/bold cyan]",
                border_style="cyan",
            ))
            self._print_tree_structure()

        # Start recursive search from root
        selected_skills = self._search_node(query, self._tree, depth=0, verbose=verbose)

        # Apply pruning if enabled
        if self.prune_enabled and selected_skills:
            before_prune_ids = [s.id for s in selected_skills]
            self._emit_event("prune_start", {"skill_count": len(selected_skills), "skill_ids": before_prune_ids})
            selected_skills = self._prune_skills(query, selected_skills, verbose)
            after_prune_ids = [s.id for s in selected_skills]
            pruned_ids = [sid for sid in before_prune_ids if sid not in after_prune_ids]
            self._emit_event("prune_complete", {
                "skill_count": len(selected_skills),
                "selected_ids": after_prune_ids,
                "pruned_ids": pruned_ids
            })

        def _to_absolute_skill_path(skill_path: str) -> str:
            """Convert relative skill_path to absolute path."""
            p = Path(skill_path)
            if p.is_absolute():
                return skill_path
            return str(PROJECT_ROOT / skill_path)

        result = SearchResult(
            query=query,
            selected_skills=[
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "path": s.path,
                    "skill_path": _to_absolute_skill_path(s.skill_path),
                    "reason": getattr(s, "selection_reason", ""),
                    "github_url": getattr(s, "github_url", ""),
                    "stars": getattr(s, "stars", 0),
                    "is_official": getattr(s, "is_official", False),
                    "author": getattr(s, "author", ""),
                }
                for s in selected_skills
            ],
            llm_calls=self._llm_calls,
            parallel_rounds=self._parallel_rounds,
            explored_nodes=self._explored_nodes,
            selected_paths=self._selected_paths,
        )

        # Emit search_complete event
        self._emit_event("search_complete", {
            "skills": result.selected_skills,
            "llm_calls": result.llm_calls,
        })

        if verbose:
            self._print_result(result)

        return result

    def _load_tree(self) -> Optional[TreeNode]:
        """Load tree from YAML file."""
        if not self.tree_path.exists():
            console.print(f"[red]Tree file not found: {self.tree_path}[/red]")
            console.print("[dim]Run 'python -m skill_retriever tree build' first.[/dim]")
            return None

        try:
            with open(self.tree_path, "r", encoding="utf-8") as f:
                tree_dict = yaml.safe_load(f)

            # Support both new recursive format and legacy domains/types format
            if "children" in tree_dict:
                # New recursive format (id/name/description/children/skills)
                tree = TreeNode.from_recursive_tree(tree_dict)
            else:
                # Legacy format (domains/types/skills)
                tree = TreeNode.from_capability_tree(tree_dict)

            # Enrich skills with metadata from skills.json
            self._enrich_skills_metadata(tree)
            return tree
        except Exception as e:
            console.print(f"[red]Failed to load tree: {e}[/red]")
            return None

    def _enrich_skills_metadata(self, tree: TreeNode) -> None:
        """Enrich skill objects with metadata from skills.json."""
        # Load metadata from skills.json (in data/skill_seeds relative to project root)
        project_root = Path(__file__).parent.parent.parent.parent
        skills_json_path = project_root / "data" / "skill_seeds" / "skills.json"
        if not skills_json_path.exists():
            return

        try:
            with open(skills_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Build metadata lookup by skill id
            metadata_map = {s["id"]: s for s in data.get("skills", [])}

            # Recursively update all skills in the tree
            self._apply_metadata_to_node(tree, metadata_map)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load skill metadata: {e}[/yellow]")

    def _apply_metadata_to_node(self, node: TreeNode, metadata_map: dict) -> None:
        """Recursively apply metadata to skills in a node."""
        for skill in node.skills:
            if skill.id in metadata_map:
                meta = metadata_map[skill.id]
                skill.github_url = meta.get("github_url", "")
                skill.stars = meta.get("stars", 0)
                skill.is_official = meta.get("is_official", False)
                skill.author = meta.get("author", "")

        for child in node.children:
            self._apply_metadata_to_node(child, metadata_map)

    def _search_node(
        self,
        query: str,
        node: TreeNode,
        depth: int,
        verbose: bool = False,
    ) -> list[Skill]:
        """
        Recursively search from a node.

        Args:
            query: Search query
            node: Current node to search from
            depth: Current depth in tree
            verbose: Print progress

        Returns:
            List of selected skills
        """
        # Emit node_enter event
        self._emit_event("node_enter", {
            "node_id": node.id,
            "node_name": node.name,
            "depth": depth,
            "is_leaf": node.is_leaf,
            "skill_count": len(node.skills) if node.is_leaf else node.count_all_skills(),
        })
        self._explored_nodes.append(node.id)

        # Base case: leaf node with skills
        if node.is_leaf:
            if len(node.skills) == 0:
                return []

            if verbose:
                console.print(f"{'  ' * depth}[dim]Leaf: {node.id} ({len(node.skills)} skills)[/dim]")

            return self._select_skills(query, node.skills, depth, verbose)

        # Intermediate node: select children first
        children = node.children

        if verbose:
            console.print(f"\n{'  ' * depth}[bold]Level {depth}: {node.id}[/bold] ({len(children)} children)")

        # Decision: expand all or use LLM selection
        if len(children) <= self.config.expand_threshold:
            selected_children = children
            if verbose:
                console.print(f"{'  ' * depth}[dim]→ Expanding all {len(children)} children[/dim]")
            # Emit event for auto-expansion
            self._emit_event("children_selected", {
                "parent_id": node.id,
                "selected": [c.id for c in selected_children],
                "rejected": [],
                "auto_expand": True,
            })
        else:
            selected_children = self._select_children(query, children, depth, verbose)
            # Emit event for LLM selection
            selected_ids = [c.id for c in selected_children]
            rejected_ids = [c.id for c in children if c.id not in selected_ids]
            self._emit_event("children_selected", {
                "parent_id": node.id,
                "selected": selected_ids,
                "rejected": rejected_ids,
                "auto_expand": False,
            })

        if not selected_children:
            return []

        # Track selected paths
        for child in selected_children:
            self._selected_paths.append(child.id)

        # Early stop optimization
        if len(selected_children) == 1:
            only_child = selected_children[0]
            total_skills = only_child.count_all_skills()

            if total_skills <= self.config.early_stop_skill_count:
                if verbose:
                    console.print(f"{'  ' * depth}[yellow]Early stop: {only_child.id} ({total_skills} skills)[/yellow]")

                self._emit_event("early_stop", {
                    "node_id": only_child.id,
                    "skill_count": total_skills,
                })

                all_skills = only_child.collect_all_skills()
                return self._select_skills(query, all_skills, depth, verbose)

        # Parallel search in selected children
        if len(selected_children) > 1:
            if verbose:
                console.print(f"{'  ' * depth}[green]Parallel search in {len(selected_children)} branches[/green]")

            results = self._parallel_search_children(query, selected_children, depth + 1, verbose)
            self._parallel_rounds += 1
        else:
            results = self._search_node(query, selected_children[0], depth + 1, verbose)

        return results

    def _select_children(
        self,
        query: str,
        children: list[TreeNode],
        depth: int,
        verbose: bool = False,
    ) -> list[TreeNode]:
        """Select relevant children using LLM."""
        options_lines = []
        for child in children:
            skill_count = child.count_all_skills()
            options_lines.append(f"- {child.id}: {child.name} ({skill_count} skills)")
            if child.description:
                options_lines.append(f"  {child.description}")

        options_text = "\n".join(options_lines)
        example = json.dumps([children[0].id, children[1].id] if len(children) > 1 else [children[0].id])

        prompt = NODE_SELECTION_PROMPT.format(
            query=query,
            options=options_text,
            example=example,
        )

        if verbose:
            console.print(f"{'  ' * depth}[dim]LLM selecting from {len(children)} options...[/dim]")

        response = self._call_llm(prompt)
        selection = self._parse_selection(response)
        selected_ids = [item["id"] for item in selection]

        if verbose:
            console.print(f"{'  ' * depth}[green]Selected: {selected_ids}[/green]")

        child_map = {c.id: c for c in children}
        return [child_map[cid] for cid in selected_ids if cid in child_map]

    def _select_skills(
        self,
        query: str,
        skills: list[Skill],
        depth: int,
        verbose: bool = False,
    ) -> list[Skill]:
        """Select relevant skills using LLM."""
        if not skills:
            return []

        options_lines = []
        for skill in skills:
            desc = skill.description[:150] + "..." if len(skill.description) > 150 else skill.description
            options_lines.append(f"- {skill.id}: {desc}")

        options_text = "\n".join(options_lines)

        prompt = SKILL_SELECTION_PROMPT.format(
            query=query,
            options=options_text,
        )

        if verbose:
            console.print(f"{'  ' * depth}[dim]LLM selecting from {len(skills)} skills...[/dim]")

        response = self._call_llm(prompt)
        selection = self._parse_selection(response)

        # Extract selected IDs (no reason at this stage - reason is added during pruning)
        selected_ids = [item["id"] for item in selection]

        if verbose:
            console.print(f"{'  ' * depth}[green]Selected: {selected_ids}[/green]")

        # Emit skills_selected event
        self._emit_event("skills_selected", {
            "selected": selected_ids,
            "rejected": [s.id for s in skills if s.id not in selected_ids],
            "total_options": len(skills),
        })

        # Return selected skills (reason will be added during pruning)
        skill_map = {s.id: s for s in skills}
        return [skill_map[sid] for sid in selected_ids if sid in skill_map]

    def _prune_skills(
        self,
        query: str,
        skills: list[Skill],
        verbose: bool = False,
    ) -> list[Skill]:
        """
        Prune similar skills by grouping and selecting representatives.

        Args:
            query: User's task description
            skills: List of skills to prune
            verbose: Print progress

        Returns:
            Pruned list of skills (one representative per group)
        """

        if verbose:
            console.print(f"\n[bold yellow]Pruning {len(skills)} skills...[/bold yellow]")

        # Build skills list for prompt with full description and content preview
        skills_lines = []
        for skill in skills:
            # Use full description (no truncation)
            skill_info = f"- {skill.id}: {skill.description}"
            # Add first 5000 chars of content if available
            if skill.content:
                content_preview = skill.content[:5000]
                if len(skill.content) > 5000:
                    content_preview += "..."
                skill_info += f"\n  Content:\n  {content_preview}"
            skills_lines.append(skill_info)

        skills_text = "\n".join(skills_lines)

        prompt = SKILL_PRUNE_PROMPT.format(
            query=query,
            skills_list=skills_text,
        )

        response = self._call_llm(prompt)
        pruned_skills = self._parse_prune_response(response, skills, verbose)

        if verbose:
            console.print(f"[green]Pruned to {len(pruned_skills)} skills[/green]")

        return pruned_skills

    def _parse_prune_response(
        self,
        response: str,
        skills: list[Skill],
        verbose: bool = False,
    ) -> list[Skill]:
        """Parse LLM pruning response (selected_skills format)."""
        skill_map = {s.id: s for s in skills}

        # Strip markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove opening ``` and optional language tag
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]  # Remove first line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    if verbose:
                        console.print("[yellow]Failed to parse prune response, returning original skills[/yellow]")
                    return skills
            else:
                if verbose:
                    console.print("[yellow]Failed to parse prune response, returning original skills[/yellow]")
                return skills

        final_skills = []
        seen_ids = set()  # Prevent duplicates

        # Extract selected skills (order is preserved - sorted by relevance from LLM)
        selected = data.get("selected_skills", [])
        for item in selected:
            skill_id = item.get("id") if isinstance(item, dict) else item
            reason = item.get("reason", "") if isinstance(item, dict) else ""
            if skill_id and skill_id in skill_map and skill_id not in seen_ids:
                skill = skill_map[skill_id]
                skill.selection_reason = reason  # Attach reason from pruning
                final_skills.append(skill)
                seen_ids.add(skill_id)
                if verbose:
                    console.print(f"  [cyan]Selected: {skill_id}[/cyan]")
                    if reason:
                        console.print(f"    [dim]{reason}[/dim]")

        # Log eliminated skills if verbose
        if verbose:
            eliminated = data.get("eliminated", [])
            if eliminated:
                console.print("  [dim]Eliminated:[/dim]")
                for item in eliminated:
                    skill_id = item.get("id") if isinstance(item, dict) else item
                    reason = item.get("reason", "") if isinstance(item, dict) else ""
                    console.print(f"    [dim strikethrough]{skill_id}[/dim strikethrough]: {reason}")

        # Fallback: if no valid skills found, return original skills
        if not final_skills:
            if verbose:
                console.print("[yellow]No valid skills found in prune response, returning original skills[/yellow]")
            return skills

        return final_skills

    def _parallel_search_children(
        self,
        query: str,
        children: list[TreeNode],
        depth: int,
        verbose: bool = False,
    ) -> list[Skill]:
        """Search multiple children in parallel."""
        results = []

        with ThreadPoolExecutor(max_workers=min(len(children), self.max_parallel)) as executor:
            futures = [
                executor.submit(self._search_node, query, child, depth, verbose)
                for child in children
            ]

            for future in futures:
                child_results = future.result()
                results.extend(child_results)

        return results

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response."""
        self._llm_calls += 1

        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                api_base=self.base_url,
                temperature=SEARCH_TEMPERATURE,
                caching=SEARCH_CACHING,
                num_retries=LLM_MAX_RETRIES,
                timeout=SEARCH_TIMEOUT,
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]LLM call failed: {e}[/red]")
            return "[]"

    def _parse_selection(self, response: str) -> list[dict]:
        """
        Parse LLM selection response.

        Supports two formats:
        - Legacy: ["skill_id_1", "skill_id_2"] - returns [{"id": "skill_id_1", "reason": ""}, ...]
        - New: [{"id": "skill_id_1", "reason": "..."}, ...] - returns as-is

        Returns: list of dicts with 'id' and 'reason' keys
        """
        parsed = None

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            pass

        if parsed is None:
            match = re.search(r'\[[\s\S]*?\]', response)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        if not parsed:
            return []

        # Normalize to list of dicts
        result = []
        for item in parsed:
            if isinstance(item, str):
                # Legacy format: plain string ID
                result.append({"id": item, "reason": ""})
            elif isinstance(item, dict) and "id" in item:
                # New format: dict with id and reason
                result.append({
                    "id": item.get("id", ""),
                    "reason": item.get("reason", ""),
                })

        return result

    def _print_tree_structure(self) -> None:
        """Print tree structure for debugging."""
        if self._tree is None:
            return

        rich_tree = RichTree(f"[bold]{self._tree.id}[/bold] ({self._tree.count_all_skills()} skills)")

        def add_children(parent_rich, node: TreeNode):
            for child in node.children:
                skill_count = child.count_all_skills()
                if child.is_leaf:
                    child_rich = parent_rich.add(f"[cyan]{child.id}[/cyan] [{skill_count} skills]")
                else:
                    child_rich = parent_rich.add(f"[yellow]{child.id}[/yellow] ({skill_count} skills)")
                    add_children(child_rich, child)

        add_children(rich_tree, self._tree)
        console.print(rich_tree)

    def _print_result(self, result: SearchResult) -> None:
        """Print search result."""
        console.print(f"\n[bold]Search Result[/bold] ({result.llm_calls} LLM calls)")

        if result.selected_skills:
            console.print("\n[bold]Selected Skills:[/bold]")
            for skill in result.selected_skills:
                console.print(f"  [cyan]{skill['id']}[/cyan] [{skill.get('path', '')}]")
                desc = skill.get('description', '')[:80]
                if desc:
                    console.print(f"    [dim]{desc}...[/dim]")
        else:
            console.print("[yellow]No skills selected.[/yellow]")


    def get_tree_data(self) -> Optional[dict]:
        """Get tree data as a JSON-serializable dict for WebUI visualization.

        Returns:
            Tree structure dict or None if tree not loaded
        """
        if self._tree is None:
            self._tree = self._load_tree()
            if self._tree is None:
                return None

        def _to_absolute_skill_path(skill_path: str) -> str:
            """Convert relative skill_path to absolute path."""
            p = Path(skill_path)
            if p.is_absolute():
                return skill_path
            return str(PROJECT_ROOT / skill_path)

        def node_to_dict(node: TreeNode) -> dict:
            """Recursively convert TreeNode to dict."""
            result = {
                "id": node.id,
                "name": node.name,
                "description": node.description or "",
                "type": "category",  # TreeNode is always a category, skills array items are skills
            }
            if node.children:
                result["children"] = [node_to_dict(child) for child in node.children]
            if node.skills:
                result["children"] = [
                    {
                        "id": skill.id,
                        "name": skill.name,
                        "description": skill.description,
                        "type": "skill",
                        "skill_path": _to_absolute_skill_path(skill.skill_path),
                    }
                    for skill in node.skills
                ]
            return result

        return node_to_dict(self._tree)


def search(query: str, tree_path: Path | str | None = None, verbose: bool = False) -> list[dict]:
    """
    Convenience function to search for skills.

    Returns:
        List of selected skill dicts
    """
    searcher = Searcher(tree_path=tree_path)
    result = searcher.search(query, verbose=verbose)
    return result.selected_skills
