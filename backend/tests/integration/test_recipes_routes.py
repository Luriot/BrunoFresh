"""Integration tests for the /api/recipes/* endpoints."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.auth import hash_password, issue_access_token
from app.models import Ingredient, Recipe, RecipeIngredient, User


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
    assert create_resp.json()["is_favorite_by_me"] is False

    # Toggle favorite via the dedicated endpoint
    fav_resp = await client.post(f"/api/recipes/{recipe_id}/favorite")
    assert fav_resp.status_code == 200
    assert fav_resp.json()["is_favorite_by_me"] is True


# ── display_name and quantity_display on ingredients ─────────────────────────

async def test_ingredient_quantity_display_fraction(client):
    """quantity=0.5 must be formatted as the '½' fraction symbol."""
    payload = {
        "title": "Omelette",
        "base_servings": 1,
        "ingredients": [
            {
                "raw_string": "half egg",
                "quantity": 0.5,
                "unit": "piece",
                "ingredient_name": "egg",
                "category": "Dairy",
            }
        ],
    }
    create_resp = await client.post("/api/recipes", json=payload)
    recipe_id = create_resp.json()["id"]

    resp = await client.get(f"/api/recipes/{recipe_id}")
    assert resp.status_code == 200
    ing = resp.json()["ingredients"][0]
    assert ing["quantity_display"] == "½"


async def test_ingredient_quantity_display_whole(client):
    """Integer quantities must be rendered without a decimal point."""
    payload = {
        "title": "Pasta",
        "ingredients": [{"raw_string": "2 eggs", "quantity": 2, "unit": "piece", "ingredient_name": "egg"}],
    }
    create_resp = await client.post("/api/recipes", json=payload)
    resp = await client.get(f"/api/recipes/{create_resp.json()['id']}")
    assert resp.json()["ingredients"][0]["quantity_display"] == "2"


async def test_ingredient_quantity_display_mixed_number(client):
    """1.5 must be rendered as '1½'."""
    payload = {
        "title": "Soup",
        "ingredients": [{"raw_string": "1.5 cups", "quantity": 1.5, "unit": "cup", "ingredient_name": "broth"}],
    }
    create_resp = await client.post("/api/recipes", json=payload)
    resp = await client.get(f"/api/recipes/{create_resp.json()['id']}")
    assert resp.json()["ingredients"][0]["quantity_display"] == "1½"


async def test_ingredient_display_name_english_default(client):
    """With the default 'en' language claim, display_name == ingredient_name."""
    payload = {
        "title": "Chicken Dish",
        "ingredients": [{"raw_string": "1 chicken", "quantity": 1, "unit": "piece", "ingredient_name": "chicken"}],
    }
    create_resp = await client.post("/api/recipes", json=payload)
    resp = await client.get(f"/api/recipes/{create_resp.json()['id']}")
    ing = resp.json()["ingredients"][0]
    assert ing["display_name"] == "chicken"
    assert ing["ingredient_name"] == "chicken"


async def test_ingredient_display_name_fr_uses_name_fr(anon_client, db_session):
    """With a 'fr' token, display_name must be the French name when available."""
    # Create a user with FR language so we can issue a real FR token.
    fr_user = User(
        username="_fr_recipe_test_",
        hashed_password=hash_password("_"),
        role="user",
        language="fr",
    )
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    # Insert an ingredient + recipe directly — the custom POST route goes through
    # the normaliser which may merge the ingredient name, so we bypass it here.
    ingredient = Ingredient(name_en="chicken", name_fr="poulet", category="Meat")
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(ingredient)

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

    link = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        raw_string="1 chicken",
        quantity=1.0,
        unit="piece",
    )
    db_session.add(link)
    await db_session.commit()

    token = issue_access_token(user_id=fr_user.id, role="user", language="fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)

    resp = await anon_client.get(f"/api/recipes/{recipe.id}")
    assert resp.status_code == 200
    ing = resp.json()["ingredients"][0]
    assert ing["display_name"] == "poulet"


# ── PATCH /api/recipes/{id} ───────────────────────────────────────────────────

async def test_patch_recipe_instructions(client):
    create_resp = await client.post("/api/recipes", json={"title": "Patchable"})
    recipe_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/recipes/{recipe_id}",
        json={"instructions_text": "Step 1. Done."},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["instructions_text"] == "Step 1. Done."


async def test_patch_recipe_prep_time(client):
    create_resp = await client.post("/api/recipes", json={"title": "Timed Recipe"})
    recipe_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/recipes/{recipe_id}", json={"prep_time_minutes": 25})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["prep_time_minutes"] == 25


async def test_patch_nonexistent_recipe_returns_404(client):
    resp = await client.patch("/api/recipes/99999", json={"prep_time_minutes": 10})
    assert resp.status_code == 404


# ── DELETE /api/recipes/{id} ──────────────────────────────────────────────────

async def test_delete_recipe(client):
    create_resp = await client.post("/api/recipes", json={"title": "To Delete"})
    recipe_id = create_resp.json()["id"]

    # Regular users cannot delete recipes (admin-only) — expect 403
    del_resp = await client.delete(f"/api/recipes/{recipe_id}")
    assert del_resp.status_code == 403

    # Confirm the recipe still exists
    get_resp = await client.get(f"/api/recipes/{recipe_id}")
    assert get_resp.status_code == 200


async def test_delete_nonexistent_recipe_returns_404(client):
    # Regular users are rejected before existence is checked (admin-only delete)
    resp = await client.delete("/api/recipes/99999")
    assert resp.status_code == 403


async def test_delete_recipe_requires_auth(anon_client):
    resp = await anon_client.delete("/api/recipes/1")
    assert resp.status_code == 401


async def test_admin_can_delete_recipe(anon_client, db_session):
    """Admin users can delete recipes; regular users get 403."""
    from app.config import settings
    from app.services.auth import hash_password, issue_access_token

    admin_user = User(username="_del_admin_", hashed_password=hash_password("_"), role="admin")
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)

    recipe = Recipe(title="Admin Delete Me", url="https://test.example/admin-del", source_domain="test", base_servings=2, instructions_text="")
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    token = issue_access_token(user_id=admin_user.id, role="admin", language="en")
    anon_client.cookies.set(settings.auth_cookie_name, token)

    del_resp = await anon_client.delete(f"/api/recipes/{recipe.id}")
    assert del_resp.status_code == 204

    get_resp = await anon_client.get(f"/api/recipes/{recipe.id}")
    assert get_resp.status_code == 404


async def test_ingredient_display_name_fr_falls_back_to_en(anon_client, db_session):
    """When name_fr is missing, display_name must fall back to name_en."""
    fr_user = User(
        username="_fr_fallback_test_",
        hashed_password=hash_password("_"),
        role="user",
        language="fr",
    )
    db_session.add(fr_user)
    await db_session.commit()
    await db_session.refresh(fr_user)

    ingredient = Ingredient(name_en="broccoli", name_fr=None, category="Vegetables")
    db_session.add(ingredient)
    await db_session.commit()
    await db_session.refresh(ingredient)

    recipe = Recipe(
        title="Broccoli Dish",
        url="https://test.example/broccoli",
        source_domain="test",
        base_servings=1,
        instructions_text="",
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)

    link = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        raw_string="1 cup broccoli",
        quantity=1.0,
        unit="cup",
    )
    db_session.add(link)
    await db_session.commit()

    token = issue_access_token(user_id=fr_user.id, role="user", language="fr")
    anon_client.cookies.set(settings.auth_cookie_name, token)

    resp = await anon_client.get(f"/api/recipes/{recipe.id}")
    assert resp.status_code == 200
    ing = resp.json()["ingredients"][0]
    assert ing["display_name"] == "broccoli"


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


# ── PUT /api/recipes/{id}/tags ────────────────────────────────────────────────

async def test_set_recipe_tags(client):
    """PUT /api/recipes/{id}/tags sets the tag list and returns the full recipe."""
    recipe_resp = await client.post("/api/recipes", json={"title": "Tagless Recipe"})
    recipe_id = recipe_resp.json()["id"]

    tag_resp = await client.post("/api/tags", json={"name": "Végétarien", "color": "#65a30d"})
    tag_id = tag_resp.json()["id"]

    put_resp = await client.put(f"/api/recipes/{recipe_id}/tags", json={"tag_ids": [tag_id]})
    assert put_resp.status_code == 200
    tag_names = [t["name"] for t in put_resp.json()["tags"]]
    assert "Végétarien" in tag_names


async def test_set_recipe_tags_clears_existing(client):
    """Sending an empty list removes all tags from the recipe."""
    recipe_resp = await client.post("/api/recipes", json={"title": "Tagged Recipe"})
    recipe_id = recipe_resp.json()["id"]

    tag_resp = await client.post("/api/tags", json={"name": "Rapide", "color": "#16a34a"})
    tag_id = tag_resp.json()["id"]

    await client.put(f"/api/recipes/{recipe_id}/tags", json={"tag_ids": [tag_id]})

    clear_resp = await client.put(f"/api/recipes/{recipe_id}/tags", json={"tag_ids": []})
    assert clear_resp.status_code == 200
    assert clear_resp.json()["tags"] == []


async def test_set_recipe_tags_nonexistent_recipe_returns_404(client):
    resp = await client.put("/api/recipes/99999/tags", json={"tag_ids": []})
    assert resp.status_code == 404
