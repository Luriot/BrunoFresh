"""Integration-style tests for aggregate_recipe_ingredients (DB-backed).

Covers the sachet→g and boîte→g fusion path: a recipe declaring "1 sachet" and
another declaring the same ingredient in grams should collapse into a single
ShoppingList row measured in grams.
"""
from __future__ import annotations

import pytest

from app.models import Ingredient, Recipe, RecipeIngredient
from app.schemas import CartRecipeIn
from app.services.aggregator import aggregate_recipe_ingredients


async def _make_recipe(
    db,
    *,
    title: str,
    servings: int,
    rows: list[tuple[Ingredient, float, str, str]],
) -> Recipe:
    recipe = Recipe(
        title=title,
        url=f"http://test/{title.replace(' ', '-')}",
        source_domain="test",
        instructions_text="",
        base_servings=servings,
    )
    db.add(recipe)
    await db.flush()
    for ing, qty, unit, raw in rows:
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing.id,
                raw_string=raw,
                quantity=qty,
                unit=unit,
                needs_review=False,
            )
        )
    await db.flush()
    return recipe


async def test_sachet_and_grams_merge_into_single_row(db_session):
    """1 sachet baking powder + 11 g baking powder → 1 row of 22 g."""
    ing = Ingredient(name_en="baking powder", name_fr="levure chimique", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec_sachet = await _make_recipe(
        db_session,
        title="Cake A",
        servings=2,
        rows=[(ing, 1.0, "sachet", "1 sachet de levure chimique")],
    )
    rec_grams = await _make_recipe(
        db_session,
        title="Cake B",
        servings=2,
        rows=[(ing, 11.0, "g", "11 g de levure chimique")],
    )

    rows, needs_review = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_sachet.id, target_servings=2),
            CartRecipeIn(recipe_id=rec_grams.id, target_servings=2),
        ],
        db_session,
    )

    assert needs_review == []
    baking_rows = [r for r in rows if r["name"] == "baking powder"]
    assert len(baking_rows) == 1, f"expected 1 merged row, got {baking_rows}"
    assert baking_rows[0]["unit"] == "g"
    assert abs(baking_rows[0]["quantity"] - 22.0) < 0.01


async def test_boite_to_grams_aggregation(db_session):
    """2 boîtes tomatoes × 400 g each → 1 row 800 g (→ smart_display rescales to 0.8 kg)."""
    ing = Ingredient(name_en="canned tomatoes", name_fr="tomates pelées", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Sauce A",
        servings=4,
        rows=[(ing, 2.0, "boîte", "2 boîtes de tomates pelées")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=4)],
        db_session,
    )

    toms = [r for r in rows if r["name"] == "canned tomatoes"]
    assert len(toms) == 1
    # 2 * 400 = 800 g → smart_display_unit keeps it at g (below 1000)
    assert toms[0]["unit"] == "g"
    assert abs(toms[0]["quantity"] - 800.0) < 0.01


async def test_unknown_pack_stays_as_paquet(db_session):
    """Ingredients not in _PACK_GRAMS keep 'paquet' as their display unit."""
    ing = Ingredient(name_en="unicorn spice", name_fr="épice licorne", category="Spices")
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Mystery A",
        servings=2,
        rows=[(ing, 1.0, "sachet", "1 sachet d'épice licorne")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=2)],
        db_session,
    )

    sp = [r for r in rows if r["name"] == "unicorn spice"]
    assert len(sp) == 1
    # sachet → paquet (canonical alias) → no static conversion → stays paquet
    assert sp[0]["unit"] == "paquet"
    assert sp[0]["quantity"] == 1.0


async def test_sachet_scales_with_servings(db_session):
    """1 sachet baking powder at 2 servings → 2 sachets (=22 g) at 4 servings."""
    ing = Ingredient(name_en="baking powder", name_fr="levure chimique", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Scale A",
        servings=2,
        rows=[(ing, 1.0, "sachet", "1 sachet de levure chimique")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=4)],
        db_session,
    )

    bp = [r for r in rows if r["name"] == "baking powder"]
    assert len(bp) == 1
    assert bp[0]["unit"] == "g"
    assert abs(bp[0]["quantity"] - 22.0) < 0.01


async def test_retro_calibration_from_raw(db_session):
    """Raw string '(7 g)' per sachet wins over the static 11 g/sachet for baking powder.
    → 2 sachets × 7 g = 14 g (not 22 g)."""
    ing = Ingredient(name_en="baking powder", name_fr="levure chimique", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Retro A",
        servings=2,
        rows=[(ing, 2.0, "sachet", "2 sachets de levure chimique (7 g)")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=2)],
        db_session,
    )

    bp = [r for r in rows if r["name"] == "baking powder"]
    assert len(bp) == 1
    assert bp[0]["unit"] == "g"
    assert abs(bp[0]["quantity"] - 14.0) < 0.01


async def test_admin_override_beats_static(db_session):
    """Ingredient with grams_per_paquet=8.5 overrides the static 11 g/sachet."""
    ing = Ingredient(
        name_en="baking powder",
        name_fr="levure chimique",
        category="Pantry",
        grams_per_paquet=8.5,
    )
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Admin A",
        servings=2,
        rows=[(ing, 1.0, "sachet", "1 sachet de levure chimique")],  # no grams figure
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=2)],
        db_session,
    )

    bp = [r for r in rows if r["name"] == "baking powder"]
    assert len(bp) == 1
    assert bp[0]["unit"] == "g"
    assert abs(bp[0]["quantity"] - 8.5) < 0.01


async def test_retro_beats_admin_override(db_session):
    """Raw '(7 g)' wins over admin override of 8.5 g/sachet."""
    ing = Ingredient(
        name_en="baking powder",
        name_fr="levure chimique",
        category="Pantry",
        grams_per_paquet=8.5,
    )
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Priority A",
        servings=4,
        rows=[(ing, 1.0, "sachet", "1 sachet de levure (7 g)")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=4)],
        db_session,
    )

    bp = [r for r in rows if r["name"] == "baking powder"]
    assert len(bp) == 1
    assert bp[0]["unit"] == "g"
    assert abs(bp[0]["quantity"] - 7.0) < 0.01


async def test_boite_admin_override_aggregation(db_session):
    """Admin-set grams_per_boite on a custom ingredient → still merges with grams rows."""
    ing = Ingredient(
        name_en="unicorn cream",
        name_fr="crème licorne",
        category="Pantry",
        grams_per_boite=300.0,
    )
    db_session.add(ing)
    await db_session.flush()

    rec_boite = await _make_recipe(
        db_session,
        title="Boîte A",
        servings=2,
        rows=[(ing, 1.0, "boîte", "1 boîte de crème licorne")],
    )
    rec_g = await _make_recipe(
        db_session,
        title="Boîte B",
        servings=2,
        rows=[(ing, 100.0, "g", "100 g de crème licorne")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_boite.id, target_servings=2),
            CartRecipeIn(recipe_id=rec_g.id, target_servings=2),
        ],
        db_session,
    )

    rows = [r for r in rows if r["name"] == "unicorn cream"]
    assert len(rows) == 1
    assert rows[0]["unit"] == "g"
    assert abs(rows[0]["quantity"] - 400.0) < 0.01  # 300 + 100


async def test_admin_patch_persists_grams_override(admin_client, db_session):
    """PATCH /api/ingredients/{id} sets grams_per_paquet and returns it."""
    ing = Ingredient(name_en="baking powder", name_fr="levure chimique", category="Pantry")
    db_session.add(ing)
    await db_session.commit()
    await db_session.refresh(ing)

    resp = await admin_client.patch(
        f"/api/ingredients/{ing.id}",
        json={"grams_per_paquet": 8.5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["grams_per_paquet"] == 8.5
    assert body["name_en"] == "baking powder"  # unchanged (name not sent)