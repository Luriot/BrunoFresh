"""Route-level chaos tests for /api/lists: the scenarios most likely to quietly
break a shopping list (cross-recipe merges, pantry auto-mark, needs_review
non-loss, determinism). These exercise the full HTTP path + DB persistence,
not just aggregate_recipe_ingredients in isolation.

Scenarios (see S1-S10 in the manual test plan):
  S3  — compatible units merge into one line via POST /api/lists
  S4  — incompatible units stay as two lines
  S7  — needs_review raw ingredients surface in response.needs_review (no silent loss)
  S8  — pantry ingredient_id match AND name-lower match → is_already_owned=True
  S10 — two POSTs of the same payload yield identical aggregated items
"""
from __future__ import annotations

from app.models import (
    Ingredient,
    PantryItem,
    Recipe,
    RecipeIngredient,
)


async def _stub_user_id(db) -> int:
    from sqlalchemy import select

    from app.models import User

    user = await db.scalar(select(User).where(User.username == "_stub_"))
    assert user is not None
    return user.id


async def _make_recipe(
    db,
    *,
    title: str,
    servings: int,
    rows: list[tuple[Ingredient | None, float, str, str]],
    needs_review: bool = False,
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
                ingredient_id=ing.id if ing else None,
                raw_string=raw,
                quantity=qty,
                unit=unit,
                needs_review=needs_review,
            )
        )
    await db.flush()
    return recipe


def _line(resp_json: dict, name: str) -> dict:
    matches = [it for it in resp_json["items"] if it["name"] == name]
    assert matches, f"no line for {name!r}: {resp_json['items']}"
    assert len(matches) == 1, f"multiple lines for {name!r}: {matches}"
    return matches[0]


# ── S3: compatible-unit merge end-to-end ─────────────────────────────────────

async def test_post_lists_merges_compatible_units(client, db_session):
    """flour declared as '1 tasse' (recipe A) + '125 g' (recipe B) → 1 line 250 g."""
    ing = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()

    rec_tasse = await _make_recipe(
        db_session, title="Post Tasse", servings=2,
        rows=[(ing, 1.0, "tasse", "1 tasse de farine")],
    )
    rec_g = await _make_recipe(
        db_session, title="Post Grams", servings=2,
        rows=[(ing, 125.0, "g", "125 g de farine")],
    )
    await db_session.commit()

    resp = await client.post(
        "/api/lists",
        json={
            "label": "Merge",
            "items": [
                {"recipe_id": rec_tasse.id, "target_servings": 2},
                {"recipe_id": rec_g.id, "target_servings": 2},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    fl = _line(data, "flour")
    assert fl["unit"] == "g"
    assert abs(fl["quantity"] - 250.0) < 0.01
    assert fl["is_custom"] is False


# ── S4: incompatible units stay separate end-to-end ─────────────────────────

async def test_post_lists_keeps_incompatible_units_separate(client, db_session):
    """1 piece tomato + 200 g tomato → 2 distinct lines persisted."""
    ing = Ingredient(name_en="tomato", name_fr="tomate", category="Produce")
    db_session.add(ing)
    await db_session.flush()

    rec_pc = await _make_recipe(
        db_session, title="Post Piece", servings=2,
        rows=[(ing, 1.0, "piece", "1 tomate")],
    )
    rec_g = await _make_recipe(
        db_session, title="Post Grams2", servings=2,
        rows=[(ing, 200.0, "g", "200 g de tomate")],
    )
    await db_session.commit()

    resp = await client.post(
        "/api/lists",
        json={
            "label": "NoMerge",
            "items": [
                {"recipe_id": rec_pc.id, "target_servings": 2},
                {"recipe_id": rec_g.id, "target_servings": 2},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    toms = [it for it in resp.json()["items"] if it["name"] == "tomato"]
    assert len(toms) == 2, f"expected 2 separate lines, got {toms}"
    assert sorted(it["unit"] for it in toms) == ["g", "piece"]


# ── S7: needs_review non-loss end-to-end ─────────────────────────────────────

async def test_post_lists_surfaces_needs_review_without_silent_drop(client, db_session):
    """A recipe ingredient flagged needs_review (ingredient_id=None) must not appear
    as a shopping line AND must appear in response.needs_review[] — no silent loss."""
    salt = Ingredient(name_en="salt", name_fr="sel", category="Pantry")
    db_session.add(salt)
    await db_session.flush()
    rec_ok = await _make_recipe(
        db_session, title="Review OK", servings=2,
        rows=[(salt, 1.0, "pincée", "1 pincée de sel")],
    )
    # second recipe with a needs_review line + a clean line
    bad_ing_recipe = await _make_recipe(
        db_session, title="Review BAD", servings=2,
        rows=[(None, 0.0, "unparsed", "unidentified celestial substance")],
        needs_review=True,
    )
    await db_session.commit()

    resp = await client.post(
        "/api/lists",
        json={
            "label": "Review",
            "items": [
                {"recipe_id": rec_ok.id, "target_servings": 2},
                {"recipe_id": bad_ing_recipe.id, "target_servings": 2},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    names = [it["name"] for it in data["items"]]
    assert "salt" in names
    # the reviewed-out raw must NOT silently become a line
    assert not any("celestial" in n for n in names)
    # it MUST be surfaced in needs_review
    assert data["needs_review"], f"expected needs_review populated, got {data['needs_review']}"
    assert any("celestial" in line for line in data["needs_review"])


# ── S8: pantry auto-mark (id match + name-lower match) ────────────────────────

async def test_pantry_match_by_ingredient_id_marks_already_owned(client, db_session):
    """A pantry item with ingredient_id matching the aggregated line → is_already_owned=True."""
    ing = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()
    db_session.add(PantryItem(user_id=await _stub_user_id(db_session), ingredient_id=ing.id, name=ing.name_en))
    rec = await _make_recipe(
        db_session, title="Pantry ID", servings=2,
        rows=[(ing, 200.0, "g", "200 g de farine")],
    )
    await db_session.commit()

    resp = await client.post(
        "/api/lists",
        json={"label": "PantryID", "items": [{"recipe_id": rec.id, "target_servings": 2}]},
    )
    assert resp.status_code == 200, resp.text
    fl = _line(resp.json(), "flour")
    assert fl["is_already_owned"] is True


async def test_pantry_match_by_name_lower_marks_already_owned(client, db_session):
    """Pantry item with no ingredient_id but a matching name (lower) still marks the line."""
    ing = Ingredient(name_en="Flour", name_fr="farine", category="Pantry")
    db_session.add(ing)
    await db_session.flush()
    db_session.add(PantryItem(user_id=await _stub_user_id(db_session), ingredient_id=None, name="flour"))
    rec = await _make_recipe(
        db_session, title="Pantry Name", servings=2,
        rows=[(ing, 200.0, "g", "200 g de Flour")],
    )
    await db_session.commit()

    resp = await client.post(
        "/api/lists",
        json={"label": "PantryName", "items": [{"recipe_id": rec.id, "target_servings": 2}]},
    )
    assert resp.status_code == 200, resp.text
    fl = [it for it in resp.json()["items"] if it["name"] == "Flour"]
    assert fl and fl[0]["is_already_owned"] is True


# ── S10: route-level determinism — covered by tests/unit/test_aggregator.py::test_aggregation_is_deterministic
# (the route introduces no random source; the unit test covers the actual function directly).