from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from ..config import settings


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def verify_passcode(candidate: str) -> bool:
    return hmac.compare_digest(candidate, settings.app_passcode)


def issue_access_token() -> str:
    expires_at = datetime.now(tz=UTC) + timedelta(minutes=settings.auth_token_ttl_minutes)
    payload = {
        "exp": int(expires_at.timestamp()),
        "scope": "api",
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


def verify_access_token(token: str) -> bool:
    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError:
        return False

    expected_signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_b64)
    except Exception:
        return False

    if not hmac.compare_digest(expected_signature, provided_signature):
        return False

    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return False

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return False

    now_ts = int(datetime.now(tz=UTC).timestamp())
    return exp > now_ts
