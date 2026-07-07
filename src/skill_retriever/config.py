"""
Skill Retriever configuration.

Imports common settings from unified config, adds module-specific paths.
"""
from pathlib import Path

import litellm

# Import from unified config
from config import (
    SKILLS_DIR,
    PROJECT_ROOT,
    LLM_MODEL,
    LLM_BASE_URL,
    LLM_API_KEY,
    LLM_MAX_RETRIES,
    BRANCHING_FACTOR,
    PRUNE_ENABLED,
    TREE_BUILD_MAX_WORKERS,
    # Tree building
    TREE_BUILD_CACHING,
    TREE_BUILD_NUM_RETRIES,
    TREE_BUILD_TIMEOUT,
    MAX_DEPTH,
    # Search
    SEARCH_MAX_PARALLEL,
    SEARCH_TEMPERATURE,
    SEARCH_TIMEOUT,
    SEARCH_CACHING,
)

# Re-export for backward compatibility
__all__ = [
    "SKILLS_DIR",
    "PROJECT_ROOT",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_MAX_RETRIES",
    "BRANCHING_FACTOR",
    "PRUNE_ENABLED",
    "TREE_BUILD_MAX_WORKERS",
    "TREE_BUILD_CACHING",
    "TREE_BUILD_NUM_RETRIES",
    "TREE_BUILD_TIMEOUT",
    "MAX_DEPTH",
    "SEARCH_MAX_PARALLEL",
    "SEARCH_TEMPERATURE",
    "SEARCH_TIMEOUT",
    "SEARCH_CACHING",
    "CAPABILITY_TREE_PATH",
    "ADAPTIVE_SEARCH_ENABLED",
    "ensure_cache",
]

# ===== Module-specific Configuration =====
MODULE_DIR = Path(__file__).parent
CAPABILITY_TREE_PATH = MODULE_DIR / "capability_tree" / "tree.yaml"

# Whether to enable adaptive layer selection based on tree size
ADAPTIVE_SEARCH_ENABLED = True

# ===== LiteLLM Cache =====
_cache_initialized = False


def ensure_cache():
    """Ensure LiteLLM disk cache is initialized"""
    global _cache_initialized
    if not _cache_initialized:
        try:
            from litellm.caching.caching import Cache
            cache_dir = MODULE_DIR / ".litellm_cache"
            litellm.cache = Cache(type="disk", disk_cache_dir=str(cache_dir))
        except Exception:
            pass  # Continue running if cache is unavailable
        _cache_initialized = True
