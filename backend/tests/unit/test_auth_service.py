"""Unit tests for app.services.auth — pure logic, no DB or network required."""
from __future__ import annotations

from itsdangerous import URLSafeTimedSerializer

from app.config import settings
from app.services.auth import (
    AUTH_SALT,
    UserClaims,
    hash_password,
    issue_access_token,
    verify_access_token,
    verify_password,
)


def _build_token(payload: dict, salt: str = AUTH_SALT) -> str:
    """Craft a token with the same serializer as the service (for negative tests)."""
    return URLSafeTimedSerializer(settings.auth_secret, salt=salt).dumps(payload)


# ── issue_access_token ────────────────────────────────────────────────────────

class TestIssueAccessToken:
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
        """Different inputs must produce different token strings."""
        t1 = issue_access_token(user_id=1, role="user")
        t2 = issue_access_token(user_id=2, role="user")
        assert t1 != t2
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

    def test_garbage_returns_none(self):
        assert verify_access_token("nodottokenvalue") is None

    def test_tampered_payload_returns_none(self):
        token = issue_access_token(user_id=1, role="user")
        first, rest = token.split(".", maxsplit=1)
        chars = list(first)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = "".join(chars) + "." + rest
        assert verify_access_token(tampered) is None

    def test_tampered_signature_returns_none(self):
        token = issue_access_token(user_id=1, role="user")
        head, sig = token.rsplit(".", maxsplit=1)
        chars = list(sig)
        chars[0] = "A" if chars[0] != "A" else "B"
        tampered = head + "." + "".join(chars)
        assert verify_access_token(tampered) is None

    def test_expired_token_returns_none(self, monkeypatch):
        token = issue_access_token(user_id=1, role="user")
        monkeypatch.setattr(settings, "auth_token_ttl_minutes", -1)
        assert verify_access_token(token) is None

    def test_non_int_sub_returns_none(self):
        token = _build_token({"sub": "not-an-int", "role": "user"})
        assert verify_access_token(token) is None

    def test_wrong_salt_returns_none(self):
        """Tokens signed with a different salt (e.g. an older version) are rejected."""
        token = _build_token({"sub": 1, "role": "user"}, salt="brunofresh-auth-v1")
        assert verify_access_token(token) is None

    def test_extra_dot_in_token_returns_none(self):
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
        token = _build_token({"sub": 1, "role": "user"})
        claims = verify_access_token(token)
        assert claims is not None
        assert claims.language == "en"

    def test_invalid_lang_falls_back_to_en(self):
        token = _build_token({"sub": 1, "role": "user", "lang": "de"})
        claims = verify_access_token(token)
        assert claims is not None
        assert claims.language == "en"
