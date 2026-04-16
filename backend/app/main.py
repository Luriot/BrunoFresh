import asyncio
import ipaddress
import socket
from collections import defaultdict
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import Ingredient, Recipe, RecipeIngredient, ScrapeJob
from .schemas import (
    CartGroupItem,
    CartRequest,
    CartResponse,
    IngredientPatch,
    JobStatusResponse,
    RecipeDetail,
    RecipeIngredientOut,
    RecipeListItem,
    ScrapeRequest,
    ScrapeResponse,
)
from .services.dedupe import looks_like_duplicate
from .services.images import download_image
from .services.normalizer import normalize_ingredient
from .services.scraper import scrape_recipe_url


SUPPORTED_SCRAPE_DOMAINS = ("hellofresh", "cuisineaz", "allrecipes", "jow", "750g")
scrape_semaphore = asyncio.Semaphore(max(1, settings.scrape_concurrency_limit))

app = FastAPI(title="MealCart API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory=str(settings.images_dir)), name="images")


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _ing_to_out(link: RecipeIngredient) -> RecipeIngredientOut:
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=link.ingredient.name_en if link.ingredient else None,
        category=link.ingredient.category if link.ingredient else None,
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _is_public_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for info in infos:
        ip_str = info[4][0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


async def _validate_scrape_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")

    hostname = parsed.hostname or ""
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL host")

    if not any(domain in hostname for domain in SUPPORTED_SCRAPE_DOMAINS):
        raise HTTPException(status_code=400, detail="Unsupported recipe domain")

    is_public = await asyncio.to_thread(_is_public_host, hostname)
    if not is_public:
        raise HTTPException(status_code=400, detail="Private or invalid network target rejected")

    return url


@app.get("/api/recipes", response_model=list[RecipeListItem])
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


@app.get("/api/recipes/{recipe_id}", response_model=RecipeDetail)
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


async def _persist_scraped_recipe(url: str, db: AsyncSession):
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        return

    scraped = await asyncio.to_thread(scrape_recipe_url, url)

    incoming_names: list[str] = []
    for ing in scraped.ingredients:
        normalized_probe = await asyncio.to_thread(normalize_ingredient, ing.raw, ing.quantity, ing.unit)
        incoming_names.append(normalized_probe.name_en if normalized_probe else ing.raw)

    existing_recipes = (
        await db.scalars(
            select(Recipe).options(
                selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
            )
        )
    ).all()
    for candidate in existing_recipes:
        candidate_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in candidate.recipe_ingredients
        ]
        if looks_like_duplicate(candidate.title, candidate_names, scraped.title, incoming_names):
            return

    recipe = Recipe(
        title=scraped.title,
        url=url,
        source_domain=scraped.source_domain,
        image_local_path=None,
        image_original_url=scraped.image_url,
        instructions_text=scraped.instructions_text,
        base_servings=scraped.base_servings,
        prep_time_minutes=scraped.prep_time_minutes,
    )
    db.add(recipe)
    await db.flush()

    local_image_path = await asyncio.to_thread(download_image, scraped.image_url, recipe.id)
    if local_image_path:
        recipe.image_local_path = local_image_path
    await db.flush()

    for ing in scraped.ingredients:
        normalized = await asyncio.to_thread(normalize_ingredient, ing.raw, ing.quantity, ing.unit)
        ingredient = None
        needs_review = False
        quantity = ing.quantity
        unit = ing.unit

        if normalized:
            ingredient = await db.scalar(select(Ingredient).where(Ingredient.name_en == normalized.name_en))
            if not ingredient:
                ingredient = Ingredient(
                    name_en=normalized.name_en,
                    category=normalized.category,
                    is_normalized=True,
                )
                db.add(ingredient)
                await db.flush()
            quantity = normalized.quantity
            unit = normalized.unit
        else:
            needs_review = True

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id if ingredient else None,
                raw_string=ing.raw,
                quantity=quantity,
                unit=unit,
                needs_review=needs_review,
            )
        )

    await db.commit()


async def _run_scrape_job(job_id: int) -> None:
    async with SessionLocal() as db:
        job = await db.get(ScrapeJob, job_id)
        if not job:
            return

        job.status = "running"
        await db.commit()

        async with scrape_semaphore:
            try:
                await _persist_scraped_recipe(job.url, db)
                job.status = "completed"
                job.error_message = None
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)[:700]
            await db.commit()


@app.post("/api/scrape", response_model=ScrapeResponse)
async def enqueue_scrape(
    payload: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    safe_url = await _validate_scrape_url(str(payload.url))

    existing = await db.scalar(select(Recipe).where(Recipe.url == safe_url))
    if existing:
        return ScrapeResponse(message="Recipe already exists", url=safe_url, status="completed")

    job = ScrapeJob(url=safe_url, status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(_run_scrape_job(job.id))
    return ScrapeResponse(message="Scrape job queued", url=safe_url, job_id=job.id, status="pending")


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(id=job.id, url=job.url, status=job.status, error_message=job.error_message)


@app.patch("/api/ingredients/{ingredient_id}")
async def patch_ingredient(
    ingredient_id: int, payload: IngredientPatch, db: AsyncSession = Depends(get_db)
):
    ingredient = await db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    ingredient.name_en = payload.name_en
    ingredient.category = payload.category
    ingredient.is_normalized = True
    await db.commit()
    return {"status": "updated"}


@app.post("/api/cart/generate", response_model=CartResponse)
async def generate_cart(payload: CartRequest, db: AsyncSession = Depends(get_db)):
    grouped: dict[str, dict[tuple[str, str], float]] = defaultdict(lambda: defaultdict(float))
    needs_review: list[str] = []

    if not payload.items:
        return CartResponse(grouped={}, needs_review=[])

    recipe_ids = list({item.recipe_id for item in payload.items})
    recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
            .where(Recipe.id.in_(recipe_ids))
        )
    ).all()
    recipes_by_id = {recipe.id: recipe for recipe in recipes}

    for item in payload.items:
        recipe = recipes_by_id.get(item.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {item.recipe_id} not found")

        multiplier = item.target_servings / max(recipe.base_servings, 1)

        for link in recipe.recipe_ingredients:
            if link.needs_review or not link.ingredient:
                needs_review.append(f"{recipe.title}: {link.raw_string}")
                continue

            category = link.ingredient.category
            key = (link.ingredient.name_en, link.unit)
            grouped[category][key] += link.quantity * multiplier

    response_grouped: dict[str, list[CartGroupItem]] = {}
    for category, values in grouped.items():
        response_grouped[category] = [
            CartGroupItem(name=name, quantity=round(qty, 2), unit=unit)
            for (name, unit), qty in sorted(values.items(), key=lambda kv: kv[0][0])
        ]

    return CartResponse(grouped=response_grouped, needs_review=sorted(set(needs_review)))
