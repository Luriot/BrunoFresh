"""Similar-recipe discovery endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models import Recipe, RecipeIngredient
from ....schemas import RecipeListItem
from ....services.dedupe import _jaccard_similarity
from .utils import _RECIPE_NOT_FOUND

router = APIRouter()


@router.get("/recipes/{recipe_id}/similar", response_model=list[RecipeListItem])
async def get_similar_recipes(
    recipe_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    target = await db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients), selectinload(Recipe.tags))
        .where(Recipe.id == recipe_id)
    )
    if not target:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    target_ids = {
        ri.ingredient_id
        for ri in target.recipe_ingredients
        if ri.ingredient_id is not None
    }
    if not target_ids:
        return []

    # Pre-filter: only load recipes that share at least one ingredient.
    shared_subq = (
        select(RecipeIngredient.recipe_id)
        .where(
            RecipeIngredient.ingredient_id.in_(target_ids),
            RecipeIngredient.recipe_id != recipe_id,
        )
        .distinct()
    )
    candidate_recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients), selectinload(Recipe.tags))
            .where(Recipe.id.in_(shared_subq))
        )
    ).all()

    scored = [
        (
            _jaccard_similarity(target_ids, {ri.ingredient_id for ri in r.recipe_ingredients if ri.ingredient_id}),
            r,
        )
        for r in candidate_recipes
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]
