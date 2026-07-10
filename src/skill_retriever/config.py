"""Skill Retriever configuration — env-based, borrow-mode defaults.

All settings read from environment variables with sensible defaults.
No YAML, no dataclasses, no AgentSkillOS config coupling.
"""

import os
from pathlib import Path

import litellm

# ── Project paths ──
MODULE_DIR = Path(__file__).parent  # src/skill_retriever/
PROJECT_ROOT = MODULE_DIR  # package root for path resolution
CAPABILITY_TREE_PATH = MODULE_DIR / "capability_tree" / "tree_10000_ship_safe.yaml"

SKILL_RETRIEVER_CACHE_DIR = Path(
    os.environ.get("SKILL_RETRIEVER_CACHE_DIR",
                   str(Path.home() / ".hermes" / "skill-retriever-cache"))
)
SKILLS_DIR = Path(
    os.environ.get("SKILLS_DIR",
                   str(Path.home() / ".hermes" / "skills"))
)

# ── LLM config (borrow-mode) ──
# Priority chain:
#   1. SKILL_RETRIEVER_LLM_* env vars (explicit per-plugin config)
#   2. OPENAI_* env vars (standard OpenAI-compatible)
#   3. Hermes config.yaml + Hermes env vars (auto-detect)

def _discover_hermes_llm_config():
    """Read Hermes config.yaml to auto-discover the active LLM provider.

    Returns (api_key, base_url, model) or (None, None, None).
    """
    try:
        import yaml
        cfg_path = Path.home() / ".hermes" / "config.yaml"
        if not cfg_path.exists():
            return None, None, None
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        model_cfg = cfg.get("model", {})
        base_url = model_cfg.get("base_url") or None
        provider = (model_cfg.get("provider") or "").strip()
        default_model = model_cfg.get("default") or "gpt-4o-mini"

        # Normalize provider name to env-var convention:
        #   "opencode-go"   → "OPENCODE_GO"
        #   "openrouter2"   → "OPENROUTER2"
        #   "opencode-zen"  → "OPENCODE_ZEN"
        #   "nous"          → "NOUS"
        norm = provider.upper().replace("-", "_").replace(".", "_")

        # Check for pooled keys: {NORM}_API_KEY_{1..N} (common in Hermes)
        # Try in descending order (higher index = newer keys in round-robin pool)
        # and verify the key works with a lightweight API call
        candidate_keys: list[str] = []
        for k, v in sorted(os.environ.items(), reverse=True):
            if k.startswith(f"{norm}_API_KEY") and v.strip():
                candidate_keys.append(v.strip())

        # Fallback: NOUS_API_KEY is the most common single-key env var
        if not candidate_keys:
            nous = os.environ.get("NOUS_API_KEY", "")
            if nous.strip():
                candidate_keys.append(nous.strip())

        # Try candidates until one works (lightweight chat completion probe)
        api_key = ""
        for ck in candidate_keys:
            try:
                import urllib.request, json, urllib.error
                # Use a minimal chat completion to verify the key works
                # (models list can return 200 even for rate-limited keys)
                probe_data = json.dumps({
                    "model": default_model or "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                }).encode()
                test_url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
                req = urllib.request.Request(
                    test_url,
                    data=probe_data,
                    headers={
                        "Authorization": f"Bearer {ck}",
                        "Content-Type": "application/json",
                        "User-Agent": "curl/8.0",
                    },
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
                api_key = ck
                break
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                continue
            except Exception:
                continue

        return api_key, base_url, default_model
    except Exception:
        return None, None, None

_hermes_key, _hermes_url, _hermes_model = _discover_hermes_llm_config()

# Priority: SKILL_RETRIEVER_LLM_* > auto-discovered Hermes key > OPENAI_* env > default
# NOTE: _hermes_key must be checked BEFORE OPENAI_API_KEY because
# importing litellm sets OPENAI_API_KEY to a litellm-internal value,
# which would shadow the correctly discovered Hermes key.
LLM_MODEL = os.environ.get("SKILL_RETRIEVER_LLM_MODEL",
                            _hermes_model or
                            os.environ.get("OPENAI_MODEL", "gpt-4o"))
LLM_API_KEY = os.environ.get("SKILL_RETRIEVER_LLM_API_KEY",
                              _hermes_key or
                              os.environ.get("OPENAI_API_KEY", ""))
LLM_BASE_URL = os.environ.get("SKILL_RETRIEVER_LLM_BASE_URL",
                               _hermes_url or
                               os.environ.get("OPENAI_BASE_URL", None))
LLM_MAX_RETRIES = int(os.environ.get("SKILL_RETRIEVER_LLM_MAX_RETRIES", "3"))

# ── Search behaviour ──
BRANCHING_FACTOR = int(os.environ.get("SKILL_RETRIEVER_BRANCHING_FACTOR", "3"))
PRUNE_ENABLED = os.environ.get("SKILL_RETRIEVER_PRUNE", "true").lower() in ("1", "true", "yes")
SEARCH_MAX_PARALLEL = int(os.environ.get("SKILL_RETRIEVER_MAX_PARALLEL", "5"))
SEARCH_TEMPERATURE = float(os.environ.get("SKILL_RETRIEVER_TEMPERATURE", "0.3"))
SEARCH_TIMEOUT = float(os.environ.get("SKILL_RETRIEVER_TIMEOUT", "600"))
SEARCH_CACHING = os.environ.get("SKILL_RETRIEVER_CACHING", "true").lower() in ("1", "true", "yes")
MAX_DEPTH = int(os.environ.get("SKILL_RETRIEVER_MAX_DEPTH", "5"))

# ── Tree building ──
TREE_BUILD_MAX_WORKERS = int(os.environ.get("SKILL_RETRIEVER_BUILD_WORKERS", "4"))
TREE_BUILD_CACHING = True
TREE_BUILD_NUM_RETRIES = 3
TREE_BUILD_TIMEOUT = 600.0

# ── Adaptive search (optional, disabled by default) ──
ADAPTIVE_SEARCH_ENABLED = os.environ.get(
    "SKILL_RETRIEVER_ADAPTIVE", ""
).lower() in ("1", "true", "yes")

# ── Public API ──
__all__ = [
    "SKILLS_DIR", "PROJECT_ROOT", "MODULE_DIR", "CAPABILITY_TREE_PATH",
    "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MAX_RETRIES",
    "BRANCHING_FACTOR", "PRUNE_ENABLED",
    "TREE_BUILD_MAX_WORKERS", "TREE_BUILD_CACHING", "TREE_BUILD_NUM_RETRIES", "TREE_BUILD_TIMEOUT",
    "MAX_DEPTH",
    "SEARCH_MAX_PARALLEL", "SEARCH_TEMPERATURE", "SEARCH_TIMEOUT", "SEARCH_CACHING",
    "ADAPTIVE_SEARCH_ENABLED", "ensure_cache",
]

# ── LiteLLM disk cache ──
_cache_initialized = False

def ensure_cache():
    """Initialize LiteLLM disk cache."""
    global _cache_initialized
    if not _cache_initialized:
        try:
            from litellm.caching.caching import Cache
            cache_dir = MODULE_DIR / ".litellm_cache"
            litellm.cache = Cache(type="disk", disk_cache_dir=str(cache_dir))
        except Exception:
            pass
        _cache_initialized = True
