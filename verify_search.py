"""Verify skill-retriever backbone: tree search returns correct results."""
import sys
sys.path.insert(0, "/home/sc/workspace/skill-retriever/src")

from skill_retriever.search.searcher import Searcher
from skill_retriever.config import _discover_hermes_llm_config, CAPABILITY_TREE_PATH
import inspect

key, url, model = _discover_hermes_llm_config()
print(f"LLM: key={'yes' if key else 'NO'}, url={url}, model={model}")
print(f"Tree: {CAPABILITY_TREE_PATH} (exists={CAPABILITY_TREE_PATH.exists()})")

# Find correct search signature
sig = inspect.signature(Searcher.search)
print(f"search signature: {sig}")

s = Searcher(tree_path=CAPABILITY_TREE_PATH, model=model, api_key=key, base_url=url)
r = s.search("deploy a cloudflare tunnel")
skills = r.selected_skills
names = [sk["name"] for sk in skills[:8]]
print(f"Results ({len(names)}): {names}")
print(f"LLM calls: {r.llm_calls}")

good = any("cloudflare" in n or "deploy" in n or "docker" in n for n in names)
print(f"RELEVANT: {'YES' if good else 'NO'}")
