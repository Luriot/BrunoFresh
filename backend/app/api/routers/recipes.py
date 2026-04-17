from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models import Ingredient, Recipe, RecipeIngredient
from ...schemas import IngredientPatch, RecipeDetail, RecipeIngredientOut, RecipeListItem

router = APIRouter(prefix="/api", tags=["recipes"])


def _ing_to_out(link: RecipeIngredient) -> RecipeIngredientOut:
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=link.ingredient.name_en if link.ingredient else None,
        category=link.ingredient.category if link.ingredient else None,
    )


@router.get("/recipes", response_model=list[RecipeListItem])
async def list_recipes(
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe)
    if q:
        stmt = stmt.where(Recipe.title.ilike(f"%{q}%"))
    if source:
        stmt = stmt.where(Recipe.source_domain == source)
    recipes = (await db.scalars(stmt.offset(offset).limit(limit))).all()
    return recipes


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

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
        ingredients=[_ing_to_out(link) for link in recipe.recipe_ingredients],
    )


@router.patch("/ingredients/{ingredient_id}")
async def patch_ingredient(
    ingredient_id: int,
    payload: IngredientPatch,
    db: AsyncSession = Depends(get_db),
):
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    ingredient.name_en = payload.name_en
    ingredient.category = payload.category
    ingredient.is_normalized = True
    await db.commit()
    return {"status": "updated"}
