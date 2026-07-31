"""Ingredient patch endpoint (part of the /api prefix router)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db
from ....models import Ingredient, IngredientTranslation, RecipeIngredient
from ....schemas import IngredientDetail, IngredientNamePatch
from ...dependencies import require_admin
from ....services.auth import UserClaims

router = APIRouter()


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientDetail)
async def patch_ingredient(
    ingredient_id: int,
    payload: IngredientNamePatch,
    claims: UserClaims = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from ....services.normalizer import translate_ingredient_name

    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    supported_langs = ["en", "fr"]

    # Name + category are optional: only translate / update when provided.
    if payload.name is not None:
        translations = await translate_ingredient_name(payload.name, payload.lang, supported_langs)
        ingredient.name_en = translations.get("en", payload.name)
        ingredient.name_fr = translations.get("fr")
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

    if payload.category is not None:
        ingredient.category = payload.category
        ingredient.is_normalized = True

    if payload.grams_per_paquet is not None:
        ingredient.grams_per_paquet = payload.grams_per_paquet
    if payload.grams_per_boite is not None:
        ingredient.grams_per_boite = payload.grams_per_boite

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
        grams_per_paquet=ingredient.grams_per_paquet,
        grams_per_boite=ingredient.grams_per_boite,
    )
