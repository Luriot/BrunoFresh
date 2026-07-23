from __future__ import annotations

from typing import NamedTuple

import bcrypt
from itsdangerous import BadSignature, URLSafeTimedSerializer

from ..config import settings

# The salt doubles as the token version: bump it to invalidate all existing tokens.
AUTH_SALT = "brunofresh-auth-v2"
MAX_TOKEN_LENGTH = 4096


class UserClaims(NamedTuple):
    user_id: int
    role: str
    language: str = "en"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.auth_secret, salt=AUTH_SALT)


# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── Token issuance / verification ────────────────────────────────────────────

def issue_access_token(user_id: int, role: str, language: str = "en") -> str:
    return _serializer().dumps({"sub": user_id, "role": role, "lang": language})


def verify_access_token(token: str) -> UserClaims | None:
    """Return UserClaims if the token is valid and unexpired, else None."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None

    try:
        payload = _serializer().loads(token, max_age=settings.auth_token_ttl_minutes * 60)
    except BadSignature:
        return None

    if not isinstance(payload, dict):
        return None

    sub = payload.get("sub")
    if not isinstance(sub, int):
        return None

    role = payload.get("role")
    if not isinstance(role, str):
        return None

    lang = payload.get("lang", "en")
    if not isinstance(lang, str) or lang not in {"en", "fr"}:
        lang = "en"

    return UserClaims(user_id=sub, role=role, language=lang)
