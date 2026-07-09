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

# ── LLM config (borrow-mode: reads OPENAI_* env vars) ──
LLM_MODEL = os.environ.get("SKILL_RETRIEVER_LLM_MODEL",
                            os.environ.get("OPENAI_MODEL", "gpt-4o"))
LLM_API_KEY = os.environ.get("SKILL_RETRIEVER_LLM_API_KEY",
                              os.environ.get("OPENAI_API_KEY", ""))
LLM_BASE_URL = os.environ.get("SKILL_RETRIEVER_LLM_BASE_URL",
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
