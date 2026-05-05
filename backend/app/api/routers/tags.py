import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import AsyncSessionLocal, get_db
from ...models import Recipe, RecipeIngredient, Tag
from ...schemas import TagCreate, TagOut
from ...services.tag_rules import match_tags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tags"])


async def _apply_new_tag_to_existing_recipes(tag_id: int) -> None:
    """Background task: run tag-matching for a newly created tag against all existing recipes."""
    async with AsyncSessionLocal() as db:
        tag = await db.get(Tag, tag_id)
        if not tag:
            return
        recipes = (
            await db.scalars(
                select(Recipe).options(
                    selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
                    selectinload(Recipe.tags),
                )
            )
        ).all()
        updated = 0
        for recipe in recipes:
            if any(t.id == tag.id for t in recipe.tags):
                continue
            ingredient_names = [
                ri.ingredient.name_en
                for ri in recipe.recipe_ingredients
                if ri.ingredient
            ]
            if match_tags([tag], recipe.title or "", ingredient_names, recipe.prep_time_minutes):
                recipe.tags = list(recipe.tags) + [tag]
                updated += 1
        if updated:
            await db.commit()
        logger.info("New tag '%s' applied to %d existing recipe(s).", tag.name, updated)


@router.get("/tags", response_model=list[TagOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    tags = (await db.scalars(select(Tag).order_by(Tag.name))).all()
    return tags


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(Tag).where(Tag.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Tag already exists")
    tag = Tag(name=payload.name, color=payload.color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    background_tasks.add_task(_apply_new_tag_to_existing_recipes, tag.id)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    await db.delete(tag)
    await db.commit()
