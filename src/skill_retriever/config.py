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

def _load_dotenv_into(target: dict[str, str]):
    """Merge Hermes .env vars into *target* (in-place) if not already set."""
    dotenv_path = Path.home() / ".hermes" / ".env"
    if not dotenv_path.exists():
        return
    try:
        for line in dotenv_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and v and k not in target:
                    target[k] = v
    except Exception:
        pass


def _probe_key(api_key: str, base_url: str | None, model: str, timeout: int = 5) -> bool:
    """Quick check — does this key work? Returns True on any 2xx.
    Silent on failure (no logging or exceptions raised).
    """
    try:
        import json, urllib.request, urllib.error
        target = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }).encode()
        req = urllib.request.Request(
            target, data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "skill-retriever/1.0",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except urllib.error.HTTPError as e:
        # 401/403 → bad key.  429/5xx → transient, skip
        return e.code < 400
    except Exception:
        return False


def _discover_hermes_llm_config():
    """Read Hermes config.yaml + .env to auto-discover a working LLM config.

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

        # ── Merge .env into process env (Hermes sources it there but
        #     subprocesses don't always inherit) ──
        _load_dotenv_into(os.environ)

        env_openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        env_openai_url = os.environ.get("OPENAI_BASE_URL", "").strip()

        custom_providers = cfg.get("custom_providers", []) or []

        # Find the custom_providers entry matching model.provider
        matched_cp = None
        if provider and isinstance(custom_providers, list):
            prov_slug = provider.split(":")[-1].strip().lower()
            for cp in custom_providers:
                cp_name = (cp.get("name") or "").strip().lower()
                cp_slug = cp_name.replace(" ", "").replace("_", "").replace("-", "")
                if cp_slug and (cp_slug == prov_slug or cp_slug in prov_slug or prov_slug in cp_slug):
                    matched_cp = cp
                    break

        # ── 2. Matched custom_providers entry (key + base_url) ──
        if matched_cp:
            cp_key = (matched_cp.get("api_key") or "").strip()
            cp_url = (matched_cp.get("base_url") or "").strip()
            if cp_key and cp_url:
                return cp_key, cp_url, default_model

        # ── 4. OPENAI_API_KEY env var + OPENAI_BASE_URL ──
        if env_openai_key:
            return env_openai_key, (env_openai_url or base_url), default_model

        # ── 5. NOUS_API_KEY + first available base_url ──
        nous = os.environ.get("NOUS_API_KEY", "").strip()
        if nous:
            if isinstance(custom_providers, list):
                for cp in custom_providers:
                    cp_url = (cp.get("base_url") or "").strip()
                    if cp_url:
                        return nous, cp_url, default_model
            return nous, base_url, default_model

        return None, None, None
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
