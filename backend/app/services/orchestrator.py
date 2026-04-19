from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Ingredient, Recipe, RecipeIngredient
from .dedupe import looks_like_duplicate
from .images import download_image
from .normalizer import normalize_ingredients_batch
from .scraper import scrape_recipe_url
from .events import JobEvent, job_event_bus

logger = logging.getLogger(__name__)

async def persist_scraped_recipe(url: str, db: AsyncSession, job_id: int | None = None) -> None:
    async def notify_progress(msg: str):
        if job_id:
            await job_event_bus.publish(job_id, JobEvent(status="running", message=msg))

    logger.info(f"Démarrage de la persistance pour l'URL: {url}")
    await notify_progress("Vérification en base de données...")
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        logger.info(f"La recette existe déjà avec l'ID {existing.id}. Action annulée.")
        await notify_progress("La recette existe déjà. Fin.")
        return

    logger.debug("Extraction des données de la recette...")
    await notify_progress("Téléchargement et analyse du site web...")
    scraped = await scrape_recipe_url(url)
    logger.debug(f"Données extraites: {scraped.title} avec {len(scraped.ingredients)} ingrédients.")

    logger.debug("Normalisation par lot (batch) des ingrédients via Ollama...")
    await notify_progress(f"Analyse IA des {len(scraped.ingredients)} ingrédients...")

    # On envoie tout d'un coup pour éviter d'asphyxier l'API
    normalized_ingredients = await normalize_ingredients_batch(scraped.ingredients)

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
    await notify_progress("Vérification des recettes similaires...")
    for candidate in existing_recipes:
        candidate_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in candidate.recipe_ingredients
        ]
        if looks_like_duplicate(candidate.title, candidate_names, scraped.title, incoming_names):
            logger.info(f"Doublon exact ou similaire trouvé: {candidate.id} - {candidate.title}. Scraping annulé.")
            await notify_progress("Recette similaire détectée. Abandon.")
            return

    logger.info(f"Création de la recette '{scraped.title}' en base...")
    await notify_progress(f"Création de la recette '{scraped.title}'...")
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

    await notify_progress("Téléchargement de l'image...")
    local_image_path = await download_image(scraped.image_url, recipe.id)
    if local_image_path:
        recipe.image_local_path = local_image_path
        logger.debug(f"Image téléchargée et sauvegardée vers : {local_image_path}")
    else:
        logger.warning(f"Échec ou absence d'image à télécharger pour la recette {recipe.id}")
    await db.flush()

    logger.debug("Sauvegarde et liaison des ingrédients à la recette...")
    await notify_progress("Sauvegarde des ingrédients...")

    for ing, normalized in zip(scraped.ingredients, normalized_ingredients):
        ingredient = None
        needs_review = False
        quantity = ing.quantity
        unit = ing.unit

        if normalized:
            # Ignorer les en-têtes (ex: "Pour la sauce")
            if normalized.name_en == "section_header_ignore":
                continue
                
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
