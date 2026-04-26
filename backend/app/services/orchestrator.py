from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Ingredient, Recipe, RecipeIngredient, Tag
from .dedupe import looks_like_duplicate, similarity_score
from .images import download_image
from .normalizer import normalize_ingredients_batch
from .scraper import scrape_recipe_url
from .events import JobEvent, job_event_bus
from .tag_rules import match_tags

logger = logging.getLogger(__name__)


@dataclass
class DuplicateFound:
    existing_id: int
    existing_title: str
    existing_url: str
    existing_image: str | None
    title_score: float
    ingredient_score: float


async def persist_scraped_recipe(
    url: str,
    db: AsyncSession,
    job_id: int | None = None,
    force: bool = False,
) -> DuplicateFound | None:
    """Scrape and persist a recipe.

    Returns ``DuplicateFound`` if a similar recipe exists and ``force`` is False.
    Returns ``None`` on success (recipe saved).
    """
    async def notify_progress(msg: str):
        if job_id:
            await job_event_bus.publish(job_id, JobEvent(status="running", message=msg))

    logger.info(f"Démarrage de la persistance pour l'URL: {url}")
    await notify_progress("Vérification en base de données...")
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        logger.info(f"La recette existe déjà avec l'ID {existing.id}. Action annulée.")
        await notify_progress("La recette existe déjà. Fin.")
        return None

    logger.debug("Extraction des données de la recette...")
    await notify_progress("Téléchargement et analyse du site web...")
    scraped = await scrape_recipe_url(url)
    logger.debug(f"Données extraites: {scraped.title} avec {len(scraped.ingredients)} ingrédients.")

    logger.debug("Normalisation par lot (batch) des ingrédients via Ollama...")
    await notify_progress(f"Analyse IA des {len(scraped.ingredients)} ingrédients...")

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

    if not force:
        for candidate in existing_recipes:
            candidate_names = [
                link.ingredient.name_en if link.ingredient else link.raw_string
                for link in candidate.recipe_ingredients
            ]
            ts, ing_s = similarity_score(candidate.title, candidate_names, scraped.title, incoming_names)
            if ts >= 85 and ing_s >= 0.7:
                logger.info(f"Doublon détecté: {candidate.id} - {candidate.title}. Renvoi de l'avertissement.")
                await notify_progress("Recette similaire détectée.")
                return DuplicateFound(
                    existing_id=candidate.id,
                    existing_title=candidate.title,
                    existing_url=candidate.url,
                    existing_image=candidate.image_local_path,
                    title_score=round(ts, 1),
                    ingredient_score=round(ing_s, 2),
                )

    logger.info(f"Création de la recette '{scraped.title}' en base...")
    await notify_progress(f"Création de la recette '{scraped.title}'...")
    recipe = Recipe(
        title=scraped.title,
        url=url,
        source_domain=scraped.source_domain,
        image_local_path=None,
        image_original_url=scraped.image_url,
        instructions_text=scraped.instructions_text,
        instruction_steps_json=json.dumps(scraped.instruction_steps) if scraped.instruction_steps else None,
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

    normalized_names = [
        norm.name_en
        for norm in normalized_ingredients
        if norm and norm.name_en != "section_header_ignore"
    ]
    existing_ingredients: dict[str, Ingredient] = {}
    if normalized_names:
        result = await db.scalars(select(Ingredient).where(Ingredient.name_en.in_(normalized_names)))
        for ing_obj in result:
            existing_ingredients[ing_obj.name_en] = ing_obj

    for ing, normalized in zip(scraped.ingredients, normalized_ingredients):
        ingredient = None
        quantity = ing.quantity
        unit = ing.unit

        if normalized:
            if normalized.name_en == "section_header_ignore":
                continue

            ingredient = existing_ingredients.get(normalized.name_en)
            if not ingredient:
                ingredient = Ingredient(
                    name_en=normalized.name_en,
                    name_fr=normalized.name_fr,
                    category=normalized.category,
                    is_normalized=True,
                )
                db.add(ingredient)
                existing_ingredients[normalized.name_en] = ingredient
                logger.debug(f"Nouvel ingrédient normalisé: {ingredient.name_en} ({ingredient.category})")
                await db.flush()
            elif not ingredient.name_fr and normalized.name_fr:
                ingredient.name_fr = normalized.name_fr
            quantity = normalized.quantity
            unit = normalized.unit
        else:
            # Normalization failed: create a raw ingredient so it still appears in shopping lists
            raw_name = ing.raw.strip().lower() or "unknown ingredient"
            ingredient = existing_ingredients.get(raw_name)
            if not ingredient:
                ingredient = Ingredient(
                    name_en=raw_name,
                    name_fr=raw_name,
                    category="Other",
                    is_normalized=False,
                )
                db.add(ingredient)
                existing_ingredients[raw_name] = ingredient
                await db.flush()

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id if ingredient else None,
                raw_string=ing.raw,
                quantity=quantity,
                unit=unit,
                needs_review=False,
            )
        )

    # ── Auto-tag ────────────────────────────────────────────────────────────
    await notify_progress("Application automatique des tags...")
    await _auto_tag_recipe(recipe, scraped.title, incoming_names, scraped.prep_time_minutes, db)

    logger.info("Validation finale en base des modifications pour la recette..")
    await db.commit()
    logger.info(f"Persistance terminée avec succès pour la recette #{recipe.id}")
    return None


async def _auto_tag_recipe(
    recipe: Recipe,
    title: str,
    ingredient_names: list[str],
    prep_time_minutes: int | None,
    db: AsyncSession,
) -> None:
    """Apply tags based on keyword matching in title/ingredients and prep time."""
    all_tags = list((await db.scalars(select(Tag))).all())
    matched = match_tags(all_tags, title, ingredient_names, prep_time_minutes)
    if matched:
        # Explicitly load the tags collection before assigning to avoid SQLAlchemy async
        # lazy-loading (MissingGreenlet) on a newly created recipe that has been flushed.
        await db.refresh(recipe, attribute_names=["tags"])
        recipe.tags = matched
        logger.debug(f"Auto-tags appliqués à la recette #{recipe.id}: {[t.name for t in matched]}")
