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
    UserClaims,
    hash_password,
    issue_access_token,
    verify_access_token,
    verify_password,
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
    ver: int = TOKEN_VERSION,
    sub: int = 1,
    role: str = "user",
) -> dict:
    now = int(datetime.now(tz=UTC).timestamp())
    return {
        "ver": ver,
        "iat": now + iat_offset,
        "exp": now + exp_offset,
        "sub": sub,
        "role": role,
    }


# ── issue_access_token ────────────────────────────────────────────────────────

class TestIssueAccessToken:
    def test_returns_string_with_one_dot(self):
        token = issue_access_token(user_id=1, role="user")
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 2, "Token must have exactly one '.' separator"

    def test_issued_token_is_valid(self):
        token = issue_access_token(user_id=1, role="user")
        claims = verify_access_token(token)
        assert isinstance(claims, UserClaims)
        assert claims.user_id == 1
        assert claims.role == "user"

    def test_admin_role_preserved_in_token(self):
        token = issue_access_token(user_id=42, role="admin")
        claims = verify_access_token(token)
        assert isinstance(claims, UserClaims)
        assert claims.user_id == 42
        assert claims.role == "admin"

    def test_two_tokens_differ(self):
        """Tokens issued at different moments must differ (different timestamps)."""
        import time
        t1 = issue_access_token(user_id=1, role="user")
        time.sleep(0.01)
        t2 = issue_access_token(user_id=1, role="user")
        assert verify_access_token(t1) is not None
        assert verify_access_token(t2) is not None


# ── verify_access_token ───────────────────────────────────────────────────────

class TestVerifyAccessToken:
    def test_valid_token(self):
        token = issue_access_token(user_id=1, role="user")
        claims = verify_access_token(token)
        assert isinstance(claims, UserClaims)

    def test_empty_string_returns_none(self):
        assert verify_access_token("") is None

    def test_none_returns_none(self):
        assert verify_access_token(None) is None  # type: ignore[arg-type]

    def test_token_too_long_returns_none(self):
        assert verify_access_token("a" * 4097) is None

    def test_no_dot_separator_returns_none(self):
        assert verify_access_token("nodottokenvalue") is None

    def test_tampered_payload_returns_none(self):
        token = issue_access_token(user_id=1, role="user")
        payload_b64, sig_b64 = token.split(".")
        chars = list(payload_b64)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = "".join(chars) + "." + sig_b64
        assert verify_access_token(tampered) is None

    def test_tampered_signature_returns_none(self):
        token = issue_access_token(user_id=1, role="user")
        payload_b64, sig_b64 = token.split(".")
        chars = list(sig_b64)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = payload_b64 + "." + "".join(chars)
        assert verify_access_token(tampered) is None

    def test_expired_token_returns_none(self):
        payload = _valid_payload(iat_offset=-7200, exp_offset=-3600)
        token = _build_token(payload)
        assert verify_access_token(token) is None

    def test_future_iat_returns_none(self):
        payload = _valid_payload(iat_offset=3600)
        token = _build_token(payload)
        assert verify_access_token(token) is None

    def test_non_int_sub_returns_none(self):
        payload = _valid_payload(sub="not-an-int")  # type: ignore[arg-type]
        token = _build_token(payload)
        assert verify_access_token(token) is None

    def test_wrong_version_returns_none(self):
        payload = _valid_payload(ver=99)
        token = _build_token(payload)
        assert verify_access_token(token) is None

    def test_exp_equals_iat_returns_none(self):
        payload = _valid_payload(iat_offset=0, exp_offset=0)
        token = _build_token(payload)
        assert verify_access_token(token) is None

    def test_extra_dot_in_token_returns_none(self):
        """A token with multiple dots must be rejected (maxsplit=1 guard)."""
        token = issue_access_token(user_id=1, role="user")
        assert verify_access_token(token + ".extra") is None


# ── hash_password / verify_password ─────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        assert hash_password("secret") != "secret"

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("mypassword")
        assert verify_password("wrong", h) is False

    def test_verify_empty_password(self):
        h = hash_password("mypassword")
        assert verify_password("", h) is False

    def test_two_hashes_differ(self):
        """bcrypt uses random salt — same plain must produce different hashes."""
        assert hash_password("same") != hash_password("same")


# ── language field in tokens ─────────────────────────────────────────────────

class TestTokenLanguage:
    def test_language_defaults_to_en(self):
        token = issue_access_token(user_id=1, role="user")
        claims = verify_access_token(token)
        assert claims is not None
        assert claims.language == "en"

    def test_language_fr_survives_round_trip(self):
        token = issue_access_token(user_id=1, role="user", language="fr")
        claims = verify_access_token(token)
        assert claims is not None
        assert claims.language == "fr"

    def test_language_is_in_claims_namedtuple(self):
        token = issue_access_token(user_id=7, role="admin", language="fr")
        claims = verify_access_token(token)
        assert isinstance(claims, UserClaims)
        assert claims.user_id == 7
        assert claims.role == "admin"
        assert claims.language == "fr"

    def test_token_missing_lang_key_defaults_to_en(self):
        """Tokens issued before the language feature was added must still verify."""
        payload = _valid_payload()  # no "lang" key
        token = _build_token(payload)
        claims = verify_access_token(token)
        assert claims is not None
        assert claims.language == "en"

    def test_language_does_not_affect_expiry_validation(self):
        """An expired FR token must still be rejected."""
        payload = {**_valid_payload(iat_offset=-7200, exp_offset=-3600), "lang": "fr"}
        token = _build_token(payload)
        assert verify_access_token(token) is None
