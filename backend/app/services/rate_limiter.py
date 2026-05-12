"""Shared in-process IP-based rate limiter for login endpoints.

State is in-process only — resets on restart and does not work across
multiple worker processes. Acceptable for single-server deployments.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, status

MAX_ATTEMPTS = 10
WINDOW_SECONDS = 900  # 15 minutes
_PRUNE_THRESHOLD = 500  # prune dict when tracking more than this many unique IPs

_attempts: dict[str, list[float]] = {}


def _prune_stale() -> None:
    """Remove IPs with no activity in the current window (prevents unbounded growth)."""
    cutoff = time.monotonic() - WINDOW_SECONDS
    stale = [ip for ip, times in _attempts.items() if all(t <= cutoff for t in times)]
    for ip in stale:
        del _attempts[ip]


def check_rate_limit(ip: str) -> None:
    """Raise HTTP 429 if `ip` has exceeded MAX_ATTEMPTS within WINDOW_SECONDS."""
    if len(_attempts) > _PRUNE_THRESHOLD:
        _prune_stale()
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS
    recent = [t for t in _attempts.get(ip, []) if t > cutoff]
    if len(recent) >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in 15 minutes.",
        )
    _attempts[ip] = recent + [now]


def clear_rate_limit(ip: str) -> None:
    """Remove all recorded attempts for `ip` after a successful login."""
    _attempts.pop(ip, None)
