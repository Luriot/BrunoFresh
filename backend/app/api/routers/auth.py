from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_auth
from ...config import settings
from ...database import get_db
from ...models import User
from ...schemas import UserOut
from ...services.auth import UserClaims, issue_access_token, verify_password
from ...services.rate_limiter import check_rate_limit, clear_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class AuthStatusResponse(BaseModel):
    authenticated: bool


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    user = await db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.hashed_password):
        await asyncio.sleep(1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    clear_rate_limit(client_ip)

    token = issue_access_token(user.id, user.role)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    return UserOut.model_validate(user)


@router.get("/me", response_model=UserOut)
async def get_me(
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await db.get(User, claims.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserOut.model_validate(user)


@router.post("/logout", response_model=AuthStatusResponse)
async def logout(response: Response) -> AuthStatusResponse:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        samesite=settings.auth_cookie_samesite,
    )
    return AuthStatusResponse(authenticated=False)



