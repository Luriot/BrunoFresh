"""Shared ingredient-aggregation logic used by both the shopping-list and cart routers.

Centralising this avoids the logic being duplicated across two routers and makes
unit-merging and density-conversion behaviour consistent everywhere.
"""
from __future__ import annotations

from typing import TypedDict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Recipe, RecipeIngredient
from ..schemas import CartRecipeIn
from .normalizer import (
    culinary_to_grams,
    get_unit_group,
    normalize_unit,
    smart_display_unit,
    to_base_unit,
)


class AggRow(TypedDict):
    category: str
    name: str
    name_fr: str | None
    unit: str
    quantity: float
    ingredient_id: int | None


async def aggregate_recipe_ingredients(
    items: list[CartRecipeIn],
    db: AsyncSession,
) -> tuple[list[AggRow], list[str]]:
    """Aggregate and unit-merge ingredients from multiple recipe+servings pairs.

    Returns ``(rows, needs_review)`` where *rows* are deduplicated, unit-merged
    ingredient lines (sorted by category then name) and *needs_review* is a
    sorted list of raw strings that could not be normalised.
    """
    if not items:
        return [], []

    grouped: dict[tuple[str, str, str | None, str, int | None], dict] = {}
    needs_review: list[str] = []

    recipe_ids = list({item.recipe_id for item in items})
    recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
            .where(Recipe.id.in_(recipe_ids))
        )
    ).all()
    recipes_by_id = {recipe.id: recipe for recipe in recipes}

    for payload in items:
        recipe = recipes_by_id.get(payload.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {payload.recipe_id} not found")

        multiplier = payload.target_servings / max(recipe.base_servings, 1)

        for link in recipe.recipe_ingredients:
            if link.needs_review or not link.ingredient:
                needs_review.append(f"{recipe.title}: {link.raw_string}")
                continue

            raw_qty = link.quantity * multiplier
            norm_unit, norm_qty = normalize_unit(link.unit, raw_qty)
            # Density conversion: c. à soupe / tasse / etc. → grams where known
            density_result = culinary_to_grams(link.ingredient.name_en, norm_unit, norm_qty)
            if density_result:
                norm_unit, norm_qty = density_result
            # Normalise to base unit so g+kg, ml+L, etc. collapse into one row
            base_unit, base_qty = to_base_unit(norm_unit, norm_qty)
            # Group by unit-family name ("Poids"/"Volume") so compatible units merge;
            # incompatible units (piece, pincée …) keep their own key.
            agg_unit = get_unit_group(norm_unit) or norm_unit
            key = (
                link.ingredient.category,
                link.ingredient.name_en,
                link.ingredient.name_fr,
                agg_unit,
                link.ingredient.id,
            )
            if key not in grouped:
                grouped[key] = {
                    "category": link.ingredient.category,
                    "name": link.ingredient.name_en,
                    "name_fr": link.ingredient.name_fr,
                    "_base_unit": base_unit,
                    "quantity": 0.0,
                    "ingredient_id": link.ingredient.id,
                }
            grouped[key]["quantity"] += base_qty

    def _finalize(item: dict) -> AggRow:
        base_unit = item["_base_unit"]
        display_unit, display_qty = smart_display_unit(base_unit, round(item["quantity"], 2))
        return AggRow(
            category=item["category"],
            name=item["name"],
            name_fr=item["name_fr"],
            unit=display_unit,
            quantity=display_qty,
            ingredient_id=item["ingredient_id"],
        )

    rows = sorted(
        (_finalize(item) for item in grouped.values()),
        key=lambda r: (r["category"], r["name"]),
    )
    return rows, sorted(set(needs_review))
