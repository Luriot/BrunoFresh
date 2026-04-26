import asyncio
import json
import re
import shutil
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models import Ingredient, IngredientTranslation, Recipe, RecipeIngredient, ShoppingList, ShoppingListRecipe
from ...schemas import (
    IngredientDetail,
    IngredientMergeRequest,
    MergeSuggestion,
    MergeSuggestionResponse,
    RecipeSimilarPair,
    RecipeSimilarPairsResponse,
    RecipeSourceStat,
    StatsOut,
    TopIngredientStat,
    TopRecipeStat,
)
from ...services.dedupe import similarity_score
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
    stmt = select(Ingredient).options(selectinload(Ingredient.translations))
    if q:
        stmt = stmt.where(Ingredient.name_en.ilike(f"%{q}%") | Ingredient.name_fr.ilike(f"%{q}%"))
    if needs_review is not None:
        if needs_review:
            # Show ingredients that have at least one flagged RecipeIngredient
            subq = select(RecipeIngredient.ingredient_id).where(
                RecipeIngredient.needs_review == True,
                RecipeIngredient.ingredient_id.isnot(None),
            )
            stmt = stmt.where(Ingredient.id.in_(subq))
        else:
            # Show only fully-normalised ingredients
            stmt = stmt.where(Ingredient.is_normalized == True)
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
            translations={t.lang_code: t.name for t in i.translations},
        )
        for i in ingredients
    ]


@router.post("/ingredients/ai-suggest-merges", response_model=MergeSuggestionResponse)
async def ai_suggest_merges(db: AsyncSession = Depends(get_db)):
    """Ask Ollama to identify ingredient names that are likely duplicates.

    Read-only endpoint — no DB writes.  The frontend applies the suggestions
    via the regular /merge endpoint.
    """
    ingredients = (
        await db.scalars(
            select(Ingredient).order_by(Ingredient.name_en).limit(300)
        )
    ).all()

    ing_list = [{"id": i.id, "name": i.name_en} for i in ingredients]
    prompt = (
        "You are a food ingredient database administrator. "
        "Here is a JSON array of ingredient entries with integer IDs and English names: "
        f"{json.dumps(ing_list)}. "
        "Identify pairs of entries that clearly refer to the same ingredient "
        "(e.g. different spelling, plural, abbreviation, or minor variation). "
        "For each pair, designate the preferred canonical entry as target_name. "
        "Return JSON only: "
        '{"suggestions": [{"source_name": "...", "target_name": "...", "reason": "..."}]}. '
        "If no clear duplicates exist, return {\"suggestions\": []}. "
        "Limit to at most 30 suggestions."
    )

    try:
        from ...services.normalizer import ollama_semaphore  # noqa: PLC0415
        async with ollama_semaphore:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
        resp.raise_for_status()
        raw_text = resp.json().get("response", "")
        raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()
        parsed = json.loads(raw_text)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI unavailable. Is Ollama running? ({exc})",
        ) from exc

    name_to_id = {i.name_en: i.id for i in ingredients}
    suggestions: list[MergeSuggestion] = []
    for s in parsed.get("suggestions", [])[:30]:
        src_name = str(s.get("source_name", "")).strip()
        tgt_name = str(s.get("target_name", "")).strip()
        reason = str(s.get("reason", ""))[:200]
        src_id = name_to_id.get(src_name)
        tgt_id = name_to_id.get(tgt_name)
        if src_id and tgt_id and src_id != tgt_id:
            suggestions.append(
                MergeSuggestion(
                    source_id=src_id,
                    source_name=src_name,
                    target_id=tgt_id,
                    target_name=tgt_name,
                    reason=reason,
                )
            )

    return MergeSuggestionResponse(suggestions=suggestions)


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


# ── Recipe duplicate scan ────────────────────────────────────────────────────

@router.post("/recipes/find-duplicates", response_model=RecipeSimilarPairsResponse)
async def find_duplicate_recipes(
    title_threshold: float = 75.0,
    ingredient_threshold: float = 0.5,
    db: AsyncSession = Depends(get_db),
):
    """Scan all recipes and return pairs that look like duplicates."""
    recipes = (
        await db.scalars(
            select(Recipe).options(
                selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
            )
        )
    ).all()

    pairs: list[RecipeSimilarPair] = []
    for i, a in enumerate(recipes):
        a_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in a.recipe_ingredients
        ]
        for b in recipes[i + 1:]:
            b_names = [
                link.ingredient.name_en if link.ingredient else link.raw_string
                for link in b.recipe_ingredients
            ]
            ts, ing_s = similarity_score(a.title, a_names, b.title, b_names)
            if ts >= title_threshold and ing_s >= ingredient_threshold:
                pairs.append(RecipeSimilarPair(
                    recipe_a_id=a.id,
                    recipe_a_title=a.title,
                    recipe_a_url=a.url,
                    recipe_a_image=a.image_local_path,
                    recipe_b_id=b.id,
                    recipe_b_title=b.title,
                    recipe_b_url=b.url,
                    recipe_b_image=b.image_local_path,
                    title_score=round(ts, 1),
                    ingredient_score=round(ing_s, 2),
                ))

    return RecipeSimilarPairsResponse(pairs=pairs)


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

