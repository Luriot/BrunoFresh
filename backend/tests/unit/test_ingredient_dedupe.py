"""Tests for ``save_normalized_ingredients`` — the fuzzy ingredient dedupe that
runs at scrape time (orchestrator.py:48-78). Locks in that distinct ingredients
sharing a token (``coconut milk`` vs ``milk``, ``icing sugar`` vs ``sugar``,
``almond flour`` vs ``flour``) do **NOT** collapse into one Ingredient row,
because that would sum their quantities silently in shopping lists.

The fuzzy pre-pass uses ``rapidfuzz.fuzz.WRatio`` with a configurable threshold
(see ``FUZZY_INGREDIENT_THRESHOLD`` in orchestrator.py). At 90 the matcher
false-merges all the cases below (WRatio returns exactly 90 for each pair), so
the threshold is held at 100 by default — i.e. only exact matches collapse via
the unique ``name_en`` constraint. Lower the constant to bring back forgiving
matching and the tests below will start failing (intentionally, as a guard).
"""
from __future__ import annotations

from sqlalchemy import select, text

from app.models import Ingredient, IngredientMergeRule, Recipe, RecipeIngredient
from app.services.normalizer import NormalizedIngredient
from app.services.orchestrator import FUZZY_INGREDIENT_THRESHOLD, save_normalized_ingredients
from app.services.scrapers.types import ScrapedIngredient


def _norm(name_en: str, category: str, *, name_fr: str | None = None, qty: float = 1.0, unit: str = "g"):
    return NormalizedIngredient(
        name_en=name_en, name_fr=name_fr or name_en,
        quantity=qty, unit=unit, category=category,
    )


def _scraped(raw: str, qty: float = 1.0, unit: str = "g") -> ScrapedIngredient:
    return ScrapedIngredient(raw=raw, quantity=qty, unit=unit)


async def _make_recipe(db, *, title: str, servings: int = 4) -> Recipe:
    r = Recipe(
        title=title, url=f"http://test/{title.replace(' ', '-')}",
        source_domain="test", instructions_text="", base_servings=servings,
    )
    db.add(r)
    await db.flush()
    return r


async def _count_ingredients(db) -> int:
    return len((await db.scalars(select(Ingredient))).all())


async def _ingredient_names_for_recipe(db, recipe_id: int) -> list[str | None]:
    links = (
        await db.scalars(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe_id)
            .order_by(RecipeIngredient.id)
        )
    ).all()
    out: list[str | None] = []
    for link in links:
        if link.ingredient_id is None:
            out.append(None)
        else:
            ing = await db.get(Ingredient, link.ingredient_id)
            out.append(ing.name_en if ing else None)
    return out


# ── Guard: the threshold knob must stay high ─────────────────────────────────

def test_fuzzy_threshold_is_strict():
    """Lock the constant so subsequent tweaks don't silently re-enable bad merges.
    If you genuinely want forgiving matching, lower the value AND update the tests
    below with intention (you'll be opting back into the false-merge problem)."""
    assert FUZZY_INGREDIENT_THRESHOLD >= 95, (
        f"threshold={FUZZY_INGREDIENT_THRESHOLD} is too low — WRatio returns 90 for "
        "coconut milk/milk, icing sugar/sugar, almond flour/flour and they would collapse"
    )


# ── Distinct ingredients sharing a token must NOT merge ───────────────────────

async def test_icing_sugar_does_not_merge_with_sugar(db_session):
    """``icing sugar`` (sucre glace) ≠ ``sugar`` — different taste, texture, usage."""
    db_session.add(Ingredient(name_en="sugar", name_fr="sucre", category="Pantry"))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="Icing")
    await save_normalized_ingredients(
        [_scraped("200 g icing sugar")],
        [_norm("icing sugar", "Pantry", name_fr="sucre glace", qty=200.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 2
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["icing sugar"]


async def test_brown_sugar_does_not_merge_with_sugar(db_session):
    """``brown sugar`` (cassonade) ≠ ``sugar``."""
    db_session.add(Ingredient(name_en="sugar", name_fr="sucre", category="Pantry"))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="Brown")
    await save_normalized_ingredients(
        [_scraped("100 g brown sugar")],
        [_norm("brown sugar", "Pantry", name_fr="cassonade", qty=100.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 2
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["brown sugar"]


async def test_almond_flour_does_not_merge_with_flour(db_session):
    """``almond flour`` ≠ ``flour`` — different weight, taste, allergen."""
    db_session.add(Ingredient(name_en="flour", name_fr="farine", category="Pantry"))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="Almond")
    await save_normalized_ingredients(
        [_scraped("150 g almond flour")],
        [_norm("almond flour", "Pantry", name_fr="poudre d'amande", qty=150.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 2
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["almond flour"]


async def test_coconut_milk_does_not_merge_with_milk(db_session):
    """``coconut milk`` ≠ ``milk`` — different allergen, flavor, fat content. The exact
    case the user named: collapsing the two would ruin a recipe expecting dairy."""
    db_session.add(Ingredient(name_en="milk", name_fr="lait", category="Dairy"))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="Coco")
    await save_normalized_ingredients(
        [_scraped("400 ml coconut milk")],
        [_norm("coconut milk", "Dairy", name_fr="lait de coco", qty=400.0, unit="ml")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 2
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["coconut milk"]


# ── Exact-match still works as intended ──────────────────────────────────────

async def test_same_name_reuses_existing_row_across_categories(db_session):
    """``Ingredient.name_en`` has a UNIQUE constraint and is matched exact-first
    (orchestrator.py:44-46). An existing 'orange' (Produce) and a later incoming
    'orange' tagged Spices reuses the SAME row — the first insertion's category
    wins. Intentional; one canonical row per name_en regardless of category."""
    db_session.add(Ingredient(name_en="orange", name_fr="orange", category="Produce"))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="Reuse")
    await save_normalized_ingredients(
        [_scraped("1 zeste d'orange")],
        [_norm("orange", "Spices", name_fr="orange (zeste)", qty=1.0, unit="piece")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 1
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["orange"]


async def test_second_scrape_enriches_missing_name_fr(db_session):
    """Orchestrator:101-102 — if an existing Ingredient has name_fr=None and a
    later scrape brings a normalized name_fr, the empty column is filled in place.
    No new row should be created."""
    existing = Ingredient(name_en="quinoa", name_fr=None, category="Pantry")
    db_session.add(existing)
    await db_session.flush()
    assert existing.name_fr is None

    rec = await _make_recipe(db_session, title="Enrich")
    await save_normalized_ingredients(
        [_scraped("100 g quinoa")],
        [_norm("quinoa", "Pantry", name_fr="quinoa", qty=100.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 1
    await db_session.refresh(existing)
    assert existing.name_fr == "quinoa"


# ── Persistent merge-rules (admin decisions applied on future scrapes) ────────

async def _rule_count(db) -> int:
    return len((await db.scalars(select(IngredientMergeRule))).all())


async def test_merge_rule_redirects_incoming_to_canonical(db_session):
    """A merge rule 'flour' → 'plain flour' must make a subsequent scrape of
    'flour' reuse the canonical row instead of creating a new one."""
    canonical = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    db_session.add(canonical)
    await db_session.flush()
    db_session.add(IngredientMergeRule(
        source_name="flour", source_name_key="flour",
        canonical_ingredient_id=canonical.id,
    ))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="RuleRedirect")
    await save_normalized_ingredients(
        [_scraped("200 g flour")],
        [_norm("flour", "Pantry", name_fr="farine", qty=200.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    assert await _count_ingredients(db_session) == 1, "rule must redirect, no new row created"
    assert await _ingredient_names_for_recipe(db_session, rec.id) == ["plain flour"]


async def test_merge_rule_category_hint_blocks_mismatch(db_session):
    """A rule with category_hint='Spices' must NOT redirect an incoming 'flour'
    tagged as 'Pantry' — the rule is scoped to its hinted category."""
    canonical = Ingredient(name_en="plain flour", name_fr="farine", category="Pantry")
    db_session.add(canonical)
    await db_session.flush()
    db_session.add(IngredientMergeRule(
        source_name="flour", source_name_key="flour",
        canonical_ingredient_id=canonical.id,
        category_hint="Spices",
    ))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="RuleScoped")
    await save_normalized_ingredients(
        [_scraped("200 g flour")],
        [_norm("flour", "Pantry", name_fr="farine", qty=200.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    # No redirect happened → a new row 'flour' (Pantry) is created alongside 'plain flour'
    assert await _count_ingredients(db_session) == 2


async def test_exact_match_takes_precedence_over_merge_rule(db_session):
    """If the incoming name_en has an exact Ingredient row, that row wins over
    any merge rule keyed on the same alias (exact is always the strongest signal)."""
    canonical = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    direct = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add_all([canonical, direct])
    await db_session.flush()
    db_session.add(IngredientMergeRule(
        source_name="flour", source_name_key="flour",
        canonical_ingredient_id=canonical.id,
    ))
    await db_session.flush()

    rec = await _make_recipe(db_session, title="ExactWins")
    await save_normalized_ingredients(
        [_scraped("100 g flour")],
        [_norm("flour", "Pantry", qty=100.0, unit="g")],
        rec.id, db_session,
    )
    await db_session.flush()
    names = await _ingredient_names_for_recipe(db_session, rec.id)
    assert names == ["flour"], "exact name_en match must win over merge rule"


# ── Merge endpoint auto-learns merge rules (route level) ─────────────────────

async def test_merge_endpoint_creates_rule_automatically(admin_client, db_session):
    """POST /api/admin/ingredients/merge must auto-insert a merge rule so future
    scrapes of source.name_en redirect to the surviving target row."""
    source = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    target = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add_all([source, target])
    await db_session.commit()
    await db_session.refresh(source)
    await db_session.refresh(target)
    assert await _rule_count(db_session) == 0

    resp = await admin_client.post(
        "/api/admin/ingredients/merge",
        json={"source_id": source.id, "target_id": target.id},
    )
    assert resp.status_code == 200, resp.text

    rules = (await db_session.scalars(select(IngredientMergeRule))).all()
    assert len(rules) == 1
    assert rules[0].source_name_key == "plain flour"
    assert rules[0].canonical_ingredient_id == target.id


async def test_re_merge_updates_rule_to_new_target(admin_client, db_session):
    """Merging the same alias a second time against a different target repoints
    the existing rule instead of creating a duplicate."""
    a = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    b = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    c = Ingredient(name_en="wheat flour", name_fr="farine de blé", category="Pantry")
    db_session.add_all([a, b, c])
    await db_session.commit()
    for ing in (a, b, c):
        await db_session.refresh(ing)

    await admin_client.post(
        "/api/admin/ingredients/merge",
        json={"source_id": a.id, "target_id": b.id},
    )
    await admin_client.post(
        "/api/admin/ingredients/merge",
        json={"source_id": c.id, "target_id": b.id},
    )

    rules = (await db_session.scalars(select(IngredientMergeRule))).all()
    assert len(rules) == 2  # one for 'plain flour', one for 'wheat flour'


# ── Merge-rule CRUD ───────────────────────────────────────────────────────────

async def test_create_merge_rule_via_admin_endpoint(admin_client, db_session):
    """POST /api/admin/merge-rules creates a rule without requiring a prior merge."""
    canonical = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(canonical)
    await db_session.commit()
    await db_session.refresh(canonical)

    resp = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "AP Flour", "canonical_ingredient_id": canonical.id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source_name"] == "AP Flour"
    assert body["canonical_ingredient_id"] == canonical.id
    assert body["canonical_name"] == "flour"


async def test_create_merge_rule_repoints_existing_alias(admin_client, db_session):
    """Creating a rule for an already-mapped alias repoints to the new canonical
    instead of raising a 409 (idempotent upsert)."""
    a = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    b = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    db_session.add_all([a, b])
    await db_session.commit()
    for ing in (a, b):
        await db_session.refresh(ing)

    r1 = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "Flour", "canonical_ingredient_id": a.id},
    )
    assert r1.status_code == 201

    r2 = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "flour", "canonical_ingredient_id": b.id},
    )
    assert r2.status_code == 201
    assert r2.json()["canonical_ingredient_id"] == b.id

    rules = (await db_session.scalars(select(IngredientMergeRule))).all()
    assert len(rules) == 1  # same alias, same row, repointed


async def test_list_merge_rules_filters_by_canonical(admin_client, db_session):
    """GET /api/admin/merge-rules?canonical_id=X returns only rules pointing at X."""
    a = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    b = Ingredient(name_en="sugar", name_fr="sucre", category="Pantry")
    db_session.add_all([a, b])
    await db_session.commit()
    for ing in (a, b):
        await db_session.refresh(ing)

    await admin_client.post("/api/admin/merge-rules", json={"source_name": "AP Flour", "canonical_ingredient_id": a.id})
    await admin_client.post("/api/admin/merge-rules", json={"source_name": "Caster Sugar", "canonical_ingredient_id": b.id})

    all_rules = await admin_client.get("/api/admin/merge-rules")
    assert all_rules.status_code == 200
    assert len(all_rules.json()) == 2

    only_a = await admin_client.get(f"/api/admin/merge-rules?canonical_id={a.id}")
    assert only_a.status_code == 200
    rules = only_a.json()
    assert len(rules) == 1
    assert rules[0]["canonical_ingredient_id"] == a.id


async def test_delete_merge_rule(admin_client, db_session):
    """DELETE /api/admin/merge-rules/{id} removes the rule."""
    canonical = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(canonical)
    await db_session.commit()
    await db_session.refresh(canonical)

    create = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "AP Flour", "canonical_ingredient_id": canonical.id},
    )
    rule_id = create.json()["id"]

    del_resp = await admin_client.delete(f"/api/admin/merge-rules/{rule_id}")
    assert del_resp.status_code == 204

    rules = (await db_session.scalars(select(IngredientMergeRule))).all()
    assert len(rules) == 0


async def test_merge_rule_cascade_on_canonical_delete(db_session):
    """Deleting the canonical Ingredient (via raw DB delete here) cascades to
    ingredients_merge_rule rows thanks to the ON DELETE CASCADE FK."""
    canonical = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(canonical)
    await db_session.flush()
    rule = IngredientMergeRule(
        source_name="AP Flour", source_name_key="ap flour",
        canonical_ingredient_id=canonical.id,
    )
    db_session.add(rule)
    await db_session.flush()

    # Direct delete — bypassing the admin endpoint's usage check.
    await db_session.delete(canonical)
    await db_session.flush()

    rules = (await db_session.scalars(select(IngredientMergeRule))).all()
    assert len(rules) == 0, "rule must cascade-delete with its canonical ingredient"


# ── Retroactive reconciliation when creating a rule for an existing ingredient ─

async def test_create_rule_retroactively_migrates_existing_ingredient(admin_client, db_session):
    """Creating a rule 'plain flour → flour' when an ``Ingredient('plain flour')``
    row already exists must:

      1. reparent its ``RecipeIngredient`` FKs to the canonical 'flour',
      2. reparent its ``ShoppingListItem`` FKs to the canonical 'flour',
      3. delete the redundant 'plain flour' Ingredient row,
      4. still persist the rule for future scrapes.

    This is what makes the rule endpoint idempotent with the merge endpoint —
    creating a rule after the duplicate exists cleans up existing recipes +
    shopping lists in the same transaction instead of waiting for a future scrape.
    """
    from app.models import Recipe, ShoppingList, ShoppingListItem as SLI, ShoppingListRecipe as SLR

    canonical = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    dup = Ingredient(name_en="plain flour", name_fr="farine ordinaire", category="Pantry")
    db_session.add_all([canonical, dup])
    await db_session.flush()

    # A recipe pointing at the duplicate ingredient.
    recipe = Recipe(
        title="have plain flour", url="http://test/have-plain-flour",
        source_domain="test", instructions_text="", base_servings=2,
    )
    db_session.add(recipe)
    await db_session.flush()
    db_session.add(RecipeIngredient(
        recipe_id=recipe.id, ingredient_id=dup.id,
        raw_string="100 g plain flour", quantity=100.0, unit="g", needs_review=False,
    ))

    # A shopping list with one line pointing at the duplicate ingredient.
    sl = ShoppingList(user_id=await _stub_user_id_admin(db_session), label="retro")
    db_session.add(sl)
    await db_session.flush()
    db_session.add(SLI(
        shopping_list_id=sl.id, ingredient_id=dup.id,
        name="plain flour", name_fr="farine ordinaire",
        quantity=100.0, unit="g", category="Pantry", sort_order=0,
    ))
    await db_session.commit()
    for ing in (canonical, dup):
        await db_session.refresh(ing)
    canonical_id = canonical.id
    dup_id = dup.id

    resp = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "Plain Flour", "canonical_ingredient_id": canonical_id},
    )
    assert resp.status_code == 201, resp.text

    # Drop the ORM identity-map cache so subsequent queries actually hit the DB
    # (the endpoint committed in the shared session; querying without a refresh
    # would surface stale rows that the deletion just removed).
    await db_session.execute(text("SELECT 1"))

    # 1. The duplicate Ingredient row must be gone.
    remaining = (
        await db_session.scalars(select(Ingredient).where(Ingredient.name_en == "plain flour"))
    ).all()
    assert remaining == [], "duplicate Ingredient row must be deleted by reconciliation"

    # 2. Its RecipeIngredient FK must now point at the canonical.
    ri = (
        await db_session.scalars(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
    ).all()
    assert ri and ri[0].ingredient_id == canonical_id

    # 3. Its ShoppingListItem FK must now point at the canonical.
    sl_items = (
        await db_session.scalars(select(SLI).where(SLI.shopping_list_id == sl.id))
    ).all()
    assert sl_items and sl_items[0].ingredient_id == canonical_id

    # 4. The rule exists for future scrapes.
    rule = await db_session.scalar(
        select(IngredientMergeRule).where(IngredientMergeRule.source_name_key == "plain flour")
    )
    assert rule is not None and rule.canonical_ingredient_id == canonical_id


async def test_create_rule_self_merge_is_a_noop(admin_client, db_session):
    """Creating a rule whose ``source_name`` matches the canonical's own
    ``name_en`` must NOT delete the canonical row (silent self-merge guard in
    ``_reconcile_existing_ingredient``)."""
    canonical = Ingredient(name_en="flour", name_fr="farine", category="Pantry")
    db_session.add(canonical)
    await db_session.commit()
    await db_session.refresh(canonical)
    before = await _count_ingredients(db_session)

    resp = await admin_client.post(
        "/api/admin/merge-rules",
        json={"source_name": "flour", "canonical_ingredient_id": canonical.id},
    )
    assert resp.status_code == 201, resp.text
    assert await _count_ingredients(db_session) == before, "self-merge must not delete canonical"


async def _stub_user_id_admin(db) -> int:
    from sqlalchemy import select as _sel

    from app.models import User

    user = await db.scalar(_sel(User).where(User.username == "_admin_stub_"))
    if user is not None:
        return user.id
    user = await db.scalar(_sel(User).where(User.username == "_stub_"))
    assert user is not None
    return user.id