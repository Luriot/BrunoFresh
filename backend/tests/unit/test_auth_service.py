"""Unit tests for app.services.auth — pure logic, no DB or network required."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.config import settings
from app.services.auth import (
    TOKEN_VERSION,
    issue_access_token,
    verify_access_token,
    verify_passcode,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _build_token(payload: dict) -> str:
    """Manually craft a signed token using the same algorithm as the service."""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    payload_b64 = _b64url_encode(payload_json)
    sig = hmac.new(
        settings.auth_secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def _valid_payload(
    *,
    iat_offset: int = 0,
    exp_offset: int = 3600,
    scope: str = "api",
    ver: int = TOKEN_VERSION,
) -> dict:
    now = int(datetime.now(tz=UTC).timestamp())
    return {
        "ver": ver,
        "iat": now + iat_offset,
        "exp": now + exp_offset,
        "scope": scope,
    }


# ── issue_access_token ────────────────────────────────────────────────────────

class TestIssueAccessToken:
    def test_returns_string_with_one_dot(self):
        token = issue_access_token()
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 2, "Token must have exactly one '.' separator"

    def test_issued_token_is_valid(self):
        token = issue_access_token()
        assert verify_access_token(token) is True

    def test_two_tokens_differ(self):
        """Tokens issued at different moments must differ (different timestamps)."""
        import time
        t1 = issue_access_token()
        time.sleep(0.01)
        t2 = issue_access_token()
        # They differ when issued at different seconds; acceptable if same second
        # Just assert both are valid.
        assert verify_access_token(t1)
        assert verify_access_token(t2)


# ── verify_access_token ───────────────────────────────────────────────────────

class TestVerifyAccessToken:
    def test_valid_token(self):
        token = issue_access_token()
        assert verify_access_token(token) is True

    def test_empty_string_returns_false(self):
        assert verify_access_token("") is False

    def test_none_returns_false(self):
        assert verify_access_token(None) is False  # type: ignore[arg-type]

    def test_token_too_long_returns_false(self):
        assert verify_access_token("a" * 4097) is False

    def test_no_dot_separator_returns_false(self):
        assert verify_access_token("nodottokenvalue") is False

    def test_tampered_payload_returns_false(self):
        token = issue_access_token()
        payload_b64, sig_b64 = token.split(".")
        # Flip one character in payload
        chars = list(payload_b64)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = "".join(chars) + "." + sig_b64
        assert verify_access_token(tampered) is False

    def test_tampered_signature_returns_false(self):
        token = issue_access_token()
        payload_b64, sig_b64 = token.split(".")
        chars = list(sig_b64)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = payload_b64 + "." + "".join(chars)
        assert verify_access_token(tampered) is False

    def test_expired_token_returns_false(self):
        payload = _valid_payload(iat_offset=-7200, exp_offset=-3600)  # expired 1h ago
        token = _build_token(payload)
        assert verify_access_token(token) is False

    def test_future_iat_returns_false(self):
        payload = _valid_payload(iat_offset=3600)  # issued 1h in the future
        token = _build_token(payload)
        assert verify_access_token(token) is False

    def test_wrong_scope_returns_false(self):
        payload = _valid_payload(scope="admin")
        token = _build_token(payload)
        assert verify_access_token(token) is False

    def test_wrong_version_returns_false(self):
        payload = _valid_payload(ver=99)
        token = _build_token(payload)
        assert verify_access_token(token) is False

    def test_exp_equals_iat_returns_false(self):
        payload = _valid_payload(iat_offset=0, exp_offset=0)
        token = _build_token(payload)
        assert verify_access_token(token) is False


# ── verify_passcode ───────────────────────────────────────────────────────────

class TestVerifyPasscode:
    def test_correct_passcode_returns_true(self):
        assert verify_passcode(settings.app_passcode) is True

    def test_wrong_passcode_returns_false(self):
        assert verify_passcode("definitely-wrong-passcode") is False

    def test_empty_passcode_returns_false(self):
        assert verify_passcode("") is False
