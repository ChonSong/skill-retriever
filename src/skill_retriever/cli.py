"""CLI for skill-retriever — search, build, install, audit, and inspect the capability tree.

Usage:
    python -m skill_retriever search "query"
    python -m skill_retriever build [--verbose]
    python -m skill_retriever list
    python -m skill_retriever info
    python -m skill_retriever install community [--dest PATH]
    python -m skill_retriever install from-dir <source_dir>
    python -m skill_retriever audit [--json]
"""

import argparse
import json
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


def cmd_install(args: argparse.Namespace) -> int:
    """Install skills from various sources. Supports community, all, and from-dir."""
    from skill_retriever.config import MODULE_DIR, SKILLS_DIR

    if args.source == "community":
        return _install_community_skills(args.dest or SKILLS_DIR)
    elif args.source == "from-dir":
        source = Path(args.source_dir)
        if not source.exists():
            print(f"Error: source directory does not exist: {source}")
            return 1
        return _install_from_directory(source, args.dest or SKILLS_DIR)
    else:
        print(f"Unknown install source: {args.source}")
        print("Available: community, from-dir")
        return 1


def _install_community_skills(dest: Path) -> int:
    """Install the bundled community skills to the given directory."""
    import shutil

    from skill_retriever.config import MODULE_DIR
    src_dir = MODULE_DIR / "community_skills"
    if not src_dir.exists():
        print("Error: Bundled community skills not found in package.")
        print("       They should have been installed with the pip package.")
        print(f"       Expected at: {src_dir}")
        return 1

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # Load license manifest
    manifest_path = src_dir / "LICENSES.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            lic_manifest = json.load(f)
        lic_map = {e["skill"]: e["resolved_license"] for e in lic_manifest}
    else:
        lic_map = {}

    installed = 0
    skipped = 0
    for skill_dir in sorted(src_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in (".", "_") or skill_dir.name.startswith("."):
            continue
        # Determine category — use first-char prefix or "community"
        category = "community"
        dst_skill = dest / category / skill_dir.name
        if dst_skill.exists():
            skipped += 1
            continue
        dst_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dst_skill, ignore=shutil.ignore_patterns("._*"))
        installed += 1

    print(f"Installed {installed} bundled community skills to {dest / 'community'}")
    if skipped:
        print(f"Skipped {skipped} already existing")
    print()

    # Print license notice
    open_src = sum(1 for v in lic_map.values() if v in ("MIT", "Apache-2.0", "BSD-3-Clause"))
    print(f"License summary for installed community skills:")
    for lic, cnt in sorted(__import__("collections").Counter(lic_map.values()).items()):
        print(f"  {cnt:4d}  {lic}")
    print(f"\nAll {open_src} skills are permissively licensed (MIT/Apache/BSD).")
    print("See skill_retriever/community_skills/LICENSES.json for per-skill details.")
    print()

    return 0


def _install_from_directory(source: Path, dest: Path) -> int:
    """Install skills from a local directory to the given destination."""
    import shutil

    from skill_retriever.tree.skill_scanner import SkillScanner
    scanner = SkillScanner(source)
    skills = scanner.scan(show_progress=False)

    if not skills:
        print(f"No skills found in {source}")
        return 0

    dest = Path(dest)
    installed = 0
    for s in skills:
        skill_id = s.id
        # Determine category — use source dir name or "imported"
        category = source.name if source.name and source.name not in (".", "", "..") else "imported"
        dst_skill = dest / category / skill_id
        if dst_skill.exists():
            continue
        dst_skill.mkdir(parents=True, exist_ok=True)
        src_path = Path(s.skill_path)
        if src_path.exists():
            shutil.copy2(src_path, dst_skill / "SKILL.md")
        installed += 1

    print(f"Installed {installed} skills from {source} to {dest / category}")
    print(f"License: scan source directory manually — skills retain their original licenses.")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Audit installed skills for licensing information."""
    from skill_retriever.config import SKILLS_DIR

    skills_dir = Path(args.skills_dir or SKILLS_DIR)
    if not skills_dir.exists():
        print(f"Skills directory not found: {skills_dir}")
        return 1

    # Scan for all SKILL.md files
    from collections import Counter
    stats = Counter()
    license_counts = Counter()
    unlicensed = []

    # Check bundled community skills manifest
    from skill_retriever.config import MODULE_DIR
    bundled_manifest = MODULE_DIR / "community_skills" / "LICENSES.json"
    bundled_licenses = {}
    if bundled_manifest.exists():
        with open(bundled_manifest) as f:
            for entry in json.load(f):
                bundled_licenses[entry["skill"]] = entry["resolved_license"]

    for cat_dir in skills_dir.iterdir():
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        for skill_dir in cat_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            stats["total"] += 1

            # Check bundled license manifest
            if skill_dir.name in bundled_licenses:
                lic = bundled_licenses[skill_dir.name]
                license_counts[lic] += 1
                continue

            # Read frontmatter
            try:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                license_counts["UNREADABLE"] += 1
                continue

            if content.startswith("---"):
                try:
                    import yaml
                    fm = yaml.safe_load(content.split("---", 2)[1]) or {}
                    lic = fm.get("license") or fm.get("License") or "NO_LICENSE"
                except Exception:
                    lic = "NO_LICENSE"
            else:
                lic = "NO_LICENSE"

            if lic == "NO_LICENSE":
                unlicensed.append(skill_dir.name)
            license_counts[lic] += 1

    if args.json:
        report = {
            "total": stats["total"],
            "by_license": dict(license_counts),
            "unlicensed_count": len(unlicensed),
            "unlicensed_sample": unlicensed[:20],
        }
        print(json.dumps(report, indent=2))
    else:
        print(f"\n=== License Audit: {skills_dir} ===\n")
        print(f"Total skills scanned: {stats['total']}")
        print(f"\nLicense breakdown:")
        for lic, cnt in license_counts.most_common():
            print(f"  {cnt:4d}  {lic}")
        if unlicensed:
            print(f"\n⚠ Unlicensed skills: {len(unlicensed)}")
            for s in unlicensed[:10]:
                print(f"    {s}")
            if len(unlicensed) > 10:
                print(f"    ... and {len(unlicensed) - 10} more")
        print()

        # License notice
        safe = sum(c for l, c in license_counts.items()
                   if l in ("MIT", "Apache-2.0", "BSD-3-Clause", "BSD"))
        print(f"Summary: {safe} permissive, "
              f"{license_counts.get('PROPRIETARY', 0)} proprietary, "
              f"{len(unlicensed)} unlicensed")
        if unlicensed:
            print("⚠  Unlicensed skills are 'all rights reserved' by default.")
            print("   Do not redistribute without checking original sources.")
        print()

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

    # install
    p_install = sub.add_parser("install", help="Install skills from bundled or external sources")
    p_install.add_argument("source", nargs="?", default="community",
                           help="Source: 'community' (default) or 'from-dir'")
    p_install.add_argument("source_dir", nargs="?",
                           help="Directory path when source='from-dir'")
    p_install.add_argument("--dest", "-d", help="Target directory (default: SKILLS_DIR from env)")
    p_install.set_defaults(func=cmd_install)

    # audit
    p_audit = sub.add_parser("audit", help="Audit installed skills for licensing information")
    p_audit.add_argument("--skills-dir", help="Path to skills directory")
    p_audit.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p_audit.set_defaults(func=cmd_audit)

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
