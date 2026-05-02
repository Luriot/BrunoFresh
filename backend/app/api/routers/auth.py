from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ..dependencies import require_auth
from ...config import settings
from ...services.auth import issue_access_token, verify_passcode

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── IP-based brute-force protection ─────────────────────────────────────────
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 900  # 15 minutes


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS
    recent = [t for t in _login_attempts.get(ip, []) if t > cutoff]
    if len(recent) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in 15 minutes.",
        )
    _login_attempts[ip] = recent + [now]


def _clear_rate_limit(ip: str) -> None:
    """Remove the IP's attempt log on successful login."""
    _login_attempts.pop(ip, None)


class LoginRequest(BaseModel):
    passcode: str = Field(min_length=1, max_length=256)


class AuthStatusResponse(BaseModel):
    authenticated: bool


@router.post("/login", response_model=AuthStatusResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> AuthStatusResponse:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    if not verify_passcode(payload.passcode):
        await asyncio.sleep(1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passcode",
        )
    _clear_rate_limit(client_ip)

    token = issue_access_token()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    return AuthStatusResponse(authenticated=True)


@router.post("/logout", response_model=AuthStatusResponse)
async def logout(response: Response) -> AuthStatusResponse:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        samesite=settings.auth_cookie_samesite,
    )
    return AuthStatusResponse(authenticated=False)


@router.get("/me", response_model=AuthStatusResponse, dependencies=[Depends(require_auth)])
async def me() -> AuthStatusResponse:
    return AuthStatusResponse(authenticated=True)
