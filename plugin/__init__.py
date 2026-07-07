"""skill-retriever — AgentSkillOS-powered skill retrieval for Hermes Agent.

Wires one behaviour via the Hermes plugin system:

    pre_llm_call hook — on each user query, runs the AgentSkillOS retrieval
    pipeline (capability tree + LLM node selection) and injects top-5 skill
    hints into the user message as natural-language instructions.

Modes:
    Borrow-mode (default): Uses the agent's active LLM via ctx.llm.complete().
    Zero additional API keys or cost.

Quirks:
    - pre_llm_call context is PREPENDED to the user message, not the system prompt.
    - Cannot intercept skill_view or available_skills — we inject instructions
      telling the LLM which skills to manually load via skill_view(name).
    - The LLM has final authority to ignore hints.

Env:
    SKILL_RETRIEVER_DISABLE=1        — disable entirely
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
_retriever = None
_scanner = None


def _get_scanner():
    """Lazy-load the skill scanner."""
    global _scanner
    if _scanner is None:
        from skill_scanner import scan_hermes_skills
        _scanner = scan_hermes_skills
    return _scanner


def _get_retriever():
    """Lazy-load the SkillRetriever singleton."""
    global _retriever
    if _retriever is None:
        from skill_retriever import SkillRetriever
        _retriever = SkillRetriever()
    return _retriever


def _on_pre_llm_call(*, user_message: str = "", ctx=None, **_kwargs) -> dict | None:
    """Run skill retrieval and inject hints into the user message.

    This hook fires before every LLM turn. We run the retrieval pipeline
    and, if confident results are found, prepend a natural-language hint
    block to the user message telling the LLM which skills may help.

    The LLM retains final authority — it can load suggested skills via
    skill_view(name) or ignore the hint entirely.
    """
    if os.environ.get(_DISABLE_ENV, "").lower() in ("1", "true", "yes"):
        return None
    if not user_message or not user_message.strip():
        return None

    try:
        retriever = _get_retriever()
        scanner = _get_scanner()

        # Ensure index is built (first call builds, subsequent calls are cached)
        skills = scanner()
        if not skills:
            logger.debug("skill-retriever: no skills found, skipping")
            return None

        retriever.ensure_index(skills)

        # Run retrieval — gets top-5 skill names with relevance scores
        results = retriever.search(user_message, top_k=5)

        if not results:
            logger.debug("skill-retriever: no results for query")
            return None

        # Format as natural-language hints the LLM can act on
        hint = _format_hint(results)
        return {"context": hint}

    except Exception as e:
        logger.debug("skill-retriever hook failed (non-fatal): %s", e)
        return None


def _format_hint(results: list) -> str:
    """Format retrieval results as a context block for the user message.

    We inject natural-language instructions because pre_llm_call context
    is prepended to the user message, NOT the system prompt. The LLM
    must decide to call skill_view() itself.
    """
    lines = [
        "[System — Skill Retrieval Hint]",
        "The following skills were found to be relevant to this query.",
        "If any seem useful, call skill_view('<name>') to load its full instructions.",
        "If none apply, ignore this hint entirely.",
        "",
    ]
    for i, r in enumerate(results, 1):
        name = r.get("name", "unknown")
        desc = r.get("description", "")
        score = r.get("score", 0)
        lines.append(f"{i}. **{name}** (relevance: {score:.2f}) — {desc}")

    lines.append("")
    return "\n".join(lines)


def register(ctx) -> None:
    """Register the pre_llm_call hook with the Hermes plugin system."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    logger.info("skill-retriever plugin registered (pre_llm_call hook)")
