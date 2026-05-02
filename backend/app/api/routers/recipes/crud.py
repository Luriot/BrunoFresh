"""CRUD endpoints: list, get, create, patch, delete recipes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models import Ingredient, Recipe, RecipeIngredient, Tag
from ....models import recipe_tags as recipe_tags_table
from ....schemas import (
    RecipeCreate,
    RecipeDetail,
    RecipeListItem,
    RecipePatch,
)
from .utils import _RECIPE_NOT_FOUND, _escape_like, _recipe_detail_opts, _recipe_to_detail

router = APIRouter()


@router.get("/recipes", response_model=list[RecipeListItem])
async def list_recipes(
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    is_favorite: bool | None = Query(default=None),
    ingredients: str | None = Query(default=None, description="Comma-separated ingredient keywords"),
    tags: str | None = Query(default=None, description="Comma-separated tag names (any match)"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe).options(selectinload(Recipe.tags))

    if q:
        q_safe = _escape_like(q)
        ingredient_recipe_ids = select(RecipeIngredient.recipe_id).join(
            Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).where(
            Ingredient.name_en.ilike(f"%{q_safe}%", escape="\\") | Ingredient.name_fr.ilike(f"%{q_safe}%", escape="\\")
        )
        stmt = stmt.where(Recipe.title.ilike(f"%{q_safe}%", escape="\\") | Recipe.id.in_(ingredient_recipe_ids))

    if source:
        stmt = stmt.where(Recipe.source_domain == source)

    if is_favorite is not None:
        stmt = stmt.where(Recipe.is_favorite == is_favorite)

    if ingredients:
        keywords = [kw.strip() for kw in ingredients.split(",") if kw.strip()]
        for kw in keywords:
            kw_safe = _escape_like(kw)
            subq = select(RecipeIngredient.recipe_id).join(
                Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
            ).where(
                Ingredient.name_en.ilike(f"%{kw_safe}%", escape="\\") | Ingredient.name_fr.ilike(f"%{kw_safe}%", escape="\\")
            )
            stmt = stmt.where(Recipe.id.in_(subq))

    if tags:
        tag_names = [t.strip() for t in tags.split(",") if t.strip()]
        tag_subq = (
            select(recipe_tags_table.c.recipe_id)
            .join(Tag, recipe_tags_table.c.tag_id == Tag.id)
            .where(Tag.name.in_(tag_names))
        )
        stmt = stmt.where(Recipe.id.in_(tag_subq))

    recipes = (await db.scalars(
        stmt.order_by(Recipe.is_favorite.desc(), func.lower(Recipe.title).asc()).offset(offset).limit(limit)
    )).all()
    return recipes


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)


@router.post("/recipes", response_model=RecipeDetail)
async def create_custom_recipe(
    payload: RecipeCreate,
    db: AsyncSession = Depends(get_db),
):
    unique_url = f"custom://recipe-{uuid.uuid4()}"
    new_recipe = Recipe(
        title=payload.title,
        url=unique_url,
        source_domain="custom",
        instructions_text=payload.instructions_text,
        base_servings=payload.base_servings,
        prep_time_minutes=payload.prep_time_minutes,
    )
    db.add(new_recipe)

    for ing_in in payload.ingredients:
        ing_obj = await db.scalar(select(Ingredient).where(Ingredient.name_en == ing_in.ingredient_name))
        if not ing_obj:
            ing_obj = Ingredient(
                name_en=ing_in.ingredient_name,
                name_fr=ing_in.ingredient_name_fr,
                category=ing_in.category or "Other",
            )
            db.add(ing_obj)
            await db.flush()

        link = RecipeIngredient(
            recipe=new_recipe,
            ingredient=ing_obj,
            raw_string=ing_in.raw_string,
            quantity=ing_in.quantity,
            unit=ing_in.unit,
        )
        db.add(link)

    await db.commit()

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == new_recipe.id)
    )
    if not recipe:
        raise HTTPException(status_code=500, detail="Failed to retrieve created recipe")
    return _recipe_to_detail(recipe)


@router.patch("/recipes/{recipe_id}", response_model=RecipeDetail)
async def patch_recipe(
    recipe_id: int,
    payload: RecipePatch,
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if payload.is_favorite is not None:
        recipe.is_favorite = payload.is_favorite
    if payload.instructions_text is not None:
        recipe.instructions_text = payload.instructions_text
    await db.commit()

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    await db.delete(recipe)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
