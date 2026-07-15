#!/usr/bin/env python3
"""Skill Composer — single LLM call to curate a skill bundle from a query.

1. Cheap keyword pre-filter against flat_index.json (top 50 candidates)
2. One LLM call: "from these 50, pick 5-10 with reasons and confidence"
3. Returns bundle as JSON

This replaces the hardcoded capability chains in the pre_llm_call hook.
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

# Prompt template — loaded once (use {{ }} to escape literal braces)
SKILL_COMPOSER_PROMPT = """You are a skill curator for an AI agent. Given a user query and a list of available skills, choose the best workflow.

## Rules
- Return **valid JSON only** — no commentary, no markdown fences
- Choose 3-10 skills (fewer for simple queries, more for complex)
- Each skill needs: name, load_as (must/should/consider), reason (1 sentence), confidence (high/medium/low)
- Prefer class-level umbrella skills over narrow ones
- Skip skills with low relevance — don't pad the bundle
- If no skills match, return []

## Output format
[{{"name": "skill-name", "load_as": "must", "reason": "...", "confidence": "high"}}]

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


def _pre_filter(skills: list[dict], query: str, top_k: int = 50) -> list[str]:
    """Cheap keyword pre-filter: match query tokens against skill name+description.

    Returns top_k skill entries as formatted strings for the LLM prompt.
    """
    tokens = set(re.findall(r'\w+', query.lower()))
    scored = []
    for s in skills:
        text = f"{s['name']} {' '.join(s.get('tags', []))} {s['description']}".lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Format for prompt
    return [
        f"- {s['name']}: {s.get('description', '')[:150]} [tags: {', '.join(s.get('tags', []))}]"
        for _, s in scored[:top_k]
    ]


def compose_skills(query: str) -> Optional[list[dict]]:
    """Curate a skill bundle for a user query.

    Returns list of skill bundle entries, or None on error.
    """
    import litellm

    skills = _flat_index()
    if not skills:
        return None

    # Step 1: cheap pre-filter
    candidates = _pre_filter(skills, query)
    if not candidates:
        return None

    # Step 2: single LLM call
    prompt = SKILL_COMPOSER_PROMPT.format(
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
    ]
    for item in bundle:
        name = item.get("name", "")
        load_as = item.get("load_as", "consider")
        reason = item.get("reason", "")
        m = marker.get(load_as, "·")
        parts.append(f"  {m} **{name}** — {reason}")
    parts.append("")
    return "\n".join(parts)
