#!/usr/bin/env python3
"""skill-retriever CLI — rebuild index and compose bundles."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes/plugins/skill-retriever/src"))

from skill_retriever.compose import compose_skills, bundle_to_hint_block, FLAT_INDEX_PATH
from skill_retriever.build_flat_index import main as build_index


def cmd_rebuild(args):
    """Rebuild the flat index from the capability tree."""
    build_index()


def cmd_compose(args):
    """Compose a skill bundle for a query."""
    query = " ".join(args.query)
    bundle = compose_skills(query)
    if bundle:
        if args.json:
            print(json.dumps(bundle, indent=2))
        else:
            print(bundle_to_hint_block(bundle))
    else:
        print("No bundle returned (no matching skills or LLM error)")


def cmd_info(args):
    """Show index info."""
    if FLAT_INDEX_PATH.exists():
        with open(FLAT_INDEX_PATH) as f:
            data = json.load(f)
        print(f"Flat index: {len(data)} skills at {FLAT_INDEX_PATH}")
        tags = set()
        for s in data:
            for t in s.get("tags", []):
                tags.add(t)
        print(f"Unique tags: {len(tags)}")
    else:
        print(f"Index not built. Run: skill-retriever rebuild")


def main():
    parser = argparse.ArgumentParser(prog="skill-retriever")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("rebuild", help="Rebuild flat index from tree").set_defaults(func=cmd_rebuild)

    compose_p = sub.add_parser("compose", help="Compose bundle for a query")
    compose_p.add_argument("query", nargs="+", help="User query")
    compose_p.add_argument("--json", action="store_true", help="Output raw JSON")
    compose_p.set_defaults(func=cmd_compose)

    sub.add_parser("info", help="Show index info").set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
