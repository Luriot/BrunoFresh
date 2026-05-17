"""Integration tests for the /api/users/me/* endpoints."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.auth import hash_password, verify_access_token
from app.models import User
from sqlalchemy import select


# ── PATCH /api/users/me/language ─────────────────────────────────────────────

async def test_patch_language_to_fr_returns_200(client):
    response = await client.patch("/api/users/me/language", json={"language": "fr"})
    assert response.status_code == 200


async def test_patch_language_response_has_updated_language(client):
    response = await client.patch("/api/users/me/language", json={"language": "fr"})
    assert response.json()["language"] == "fr"


async def test_patch_language_to_en_returns_200(client):
    response = await client.patch("/api/users/me/language", json={"language": "en"})
    assert response.status_code == 200
    assert response.json()["language"] == "en"


async def test_patch_language_unsupported_returns_422(client):
    """Languages outside {en, fr} are rejected."""
    response = await client.patch("/api/users/me/language", json={"language": "de"})
    assert response.status_code == 422


async def test_patch_language_empty_string_rejected_by_schema(client):
    """LanguagePatch has min_length=2, so an empty string should fail validation."""
    response = await client.patch("/api/users/me/language", json={"language": ""})
    assert response.status_code == 422


async def test_patch_language_requires_auth(anon_client):
    response = await anon_client.patch("/api/users/me/language", json={"language": "fr"})
    assert response.status_code == 401


async def test_patch_language_persists_to_db(client, db_session):
    """The updated language must be flushed to the database."""
    await client.patch("/api/users/me/language", json={"language": "fr"})

    user = await db_session.scalar(select(User).where(User.username == "_stub_"))
    assert user is not None
    assert user.language == "fr"


async def test_patch_language_reissues_cookie(client):
    """A fresh auth cookie must be present in the response."""
    response = await client.patch("/api/users/me/language", json={"language": "fr"})
    assert response.status_code == 200
    assert settings.auth_cookie_name in response.cookies


async def test_patch_language_cookie_encodes_new_language(client):
    """The reissued token must carry the updated language claim."""
    response = await client.patch("/api/users/me/language", json={"language": "fr"})
    cookie_token = response.cookies.get(settings.auth_cookie_name)
    assert cookie_token is not None

    claims = verify_access_token(cookie_token)
    assert claims is not None
    assert claims.language == "fr"


async def test_patch_language_idempotent(client):
    """Switching to the same language twice must not cause an error."""
    r1 = await client.patch("/api/users/me/language", json={"language": "fr"})
    r2 = await client.patch("/api/users/me/language", json={"language": "fr"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["language"] == "fr"


async def test_patch_language_roundtrip_en_fr_en(client, db_session):
    """Switching en → fr → en must leave the DB with 'en'."""
    await client.patch("/api/users/me/language", json={"language": "fr"})
    await client.patch("/api/users/me/language", json={"language": "en"})

    user = await db_session.scalar(select(User).where(User.username == "_stub_"))
    assert user is not None
    assert user.language == "en"
