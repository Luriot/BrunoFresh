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


async def test_density_merges_tasse_and_grams(db_session):
    """1 tasse flour (125 g) + 125 g flour → 1 row 250 g (via _CULINARY_UNIT_DENSITIES)."""
    ing = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec_tasse = await _make_recipe(
        db_session,
        title="Density A",
        servings=2,
        rows=[(ing, 1.0, "tasse", "1 tasse de farine")],
    )
    rec_g = await _make_recipe(
        db_session,
        title="Density B",
        servings=2,
        rows=[(ing, 125.0, "g", "125 g de farine")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_tasse.id, target_servings=2),
            CartRecipeIn(recipe_id=rec_g.id, target_servings=2),
        ],
        db_session,
    )

    fl = [r for r in rows if r["name"] == "flour"]
    assert len(fl) == 1, f"expected 1 merged row, got {fl}"
    assert fl[0]["unit"] == "g"
    assert abs(fl[0]["quantity"] - 250.0) < 0.01


async def test_incompatible_units_keep_separate(db_session):
    """1 piece tomato + 200 g tomato → 2 distinct rows (count vs weight don't merge)."""
    ing = Ingredient(name_en="tomato", name_fr="tomate", category="Produce")
    db_session.add(ing)
    await db_session.flush()

    rec_pc = await _make_recipe(
        db_session,
        title="Piece A",
        servings=2,
        rows=[(ing, 1.0, "piece", "1 tomate")],
    )
    rec_g = await _make_recipe(
        db_session,
        title="Piece B",
        servings=2,
        rows=[(ing, 200.0, "g", "200 g de tomate")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_pc.id, target_servings=2),
            CartRecipeIn(recipe_id=rec_g.id, target_servings=2),
        ],
        db_session,
    )

    toms = [r for r in rows if r["name"] == "tomato"]
    assert len(toms) == 2, f"expected 2 separate rows for incompatible units, got {toms}"
    units = sorted(r["unit"] for r in toms)
    assert units == ["g", "piece"]


async def test_fractional_multiplier_keeps_zero_loss(db_session):
    """base 4 → target 1 (×0.25): 4 gousses garlic → 1 gousse, no 0.9999 rounding noise."""
    ing = Ingredient(name_en="garlic", name_fr="ail", category="Produce")
    db_session.add(ing)
    await db_session.flush()

    rec = await _make_recipe(
        db_session,
        title="Garlic A",
        servings=4,
        rows=[(ing, 4.0, "gousse", "4 gousses d'ail")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=1)],
        db_session,
    )

    ga = [r for r in rows if r["name"] == "garlic"]
    assert len(ga) == 1
    assert ga[0]["unit"] == "gousse"
    assert abs(ga[0]["quantity"] - 1.0) < 0.001


async def test_base_servings_zero_does_not_diverge(db_session):
    """base_servings=0 must yield multiplier=target (via max(.,1)), never inf/NaN."""
    ing = Ingredient(name_en="milk", name_fr="lait", category="Dairy")
    db_session.add(ing)
    await db_session.flush()

    rec = Recipe(
        title="Zero A",
        url="http://test/zero-a",
        source_domain="test",
        instructions_text="",
        base_servings=0,
    )
    db_session.add(rec)
    await db_session.flush()
    db_session.add(
        RecipeIngredient(
            recipe_id=rec.id,
            ingredient_id=ing.id,
            raw_string="200 ml de lait",
            quantity=200.0,
            unit="ml",
            needs_review=False,
        )
    )
    await db_session.flush()

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=2)],
        db_session,
    )
    mk = [r for r in rows if r["name"] == "milk"]
    assert len(mk) == 1
    assert mk[0]["unit"] in ("ml", "cl", "L")
    # multiplier=2/1=2 → 400 ml
    assert abs(mk[0]["quantity"] - 400.0) < 0.01 or abs(mk[0]["quantity"] - 40.0) < 0.01


async def test_aggregation_is_deterministic(db_session):
    """Two runs over the same recipe set return identical rows (no nondeterminism source)."""
    ing = Ingredient(name_en="sugar", name_fr="sucre", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec_a = await _make_recipe(
        db_session, title="Det A", servings=2,
        rows=[(ing, 2.0, "c. à soupe", "2 c. à soupe de sucre")],
    )
    rec_b = await _make_recipe(
        db_session, title="Det B", servings=4,
        rows=[(ing, 100.0, "g", "100 g de sucre")],
    )

    payload = [
        CartRecipeIn(recipe_id=rec_a.id, target_servings=2),
        CartRecipeIn(recipe_id=rec_b.id, target_servings=4),
    ]
    rows1, _ = await aggregate_recipe_ingredients(payload, db_session)
    rows2, _ = await aggregate_recipe_ingredients(payload, db_session)
    assert rows1 == rows2


# ── Tricky duplicate / cross-unit merge cases (chaos hunting) ────────────────

async def test_intra_recipe_duplicate_same_ingredient_merges(db_session):
    """A single recipe declaring the same ingredient twice (e.g. '100 g flour'
    + '2 c. à soupe flour' in two steps) must aggregate into ONE shopping line."""
    ing = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec = Recipe(
        title="Twice A",
        url="http://test/twice-a",
        source_domain="test",
        instructions_text="",
        base_servings=4,
    )
    db_session.add(rec)
    await db_session.flush()
    db_session.add(RecipeIngredient(
        recipe_id=rec.id, ingredient_id=ing.id,
        raw_string="100 g de farine", quantity=100.0, unit="g", needs_review=False,
    ))
    db_session.add(RecipeIngredient(
        recipe_id=rec.id, ingredient_id=ing.id,
        raw_string="2 c. à soupe de farine", quantity=2.0, unit="c. à soupe", needs_review=False,
    ))
    await db_session.flush()

    rows, _ = await aggregate_recipe_ingredients(
        [CartRecipeIn(recipe_id=rec.id, target_servings=4)], db_session,
    )
    fl = [r for r in rows if r["name"] == "flour"]
    assert len(fl) == 1, f"expected intra-recipe merge, got {fl}"
    # 100 g + 2 * 7.8 g (flour tbsp density) = 115.6 g
    assert fl[0]["unit"] == "g"
    assert abs(fl[0]["quantity"] - 115.6) < 0.05


async def test_kg_and_g_cross_recipe_merge(db_session):
    """Recette A: 200 g flour. Recette B: 1 kg flour. → 1 line 1.2 kg."""
    ing = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec_g = await _make_recipe(
        db_session, title="KG G", servings=4,
        rows=[(ing, 200.0, "g", "200 g de farine")],
    )
    rec_kg = await _make_recipe(
        db_session, title="KG KG", servings=4,
        rows=[(ing, 1.0, "kg", "1 kg de farine")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_g.id, target_servings=4),
            CartRecipeIn(recipe_id=rec_kg.id, target_servings=4),
        ],
        db_session,
    )
    fl = [r for r in rows if r["name"] == "flour"]
    assert len(fl) == 1
    assert fl[0]["unit"] == "kg"
    assert abs(fl[0]["quantity"] - 1.2) < 0.01


async def test_oz_and_g_cross_recipe_merge(db_session):
    """Non-metric oz converts to g then merges with another g declaration.
    1 oz (~28.35 g) + 100 g → 1 line ≈ 128.35 g."""
    ing = Ingredient(name_en="butter", name_fr="beurre", category="Dairy")
    db_session.add(ing)
    await db_session.flush()

    rec_oz = await _make_recipe(
        db_session, title="OZ", servings=4,
        rows=[(ing, 1.0, "oz", "1 oz butter")],
    )
    rec_g = await _make_recipe(
        db_session, title="G2", servings=4,
        rows=[(ing, 100.0, "g", "100 g butter")],
    )

    rows, _ = await aggregate_recipe_ingredients(
        [
            CartRecipeIn(recipe_id=rec_oz.id, target_servings=4),
            CartRecipeIn(recipe_id=rec_g.id, target_servings=4),
        ],
        db_session,
    )
    bt = [r for r in rows if r["name"] == "butter"]
    assert len(bt) == 1
    assert bt[0]["unit"] == "g"
    assert abs(bt[0]["quantity"] - 128.35) < 0.1


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