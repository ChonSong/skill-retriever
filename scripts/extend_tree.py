#!/usr/bin/env python3
"""
Extend the capability tree with newly ingested AAS skills.

Reads the existing ship-safe tree, maps new skills to matching leaf nodes
by keyword overlap, and writes an updated tree.

Usage:
    python scripts/extend_tree.py                    # dry-run: report only
    python scripts/extend_tree.py --execute          # actually write updated tree
    python scripts/extend_tree.py --execute --target full   # update full tree too
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
import yaml

REPO_DIR = Path(__file__).parent.parent.resolve()
SKILLS_DIR = REPO_DIR / "src" / "skill_retriever" / "community_skills"
SHIP_TREE = REPO_DIR / "src" / "skill_retriever" / "capability_tree" / "tree_10000_ship_safe.yaml"
FULL_TREE = REPO_DIR / "src" / "skill_retriever" / "capability_tree" / "tree_10000.yaml"
AAS_REPORT = REPO_DIR / "data" / "aas_ingest_report.json"
OUT_PATH = REPO_DIR / "src" / "skill_retriever" / "capability_tree"


def parse_frontmatter(smd_path):
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        with open(smd_path) as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return yaml.safe_load(parts[1])
    except Exception:
        pass
    return {}


def collect_skills():
    """Collect all skills from community_skills/ with metadata."""
    skills = []
    for d in sorted(os.listdir(SKILLS_DIR)):
        dpath = SKILLS_DIR / d
        smd = dpath / "SKILL.md"
        if not dpath.is_dir() or not smd.exists():
            continue
        meta = parse_frontmatter(smd)
        if meta and meta.get("name"):
            name = meta["name"].strip()
        else:
            name = d
        
        desc = (meta.get("description") or "")[:500] if meta else ""
        tags = meta.get("tags", []) if meta else []
        if isinstance(tags, str):
            tags = [tags]
        
        skills.append({
            "name": name,
            "dir": d,
            "description": desc,
            "tags": [t.lower() for t in tags],
            "risk": meta.get("risk", "unknown") if meta else "unknown",
            "license": meta.get("license", "unknown") if meta else "unknown",
        })
    
    return skills


def flatten_tree(node, path=None):
    """Flatten a capability tree into leaf nodes with paths."""
    if path is None:
        path = []
    
    leaves = []
    node_id = node.get("id", "unknown")
    node_name = node.get("name", "")
    current_path = path + [node_name]
    
    children = node.get("children", [])
    skills = node.get("skills", [])
    
    if skills and not children:
        # Leaf node
        existing_names = set()
        for sk in skills:
            if isinstance(sk, dict):
                existing_names.add(sk.get("name", "").lower().strip())
            elif isinstance(sk, str):
                existing_names.add(sk.lower().strip())
        
        leaves.append({
            "path": " > ".join(current_path),
            "path_list": current_path,
            "node_id": node_id,
            "existing_names": existing_names,
            "skills": skills,
        })
    
    for child in children:
        leaves.extend(flatten_tree(child, current_path))
    
    return leaves


def build_keywords(description, tags):
    """Extract meaningful keywords from description + tags."""
    text = f"{description} {' '.join(tags)}".lower()
    # Simple tokenization, remove common words
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "use", "used", "using",
        "this", "that", "these", "those", "it", "its", "they", "them", "their",
        "we", "you", "your", "our", "all", "each", "every", "some", "any",
        "not", "no", "nor", "none", "very", "just", "about", "above", "after",
        "again", "against", "between", "down", "during", "from", "into", "off",
        "over", "through", "under", "up", "out", "as", "if", "than", "so", "also",
        "too", "well", "now", "then", "here", "there", "when", "where", "why",
        "how", "what", "which", "who", "whom", "when", "skill", "skills", "expert",
    }
    
    words = text.replace("-", " ").replace("_", " ").split()
    words = [w.strip(",.!?();:[]{}'\"") for w in words]
    words = [w for w in words if len(w) > 2 and w not in stopwords]
    return set(words)


def score_skill_for_leaf(skill_keywords, leaf):
    """Score how well a skill matches a leaf node using keyword overlap."""
    # Build leaf keywords from its name and path
    leaf_text = " ".join(leaf["path_list"]).lower()
    leaf_keywords = set(leaf_text.split())
    leaf_keywords = {w.strip(",.!?()-") for w in leaf_keywords if len(w.strip(",.!?()-")) > 2}
    
    overlap = skill_keywords & leaf_keywords
    return len(overlap)


def assign_skills_to_tree(tree, new_skills):
    """Assign new skills to best-matching leaf nodes in the tree."""
    leaves = flatten_tree(tree)
    
    unassigned = []
    assigned = defaultdict(list)
    
    for skill in new_skills:
        skill_keywords = build_keywords(skill["description"], skill["tags"])
        
        if not skill_keywords:
            unassigned.append((skill, "No keywords extracted"))
            continue
        
        # Score against each leaf
        scored = [(score_skill_for_leaf(skill_keywords, leaf), leaf) for leaf in leaves]
        scored.sort(key=lambda x: -x[0])
        
        best_score, best_leaf = scored[0]
        
        if best_score > 0:
            assigned[best_leaf["node_id"]].append(skill)
        else:
            unassigned.append((skill, f"No match (best: {best_leaf['path']}, score={best_score})"))
    
    return assigned, unassigned


def add_skills_to_tree_node(node, skills_to_add):
    """Add skills to a tree node's skills list."""
    existing_names = set()
    for sk in node.get("skills", []):
        if isinstance(sk, dict):
            existing_names.add(sk.get("name", "").lower().strip())
        elif isinstance(sk, str):
            existing_names.add(sk.lower().strip())
    
    for skill in skills_to_add:
        if skill["name"].lower().strip() not in existing_names:
            entry = {
                "name": skill["name"],
                "description": skill["description"][:200],
                "source": "aas",
                "license": skill["license"],
            }
            node.setdefault("skills", []).append(entry)
            existing_names.add(skill["name"].lower().strip())


def find_node_by_id(node, node_id):
    """Find a tree node by its id."""
    if node.get("id") == node_id:
        return node
    for child in node.get("children", []):
        result = find_node_by_id(child, node_id)
        if result:
            return result
    return None


def main():
    parser = argparse.ArgumentParser(description="Extend capability tree with new AAS skills")
    parser.add_argument("--execute", action="store_true", help="Actually write updated tree")
    parser.add_argument("--target", choices=["ship-safe", "full", "both"], default="ship-safe",
                        help="Which tree to update (default: ship-safe)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🌲 Extending Capability Tree with AAS Skills")
    print("=" * 60)
    
    # Load existing tree
    tree_path = SHIP_TREE if args.target in ("ship-safe", "both") else FULL_TREE
    print(f"\n📂 Loading {args.target} tree from: {tree_path.name}")
    
    with open(tree_path) as f:
        tree = yaml.safe_load(f)
    
    leaves = flatten_tree(tree)
    total_existing = sum(len(l["existing_names"]) for l in leaves)
    print(f"   {len(leaves)} leaf nodes, {total_existing} existing skills")
    
    # Collect new skills
    print(f"\n📂 Scanning community skills...")
    all_skills = collect_skills()
    
    # Get existing names from tree
    existing_in_tree = set()
    for leaf in leaves:
        existing_in_tree |= leaf["existing_names"]
    
    # Also check hermes skills (those in the tree already)
    new_skills = [s for s in all_skills if s["name"].lower().strip() not in existing_in_tree]
    
    print(f"   {len(all_skills)} total skills in community_skills/")
    print(f"   {len(new_skills)} new skills not yet in tree")
    
    if not new_skills:
        print("\n✅ All skills already in tree — nothing to do.")
        return 0
    
    # Assign to leaves
    print(f"\n📊 Assigning {len(new_skills)} skills to tree nodes by keyword matching...")
    assigned, unassigned = assign_skills_to_tree(tree, new_skills)
    
    total_assigned = sum(len(v) for v in assigned.values())
    print(f"   ✅ {total_assigned} assigned to {len(assigned)} tree nodes")
    print(f"   ⚠️  {len(unassigned)} unassigned (no keyword match)")
    
    if unassigned and not args.execute:
        print(f"\n   Sample unassigned:")
        for skill, reason in unassigned[:5]:
            print(f"     - {skill['name']} ({reason})")
    
    # Report per-node
    print(f"\n📊 Assignment breakdown (top 10 nodes):")
    node_counts = [(len(v), k) for k, v in assigned.items()]
    node_counts.sort(key=lambda x: -x[0])
    for count, node_id in node_counts[:10]:
        node = find_node_by_id(tree, node_id)
        node_name = node.get("name", node_id) if node else node_id
        print(f"   {count} → {node_name} ({node_id})")
    
    # === Write updated tree ===
    if args.execute:
        print(f"\n📝 Writing updated tree...")
        
        # Add skills to tree nodes
        for node_id, skills_to_add in assigned.items():
            node = find_node_by_id(tree, node_id)
            if node:
                add_skills_to_tree_node(node, skills_to_add)
        
        # Add unassigned to "Other" catch-all
        if unassigned:
            unassigned_skills = [s for s, _ in unassigned]
            # Find or create a misc node
            for child in tree.get("children", []):
                if child.get("id") == "other" or child.get("name", "").lower() == "other":
                    add_skills_to_tree_node(child, unassigned_skills)
                    print(f"   Added {len(unassigned_skills)} unassigned to '{child.get('name')}'")
                    break
        
        # Write
        if args.target in ("ship-safe", "both"):
            out = SHIP_TREE
            with open(out, "w") as f:
                yaml.dump(tree, f, default_flow_style=False, sort_keys=False)
            print(f"   ✅ Updated ship-safe tree: {out}")
        
        if args.target in ("full", "both"):
            with open(FULL_TREE) as f:
                full_tree = yaml.safe_load(f)
            for node_id, skills_to_add in assigned.items():
                node = find_node_by_id(full_tree, node_id)
                if node:
                    add_skills_to_tree_node(node, skills_to_add)
            with open(FULL_TREE, "w") as f:
                yaml.dump(full_tree, f, default_flow_style=False, sort_keys=False)
            print(f"   ✅ Updated full tree: {FULL_TREE}")
        
        # Verify
        updated_leaves = flatten_tree(tree)
        updated_total = sum(len(l["existing_names"]) for l in updated_leaves)
        print(f"   📊 Tree now has {updated_total} skills")
        
    else:
        print(f"\n   💡 Run with --execute to write the updated tree\n")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📋 SUMMARY")
    print(f"{'='*60}")
    print(f"   New skills added to tree: {total_assigned}")
    print(f"   Unassigned (need manual): {len(unassigned)}")
    print(f"   Tree total before: {total_existing}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
