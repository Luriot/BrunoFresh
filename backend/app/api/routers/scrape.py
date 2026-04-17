import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...config import settings
from ...database import SessionLocal, get_db
from ...models import Ingredient, Recipe, RecipeIngredient, ScrapeJob
from ...schemas import JobStatusResponse, ScrapeRequest, ScrapeResponse
from ...services.dedupe import looks_like_duplicate
from ...services.images import download_image
from ...services.normalizer import normalize_ingredient
from ...services.scraper import scrape_recipe_url

SUPPORTED_SCRAPE_DOMAINS = ("hellofresh", "cuisineaz", "allrecipes", "jow", "750g")
scrape_semaphore = asyncio.Semaphore(max(1, settings.scrape_concurrency_limit))

router = APIRouter(prefix="/api", tags=["scrape"])


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


async def _persist_scraped_recipe(url: str, db: AsyncSession):
    existing = await db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        return

    scraped = await scrape_recipe_url(url)

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


@router.post("/scrape", response_model=ScrapeResponse)
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


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(id=job.id, url=job.url, status=job.status, error_message=job.error_message)
