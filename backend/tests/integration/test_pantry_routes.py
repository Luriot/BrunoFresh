"""Integration tests for the /api/pantry/* endpoints."""
from __future__ import annotations

import pytest

from app.models import PantryItem


async def test_list_pantry_empty(client):
    response = await client.get("/api/pantry")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_pantry_requires_auth(anon_client):
    response = await anon_client.get("/api/pantry")
    assert response.status_code == 401


async def test_delete_pantry_item(client, db_session):
    """Insert a pantry item directly and verify DELETE removes it."""
    item = PantryItem(name="milk", category="Dairy")
    db_session.add(item)
    await db_session.flush()
    item_id = item.id
    await db_session.commit()

    del_resp = await client.delete(f"/api/pantry/{item_id}")
    assert del_resp.status_code == 204

    # Confirm it no longer appears in the list
    list_resp = await client.get("/api/pantry")
    assert all(i["id"] != item_id for i in list_resp.json())


async def test_delete_nonexistent_pantry_item_returns_404(client):
    response = await client.delete("/api/pantry/99999")
    assert response.status_code == 404
