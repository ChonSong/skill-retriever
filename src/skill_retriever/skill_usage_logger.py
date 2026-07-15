#!/usr/bin/env python3
"""Skill usage logging and metrics.

Logs every skill_view() invocation to a JSONL file for later analysis.
Zero-cost: just a file append. Agent calls this after each skill_view().

Usage:
    result = skill_view(name="fastapi-patterns")
    log_skill_view("fastapi-patterns", load_as="must", confidence="high")
"""
import json
import time
from pathlib import Path
from typing import Optional

LOG_DIR = Path.home() / ".hermes" / "state"
LOG_DIR.mkdir(parents=True, exist_ok=True)
USAGE_LOG = LOG_DIR / "skill-usage.jsonl"


def log_skill_view(
    skill_name: str,
    load_as: str = "must",
    confidence: str = "high",
    session_id: Optional[str] = None,
    outcome_signal: Optional[str] = None,
):
    """Log a skill_view invocation to the JSONL file."""
    try:
        entry = {
            "ts": time.time(),
            "skill_name": skill_name,
            "load_as": load_as,
            "confidence": confidence,
            "session_id": session_id,
            "outcome_signal": outcome_signal,
        }
        with open(USAGE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_usage_stats(window_hours: int = 24) -> dict:
    """Get usage statistics for the last N hours."""
    if not USAGE_LOG.exists():
        return {"total": 0, "skills": []}

    cutoff = time.time() - (window_hours * 3600)
    counts = {}
    with open(USAGE_LOG) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("ts", 0) < cutoff:
                    continue
                name = entry.get("skill_name", "?")
                counts[name] = counts.get(name, 0) + 1
            except (json.JSONDecodeError, ValueError):
                continue

    return {
        "total": sum(counts.values()),
        "unique_skills": len(counts),
        "skills": sorted(counts.items(), key=lambda x: x[1], reverse=True),
    }


def format_stats(stats: dict) -> str:
    """Format stats for display."""
    if not stats.get("total"):
        return "No skills accessed recently."
    lines = [
        f"[Usage: {stats['total']} calls, {stats['unique_skills']} unique skills]",
        "",
    ]
    for name, count in stats["skills"][:20]:
        lines.append(f"  {name}: {count}")
    return "\n".join(lines)
