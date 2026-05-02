from __future__ import annotations

from pydantic import BaseModel


class RecipeSourceStat(BaseModel):
    source_domain: str
    count: int


class TopRecipeStat(BaseModel):
    recipe_id: int
    title: str
    appearance_count: int


class TopIngredientStat(BaseModel):
    name: str
    count: int


class StatsOut(BaseModel):
    total_recipes: int
    total_lists: int
    recipes_by_source: list[RecipeSourceStat]
    top_recipes_in_lists: list[TopRecipeStat]
    top_ingredients: list[TopIngredientStat]
