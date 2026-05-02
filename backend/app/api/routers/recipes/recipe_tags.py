"""Tag management endpoints for recipes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models import Recipe, Tag
from ....schemas import RecipeDetail, RecipeTagsUpdate
from .utils import _RECIPE_NOT_FOUND, _recipe_detail_opts, _recipe_to_detail

router = APIRouter()


@router.put("/recipes/{recipe_id}/tags", response_model=RecipeDetail)
async def set_recipe_tags(
    recipe_id: int,
    payload: RecipeTagsUpdate,
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if payload.tag_ids:
        new_tags = (await db.scalars(select(Tag).where(Tag.id.in_(payload.tag_ids)))).all()
    else:
        new_tags = []
    recipe.tags = list(new_tags)
    await db.commit()

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)
