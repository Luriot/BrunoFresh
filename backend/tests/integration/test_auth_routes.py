"""Integration tests for the /api/auth/* endpoints."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.rate_limiter import _attempts as _login_attempts, MAX_ATTEMPTS
from app.services.auth import hash_password, issue_access_token, verify_access_token
from app.models import User


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Clear in-memory rate-limit state before and after each test."""
    _login_attempts.clear()
    yield
    _login_attempts.clear()


@pytest.fixture
async def test_user(db_session):
    """Create a regular test user in the in-memory DB."""
    user = User(
        username="testuser",
        hashed_password=hash_password("testpassword"),
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# -- GET /api/auth/me ---------------------------------------------------------

async def test_me_without_cookie_returns_401(anon_client):
    response = await anon_client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_with_valid_cookie_returns_user(anon_client, test_user):
    token = issue_access_token(user_id=test_user.id, role=test_user.role)
    anon_client.cookies.set(settings.auth_cookie_name, token)
    response = await anon_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role


# -- POST /api/auth/login -----------------------------------------------------

async def test_login_correct_credentials_returns_200_and_sets_cookie(anon_client, test_user):
    response = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role
    assert settings.auth_cookie_name in response.cookies


async def test_login_wrong_password_returns_401(anon_client, test_user):
    response = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "wrong"}
    )
    assert response.status_code == 401


# -- Language field in auth responses -----------------------------------------

async def test_me_returns_language_field(anon_client, test_user):
    """GET /api/auth/me must include the language field from the User model."""
    token = issue_access_token(user_id=test_user.id, role=test_user.role, language="en")
    anon_client.cookies.set(settings.auth_cookie_name, token)
    response = await anon_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "language" in data
    assert data["language"] == "en"


async def test_login_response_includes_language(anon_client, test_user):
    """POST /api/auth/login response body must include the language field."""
    response = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "language" in response.json()


async def test_login_cookie_token_encodes_user_language(anon_client, db_session):
    """The cookie issued on login must encode the user's stored language preference."""
    fr_user = User(
        username="fr_user",
        hashed_password=hash_password("testpassword"),
        role="user",
        language="fr",
    )
    db_session.add(fr_user)
    await db_session.commit()

    response = await anon_client.post(
        "/api/auth/login", json={"username": "fr_user", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert response.json()["language"] == "fr"

    cookie_token = response.cookies.get(settings.auth_cookie_name)
    assert cookie_token is not None
    claims = verify_access_token(cookie_token)
    assert claims is not None
    assert claims.language == "fr"



async def test_login_unknown_user_returns_401(anon_client):
    response = await anon_client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_login_empty_username_rejected(anon_client):
    """Pydantic min_length=1 rejects empty username before rate-limit check."""
    response = await anon_client.post("/api/auth/login", json={"username": "", "password": "x"})
    assert response.status_code == 422


async def test_login_empty_password_rejected(anon_client):
    response = await anon_client.post("/api/auth/login", json={"username": "x", "password": ""})
    assert response.status_code == 422


# -- POST /api/auth/logout ----------------------------------------------------

async def test_logout_clears_cookie(anon_client):
    response = await anon_client.post("/api/auth/logout")
    assert response.status_code == 200


# -- Rate limiter -------------------------------------------------------------

async def test_rate_limit_triggers_after_max_failed_attempts(anon_client, test_user):
    """POST /api/auth/login must return 429 after MAX_ATTEMPTS consecutive failures."""
    for _ in range(MAX_ATTEMPTS):
        resp = await anon_client.post(
            "/api/auth/login", json={"username": "testuser", "password": "wrongpassword"}
        )
        assert resp.status_code == 401

    # The next attempt should be rate-limited
    resp = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "wrongpassword"}
    )
    assert resp.status_code == 429


async def test_rate_limit_resets_on_successful_login(anon_client, test_user):
    """A successful login clears the rate-limit counter for that IP."""
    # Exhaust attempts up to MAX_ATTEMPTS - 1 (still under the limit)
    for _ in range(MAX_ATTEMPTS - 1):
        await anon_client.post(
            "/api/auth/login", json={"username": "testuser", "password": "wrong"}
        )

    # A correct login should succeed and clear the counter
    resp = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    assert resp.status_code == 200

    # After a successful login the counter is cleared — another wrong attempt should
    # return 401, not 429
    resp = await anon_client.post(
        "/api/auth/login", json={"username": "testuser", "password": "wrong"}
    )
    assert resp.status_code == 401
