from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from ..dependencies import require_auth
from ...config import settings
from ...services.auth import issue_access_token, verify_passcode

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    passcode: str = Field(min_length=1, max_length=256)


class AuthStatusResponse(BaseModel):
    authenticated: bool


@router.post("/login", response_model=AuthStatusResponse)
async def login(payload: LoginRequest, response: Response) -> AuthStatusResponse:
    if not verify_passcode(payload.passcode):
        await asyncio.sleep(1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passcode",
        )

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
