"""CLI for skill-retriever — search, build, and inspect the capability tree.

Usage:
    python -m skill_retriever search "query"
    python -m skill_retriever build [--verbose]
    python -m skill_retriever list
    python -m skill_retriever info
"""

import argparse
import sys
from pathlib import Path

def _get_searcher(tree_path: str | None = None, **kwargs):
    """Lazy import & instantiate Searcher."""
    from skill_retriever.search.searcher import Searcher
    return Searcher(tree_path=tree_path, **kwargs)


def _get_builder(skills_dir: str | None = None, **kwargs):
    """Lazy import & instantiate TreeBuilder."""
    from skill_retriever.tree.builder import TreeBuilder
    return TreeBuilder(skills_dir=skills_dir, **kwargs)


def cmd_search(args: argparse.Namespace) -> int:
    """Search the capability tree for skills matching a query."""
    searcher = _get_searcher(tree_path=args.tree)
    result = searcher.search(args.query, verbose=args.verbose)

    if not result.selected_skills:
        print("No skills found.")
        return 0

    print(f"\nFound {len(result.selected_skills)} skills ({result.llm_calls} LLM calls):\n")
    for i, skill in enumerate(result.selected_skills, 1):
        desc = (skill.get("description") or "")[:120]
        path = skill.get("path", "")
        reason = skill.get("reason", "")
        print(f"  {i}. {skill['id']}")
        if desc:
            print(f"     {desc}")
        if path:
            print(f"     [{path}]")
        if reason:
            print(f"     → {reason}")
        print()

    if args.verbose:
        print(f"Explored nodes: {result.explored_nodes}")
        print(f"Selected paths: {result.selected_paths}")
        print(f"Parallel rounds: {result.parallel_rounds}")

    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build the capability tree from the skills corpus."""
    builder = _get_builder(
        skills_dir=args.skills_dir,
        output_path=args.output,
        verbose=args.verbose,
    )
    tree = builder.build(
        verbose=args.verbose,
        show_tree=args.show_tree,
        generate_html=not args.no_html,
    )

    if not tree:
        print("Tree build failed — no skills found.")
        return 1

    print(f"\n✅ Tree built with {builder._llm_calls} LLM calls.")
    print(f"   Output: {builder.output_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all skills in the data directory."""
    from skill_retriever.tree.skill_scanner import SkillScanner
    scanner = SkillScanner(skills_dir=args.skills_dir)
    skills = scanner.scan(show_progress=False)

    if not skills:
        print("No skills found.")
        return 0

    print(f"\n{len(skills)} skills available:\n")
    for s in skills:
        desc = (s.description or "")[:80]
        print(f"  {s.id:<35} {desc}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show info about the installed skill tree and corpus."""
    from skill_retriever.config import CAPABILITY_TREE_PATH, SKILLS_DIR

    tree_path = Path(args.tree or CAPABILITY_TREE_PATH)
    print(f"Capability tree:  {tree_path}")
    print(f"  Exists:         {tree_path.exists()}")
    if tree_path.exists():
        print(f"  Size:           {tree_path.stat().st_size / 1024:.1f} KB")

    skills_dir = Path(args.skills_dir or SKILLS_DIR)
    print(f"\nSkills directory: {skills_dir}")
    print(f"  Exists:         {skills_dir.exists()}")
    if skills_dir.exists():
        count = sum(1 for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
        print(f"  Skill dirs:     {count}")

    # Show module version
    try:
        import importlib.metadata
        ver = importlib.metadata.version("skill-retriever")
        print(f"\nPackage version:  {ver}")
    except Exception:
        pass

    # Show the tree structure (first 3 levels)
    if tree_path.exists():
        try:
            import yaml
            with open(tree_path) as f:
                tree = yaml.safe_load(f)
            if tree:
                _print_tree_summary(tree, 0, max_depth=2)
        except Exception:
            pass

    return 0


def _print_tree_summary(node: dict, depth: int = 0, max_depth: int = 2) -> None:
    """Print a compact summary of the tree structure."""
    indent = "  " * depth
    name = node.get("name", node.get("id", "?"))
    children = node.get("children", [])
    skills = node.get("skills", [])

    if skills:
        print(f"{indent}📄 {name} ({len(skills)} skills)")
    elif children:
        skill_count = sum(
            len(c.get("skills", []))
            for c in children
        ) if depth < max_depth else "?"
        print(f"{indent}📁 {name} ({len(children)} children, {skill_count} skills)")
        if depth < max_depth:
            for child in children[:10]:
                _print_tree_summary(child, depth + 1, max_depth)
            if len(children) > 10:
                print(f"{indent}  ... and {len(children) - 10} more")
    else:
        print(f"{indent}📁 {name} (empty)")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="skill-retriever",
        description="AgentSkillOS-powered semantic skill retrieval for Hermes Agent.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search skills by query")
    p_search.add_argument("query", help="Search query (natural language)")
    p_search.add_argument("--tree", help="Path to capability tree YAML")
    p_search.set_defaults(func=cmd_search)

    # build
    p_build = sub.add_parser("build", help="Build capability tree from skills")
    p_build.add_argument("--skills-dir", help="Path to skill_seeds directory")
    p_build.add_argument("--output", help="Output path for tree YAML")
    p_build.add_argument("--show-tree", action="store_true", default=True, help="Display tree after build")
    p_build.add_argument("--no-html", action="store_true", help="Skip HTML visualization generation")
    p_build.set_defaults(func=cmd_build)

    # list
    p_list = sub.add_parser("list", help="List available skills")
    p_list.add_argument("--skills-dir", help="Path to skill_seeds directory")
    p_list.set_defaults(func=cmd_list)

    # info
    p_info = sub.add_parser("info", help="Show system info")
    p_info.add_argument("--tree", help="Path to capability tree YAML")
    p_info.add_argument("--skills-dir", help="Path to skill_seeds directory")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
