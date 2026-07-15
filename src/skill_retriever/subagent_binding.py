#!/usr/bin/env python3
"""Subagent skill binding — compose and inject skill bundles into delegate_task calls.

Usage (inside an agent turn):

    from skill_retriever.subagent_binding import compose_subagent_context

    bundle = compose_subagent_context("build a FastAPI backend")
    # bundle = [{"name": "fastapi-patterns", "load_as": "must", ...}, ...]

    # Inject into delegate_task context:
    context = f'''
    Skill bundle for this task:
    {format_bundle(bundle)}

    Task: Build a FastAPI backend with async patterns
    ...
    '''

Key design: Parent composes once per task, each subagent gets its own slice.
No subagent queries the composer — avoids duplicate LLM calls.
"""
import json
from typing import Optional
from skill_retriever.compose import compose_skills


def format_bundle(bundle: list[dict]) -> str:
    """Format a bundle for subagent context.

    Uses the ★/▸/· markers from skill-chain-approach format.
    """
    if not bundle:
        return "(no skills recommended for this task)"

    marker = {"must": "★", "should": "▸", "consider": "·"}
    lines = []
    for item in bundle:
        name = item.get("name", "")
        load_as = item.get("load_as", "consider")
        reason = item.get("reason", "")
        m = marker.get(load_as, "·")
        lines.append(f"  {m} **{name}** — {reason}")
    return "\n".join(lines)


def compose_subagent_context(task_description: str, top_k: int = 10) -> list[dict]:
    """Compose a skill bundle for a subagent task.

    Returns the bundle (list of dicts). Caller decides how to inject.
    Filters out low-confidence items beyond top_k.
    """
    bundle = compose_skills(task_description) or []
    # Filter: keep only high/medium confidence up to top_k
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    bundle.sort(key=lambda x: confidence_order.get(x.get("confidence", "low"), 3))
    return bundle[:top_k]


def section_skills_by_phase(bundle: list[dict], phases: list[str]) -> dict[str, list[dict]]:
    """Section a bundle by workflow phase using affinity scoring.

    Each skill is assigned to the phase with the highest keyword affinity.
    Skills that don't match any specific phase go to "general".
    Returns: {"phase_name": [skill_entries], "general": [...]}
    """
    sectioned = {p: [] for p in phases}
    sectioned["general"] = []

    for item in bundle:
        text = f"{item.get('name', '')} {item.get('reason', '')}".lower()
        best_phase = "general"
        best_score = 0
        for phase in phases:
            phase_lower = phase.lower()
            # Score: count distinct words from phase that appear in skill text
            score = sum(1 for w in phase_lower.split() if len(w) > 2 and w in text)
            # Also match common synonyms
            synonyms = {
                "architecture": ["design", "system", "structure", "plan"],
                "backend": ["api", "fastapi", "express", "node", "server"],
                "frontend": ["react", "vue", "html", "css", "dom", "component"],
                "testing": ["test", "jest", "pytest", "e2e", "qa"],
                "deployment": ["deploy", "docker", "tunnel", "release", "ship"],
                "database": ["postgres", "sql", "migration", "schema"],
                "auth": ["oauth", "login", "session", "token", "jwt"],
                "refactor": ["simplify", "restructure", "cleanup"],
                "debug": ["debug", "fix", "bug", "root"],
                "monitor": ["log", "metric", "grafana", "prometheus"],
            }
            for syn in synonyms.get(phase_lower, []):
                if syn in text:
                    score += 2
            if score > best_score:
                best_score = score
                best_phase = phase
        sectioned[best_phase].append(item)
    return sectioned
