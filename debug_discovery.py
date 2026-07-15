"""Debug the LLM config discovery."""
import sys
sys.path.insert(0, "/home/sc/workspace/skill-retriever/src")

# Force reimport
import importlib
import skill_retriever.config as cfg_mod
importlib.reload(cfg_mod)

# Manually trace the discovery
from pathlib import Path
import yaml

cfg_path = Path.home() / ".hermes" / "config.yaml"
cfg = yaml.safe_load(cfg_path.read_text())
model_cfg = cfg.get("model", {})
custom_providers = cfg.get("custom_providers", [])

base_url = model_cfg.get("base_url") or None
provider = (model_cfg.get("provider") or "").strip()
default_model = model_cfg.get("default") or "gpt-4o-mini"

print(f"model_cfg: base_url={base_url!r}, provider={provider!r}, default={default_model!r}")
print(f"custom_providers ({len(custom_providers)} entries):")
for cp in custom_providers:
    print(f"  - name={cp.get('name')!r}, base_url={cp.get('base_url')!r}, api_key={cp.get('api_key','')[:8]}...")

# Now check what _discover_hermes_llm_config returns
import os
print("\nEnv OPENAI_API_KEY:", "yes" if os.environ.get("OPENAI_API_KEY") else "no")
key, url, model = cfg_mod._discover_hermes_llm_config()
print(f"Discovery: key={bool(key)}, url={url!r}, model={model!r}")
