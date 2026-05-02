"""Ingredient patch endpoint (part of the /api prefix router)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models import Ingredient, IngredientTranslation, RecipeIngredient
from ....schemas import IngredientDetail, IngredientNamePatch

router = APIRouter()


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientDetail)
async def patch_ingredient(
    ingredient_id: int,
    payload: IngredientNamePatch,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from ....services.normalizer import translate_ingredient_name

    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    supported_langs = ["en", "fr"]
    translations = await translate_ingredient_name(payload.name, payload.lang, supported_langs)

    ingredient.name_en = translations.get("en", payload.name)
    ingredient.name_fr = translations.get("fr")
    ingredient.category = payload.category
    ingredient.is_normalized = True

    for lang_code, trans_name in translations.items():
        existing = await db.scalar(
            select(IngredientTranslation).where(
                IngredientTranslation.ingredient_id == ingredient_id,
                IngredientTranslation.lang_code == lang_code,
            )
        )
        if existing:
            existing.name = trans_name
        else:
            db.add(IngredientTranslation(
                ingredient_id=ingredient_id,
                lang_code=lang_code,
                name=trans_name,
            ))

    await db.commit()
    await db.refresh(ingredient)

    trans_rows = (await db.scalars(
        select(IngredientTranslation).where(IngredientTranslation.ingredient_id == ingredient_id)
    )).all()
    translations_dict = {row.lang_code: row.name for row in trans_rows}

    usage_count = (
        await db.scalar(
            select(func.count()).select_from(RecipeIngredient).where(RecipeIngredient.ingredient_id == ingredient.id)
        )
    ) or 0
    return IngredientDetail(
        id=ingredient.id,
        name_en=ingredient.name_en,
        name_fr=ingredient.name_fr,
        category=ingredient.category,
        is_normalized=ingredient.is_normalized,
        needs_review=False,
        usage_count=usage_count,
        translations=translations_dict,
    )
