"""Shared utilities for all recipe sub-routers."""
from __future__ import annotations

import json

from sqlalchemy.orm import selectinload

from ....models import Recipe, RecipeIngredient, Tag
from ....schemas import InstructionStep, RecipeDetail, RecipeIngredientOut, TagOut
from ....schemas.recipes import pick_display_name

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


def _ing_to_out(link: RecipeIngredient, language: str = "en") -> RecipeIngredientOut:
    ing = link.ingredient
    display_name = pick_display_name(ing.name_en, ing.name_fr, language) if ing else None
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=ing.name_en if ing else None,
        ingredient_name_fr=ing.name_fr if ing else None,
        display_name=display_name,
        category=ing.category if ing else None,
    )


def _recipe_to_detail(
    recipe: Recipe,
    is_favorite_by_me: bool = False,
    recommenders: list[str] | None = None,
    language: str = "en",
) -> RecipeDetail:
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
        is_favorite_by_me=is_favorite_by_me,
        recommenders=recommenders or [],
        tags=[TagOut.model_validate(t) for t in recipe.tags],
        ingredients=[_ing_to_out(link, language) for link in recipe.recipe_ingredients],
        instruction_steps=steps,
    )
