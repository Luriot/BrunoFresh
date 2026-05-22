"""Integration tests for the /api/pantry/* endpoints."""
from __future__ import annotations

import pytest

from app.models import PantryItem, User


async def test_list_pantry_empty(client):
    response = await client.get("/api/pantry")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_pantry_requires_auth(anon_client):
    response = await anon_client.get("/api/pantry")
    assert response.status_code == 401


async def test_delete_pantry_item(client, db_session):
    """Insert a pantry item via API and verify DELETE removes it."""
    # Create via the API so the correct user_id from fake claims is applied.
    add_resp = await client.post("/api/pantry", json={"name": "milk", "category": "Dairy"})
    item_id = add_resp.json()["id"]

    del_resp = await client.delete(f"/api/pantry/{item_id}")
    assert del_resp.status_code == 204

    # Confirm it no longer appears in the list
    list_resp = await client.get("/api/pantry")
    assert all(i["id"] != item_id for i in list_resp.json())


async def test_delete_nonexistent_pantry_item_returns_404(client):
    response = await client.delete("/api/pantry/99999")
    assert response.status_code == 404


async def test_add_pantry_item_requires_auth(anon_client):
    response = await anon_client.post("/api/pantry", json={"name": "milk", "category": "Dairy"})
    assert response.status_code == 401


async def test_delete_pantry_item_requires_auth(anon_client):
    response = await anon_client.delete("/api/pantry/1")
    assert response.status_code == 401


async def test_pantry_display_name_fr(anon_client, db_session):
    """With a 'fr' token, display_name uses name_fr when available."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_pantry_test_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    item = PantryItem(user_id=fr_user.id, name="milk", name_fr="lait", category="Dairy")
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)
    resp = await anon_client.get("/api/pantry")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "lait"


async def test_pantry_display_name_fr_fallback(anon_client, db_session):
    """With a 'fr' token but no name_fr, display_name falls back to name_en."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_pantry_fallback_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    item = PantryItem(user_id=fr_user.id, name="milk", name_fr=None, category="Dairy")
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)
    resp = await anon_client.get("/api/pantry")
    assert resp.status_code == 200
    assert resp.json()[0]["display_name"] == "milk"
