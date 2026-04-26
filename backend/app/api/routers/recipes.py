import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models import Ingredient, Recipe, RecipeIngredient, Tag
from ...models import recipe_tags as recipe_tags_table
from ...schemas import (
    IngredientDetail,
    IngredientNamePatch,
    InstructionStep,
    RecipeCreate,
    RecipeDetail,
    RecipeIngredientOut,
    RecipeListItem,
    RecipePatch,
    RecipeTagsUpdate,
    ScrapeResponse,
    TagOut,
)

router = APIRouter(prefix="/api", tags=["recipes"])

_RECIPE_NOT_FOUND = "Recipe not found"


def _ing_to_out(link: RecipeIngredient) -> RecipeIngredientOut:
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=link.ingredient.name_en if link.ingredient else None,
        ingredient_name_fr=link.ingredient.name_fr if link.ingredient else None,
        category=link.ingredient.category if link.ingredient else None,
    )


def _recipe_to_detail(recipe: Recipe) -> RecipeDetail:
    steps: list[InstructionStep] = []
    if recipe.instruction_steps_json:
        try:
            raw = json.loads(recipe.instruction_steps_json)
            steps = [InstructionStep(**s) for s in raw if isinstance(s, dict)]
        except Exception:
            pass
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
        is_favorite=recipe.is_favorite,
        tags=[TagOut.model_validate(t) for t in recipe.tags],
        ingredients=[_ing_to_out(link) for link in recipe.recipe_ingredients],
        instruction_steps=steps,
    )


@router.get("/recipes", response_model=list[RecipeListItem])
async def list_recipes(
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    is_favorite: bool | None = Query(default=None),
    ingredients: str | None = Query(default=None, description="Comma-separated ingredient keywords"),
    tags: str | None = Query(default=None, description="Comma-separated tag names (any match)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe).options(selectinload(Recipe.tags))

    if q:
        # Search by title OR ingredient name
        ingredient_recipe_ids = select(RecipeIngredient.recipe_id).join(
            Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).where(
            Ingredient.name_en.ilike(f"%{q}%") | Ingredient.name_fr.ilike(f"%{q}%")
        )
        stmt = stmt.where(Recipe.title.ilike(f"%{q}%") | Recipe.id.in_(ingredient_recipe_ids))

    if source:
        stmt = stmt.where(Recipe.source_domain == source)

    if is_favorite is not None:
        stmt = stmt.where(Recipe.is_favorite == is_favorite)

    if ingredients:
        keywords = [kw.strip() for kw in ingredients.split(",") if kw.strip()]
        for kw in keywords:
            subq = select(RecipeIngredient.recipe_id).join(
                Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
            ).where(
                Ingredient.name_en.ilike(f"%{kw}%") | Ingredient.name_fr.ilike(f"%{kw}%")
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

    recipes = (await db.scalars(stmt.order_by(Recipe.is_favorite.desc(), func.lower(Recipe.title).asc()).offset(offset).limit(limit))).all()
    return recipes


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(recipe_id: int, db: AsyncSession = Depends(get_db)):
    recipe = await db.scalar(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
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
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == new_recipe.id)
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
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if payload.is_favorite is not None:
        recipe.is_favorite = payload.is_favorite
    if payload.instructions_text is not None:
        recipe.instructions_text = payload.instructions_text
    await db.commit()

    recipe = await db.scalar(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
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


@router.put("/recipes/{recipe_id}/tags", response_model=RecipeDetail)
async def set_recipe_tags(
    recipe_id: int,
    payload: RecipeTagsUpdate,
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
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
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)


@router.get("/recipes/{recipe_id}/similar", response_model=list[RecipeListItem])
async def get_similar_recipes(
    recipe_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    target = await db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients), selectinload(Recipe.tags))
        .where(Recipe.id == recipe_id)
    )
    if not target:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    target_ids = {
        ri.ingredient_id
        for ri in target.recipe_ingredients
        if ri.ingredient_id is not None
    }

    all_recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients), selectinload(Recipe.tags))
            .where(Recipe.id != recipe_id)
        )
    ).all()

    def jaccard(a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    scored = [
        (jaccard(target_ids, {ri.ingredient_id for ri in r.recipe_ingredients if ri.ingredient_id}), r)
        for r in all_recipes
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:limit]]


@router.post("/recipes/{recipe_id}/rescrape", response_model=ScrapeResponse)
async def rescrape_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    from ...models import ScrapeJob
    from ...services.events import JobEvent, job_event_bus
    from ...services.orchestrator import persist_scraped_recipe
    from ...database import AsyncSessionLocal

    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if recipe.url.startswith("custom://"):
        raise HTTPException(status_code=400, detail="Cannot re-scrape a custom recipe")

    job = ScrapeJob(url=recipe.url, status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    job_id = job.id
    target_url = recipe.url

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            target_recipe = await session.get(Recipe, recipe_id)
            if not target_recipe:
                return
            try:
                from ...models import ScrapeJob as SJ
                running_job = await session.get(SJ, job_id)
                if running_job:
                    running_job.status = "running"
                    await session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="running", message="Re-scraping..."))

                from ...services.scrapers.router import scrape_recipe_url
                from ...services.normalizer import normalize_ingredients_batch
                from ...services.images import download_image

                scraped = await scrape_recipe_url(target_url)
                await job_event_bus.publish(job_id, JobEvent(status="running", message="Normalising ingredients..."))
                normalized = await normalize_ingredients_batch(scraped.ingredients)

                # Update recipe fields
                target_recipe.title = scraped.title
                target_recipe.instructions_text = scraped.instructions_text
                target_recipe.base_servings = scraped.base_servings
                target_recipe.prep_time_minutes = scraped.prep_time_minutes
                if scraped.image_url and scraped.image_url != target_recipe.image_original_url:
                    target_recipe.image_original_url = scraped.image_url
                    local_path = await download_image(scraped.image_url, recipe_id)
                    if local_path:
                        target_recipe.image_local_path = local_path

                # Replace ingredients
                await session.execute(
                    delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
                )
                await session.flush()

                existing_ingredients: dict[str, Ingredient] = {}
                normalized_names = [n.name_en for n in normalized if n and n.name_en != "section_header_ignore"]
                if normalized_names:
                    result = await session.scalars(select(Ingredient).where(Ingredient.name_en.in_(normalized_names)))
                    for ing_obj in result:
                        existing_ingredients[ing_obj.name_en] = ing_obj

                from ...services.normalizer import normalize_unit as _nu
                for ing, norm in zip(scraped.ingredients, normalized):
                    if norm and norm.name_en == "section_header_ignore":
                        continue
                    ingredient = None
                    needs_review = False
                    quantity = ing.quantity
                    unit = ing.unit
                    if norm:
                        ingredient = existing_ingredients.get(norm.name_en)
                        if not ingredient:
                            ingredient = Ingredient(
                                name_en=norm.name_en,
                                name_fr=norm.name_fr,
                                category=norm.category,
                                is_normalized=True,
                            )
                            session.add(ingredient)
                            existing_ingredients[norm.name_en] = ingredient
                            await session.flush()
                        quantity = norm.quantity
                        unit = norm.unit
                    else:
                        needs_review = True
                    session.add(RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_id=ingredient.id if ingredient else None,
                        raw_string=ing.raw,
                        quantity=quantity,
                        unit=unit,
                        needs_review=needs_review,
                    ))

                running_job = await session.get(SJ, job_id)
                if running_job:
                    running_job.status = "completed"
                await session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="completed", message="Re-scrape complete"))
            except Exception as exc:
                from ...models import ScrapeJob as SJ2
                running_job = await session.get(SJ2, job_id)
                if running_job:
                    running_job.status = "failed"
                    running_job.error_message = str(exc)[:800]
                    await session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="failed", message=str(exc)))

    asyncio.create_task(_run())
    return ScrapeResponse(message="Re-scrape job queued", url=target_url, job_id=job_id, status="pending")


@router.post("/recipes/{recipe_id}/format-instructions", response_model=RecipeDetail)
async def format_recipe_instructions(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    from ...services.normalizer import ollama_semaphore
    from ...config import settings
    import httpx as _httpx

    recipe = await db.scalar(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if not recipe.instructions_text.strip():
        raise HTTPException(status_code=400, detail="Recipe has no instructions to format")

    prompt = (
        "Reformatte les instructions de cuisine suivantes en étapes numérotées claires. "
        "Une étape par ligne, commence chaque ligne par le numéro suivi d'un point. "
        "Conserve la langue d'origine. Ne retourne que les instructions reformattées, sans commentaire.\n\n"
        f"Instructions originales:\n{recipe.instructions_text[:8000]}"
    )

    try:
        async with ollama_semaphore:
            async with _httpx.AsyncClient(timeout=_httpx.Timeout(120.0, connect=5.0)) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
        formatted = resp.json().get("response", "").strip()
        if formatted:
            recipe.instructions_text = formatted
            await db.commit()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")

    recipe = await db.scalar(
        select(Recipe)
        .options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient),
            selectinload(Recipe.tags),
        )
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)


@router.patch("/ingredients/{ingredient_id}", response_model=IngredientDetail)
async def patch_ingredient(
    ingredient_id: int,
    payload: IngredientNamePatch,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from ...models import IngredientTranslation
    from ...services.normalizer import translate_ingredient_name

    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # Translate to all supported languages
    supported_langs = ["en", "fr"]
    translations = await translate_ingredient_name(payload.name, payload.lang, supported_langs)

    # Update the ingredient row (backward compat columns)
    ingredient.name_en = translations.get("en", payload.name)
    ingredient.name_fr = translations.get("fr")
    ingredient.category = payload.category
    ingredient.is_normalized = True

    # Upsert into ingredient_translations
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

    # Reload translations
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