"""Integration tests for the /api/auth/* endpoints.

These tests exercise the real auth logic (no require_auth override) using
`anon_client` which only overrides the DB session.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.api.routers.auth import _login_attempts


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Clear in-memory rate-limit state before and after each test."""
    _login_attempts.clear()
    yield
    _login_attempts.clear()


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

async def test_me_without_cookie_returns_401(anon_client):
    response = await anon_client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_with_valid_cookie_returns_200(anon_client):
    from app.services.auth import issue_access_token
    from app.config import settings

    token = issue_access_token()
    anon_client.cookies.set(settings.auth_cookie_name, token)
    response = await anon_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


# ── POST /api/auth/login ──────────────────────────────────────────────────────

async def test_login_wrong_passcode_returns_401(anon_client):
    response = await anon_client.post(
        "/api/auth/login", json={"passcode": "definitely-wrong"}
    )
    assert response.status_code == 401


async def test_login_correct_passcode_returns_200_and_sets_cookie(anon_client):
    response = await anon_client.post(
        "/api/auth/login", json={"passcode": settings.app_passcode}
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    # Cookie must be set in the response
    assert settings.auth_cookie_name in response.cookies


async def test_login_empty_passcode_rejected(anon_client):
    """Pydantic min_length=1 rejects empty passcodes before rate-limit check."""
    response = await anon_client.post("/api/auth/login", json={"passcode": ""})
    assert response.status_code == 422  # Pydantic validation error


# ── POST /api/auth/logout ─────────────────────────────────────────────────────

async def test_logout_returns_200(anon_client):
    response = await anon_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


async def test_logout_sends_delete_cookie_header(anon_client):
    """Logout must send a Set-Cookie header that instructs the browser to delete
    the session cookie (max-age=0 / expired date)."""
    from app.services.auth import issue_access_token

    token = issue_access_token()
    anon_client.cookies.set(settings.auth_cookie_name, token)
    response = await anon_client.post("/api/auth/logout")
    assert response.status_code == 200
    cookie_header = response.headers.get("set-cookie", "")
    assert settings.auth_cookie_name in cookie_header
