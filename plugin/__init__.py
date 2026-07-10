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

logger = logging.getLogger(__name__)

_DISABLE_ENV = "SKILL_RETRIEVER_DISABLE"

# Lazy-loaded singletons
_searcher = None
_scanner = None


def _get_scanner():
    """Lazy-load the skill scanner function."""
    global _scanner
    if _scanner is None:
        from skill_retriever.scanner import scan_hermes_skills
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
    from skill_retriever.config import (
        CAPABILITY_TREE_PATH,
        LLM_MODEL as _cfg_model,
        LLM_API_KEY as _cfg_key,
        LLM_BASE_URL as _cfg_url,
    )

    # Use the pre-built tree from skill_retriever/data or fall back to
    # the bundled tree in the retriever package.
    tree_path = os.environ.get(
        "SKILL_RETRIEVER_TREE_PATH",
        str(CAPABILITY_TREE_PATH),
    )

    # Read LLM config from config.py (which auto-discovers Hermes provider)
    # with env var override on top.
    model = os.environ.get("SKILL_RETRIEVER_LLM_MODEL", _cfg_model)
    api_key = os.environ.get("SKILL_RETRIEVER_LLM_API_KEY", _cfg_key)
    base_url = os.environ.get("SKILL_RETRIEVER_LLM_BASE_URL", _cfg_url)

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
        # If using a custom base_url and the model lacks a provider prefix,
        # wrap it with "openai/" so litellm routes through the OpenAI-compatible
        # adapter instead of trying to match a built-in provider.
        if _searcher and _searcher.base_url and _searcher.model and "/" not in _searcher.model:
            _searcher.model = f"openai/{_searcher.model}"
    except Exception as e:
        logger.warning(
            "skill-retriever: failed to initialize searcher: %s. "
            "Skill hints will be disabled.",
            e,
        )
        _searcher = None

    return _searcher


# ── Intent classification ──────────────────────────────────────────────

# Intent detection: keyword pattern → intent label.
# Intents trigger capability-chain bundles that the retriever injects
# regardless of individual embedding scores. This compensates for the
# fact that "subagent-driven-development" doesn't semantically match
# "build a web app" even though it's the correct next step.
_INTENT_PATTERNS: dict[str, list[str]] = {
    "large_build": [
        "build a", "create a", "from scratch", "fully featured",
        "complete app", "full application", "new project", "new repo",
        "scaffold", "boilerplate", "greenfield", "fullstack",
        "monorepo", "many features", "multi-page", "complex app",
    ],
    "code_review": [
        "review", "audit", "inspect", "evaluate", "assess",
        "code quality", "security audit", "check for", "find bugs",
        "qa", "quality assurance",
    ],
    "large_refactor": [
        "refactor", "rewrite", "restructure", "clean up", "reorganize",
        "split up", "decouple", "extract module", "migrate",
        "upgrade all", "across many files",
    ],
    "deploy": [
        "deploy", "ship", "release", "publish", "launch",
        "go live", "production", "docker", "containerize",
    ],
}

# Capability chain bundles: intent → [(skill_name, loading_priority, why)]
# Priority: 1=must load, 2=should load, 3=consider
_CAPABILITY_CHAINS: dict[str, list[tuple[str, int, str]]] = {
    "large_build": [
        ("writing-plans", 1, "architecture and phased planning before any code"),
        ("subagent-driven-development", 1, "parallel delegation for multi-file builds"),
        ("codebase-ingestion", 2, "index the repo for semantic code search"),
        ("code-quality-audit", 2, "language-agnostic quality checks before commits"),
        ("test-driven-development", 2, "TDD: tests first, then code, then refactor"),
        ("search-first", 3, "research existing tools before building custom"),
        ("web-app-factory", 3, "repeatable web app build workflow"),
        ("docker-patterns", 3, "containerize if deploying"),
    ],
    "code_review": [
        ("code-quality-audit", 1, "structured code quality and security checks"),
        ("requesting-code-review", 1, "pre-commit security scan and quality gates"),
        ("simplify-code", 2, "parallel 3-agent cleanup of recent changes"),
        ("fec-e2e-testing", 2, "real-browser E2E tests with Playwright"),
        ("playwright-best-practices", 3, "battle-tested testing patterns"),
        ("dogfood", 3, "exploratory QA and bug hunting"),
    ],
    "large_refactor": [
        ("codebase-exploration", 1, "semantic search to understand the codebase"),
        ("simplify-code", 1, "parallel review for reuse, quality, efficiency"),
        ("subagent-driven-development", 2, "parallel subagents for independent files"),
        ("test-driven-development", 2, "tests before and after refactoring"),
        ("systematic-debugging", 3, "4-phase root cause if the refactor exposes bugs"),
    ],
    "deploy": [
        ("deployment-patterns", 1, "CI/CD, Docker, health checks, rollback"),
        ("cloudflare-tunnel", 2, "expose local services via Cloudflare"),
        ("code-quality-audit", 2, "pre-deploy quality gate"),
        ("canary-watch", 3, "post-deploy monitoring for regressions"),
    ],
}

# Behavioral nudge snippets: one-line imperatives per intent
# Injected after the skill hints to bridge the selection→execution gap.
_BEHAVIORAL_NUDGES: dict[str, str] = {
    "large_build": (
        "For multi-file builds: plan the architecture first, "
        "delegate parallel workstreams via delegate_task, "
        "then run a quality gate before committing."
    ),
    "code_review": (
        "For reviews: load the quality-audit skill, run its checks, "
        "then use browser or e2e tests to verify, not just manual inspection."
    ),
    "large_refactor": (
        "For refactors: index the codebase first for semantic search, "
        "run tests before touching code, delegate independent files in parallel, "
        "run the full test suite after each batch."
    ),
    "deploy": (
        "For deploys: verify all tests pass, run pre-deploy quality checks, "
        "ensure health-check endpoints exist, monitor for regressions after shipping."
    ),
}


def _detect_intent(message: str) -> str | None:
    """Classify user query into an intent label via keyword pattern matching.

    Returns None when no intent is detected (skip injection).
    Multiple intents: first match wins, ordered by specificity.
    """
    msg_lower = message.lower()
    # Code review before general build — "review this code and build" should catch review
    for intent in ("code_review", "large_refactor", "deploy"):
        for pattern in _INTENT_PATTERNS[intent]:
            if pattern in msg_lower:
                return intent
    # "large_build" requires at least ONE build keyword AND either scope or scale signal
    build_hit = any(p in msg_lower for p in _INTENT_PATTERNS["large_build"])
    has_scope = len(message.split()) > 5  # short queries aren't "large" builds
    if build_hit and has_scope:
        return "large_build"
    return None


def _build_hint_block(
    skills: list[tuple[str, int, str]], intent: str | None
) -> str:
    """Format a capability chain into a natural-language hint block.

    Includes a behavioral nudge when intent is recognized.
    """
    parts = [
        "[Skill Capability Chain]",
        "",
        "These skills form a complete workflow for this type of task.",
        "Load the priority-1 skills first, then others as needed.",
        "Call skill_view('<name>') to load each one.",
        "",
    ]
    for name, pri, why in skills:
        marker = {1: "★", 2: "▸", 3: "·"}[pri]
        parts.append(f"  {marker} **{name}** — {why}")
    parts.append("")

    if intent and intent in _BEHAVIORAL_NUDGES:
        parts.append(f"[Workflow note] {_BEHAVIORAL_NUDGES[intent]}")
        parts.append("")

    return "\n".join(parts)


# ── Hook ────────────────────────────────────────────────────────────────

def _on_pre_llm_call(*, user_message: str = "", **_kwargs) -> dict | None:
    """Run skill retrieval and inject hints into the user message.

    Two pathways, both fire independently:
      1. LLM tree navigation (Searcher) — if available, augments the bundle
      2. Capability chain injection — intent-aware bundles (primary path)

    This hook fires before every LLM turn. Hints are prepended to the
    user message as natural-language instructions.
    """
    if os.environ.get(_DISABLE_ENV, "").lower() in ("1", "true", "yes"):
        return None
    if not user_message or not user_message.strip():
        return None
    if len(user_message.strip()) < 10:
        return None

    try:
        # ── Path 1: Intent-aware capability chain (always runs) ─────────
        intent = _detect_intent(user_message)
        chain_skills = _CAPABILITY_CHAINS.get(intent, []) if intent else []

        if not chain_skills:
            return None

        hint_block = _build_hint_block(chain_skills, intent)

        # ── Path 2 (skipped in hook — tree search is available via CLI) ─
        # The deep AgentSkillOS tree search requires ~15-60s and is meant
        # for the `skill-retriever search` CLI command, not the real-time
        # pre_llm_call hook. Only the capability chain runs here.

        logger.info(
            "skill-retriever: intent=%s chain_skills=%d",
            intent, len(chain_skills),
        )
        return {"context": hint_block}

    except Exception as e:
        logger.debug("skill-retriever hook failed (non-fatal): %s", e)
        return None


def register(ctx) -> None:
    """Register the pre_llm_call hook with the Hermes plugin system."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    logger.info("skill-retriever plugin registered (pre_llm_call hook)")
