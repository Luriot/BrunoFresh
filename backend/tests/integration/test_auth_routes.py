"""Integration tests for the /api/auth/* endpoints."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.rate_limiter import _attempts as _login_attempts
from app.services.auth import hash_password, issue_access_token
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
