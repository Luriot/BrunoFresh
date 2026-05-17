from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Ingredient, PantryItem
from ...schemas import PantryItemCreate, PantryItemOut
from ...services.normalizer import translate_ingredient_name
from ..dependencies import require_auth
from ...services.auth import UserClaims
from ...schemas.recipes import pick_display_name

router = APIRouter(prefix="/api", tags=["pantry"])

_NOT_FOUND = "Pantry item not found"


@router.get("/pantry", response_model=list[PantryItemOut])
async def list_pantry(
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    items = (
        await db.scalars(
            select(PantryItem)
            .options(selectinload(PantryItem.ingredient))
            .where(PantryItem.user_id == claims.user_id)
            .order_by(PantryItem.name)
        )
    ).all()
    lang = claims.language
    result: list[PantryItemOut] = []
    for item in items:
        display_name = pick_display_name(item.name, item.name_fr, lang)
        out = PantryItemOut.model_validate(item).model_copy(update={"display_name": display_name})
        result.append(out)
    return result


@router.post("/pantry", response_model=PantryItemOut, status_code=status.HTTP_201_CREATED)
async def add_pantry_item(
    payload: PantryItemCreate,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
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
        user_id=claims.user_id,
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
async def remove_pantry_item(
    item_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(
        select(PantryItem).where(PantryItem.id == item_id, PantryItem.user_id == claims.user_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    await db.delete(item)
    await db.commit()

