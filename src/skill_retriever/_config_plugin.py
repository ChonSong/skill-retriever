"""Minimal config for skill-retriever — provides the variables that
AgentSkillOS's skill_retriever module expects without needing the
full AgentSkillOS config infrastructure.

Uses environment variables for LLM credentials (borrow-mode by default).
This is the development entry point; the production copy lives at
skill_retriever/_config_plugin.py.
"""

import os
from pathlib import Path

# ── Project paths ──
PROJECT_ROOT = Path(__file__).parent.parent
SKILL_RETRIEVER_CACHE_DIR = Path(
    os.environ.get("SKILL_RETRIEVER_CACHE_DIR",
                   str(Path.home() / ".hermes" / "skill-retriever-cache"))
)
SKILLS_DIR = Path(
    os.environ.get("SKILLS_DIR",
                   str(Path.home() / ".hermes" / "skills"))
)

# ── LLM config (borrow-mode: defaults read from env, plugin overrides with ctx.llm) ──
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


# ── Cache helper ──
def ensure_cache():
    """Create cache directory if it doesn't exist."""
    SKILL_RETRIEVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return SKILL_RETRIEVER_CACHE_DIR
