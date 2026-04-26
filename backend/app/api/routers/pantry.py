from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Ingredient, PantryItem
from ...schemas import PantryItemCreate, PantryItemOut
from ...services.normalizer import translate_ingredient_name

router = APIRouter(prefix="/api", tags=["pantry"])

_NOT_FOUND = "Pantry item not found"


@router.get("/pantry", response_model=list[PantryItemOut])
async def list_pantry(db: AsyncSession = Depends(get_db)):
    items = (
        await db.scalars(
            select(PantryItem)
            .options(selectinload(PantryItem.ingredient))
            .order_by(PantryItem.name)
        )
    ).all()
    return items


@router.post("/pantry", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
async def add_pantry_item(payload: PantryItemCreate, db: AsyncSession = Depends(get_db)):
    # If ingredient_id provided, verify it exists
    category = payload.category
    if payload.ingredient_id is not None:
        ingredient = await db.get(Ingredient, payload.ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        if not category:
            category = ingredient.category

    # Auto-translate: always store English as the primary name
    translations = await translate_ingredient_name(payload.name, payload.lang, ["en", "fr"])
    primary_name = translations.get("en", payload.name)
    name_fr = translations.get("fr") if "fr" != payload.lang else payload.name

    item = PantryItem(
        name=primary_name,
        name_fr=name_fr,
        ingredient_id=payload.ingredient_id,
        category=category,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/pantry/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_pantry_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(PantryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    await db.delete(item)
    await db.commit()
