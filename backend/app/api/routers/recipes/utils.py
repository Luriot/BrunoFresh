"""Shared utilities for all recipe sub-routers."""
from __future__ import annotations

import json

from sqlalchemy.orm import selectinload

from ....models import Recipe, RecipeIngredient, Tag
from ....schemas import InstructionStep, RecipeDetail, RecipeIngredientOut, TagOut

_RECIPE_NOT_FOUND = "Recipe not found"


def _escape_like(s: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input is treated as a literal substring."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _recipe_detail_opts() -> tuple:
    """Selectinload options shared by all endpoints that return RecipeDetail."""
    return (
        selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
        selectinload(Recipe.tags),
    )


def _ing_to_out(link: RecipeIngredient) -> RecipeIngredientOut:
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=link.ingredient.name_en if link.ingredient else None,
        ingredient_name_fr=link.ingredient.name_fr if link.ingredient else None,
        category=link.ingredient.category if link.ingredient else None,
    )


def _recipe_to_detail(recipe: Recipe) -> RecipeDetail:
    steps: list[InstructionStep] = []
    if recipe.instruction_steps_json:
        try:
            raw = json.loads(recipe.instruction_steps_json)
            steps = [InstructionStep(**s) for s in raw if isinstance(s, dict)]
        except Exception:
            pass
    return RecipeDetail(
        id=recipe.id,
        title=recipe.title,
        url=recipe.url,
        source_domain=recipe.source_domain,
        image_local_path=recipe.image_local_path,
        image_original_url=recipe.image_original_url,
        instructions_text=recipe.instructions_text,
        base_servings=recipe.base_servings,
        prep_time_minutes=recipe.prep_time_minutes,
        is_favorite=recipe.is_favorite,
        tags=[TagOut.model_validate(t) for t in recipe.tags],
        ingredients=[_ing_to_out(link) for link in recipe.recipe_ingredients],
        instruction_steps=steps,
    )
