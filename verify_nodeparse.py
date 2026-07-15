"""Verify if tree search gets parseable JSON from the LLM at each level."""
import sys, json, re
sys.path.insert(0, "/home/sc/workspace/skill-retriever/src")

from skill_retriever.tree.prompts import NODE_SELECTION_PROMPT
from skill_retriever.tree.schema import TreeNode
from skill_retriever.config import _discover_hermes_llm_config, CAPABILITY_TREE_PATH
import yaml, litellm

key, url, model_str = _discover_hermes_llm_config()

# Load tree and get first-level node children for a test
with open(CAPABILITY_TREE_PATH) as f:
    tree = yaml.safe_load(f)

# Simulate root node selection prompt
children = tree.get("children", [])[:3]  # first 3 child nodes
print(f"Root has {len(tree.get('children',[]))}, testing first {len(children)}")

# Build a simple prompt
options = "\n".join(f"- {c['id']}: {c['description'][:100]}" for c in children)
prompt = f"Query: deploy a cloudflare tunnel\nChoose category:\n{options}\nReturn JSON list of category IDs."
print(f"\nPrompt:\n{prompt}\n")

# Call LLM with correct key
model = f"openai/{model_str}" if "/" not in model_str else model_str
resp = litellm.completion(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    api_key=key,
    api_base=url,
    max_tokens=200,
    timeout=15,
)
msg = resp.choices[0].message
text = msg.content or msg.reasoning_content or ""

print(f"LLM response ({len(text)} chars):")
print(text[:1000])
print()

# Try to parse JSON
try:
    ids = json.loads(text)
    print(f"Parsed JSON: {ids}")
except:
    ids = re.findall(r'"([^"]+)"', text)
    print(f"Fallback parse (quoted strings): {ids}")
