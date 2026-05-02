"""Re-scrape and format-instructions endpoints."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_db, AsyncSessionLocal
from ....models import Recipe, RecipeIngredient
from ....schemas import RecipeDetail, ScrapeResponse
from .utils import _RECIPE_NOT_FOUND, _recipe_detail_opts, _recipe_to_detail

router = APIRouter()


@router.post("/recipes/{recipe_id}/rescrape", response_model=ScrapeResponse)
async def rescrape_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    from ....models import ScrapeJob
    from ....services.events import JobEvent, job_event_bus

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
                from ....models import ScrapeJob as SJ
                running_job = await session.get(SJ, job_id)
                if running_job:
                    running_job.status = "running"
                    await session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="running", message="Re-scraping..."))

                from ....services.scrapers.router import scrape_recipe_url
                from ....services.normalizer import normalize_ingredients_batch
                from ....services.images import download_image

                scraped = await scrape_recipe_url(target_url)
                await job_event_bus.publish(job_id, JobEvent(status="running", message="Normalising ingredients..."))
                normalized = await normalize_ingredients_batch(scraped.ingredients)

                target_recipe.title = scraped.title
                target_recipe.instructions_text = scraped.instructions_text
                target_recipe.instruction_steps_json = (
                    json.dumps(scraped.instruction_steps) if scraped.instruction_steps else None
                )
                target_recipe.base_servings = scraped.base_servings
                target_recipe.prep_time_minutes = scraped.prep_time_minutes
                if scraped.image_url and scraped.image_url != target_recipe.image_original_url:
                    target_recipe.image_original_url = scraped.image_url
                    local_path = await download_image(scraped.image_url, recipe_id)
                    if local_path:
                        target_recipe.image_local_path = local_path

                await session.execute(
                    delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
                )
                await session.flush()

                from ....services.orchestrator import auto_tag_recipe, save_normalized_ingredients
                await save_normalized_ingredients(scraped.ingredients, normalized, recipe_id, session)

                incoming_names = [
                    n.name_en if n and n.name_en != "section_header_ignore" else ing.raw
                    for n, ing in zip(normalized, scraped.ingredients)
                ]
                await auto_tag_recipe(
                    target_recipe, scraped.title, incoming_names, scraped.prep_time_minutes, session
                )

                running_job = await session.get(SJ, job_id)
                if running_job:
                    running_job.status = "completed"
                await session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="completed", message="Re-scrape complete"))
            except Exception as exc:
                async with AsyncSessionLocal() as fail_session:
                    from ....models import ScrapeJob as SJ2
                    failed_job = await fail_session.get(SJ2, job_id)
                    if failed_job:
                        failed_job.status = "failed"
                        failed_job.error_message = str(exc)[:800]
                        await fail_session.commit()
                await job_event_bus.publish(job_id, JobEvent(status="failed", message=str(exc)))

    asyncio.create_task(_run())
    return ScrapeResponse(message="Re-scrape job queued", url=target_url, job_id=job_id, status="pending")


@router.post("/recipes/{recipe_id}/format-instructions", response_model=RecipeDetail)
async def format_recipe_instructions(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
):
    from ....services.normalizer import ollama_semaphore
    from ....config import settings
    import httpx as _httpx

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
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
    except Exception:
        raise HTTPException(status_code=502, detail="Ollama service unavailable. Is Ollama running?")

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    return _recipe_to_detail(recipe)
