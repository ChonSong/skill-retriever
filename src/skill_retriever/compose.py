#!/usr/bin/env python3
"""Skill Composer — single LLM call to curate a skill bundle from a query.

1. Cheap keyword pre-filter against flat_index.json (top 50 candidates)
2. One LLM call: "from these 50, pick 5-10 with reasons and confidence"
3. Returns bundle as JSON

This replaces the hardcoded capability chains in the pre_llm_call hook.

Closed loop: injects "previously useful for similar queries" context from
skill-usage.jsonl, so the composer learns from past success/failure.
"""
import json
import re
from pathlib import Path
from typing import Optional

from skill_retriever.config import (
    _discover_hermes_llm_config,
    LLM_MODEL,
    LLM_MAX_RETRIES,
    SEARCH_TEMPERATURE,
    SEARCH_TIMEOUT,
)
from concurrent.futures import ThreadPoolExecutor

FLAT_INDEX_PATH = Path.home() / ".hermes/skill-retriever-cache/flat_index.json"
USAGE_LOG_PATH = Path.home() / ".hermes/state/skill-usage.jsonl"

# Minimum quality signals for a skill to be considered high-quality
# (skills missing these get a 0.5x score penalty)
QUALITY_SIGNALS = ("has_steps", "has_verification", "has_pitfalls")

# Prompt template — loaded once (use {{ }} to escape literal braces)
SKILL_COMPOSER_PROMPT = """You are a skill curator for an AI agent. Given a user query and a list of available skills, choose the best workflow.

## Rules
- Return **valid JSON only** — no commentary, no markdown fences
- Choose 3-10 skills (fewer for simple queries, more for complex)
- Each skill needs: name, load_as (must/should/consider), reason (1 sentence), confidence (high/medium/low)
- Prefer class-level umbrella skills over narrow ones
- Skip skills with low relevance — don't pad the bundle
- If no skills match, return []
- If a skill was previously useful for a similar query, prioritize it

## Output format
[{{"name": "skill-name", "load_as": "must", "reason": "...", "confidence": "high"}}]

## Previously useful for similar queries
{previously_useful}

## Available Skills
{skill_list}

## User Query
{query}

## Bundle
"""


def _flat_index() -> list[dict]:
    """Load flat index from disk, lazy."""
    if not FLAT_INDEX_PATH.exists():
        return []
    with open(FLAT_INDEX_PATH) as f:
        return json.load(f)


def _load_usage_history(window_hours: int = 720) -> dict:
    """Load recent usage history from skill-usage.jsonl.

    Returns dict: skill_name -> {"useful": int, "irrelevant": int, "total": int}
    Only loads entries from the last `window_hours` (default 30 days).
    """
    if not USAGE_LOG_PATH.exists():
        return {}
    import time
    cutoff = time.time() - (window_hours * 3600)
    history = {}
    try:
        with open(USAGE_LOG_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("ts", 0) < cutoff:
                    continue
                name = entry.get("skill_name", "?")
                if name not in history:
                    history[name] = {"useful": 0, "irrelevant": 0, "harmful": 0, "total": 0}
                history[name]["total"] += 1
                signal = entry.get("outcome_signal")
                if signal in history[name]:
                    history[name][signal] += 1
    except Exception:
        pass
    return history


def _find_previously_useful(history: dict, query: str, top_k: int = 5) -> list[dict]:
    """Find skills that were useful for similar queries recently.

    Uses keyword matching against the query to find relevant past-successful skills.
    """
    tokens = set(re.findall(r'\w+', query.lower()))
    if not tokens:
        return []

    # Score each skill by: usefulness_ratio × keyword_overlap
    scored = []
    for name, stats in history.items():
        if stats["useful"] == 0:
            continue
        ratio = stats["useful"] / max(stats["total"], 1)
        # Name token overlap with query
        name_tokens = set(re.findall(r'\w+', name.lower()))
        overlap = len(tokens & name_tokens)
        if overlap == 0:
            continue
        score = ratio * overlap
        scored.append((score, name, stats))

    scored.sort(key=lambda x: -x[0])
    return [
        {"name": name, "useful_count": stats["useful"], "total_count": stats["total"]}
        for _, name, stats in scored[:top_k]
    ]


def _pre_filter(skills: list[dict], query: str, top_k: int = 50,
                  history: Optional[dict] = None) -> list[str]:
    """Cheap keyword pre-filter: match query tokens against skill name+description.

    Applies quality floor penalty for skills missing steps/verification/pitfalls.
    Previously-useful skills get a boost.

    Returns top_k skill entries as formatted strings for the LLM prompt.
    """
    tokens = set(re.findall(r'\w+', query.lower()))
    scored = []
    for s in skills:
        name = s.get("name", "")
        desc = s.get("description", "")
        tags = s.get("tags", [])
        text = f"{name} {' '.join(tags)} {desc}".lower()
        score = sum(1 for t in tokens if t in text)

        if score == 0:
            continue

        # Quality floor penalty: skills missing key signals lose half their score
        quality_flags = s.get("_quality", {})
        missing_quality = sum(1 for sig in QUALITY_SIGNALS if not quality_flags.get(sig))
        if missing_quality >= 2:
            score *= 0.5

        # Previously useful boost
        if history and name in history:
            h = history[name]
            if h["useful"] > 0:
                usefulness_ratio = h["useful"] / max(h["total"], 1)
                score *= (1.0 + usefulness_ratio)

        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        f"- {s['name']}: {s.get('description', '')[:150]} [tags: {', '.join(s.get('tags', []))}]"
        for _, s in scored[:top_k]
    ]


def compose_skills(query: str) -> Optional[list[dict]]:
    """Curate a skill bundle for a user query.

    Injects previously-useful skill context from usage history.
    Returns list of skill bundle entries, or None on error.
    """
    import litellm

    skills = _flat_index()
    if not skills:
        return None

    # Load usage history for feedback
    history = _load_usage_history()
    previously_useful = _find_previously_useful(history, query)

    # Step 1: cheap pre-filter (with quality floor + history boost)
    candidates = _pre_filter(skills, query, history=history)
    if not candidates:
        return None

    # Build previously-useful section
    previously_useful_text = "(none)"
    if previously_useful:
        previously_useful_text = "\n".join(
            f"- {s['name']} (useful {s['useful_count']}/{s['total_count']}recent similar queries)"
            for s in previously_useful
        )

    # Step 2: single LLM call
    prompt = SKILL_COMPOSER_PROMPT.format(
        previously_useful=previously_useful_text,
        skill_list="\n".join(candidates),
        query=query,
    )

    key, url, model = _discover_hermes_llm_config()
    if not key:
        return None

    # litellm needs provider prefix for custom endpoints
    if url and "/" not in model:
        model = f"openai/{model}"

    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=key,
            api_base=url,
            temperature=SEARCH_TEMPERATURE,
            max_tokens=1000,
            timeout=30,
            num_retries=LLM_MAX_RETRIES,
        )
        msg = resp.choices[0].message
        text = msg.content or msg.reasoning_content or ""

        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        bundle = json.loads(text)
        # Auto-log each skill before returning (lightweight: one file write each)
        from .skill_usage_logger import log_skill_view
        for item in bundle:
            log_skill_view(
                item.get("name", "?"),
                item.get("load_as", "consider"),
                item.get("confidence", "high"),
            )
        return bundle
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("compose_skills failed: %s", e)
        return None


def bundle_to_hint_block(bundle: list[dict]) -> str:
    """Format a bundle into a natural-language hint block for pre_llm_call injection."""
    if not bundle:
        return ""

    marker = {"must": "★", "should": "▸", "consider": "·"}
    parts = [
        "[Skill Capability Chain]",
        "",
        "These skills are curated for this query.",
        "Call skill_view('<name>') to load each one.",
        "",
        "COMPLIANCE REQUIRED:",
        "1. You MUST call skill_view() for all ★ must skills BEFORE starting work.",
        "2. For ▸ should skills: load if domain-relevant.",
        "3. For · consider skills: load only if genuinely useful.",
        "4. After responding, log each loaded skill's usefulness:",
        "   log_skill_view('skill-name', outcome_signal='useful') if it appeared in your answer",
        "   log_skill_view('skill-name', outcome_signal='irrelevant') if not used",
        "   log_skill_view('skill-name', outcome_signal='harmful') if it misled you",
        "",
    ]
    for item in bundle:
        name = item.get("name", "")
        load_as = item.get("load_as", "consider")
        reason = item.get("reason", "")
        m = marker.get(load_as, "·")
        parts.append(f"  {m} **{name}** — {reason}")
    parts.append("")
    return "\n".join(parts)
