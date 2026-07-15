#!/usr/bin/env python3
"""Deepthink skill integration — discover skills as an explicit planning phase.

For long-horizon tasks:
1. Goal decomposition → phases identified
2. Skill discovery → bundle curated per phase
3. Each phase dispatches subagents with phase-specific bundles

Usage:

    phases = ["architecture", "backend API", "frontend UI", "testing"]
    plan = plan_with_skills("build a full-stack web app", phases)
    # Returns:
    # {
    #   "architecture": [{"name": "writing-plans", ...}, ...],
    #   "backend API": [{"name": "fastapi-patterns", ...}, ...],
    #   "frontend UI": [{"name": "react-patterns", ...}, ...],
    #   "testing": [{"name": "pytest-skill", ...}, ...],
    # }

This makes skill discovery a first-class planning step rather than an afterthought.
"""
from typing import Optional
from skill_retriever.compose import compose_skills
from skill_retriever.subagent_binding import compose_subagent_context, section_skills_by_phase


def plan_with_skills(goal: str, phases: list[str]) -> dict[str, list[dict]]:
    """Discover and section skills across planning phases.

    Args:
        goal: User's high-level goal
        phases: Workflow phase names (e.g., ["arch", "backend", "frontend", "deploy"])

    Returns:
        dict mapping phase name → list of skill bundle entries
    """
    # Compose one big bundle for the entire goal (1 LLM call)
    full_bundle = compose_subagent_context(goal, top_k=20)
    if not full_bundle:
        return {phase: [] for phase in phases}

    # Section skills by phase
    sectioned = section_skills_by_phase(full_bundle, phases)

    # Ensure every phase has at least the top 2 universal skills
    universal = [s for s in full_bundle if s.get("load_as") == "must"][:2]
    for phase in phases:
        if not sectioned[phase]:
            sectioned[phase] = universal

    return sectioned


def format_plan_for_display(plan: dict[str, list[dict]]) -> str:
    """Format a skill plan for display/logging."""
    from skill_retriever.subagent_binding import format_bundle
    lines = ["[Skill Discovery Plan]", ""]
    for phase, bundle in plan.items():
        lines.append(f"Phase: {phase}")
        lines.append(format_bundle(bundle))
        lines.append("")
    return "\n".join(lines)
