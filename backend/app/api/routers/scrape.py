import asyncio
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import SessionLocal, get_db
from ...models import Recipe, ScrapeJob
from ...schemas import ScrapeRequest, ScrapeResponse
from ...services.events import JobEvent, job_event_bus
from ...services.network import validate_public_http_url
from ...services.orchestrator import persist_scraped_recipe

SUPPORTED_SCRAPE_DOMAINS = ("hellofresh", "cuisineaz", "allrecipes", "jow", "750g")
scrape_semaphore = asyncio.Semaphore(max(1, settings.scrape_concurrency_limit))

router = APIRouter(prefix="/api", tags=["scrape"])


def _format_sse(event_name: str, payload: dict[str, str | int | None]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


async def _validate_scrape_url(url: str) -> str:
    safe_url = await validate_public_http_url(url)
    hostname = (urlparse(safe_url).hostname or "").lower()
    if not any(domain in hostname for domain in SUPPORTED_SCRAPE_DOMAINS):
        raise HTTPException(status_code=400, detail="Unsupported recipe domain")

    return safe_url


async def _run_scrape_job(job_id: int) -> None:
    async with SessionLocal() as db:
        job = await db.get(ScrapeJob, job_id)
        if not job:
            logger.warning(f"Job {job_id} introuvable en base.")
            return

        logger.info(f"Démarrage du job de scraping {job_id}: {job.url}")
        job.status = "running"
        await db.commit()
        await job_event_bus.publish(job_id, JobEvent(status="running"))

        async with scrape_semaphore:
            try:
                await persist_scraped_recipe(job.url, db)
                job.status = "completed"
                job.error_message = None
                logger.info(f"Job {job_id} terminé avec succès.")
                await job_event_bus.publish(job_id, JobEvent(status="completed"))
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)[:700]
                logger.error(f"Échec du job {job_id}: {exc}", exc_info=True)
                await job_event_bus.publish(
                    job_id,
                    JobEvent(status="failed", message=job.error_message),
                )
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


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        yield _format_sse(
            "status",
            {
                "job_id": job.id,
                "status": job.status,
                "error_message": job.error_message,
            },
        )

        if job.status in {"completed", "failed"}:
            return

        async for queue in job_event_bus.subscribe(job_id):
            while True:
                event = await queue.get()
                yield _format_sse(
                    "status",
                    {
                        "job_id": job_id,
                        "status": event.status,
                        "error_message": event.message,
                    },
                )
                if event.status in {"completed", "failed"}:
                    return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
