"""Integration tests for the /api/lists/* endpoints."""
from __future__ import annotations

import pytest

from app.models import ShoppingList, ShoppingListItem, User


# ── POST /api/lists ───────────────────────────────────────────────────────────

async def test_create_empty_list(client):
    """A list with no recipes and no extra items is a valid request."""
    resp = await client.post("/api/lists", json={"items": [], "label": "Groceries"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "Groceries"
    assert data["items"] == []
    assert "id" in data


async def test_create_list_with_custom_items(client):
    """Extra items are aggregated and returned in the response."""
    payload = {
        "items": [],
        "label": "Weekend",
        "extra_items": [
            {"name": "avocado", "quantity": 2, "unit": "piece", "category": "Produce"}
        ],
    }
    resp = await client.post("/api/lists", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "avocado"
    assert data["items"][0]["is_custom"] is True


async def test_create_list_requires_auth(anon_client):
    resp = await anon_client.post("/api/lists", json={"items": []})
    assert resp.status_code == 401


# ── GET /api/lists ────────────────────────────────────────────────────────────

async def test_list_all_empty(client):
    resp = await client.get("/api/lists")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_all_returns_created_list(client):
    await client.post("/api/lists", json={"items": [], "label": "Visible"})
    resp = await client.get("/api/lists")
    assert resp.status_code == 200
    labels = [lst["label"] for lst in resp.json()]
    assert "Visible" in labels


async def test_list_all_requires_auth(anon_client):
    resp = await anon_client.get("/api/lists")
    assert resp.status_code == 401


# ── GET /api/lists/{id} ───────────────────────────────────────────────────────

async def test_get_list_by_id(client):
    create_resp = await client.post("/api/lists", json={"items": [], "label": "Fetch me"})
    list_id = create_resp.json()["id"]
    resp = await client.get(f"/api/lists/{list_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == list_id


async def test_get_nonexistent_list_returns_404(client):
    resp = await client.get("/api/lists/99999")
    assert resp.status_code == 404


async def test_get_list_requires_auth(anon_client):
    resp = await anon_client.get("/api/lists/1")
    assert resp.status_code == 401


# ── PATCH /api/lists/{id} ─────────────────────────────────────────────────────

async def test_patch_list_label(client):
    create_resp = await client.post("/api/lists", json={"items": [], "label": "Old Name"})
    list_id = create_resp.json()["id"]
    patch_resp = await client.patch(f"/api/lists/{list_id}", json={"label": "New Name"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["label"] == "New Name"


async def test_patch_nonexistent_list_returns_404(client):
    resp = await client.patch("/api/lists/99999", json={"label": "ghost"})
    assert resp.status_code == 404


# ── DELETE /api/lists/{id} ────────────────────────────────────────────────────

async def test_delete_list(client):
    create_resp = await client.post("/api/lists", json={"items": [], "label": "Bye"})
    list_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/lists/{list_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    get_resp = await client.get(f"/api/lists/{list_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_list_returns_404(client):
    resp = await client.delete("/api/lists/99999")
    assert resp.status_code == 404


async def test_delete_list_requires_auth(anon_client):
    resp = await anon_client.delete("/api/lists/1")
    assert resp.status_code == 401


# ── POST /api/lists/{id}/items ────────────────────────────────────────────────

async def test_add_custom_item_to_list(client):
    create_resp = await client.post("/api/lists", json={"items": [], "label": "Add to me"})
    list_id = create_resp.json()["id"]
    item_resp = await client.post(
        f"/api/lists/{list_id}/items",
        json={"name": "parsley", "quantity": 1, "unit": "bunch", "category": "Produce"},
    )
    assert item_resp.status_code == 200
    data = item_resp.json()
    assert data["name"] == "parsley"
    assert data["is_custom"] is True


async def test_add_item_to_nonexistent_list_returns_404(client):
    resp = await client.post(
        "/api/lists/99999/items",
        json={"name": "milk", "quantity": 1, "unit": "L", "category": "Dairy"},
    )
    assert resp.status_code == 404


# ── FR display name ───────────────────────────────────────────────────────────

async def test_list_display_name_fr(anon_client, db_session):
    """With a 'fr' token, shopping list item display_name uses name_fr when available."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_list_test_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    shopping_list = ShoppingList(user_id=fr_user.id, label="FR test list")
    db_session.add(shopping_list)
    await db_session.commit()
    await db_session.refresh(shopping_list)

    item = ShoppingListItem(
        shopping_list_id=shopping_list.id,
        name="milk",
        name_fr="lait",
        quantity=1.0,
        unit="L",
        category="Dairy",
    )
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)
    resp = await anon_client.get(f"/api/lists/{shopping_list.id}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["display_name"] == "lait"


async def test_list_display_name_fr_fallback(anon_client, db_session):
    """With a 'fr' token but no name_fr, display_name falls back to name_en."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    fr_user = User(username="_fr_list_fallback_", hashed_password=hash_password("_"), role="user", language="fr")
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    shopping_list = ShoppingList(user_id=fr_user.id, label="FR fallback list")
    db_session.add(shopping_list)
    await db_session.commit()
    await db_session.refresh(shopping_list)

    item = ShoppingListItem(
        shopping_list_id=shopping_list.id,
        name="milk",
        name_fr=None,
        quantity=1.0,
        unit="L",
        category="Dairy",
    )
    db_session.add(item)
    await db_session.commit()

    token = issue_access_token(fr_user.id, "user", "fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)
    resp = await anon_client.get(f"/api/lists/{shopping_list.id}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["display_name"] == "milk"


# ── PATCH /api/lists/{list_id}/items/{item_id} ────────────────────────────────

async def test_patch_list_item_is_already_owned(client):
    """Marking an item as already-owned persists and is reflected in the response."""
    create_resp = await client.post(
        "/api/lists",
        json={
            "items": [],
            "extra_items": [{"name": "butter", "quantity": 1, "unit": "pack", "category": "Dairy"}],
        },
    )
    list_id = create_resp.json()["id"]
    item_id = create_resp.json()["items"][0]["id"]

    patch_resp = await client.patch(
        f"/api/lists/{list_id}/items/{item_id}", json={"is_already_owned": True}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_already_owned"] is True


async def test_patch_list_item_nonexistent_returns_404(client):
    create_resp = await client.post("/api/lists", json={"items": []})
    list_id = create_resp.json()["id"]
    resp = await client.patch(f"/api/lists/{list_id}/items/99999", json={"is_already_owned": True})
    assert resp.status_code == 404


# ── DELETE /api/lists/{list_id}/items/{item_id} ───────────────────────────────

async def test_delete_list_item(client):
    """A custom item can be deleted; subsequent GET should not include it."""
    create_resp = await client.post(
        "/api/lists",
        json={
            "items": [],
            "extra_items": [{"name": "avocado", "quantity": 1, "unit": "piece", "category": "Produce"}],
        },
    )
    list_id = create_resp.json()["id"]
    item_id = create_resp.json()["items"][0]["id"]

    del_resp = await client.delete(f"/api/lists/{list_id}/items/{item_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/lists/{list_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["items"] == []


async def test_delete_list_item_nonexistent_returns_404(client):
    create_resp = await client.post("/api/lists", json={"items": []})
    list_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/lists/{list_id}/items/99999")
    assert resp.status_code == 404
