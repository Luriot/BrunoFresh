from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Ingredient, Recipe, RecipeIngredient
from .dedupe import looks_like_duplicate
from .images import download_image
from .normalizer import normalize_ingredient
from .scraper import scrape_recipe_url


async def persist_scraped_recipe(url: str, db: AsyncSession) -> None:
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        return

    scraped = await scrape_recipe_url(url)

    incoming_names: list[str] = []
    for ing in scraped.ingredients:
        normalized_probe = await asyncio.to_thread(normalize_ingredient, ing.raw, ing.quantity, ing.unit)
        incoming_names.append(normalized_probe.name_en if normalized_probe else ing.raw)

    existing_recipes = (
        await db.scalars(
            select(Recipe).options(
                selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
            )
        )
    ).all()
    for candidate in existing_recipes:
        candidate_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in candidate.recipe_ingredients
        ]
        if looks_like_duplicate(candidate.title, candidate_names, scraped.title, incoming_names):
            return

    recipe = Recipe(
        title=scraped.title,
        url=url,
        source_domain=scraped.source_domain,
        image_local_path=None,
        image_original_url=scraped.image_url,
        instructions_text=scraped.instructions_text,
        base_servings=scraped.base_servings,
        prep_time_minutes=scraped.prep_time_minutes,
    )
    db.add(recipe)
    await db.flush()

    local_image_path = await download_image(scraped.image_url, recipe.id)
    if local_image_path:
        recipe.image_local_path = local_image_path
    await db.flush()

    for ing in scraped.ingredients:
        normalized = await asyncio.to_thread(normalize_ingredient, ing.raw, ing.quantity, ing.unit)
        ingredient = None
        needs_review = False
        quantity = ing.quantity
        unit = ing.unit

        if normalized:
            ingredient = await db.scalar(select(Ingredient).where(Ingredient.name_en == normalized.name_en))
            if not ingredient:
                ingredient = Ingredient(
                    name_en=normalized.name_en,
                    category=normalized.category,
                    is_normalized=True,
                )
                db.add(ingredient)
                await db.flush()
            quantity = normalized.quantity
            unit = normalized.unit
        else:
            needs_review = True

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id if ingredient else None,
                raw_string=ing.raw,
                quantity=quantity,
                unit=unit,
                needs_review=needs_review,
            )
        )

    await db.commit()
