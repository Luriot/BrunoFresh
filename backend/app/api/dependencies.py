from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Response, status

from ..config import settings
from ..services.auth import UserClaims, verify_access_token


def _extract_cookie_token(request: Request) -> str | None:
    token = request.cookies.get(settings.auth_cookie_name)
    if token and token.strip():
        return token.strip()
    return None


async def require_auth(request: Request) -> UserClaims:
    token = _extract_cookie_token(request)
    claims = verify_access_token(token or "")
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return claims


def require_admin(claims: UserClaims = Depends(require_auth)) -> UserClaims:
    if claims.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return claims


def set_auth_cookie(response: Response, token: str) -> None:
    """Write the auth cookie from a single authoritative location.

    Centralising the cookie parameters here means any future change (domain,
    partitioned flag, etc.) only needs to be made in one place.
    """
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_token_ttl_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
