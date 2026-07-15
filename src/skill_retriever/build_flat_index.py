#!/usr/bin/env python3
"""Build flat_index.json from the skill capability tree.

Walks every node in the tree YAML and extracts named skills with
description + domain path (for tag inference).

Output: ~/.hermes/skill-retriever-cache/flat_index.json
"""
import json
import yaml
from pathlib import Path

TREE_PATH = Path.home() / ".hermes/plugins/skill-retriever/src/skill_retriever/capability_tree/tree_10000_ship_safe.yaml"
OUT_DIR = Path.home() / ".hermes/skill-retriever-cache"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "flat_index.json"

def walk_node(node, domain_path, results):
    name = node.get("name", "")
    desc = node.get("description", "")
    node_id = node.get("id", "")
    domain_path = domain_path + [name] if name else domain_path

    for skill in node.get("skills", []):
        skill_name = skill.get("name", "")
        skill_desc = skill.get("description", "") or desc
        skill_path = skill.get("skill_path", "")
        results.append({
            "name": skill_name,
            "description": skill_desc[:500],
            "path": skill_path,
            "tags": domain_path[-2:] if len(domain_path) >= 2 else domain_path,
            "skill_id": skill.get("id", ""),
        })

    for child in node.get("children", []):
        walk_node(child, domain_path, results)

def main():
    with open(TREE_PATH) as f:
        tree = yaml.safe_load(f)

    results = []
    walk_node(tree, [], results)
    # Dedup by name, keep the most specific (longest path)
    by_name = {}
    for r in results:
        name = r["name"]
        if name not in by_name or len(r["tags"]) > len(by_name[name]["tags"]):
            by_name[name] = r

    flat = sorted(by_name.values(), key=lambda x: x["name"])
    with open(OUT_PATH, "w") as f:
        json.dump(flat, f, indent=2)

    print(f"Built {len(flat)} skills → {OUT_PATH}")

if __name__ == "__main__":
    main()
