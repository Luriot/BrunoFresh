import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models import Ingredient, Recipe, RecipeIngredient, ShoppingList, ShoppingListRecipe
from ...schemas import (
    IngredientDetail,
    IngredientMergeRequest,
    RecipeSourceStat,
    StatsOut,
    TopIngredientStat,
    TopRecipeStat,
)
from ..dependencies import require_auth

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_auth)])


@router.get("/db/export")
async def export_db():
    if not settings.db_file.exists():
        raise HTTPException(status_code=404, detail="Database file not found.")
    return FileResponse(
        path=settings.db_file,
        filename="app.db",
        media_type="application/x-sqlite3",
    )


@router.post("/db/import")
async def import_db(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not (filename.endswith(".db") or filename.endswith(".sqlite") or filename.endswith(".sqlite3")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a SQLite database file.")

    content = await file.read()
    await file.close()

    _SQLITE_MAGIC = b"SQLite format 3\x00"
    if not content.startswith(_SQLITE_MAGIC):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid SQLite database.")

    temp_path = settings.db_file.with_suffix(".temp")
    try:
        await asyncio.to_thread(temp_path.write_bytes, content)
        await asyncio.to_thread(shutil.move, str(temp_path), str(settings.db_file))
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to import database.")

    return {"message": "Database imported successfully."}


# ── Ingredient admin ────────────────────────────────────────────────────────

@router.get("/ingredients", response_model=list[IngredientDetail])
async def list_ingredients_admin(
    q: str | None = Query(default=None),
    needs_review: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ingredient)
    if q:
        stmt = stmt.where(Ingredient.name_en.ilike(f"%{q}%") | Ingredient.name_fr.ilike(f"%{q}%"))
    if needs_review is not None:
        # Ingredients with needs_review=True means they have RecipeIngredients flagged
        if needs_review:
            subq = select(RecipeIngredient.ingredient_id).where(
                RecipeIngredient.needs_review == True,
                RecipeIngredient.ingredient_id.isnot(None),
            )
            stmt = stmt.where(Ingredient.id.in_(subq))
        stmt = stmt.where(Ingredient.is_normalized == (not needs_review))
    stmt = stmt.order_by(Ingredient.name_en).offset(offset).limit(limit)
    ingredients = (await db.scalars(stmt)).all()

    # Compute usage counts in a single query
    ids = [i.id for i in ingredients]
    if ids:
        count_rows = (
            await db.execute(
                select(RecipeIngredient.ingredient_id, func.count().label("cnt"))
                .where(RecipeIngredient.ingredient_id.in_(ids))
                .group_by(RecipeIngredient.ingredient_id)
            )
        ).all()
        usage_map = {row[0]: row[1] for row in count_rows}
        # Check which have needs_review RecipeIngredients
        review_rows = (
            await db.execute(
                select(RecipeIngredient.ingredient_id)
                .where(
                    RecipeIngredient.ingredient_id.in_(ids),
                    RecipeIngredient.needs_review == True,
                )
                .distinct()
            )
        ).scalars().all()
        review_set = set(review_rows)
    else:
        usage_map = {}
        review_set = set()

    return [
        IngredientDetail(
            id=i.id,
            name_en=i.name_en,
            name_fr=i.name_fr,
            category=i.category,
            is_normalized=i.is_normalized,
            needs_review=i.id in review_set,
            usage_count=usage_map.get(i.id, 0),
        )
        for i in ingredients
    ]


@router.post("/ingredients/merge", response_model=IngredientDetail)
async def merge_ingredients(
    payload: IngredientMergeRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.source_id == payload.target_id:
        raise HTTPException(status_code=400, detail="Source and target must be different")

    source = await db.get(Ingredient, payload.source_id)
    target = await db.get(Ingredient, payload.target_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source ingredient not found")
    if not target:
        raise HTTPException(status_code=404, detail="Target ingredient not found")

    # Reassign all RecipeIngredients from source → target
    await db.execute(
        update(RecipeIngredient)
        .where(RecipeIngredient.ingredient_id == payload.source_id)
        .values(ingredient_id=payload.target_id)
    )
    await db.delete(source)
    await db.commit()
    await db.refresh(target)
    usage_count = (
        await db.scalar(
            select(func.count()).select_from(RecipeIngredient).where(RecipeIngredient.ingredient_id == target.id)
        )
    ) or 0
    return IngredientDetail(
        id=target.id,
        name_en=target.name_en,
        name_fr=target.name_fr,
        category=target.category,
        is_normalized=target.is_normalized,
        needs_review=False,
        usage_count=usage_count,
    )


# ── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_recipes = (await db.scalar(select(func.count(Recipe.id)))) or 0
    total_lists = (await db.scalar(select(func.count(ShoppingList.id)))) or 0

    source_rows = (
        await db.execute(
            select(Recipe.source_domain, func.count(Recipe.id).label("cnt"))
            .group_by(Recipe.source_domain)
            .order_by(func.count(Recipe.id).desc())
            .limit(10)
        )
    ).all()
    recipes_by_source = [RecipeSourceStat(source_domain=row[0], count=row[1]) for row in source_rows]

    top_recipes_rows = (
        await db.execute(
            select(ShoppingListRecipe.recipe_id, Recipe.title, func.count(ShoppingListRecipe.id).label("cnt"))
            .join(Recipe, ShoppingListRecipe.recipe_id == Recipe.id)
            .group_by(ShoppingListRecipe.recipe_id, Recipe.title)
            .order_by(func.count(ShoppingListRecipe.id).desc())
            .limit(10)
        )
    ).all()
    top_recipes_in_lists = [
        TopRecipeStat(recipe_id=row[0], title=row[1], appearance_count=row[2])
        for row in top_recipes_rows
    ]

    top_ing_rows = (
        await db.execute(
            select(Ingredient.name_en, func.count(RecipeIngredient.id).label("cnt"))
            .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .group_by(Ingredient.name_en)
            .order_by(func.count(RecipeIngredient.id).desc())
            .limit(10)
        )
    ).all()
    top_ingredients = [TopIngredientStat(name=row[0], count=row[1]) for row in top_ing_rows]

    return StatsOut(
        total_recipes=total_recipes,
        total_lists=total_lists,
        recipes_by_source=recipes_by_source,
        top_recipes_in_lists=top_recipes_in_lists,
        top_ingredients=top_ingredients,
    )

