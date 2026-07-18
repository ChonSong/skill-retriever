#!/usr/bin/env python3
"""Skill Composer Watchdog — monitors compose_skills() health and surfaces failures.

The composer fails silently ~95% of the time. This watchdog:
1. Tracks success/failure rates per failure mode
2. Logs detailed failure reasons (not just "failed")
3. Alerts after N consecutive failures
4. Provides a health check for diagnostics

Usage:
    from skill_retriever.watchdog import watched_compose_skills
    bundle = watched_compose_skills(query)
    
    # Check health:
    from skill_retriever.watchdog import get_health
    print(get_health())
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional
from collections import deque
from datetime import datetime, timezone

from skill_retriever.compose import compose_skills, _flat_index, _discover_hermes_llm_config, FLAT_INDEX_PATH

logger = logging.getLogger(__name__)

# Config
ALERT_THRESHOLD = 3  # consecutive failures before alerting
HISTORY_WINDOW = 50  # keep last N results for health stats
HEALTH_LOG_PATH = Path.home() / ".hermes/state/skill-composer-health.jsonl"

# State
_recent_results: deque = deque(maxlen=HISTORY_WINDOW)
_consecutive_failures = 0
_last_failure_reason: Optional[str] = None
_last_success_time: Optional[float] = None


class ComposerHealth:
    """Health status for the skill composer."""
    
    def __init__(self):
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.recent_attempts = 0
        self.recent_successes = 0
        self.recent_failures = 0
        self.consecutive_failures = 0
        self.last_failure_reason = None
        self.last_success_time = None
        self.failure_breakdown = {}
        self.alert_active = False
    
    def to_dict(self) -> dict:
        return {
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": round(self.total_successes / max(self.total_attempts, 1) * 100, 1),
            "recent_attempts": self.recent_attempts,
            "recent_successes": self.recent_successes,
            "recent_failures": self.recent_failures,
            "recent_success_rate": round(
                self.recent_successes / max(self.recent_attempts, 1) * 100, 1
            ),
            "consecutive_failures": self.consecutive_failures,
            "last_failure_reason": self.last_failure_reason,
            "last_success_time": self.last_success_time,
            "failure_breakdown": self.failure_breakdown,
            "alert_active": self.alert_active,
        }
    
    def summary(self) -> str:
        d = self.to_dict()
        lines = [
            f"[Skill Composer Health]",
            f"  Total: {d['total_successes']}/{d['total_attempts']} ({d['success_rate']}% success)",
            f"  Recent ({HISTORY_WINDOW}): {d['recent_successes']}/{d['recent_attempts']} ({d['recent_success_rate']}% success)",
            f"  Consecutive failures: {d['consecutive_failures']}",
        ]
        if d['last_failure_reason']:
            lines.append(f"  Last failure: {d['last_failure_reason']}")
        if d['last_success_time']:
            ts = datetime.fromtimestamp(d['last_success_time']).strftime('%Y-%m-%d %H:%M')
            lines.append(f"  Last success: {ts}")
        if d['alert_active']:
            lines.append(f"  ⚠️ ALERT: {d['consecutive_failures']} consecutive failures!")
        if d['failure_breakdown']:
            lines.append(f"  Failure breakdown:")
            for reason, count in sorted(d['failure_breakdown'].items(), key=lambda x: -x[1]):
                lines.append(f"    {reason}: {count}")
        return "\n".join(lines)


def _diagnose_failure(query: str) -> str:
    """Diagnose why compose_skills() would fail for this query."""
    # Check 1: flat index exists and is non-empty
    flat = _flat_index()
    if not flat:
        return "flat_index_empty"
    
    # Check 2: LLM config discoverable
    key, url, model = _discover_hermes_llm_config()
    if not key:
        return "llm_config_missing"
    
    # Check 3: keyword pre-filter produces candidates
    from skill_retriever.compose import _pre_filter
    candidates = _pre_filter(flat, query)
    if not candidates:
        return "no_keyword_match"
    
    # Check 4: LLM reachable (lightweight probe)
    try:
        import litellm
        resp = litellm.completion(
            model=f"openai/{model}" if url and "/" not in model else model,
            messages=[{"role": "user", "content": "reply with OK"}],
            api_key=key,
            api_base=url,
            max_tokens=5,
            timeout=10,
        )
        if not resp.choices:
            return "llm_no_response"
    except Exception as e:
        return f"llm_error: {type(e).__name__}"
    
    return "unknown"


def _log_health(event: str, detail: str, query: str = ""):
    """Append health event to JSONL."""
    entry = {
        "ts": time.time(),
        "event": event,
        "detail": detail,
        "query": query[:100],
    }
    try:
        HEALTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HEALTH_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def watched_compose_skills(query: str) -> Optional[list[dict]]:
    """Wrapped compose_skills() with monitoring and alerting.
    
    Use this instead of compose_skills() directly.
    Tracks success/failure, diagnoses failures, and alerts after threshold.
    """
    global _consecutive_failures, _last_failure_reason, _last_success_time
    
    # Attempt composition
    try:
        bundle = compose_skills(query)
    except Exception as e:
        bundle = None
        failure_reason = f"exception: {type(e).__name__}: {e}"
    
    if bundle is not None:
        # Success
        _consecutive_failures = 0
        _last_success_time = time.time()
        _log_health("success", f"bundle: {len(bundle)} skills", query)
        _recent_results.append({"ts": time.time(), "success": True, "query": query})
        return bundle
    
    # Failure — diagnose why
    failure_reason = _diagnose_failure(query)
    _consecutive_failures += 1
    _last_failure_reason = failure_reason
    _log_health("failure", failure_reason, query)
    _recent_results.append({"ts": time.time(), "success": False, "query": query, "reason": failure_reason})
    
    # Alert if threshold reached
    if _consecutive_failures >= ALERT_THRESHOLD:
        logger.warning(
            "Skill composer: %d consecutive failures (last: %s). Run `skill-retriever health` for diagnosis.",
            _consecutive_failures, failure_reason
        )
    
    return None


def get_health() -> ComposerHealth:
    """Get current composer health status."""
    health = ComposerHealth()
    
    # Aggregate from recent results
    health.recent_attempts = len(_recent_results)
    health.recent_successes = sum(1 for r in _recent_results if r.get("success"))
    health.recent_failures = health.recent_attempts - health.recent_successes
    health.consecutive_failures = _consecutive_failures
    health.last_failure_reason = _last_failure_reason
    health.last_success_time = _last_success_time
    health.alert_active = _consecutive_failures >= ALERT_THRESHOLD
    
    # Failure breakdown from recent
    for r in _recent_results:
        if not r.get("success") and "reason" in r:
            reason = r["reason"]
            health.failure_breakdown[reason] = health.failure_breakdown.get(reason, 0) + 1
    
    # Load historical totals from health log
    if HEALTH_LOG_PATH.exists():
        try:
            with open(HEALTH_LOG_PATH) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    health.total_attempts += 1
                    if entry.get("event") == "success":
                        health.total_successes += 1
                    elif entry.get("event") == "failure":
                        health.total_failures += 1
                        reason = entry.get("detail", "unknown")
                        # Don't double-count recent (they're in both)
                        if health.recent_attempts > 0:
                            health.failure_breakdown[reason] = health.failure_breakdown.get(reason, 0)
        except Exception:
            pass
    
    return health


def health_check() -> str:
    """Run a full health check and return human-readable report."""
    health = get_health()
    lines = [health.summary(), ""]
    
    # Additional diagnostics
    flat = _flat_index()
    lines.append(f"  Flat index: {len(flat)} skills")
    
    key, url, model = _discover_hermes_llm_config()
    lines.append(f"  LLM config: {'✓' if key else '✗'} {model} @ {url}")
    
    if not key:
        lines.append("  ⚠️ Fix: Set OPENAI_API_KEY in ~/.hermes/.env or run `hermes auth add`")
    
    if not flat:
        lines.append("  ⚠️ Fix: Run `python scripts/rebalance_flat_index.py`")
    
    return "\n".join(lines)
