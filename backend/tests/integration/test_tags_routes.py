"""Integration tests for the /api/tags/* endpoints."""
from __future__ import annotations

import pytest


async def test_list_tags_empty(client):
    response = await client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_tag(client):
    payload = {"name": "Vegan", "color": "#4d7c0f"}
    response = await client.post("/api/tags", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Vegan"
    assert data["color"] == "#4d7c0f"
    assert "id" in data


async def test_create_tag_requires_auth(anon_client):
    response = await anon_client.post("/api/tags", json={"name": "NoAuth"})
    assert response.status_code == 401


async def test_create_duplicate_tag_returns_409(client):
    await client.post("/api/tags", json={"name": "Unique"})
    resp2 = await client.post("/api/tags", json={"name": "Unique"})
    assert resp2.status_code == 409


async def test_delete_tag(client):
    create_resp = await client.post("/api/tags", json={"name": "ToDelete"})
    tag_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/tags/{tag_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone
    list_resp = await client.get("/api/tags")
    names = [t["name"] for t in list_resp.json()]
    assert "ToDelete" not in names


async def test_delete_nonexistent_tag_returns_404(client):
    response = await client.delete("/api/tags/99999")
    assert response.status_code == 404
