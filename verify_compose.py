"""Test the composer with a real query."""
import sys
sys.path.insert(0, "/home/sc/workspace/skill-retriever/src")

from skill_retriever.compose import compose_skills, bundle_to_hint_block

query = "deploy a cloudflare tunnel"
print(f"Query: {query}\n")

bundle = compose_skills(query)
if bundle:
    print(f"Bundle ({len(bundle)} skills):")
    for item in bundle:
        print(f"  {item.get('load_as'):8} {item.get('name'):30} conf={item.get('confidence','?'):6}  {item.get('reason','')[:60]}")
    print()
    print("Hint block:")
    print(bundle_to_hint_block(bundle))
else:
    print("No bundle returned")
