from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Ingredient, Recipe, RecipeIngredient
from .dedupe import looks_like_duplicate
from .images import download_image
from .normalizer import normalize_ingredient
from .scraper import scrape_recipe_url

logger = logging.getLogger(__name__)

async def persist_scraped_recipe(url: str, db: AsyncSession) -> None:
    logger.info(f"Démarrage de la persistance pour l'URL: {url}")
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        logger.info(f"La recette existe déjà avec l'ID {existing.id}. Action annulée.")
        return

    logger.debug("Extraction des données de la recette...")
    scraped = await scrape_recipe_url(url)
    logger.debug(f"Données extraites: {scraped.title} avec {len(scraped.ingredients)} ingrédients.")

    logger.debug("Normalisation asynchrone des ingrédients...")

    normalized_ingredients = await asyncio.gather(
        *[
            normalize_ingredient(ing.raw, ing.quantity, ing.unit)
            for ing in scraped.ingredients
        ]
    )

    incoming_names: list[str] = [
        norm.name_en if norm else ing.raw
        for norm, ing in zip(normalized_ingredients, scraped.ingredients)
    ]

    existing_recipes = (
        await db.scalars(
            select(Recipe).options(
                selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
            )
        )
    ).all()
    logger.debug(f"Détection de doublons face à {len(existing_recipes)} recettes existantes...")
    for candidate in existing_recipes:
        candidate_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in candidate.recipe_ingredients
        ]
        if looks_like_duplicate(candidate.title, candidate_names, scraped.title, incoming_names):
            logger.info(f"Doublon exact ou similaire trouvé: {candidate.id} - {candidate.title}. Scraping annulé.")
            return

    logger.info(f"Création de la recette '{scraped.title}' en base...")
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
        logger.debug(f"Image téléchargée et sauvegardée vers : {local_image_path}")
    else:
        logger.warning(f"Échec ou absence d'image à télécharger pour la recette {recipe.id}")
    await db.flush()

    logger.debug("Sauvegarde et liaison des ingrédients à la recette...")

    for ing, normalized in zip(scraped.ingredients, normalized_ingredients):
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
                logger.debug(f"Nouvel ingrédient normalisé: {ingredient.name_en} ({ingredient.category})")
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

    logger.info("Validation finale en base des modifications pour la recette..")
    await db.commit()
    logger.info(f"Persistance terminée avec succès pour la recette #{recipe.id}")
