"""Integration tests for the /api/meal-plans/* endpoints."""
from __future__ import annotations

from app.models import Recipe


# ── GET /api/meal-plans ───────────────────────────────────────────────────────

async def test_list_meal_plans_empty(client):
    resp = await client.get("/api/meal-plans")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_meal_plans_requires_auth(anon_client):
    resp = await anon_client.get("/api/meal-plans")
    assert resp.status_code == 401


# ── POST /api/meal-plans ──────────────────────────────────────────────────────

async def test_create_meal_plan_returns_201(client):
    resp = await client.post("/api/meal-plans", json={"label": "Week 1"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == "Week 1"
    assert data["entries"] == []
    assert "id" in data


async def test_create_meal_plan_requires_auth(anon_client):
    resp = await anon_client.post("/api/meal-plans", json={"label": "Test"})
    assert resp.status_code == 401


# ── GET /api/meal-plans/{id} ──────────────────────────────────────────────────

async def test_get_meal_plan_by_id(client):
    create_resp = await client.post("/api/meal-plans", json={"label": "Fetch me"})
    plan_id = create_resp.json()["id"]

    resp = await client.get(f"/api/meal-plans/{plan_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == plan_id


async def test_get_nonexistent_meal_plan_returns_404(client):
    resp = await client.get("/api/meal-plans/99999")
    assert resp.status_code == 404


# ── DELETE /api/meal-plans/{id} ───────────────────────────────────────────────

async def test_delete_meal_plan(client):
    create_resp = await client.post("/api/meal-plans", json={"label": "Delete me"})
    plan_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/meal-plans/{plan_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/meal-plans/{plan_id}")
    assert get_resp.status_code == 404


async def test_delete_nonexistent_meal_plan_returns_404(client):
    resp = await client.delete("/api/meal-plans/99999")
    assert resp.status_code == 404


# ── PATCH /api/meal-plans/{id} ────────────────────────────────────────────────

async def test_patch_meal_plan_label(client):
    create_resp = await client.post("/api/meal-plans", json={"label": "Old"})
    plan_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/meal-plans/{plan_id}", json={"label": "New"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["label"] == "New"


async def test_patch_nonexistent_meal_plan_returns_404(client):
    resp = await client.patch("/api/meal-plans/99999", json={"label": "Ghost"})
    assert resp.status_code == 404


# ── POST /api/meal-plans/{id}/entries ─────────────────────────────────────────

async def test_add_entry_to_meal_plan(client, db_session):
    """An entry linking a recipe to a day can be created."""
    recipe = Recipe(
        title="Poulet Rôti",
        url="https://test.example/poulet",
        source_domain="test",
        base_servings=2,
        instructions_text="",
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    create_resp = await client.post("/api/meal-plans", json={"label": "Week A"})
    plan_id = create_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/meal-plans/{plan_id}/entries",
        json={"recipe_id": recipe.id, "day_of_week": 0, "target_servings": 4},
    )
    assert entry_resp.status_code == 201
    data = entry_resp.json()
    assert data["recipe_id"] == recipe.id
    assert data["day_of_week"] == 0
    assert data["target_servings"] == 4


async def test_add_entry_nonexistent_recipe_returns_404(client):
    create_resp = await client.post("/api/meal-plans", json={"label": "Plan"})
    plan_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/meal-plans/{plan_id}/entries",
        json={"recipe_id": 99999, "day_of_week": 1},
    )
    assert resp.status_code == 404


# ── DELETE /api/meal-plans/{id}/entries/{entry_id} ────────────────────────────

async def test_delete_meal_plan_entry(client, db_session):
    recipe = Recipe(
        title="Pasta",
        url="https://test.example/pasta",
        source_domain="test",
        base_servings=2,
        instructions_text="",
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    create_resp = await client.post("/api/meal-plans", json={"label": "Week B"})
    plan_id = create_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/meal-plans/{plan_id}/entries",
        json={"recipe_id": recipe.id, "day_of_week": 2},
    )
    entry_id = entry_resp.json()["id"]

    del_resp = await client.delete(f"/api/meal-plans/{plan_id}/entries/{entry_id}")
    assert del_resp.status_code == 204

    # Confirm it's gone from the plan
    get_resp = await client.get(f"/api/meal-plans/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["entries"] == []


# ── PATCH /api/meal-plans/{id}/entries/{entry_id} ────────────────────────────

async def test_patch_meal_plan_entry_servings(client, db_session):
    recipe = Recipe(
        title="Risotto",
        url="https://test.example/risotto",
        source_domain="test",
        base_servings=2,
        instructions_text="",
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    create_resp = await client.post("/api/meal-plans", json={"label": "Week C"})
    plan_id = create_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/meal-plans/{plan_id}/entries",
        json={"recipe_id": recipe.id, "day_of_week": 3, "target_servings": 2},
    )
    entry_id = entry_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/meal-plans/{plan_id}/entries/{entry_id}",
        json={"target_servings": 6},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["target_servings"] == 6
