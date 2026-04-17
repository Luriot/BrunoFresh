from __future__ import annotations

from fastapi import HTTPException, Request, status

from ..config import settings
from ..services.auth import verify_access_token


def _extract_cookie_token(request: Request) -> str | None:
    token = request.cookies.get(settings.auth_cookie_name)
    if token and token.strip():
        return token.strip()
    return None


async def require_auth(request: Request) -> None:
    token = _extract_cookie_token(request)
    if not token or not verify_access_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
