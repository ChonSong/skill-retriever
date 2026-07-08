"""skill-retriever — AgentSkillOS-powered skill retrieval for Hermes Agent.

Wires one behaviour via the Hermes plugin system:

    pre_llm_call hook — on each user query, runs the AgentSkillOS retrieval
    pipeline (capability tree + LLM node selection) and injects top-5 skill
    hints into the user message as natural-language instructions.

Modes:
    Borrow-mode (default): Uses Hermes' active LLM credentials for the
    retrieval gate. Reads OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
    from the environment. Zero additional configuration.

Quirks:
    - pre_llm_call context is PREPENDED to the user message, not the system prompt.
    - Cannot intercept skill_view or available_skills — we inject instructions
      telling the LLM which skills to manually load via skill_view(name).
    - The LLM has final authority to ignore hints.

Env:
    SKILL_RETRIEVER_DISABLE=1        — disable entirely
    SKILL_RETRIEVER_LLM_MODEL        — override LLM model (default: gpt-4o)
    SKILL_RETRIEVER_CACHE_DIR        — override cache dir (default: ~/.hermes/skill-retriever-cache)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_DISABLE_ENV = "SKILL_RETRIEVER_DISABLE"

# Ensure src/ is importable when running as a Hermes plugin
_plugin_dir = Path(__file__).parent.parent
_src_dir = _plugin_dir / "src"
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

# Lazy-loaded singletons
_searcher = None
_scanner = None


def _get_scanner():
    """Lazy-load the skill scanner function."""
    global _scanner
    if _scanner is None:
        from skill_retriever._scanner_plugin import scan_hermes_skills
        _scanner = scan_hermes_skills
    return _scanner


def _get_searcher():
    """Lazy-load the Searcher singleton from skill_retriever.

    On first call, initializes the Searcher with the capability tree
    and loads skill metadata. The tree is built once and cached to disk.

    LLM credentials are read from the environment (borrow-mode):
        OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    or the skill-retriever-specific env vars:
        SKILL_RETRIEVER_LLM_API_KEY, SKILL_RETRIEVER_LLM_BASE_URL,
        SKILL_RETRIEVER_LLM_MODEL
    """
    global _searcher
    if _searcher is not None:
        return _searcher

    from skill_retriever.search.searcher import Searcher
    from skill_retriever.config import CAPABILITY_TREE_PATH

    # Use the pre-built tree from skill_retriever/data or fall back to
    # the bundled tree in the retriever package.
    tree_path = os.environ.get(
        "SKILL_RETRIEVER_TREE_PATH",
        str(CAPABILITY_TREE_PATH),
    )

    model = os.environ.get(
        "SKILL_RETRIEVER_LLM_MODEL",
        os.environ.get("OPENAI_MODEL", "gpt-4o"),
    )
    api_key = os.environ.get(
        "SKILL_RETRIEVER_LLM_API_KEY",
        os.environ.get("OPENAI_API_KEY", ""),
    )
    base_url = os.environ.get(
        "SKILL_RETRIEVER_LLM_BASE_URL",
        os.environ.get("OPENAI_BASE_URL", None),
    )

    logger.info(
        "skill-retriever: initializing searcher (model=%s, tree=%s)",
        model, tree_path,
    )

    try:
        _searcher = Searcher(
            tree_path=tree_path,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
    except Exception as e:
        logger.warning(
            "skill-retriever: failed to initialize searcher: %s. "
            "Skill hints will be disabled.",
            e,
        )
        _searcher = None

    return _searcher


def _on_pre_llm_call(*, user_message: str = "", **_kwargs) -> dict | None:
    """Run skill retrieval and inject hints into the user message.

    This hook fires before every LLM turn. We run the AgentSkillOS
    retrieval pipeline and, if confident results are found, prepend
    a natural-language hint block telling the LLM which skills may help.
    """
    if os.environ.get(_DISABLE_ENV, "").lower() in ("1", "true", "yes"):
        return None
    if not user_message or not user_message.strip():
        return None
    # Skip very short queries — they're usually greetings or follow-ups
    if len(user_message.strip()) < 10:
        return None

    try:
        searcher = _get_searcher()
        if searcher is None:
            return None

        # Run the multi-level tree search
        result = searcher.search(user_message)

        if not result or not result.selected_skills:
            logger.debug(
                "skill-retriever: no skills found for query (llm_calls=%d)",
                result.llm_calls if result else 0,
            )
            return None

        # Helper for source badge
        _SOURCE_BADGE = {
            "hermes": "🔒hermes",
            "community": "🌐community",
            "anthropic": "⭐anthropic",
        }

        # Format as natural-language hints with source + safety badges
        hints = []
        for skill in result.selected_skills[:5]:
            name = skill.get("name", skill.get("id", "unknown"))
            desc = skill.get("description", "")
            source = skill.get("source", "community")
            safety = skill.get("safety", "clean")
            badge = _SOURCE_BADGE.get(source, source)
            safety_tag = "" if safety == "clean" else " ⚠️"
            hints.append(f"{len(hints)+1}. **{name}** [{badge}{safety_tag}] — {desc}")

        if not hints:
            return None

        hint_block = (
            "[Skill Retrieval Hint]\n"
            "The following skills were semantically matched to this query.\n"
            "If any seem useful, call skill_view('<name>') to load it.\n"
            "If none apply, ignore this hint entirely.\n\n"
            + "\n".join(hints)
            + "\n"
        )

        logger.info(
            "skill-retriever: injected %d skill hints (llm_calls=%d)",
            len(hints), result.llm_calls,
        )
        return {"context": hint_block}

    except Exception as e:
        logger.debug("skill-retriever hook failed (non-fatal): %s", e)
        return None


def register(ctx) -> None:
    """Register the pre_llm_call hook with the Hermes plugin system."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    logger.info("skill-retriever plugin registered (pre_llm_call hook)")
