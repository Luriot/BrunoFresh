"""Integration tests for the /api/recipes/* endpoints."""
from __future__ import annotations

import pytest


# ── GET /api/recipes ──────────────────────────────────────────────────────────

async def test_list_recipes_empty(client):
    response = await client.get("/api/recipes")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_recipes_requires_auth(anon_client):
    response = await anon_client.get("/api/recipes")
    assert response.status_code == 401


# ── POST /api/recipes (create custom) ────────────────────────────────────────

async def test_create_recipe_returns_200(client):
    payload = {
        "title": "Test Pasta",
        "instructions_text": "Boil water. Cook pasta.",
        "base_servings": 2,
    }
    response = await client.post("/api/recipes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Pasta"
    assert data["source_domain"] == "custom"
    assert data["base_servings"] == 2
    assert data["ingredients"] == []


async def test_create_recipe_with_ingredients(client):
    payload = {
        "title": "Simple Omelette",
        "base_servings": 1,
        "ingredients": [
            {
                "raw_string": "2 eggs",
                "quantity": 2,
                "unit": "piece",
                "ingredient_name": "eggs",
                "category": "Dairy",
            }
        ],
    }
    response = await client.post("/api/recipes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["ingredient_name"] == "eggs"


# ── GET /api/recipes/{id} ─────────────────────────────────────────────────────

async def test_get_recipe_by_id(client):
    create_resp = await client.post("/api/recipes", json={"title": "My Recipe"})
    recipe_id = create_resp.json()["id"]

    response = await client.get(f"/api/recipes/{recipe_id}")
    assert response.status_code == 200
    assert response.json()["id"] == recipe_id
    assert response.json()["title"] == "My Recipe"


async def test_get_recipe_not_found(client):
    response = await client.get("/api/recipes/99999")
    assert response.status_code == 404


# ── PATCH /api/recipes/{id} ───────────────────────────────────────────────────

async def test_patch_recipe_favorite(client):
    create_resp = await client.post("/api/recipes", json={"title": "Patchable Recipe"})
    recipe_id = create_resp.json()["id"]
    assert create_resp.json()["is_favorite"] is False

    patch_resp = await client.patch(
        f"/api/recipes/{recipe_id}", json={"is_favorite": True}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_favorite"] is True


# ── DELETE /api/recipes/{id} ──────────────────────────────────────────────────

async def test_delete_recipe(client):
    create_resp = await client.post("/api/recipes", json={"title": "Delete Me"})
    recipe_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/recipes/{recipe_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/recipes/{recipe_id}")
    assert get_resp.status_code == 404


# ── GET /api/recipes?q=… ─────────────────────────────────────────────────────

async def test_search_recipes_by_title(client):
    await client.post("/api/recipes", json={"title": "Banana Bread"})
    await client.post("/api/recipes", json={"title": "Chocolate Cake"})

    resp = await client.get("/api/recipes?q=banana")
    assert resp.status_code == 200
    titles = [r["title"] for r in resp.json()]
    assert "Banana Bread" in titles
    assert "Chocolate Cake" not in titles


async def test_search_recipes_no_results(client):
    await client.post("/api/recipes", json={"title": "Known Recipe"})
    resp = await client.get("/api/recipes?q=xyznotfound999")
    assert resp.status_code == 200
    assert resp.json() == []
