from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

import bcrypt

from ..config import settings


TOKEN_VERSION = 2  # Bumped — old passcode-based tokens are intentionally invalid
MAX_TOKEN_LENGTH = 4096


class UserClaims(NamedTuple):
    user_id: int
    role: str
    language: str = "en"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


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
    issued_at = datetime.now(tz=UTC)
    expires_at = issued_at + timedelta(minutes=settings.auth_token_ttl_minutes)
    payload = {
        "ver": TOKEN_VERSION,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "sub": user_id,
        "role": role,
        "lang": language,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)

    signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}"


def verify_access_token(token: str) -> UserClaims | None:
    """Return UserClaims if the token is valid and unexpired, else None."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None

    try:
        parts = token.split(".", maxsplit=1)
        if len(parts) != 2:
            return None
        payload_b64, signature_b64 = parts
    except ValueError:
        return None

    if not payload_b64 or not signature_b64:
        return None

    expected_signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_b64)
    except Exception:
        return None

    if not hmac.compare_digest(expected_signature, provided_signature):
        return None

    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    if payload.get("ver") != TOKEN_VERSION:
        return None

    issued_at = payload.get("iat")
    if not isinstance(issued_at, int):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None

    if exp <= issued_at:
        return None

    now_ts = int(datetime.now(tz=UTC).timestamp())
    if issued_at > now_ts or exp <= now_ts:
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
