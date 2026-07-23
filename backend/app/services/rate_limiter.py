"""Shared in-process rate limiter (sliding window, namespaced by action).

State is in-process only — resets on restart and does not work across
multiple worker processes. Acceptable for single-server deployments.
For multi-worker deployments, replace with a Redis-backed store.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, status

MAX_ATTEMPTS = 10
WINDOW_SECONDS = 900  # 15 minutes
_PRUNE_THRESHOLD = 500  # prune a bucket when tracking more than this many keys

_action_windows: dict[str, dict[str, list[float]]] = {}


def _prune_stale(bucket: dict[str, list[float]], window: int) -> None:
    """Remove keys with no activity in the current window (prevents unbounded growth)."""
    cutoff = time.monotonic() - window
    stale = [k for k, times in bucket.items() if all(t <= cutoff for t in times)]
    for k in stale:
        del bucket[k]


def check_action_rate_limit(
    key: str,
    action: str,
    *,
    max_calls: int = 10,
    window_seconds: int = 60,
    detail: str | None = None,
) -> None:
    """Raise HTTP 429 if `key` has exceeded `max_calls` for `action` within `window_seconds`.

    Typical usage: ``check_action_rate_limit(str(claims.user_id), "scrape", max_calls=5, window_seconds=300)``

    The ``action`` namespace prevents cross-contamination between different rate-limited
    operations on the same key.
    """
    bucket = _action_windows.setdefault(action, {})
    if len(bucket) > _PRUNE_THRESHOLD:
        _prune_stale(bucket, window_seconds)
    now = time.monotonic()
    cutoff = now - window_seconds
    recent = [t for t in bucket.get(key, []) if t > cutoff]
    if len(recent) >= max_calls:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail or f"Rate limit exceeded for {action}. Try again later.",
        )
    bucket[key] = recent + [now]


def check_rate_limit(ip: str) -> None:
    """Raise HTTP 429 if `ip` has exceeded MAX_ATTEMPTS login attempts within WINDOW_SECONDS."""
    check_action_rate_limit(
        ip,
        "login",
        max_calls=MAX_ATTEMPTS,
        window_seconds=WINDOW_SECONDS,
        detail="Too many login attempts. Try again in 15 minutes.",
    )


def clear_rate_limit(ip: str) -> None:
    """Remove all recorded login attempts for `ip` after a successful login."""
    _action_windows.get("login", {}).pop(ip, None)
