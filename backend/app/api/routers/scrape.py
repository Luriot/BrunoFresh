import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import SessionLocal, get_db
from ...models import Recipe, ScrapeJob
from ...schemas import DuplicateWarningInfo, JobStatus, JobStatusResponse, ScrapeRequest, ScrapeResponse
from ...services.events import JobEvent, job_event_bus
from ...services.network import validate_public_http_url
from ...services.orchestrator import DuplicateFound, persist_scraped_recipe

logger = logging.getLogger(__name__)

scrape_semaphore = asyncio.Semaphore(max(1, settings.scrape_concurrency_limit))
# Keeps a hard reference to fire-and-forget tasks so they aren't collected mid-execution.
_background_tasks: set[asyncio.Task] = set()

router = APIRouter(prefix="/api", tags=["scrape"])


def _format_sse(event_name: str, payload: dict[str, str | int | None]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


async def _run_scrape_job(job_id: int, force: bool = False) -> None:
    async with SessionLocal() as db:
        job = await db.get(ScrapeJob, job_id)
        if not job:
            logger.warning(f"Job {job_id} introuvable en base.")
            return

        logger.info(f"Démarrage du job de scraping {job_id}: {job.url}")
        job.status = "running"
        await db.commit()
        await job_event_bus.publish(job_id, JobEvent(status="running", message="Démarrage de l'analyse..."))

        async with scrape_semaphore:
            try:
                result = await persist_scraped_recipe(job.url, db, job_id, force=force)
                if isinstance(result, DuplicateFound):
                    job.status = "duplicate_warning"
                    job.error_message = f"DUPLICATE:{result.existing_id}:{result.existing_title}:{result.title_score}:{result.ingredient_score}"
                    await db.commit()
                    await job_event_bus.publish(
                        job_id,
                        JobEvent(
                            status="duplicate_warning",
                            message=f"Recette similaire : {result.existing_title}",
                            extra={
                                "similar_id": result.existing_id,
                                "similar_title": result.existing_title,
                                "similar_url": result.existing_url,
                                "similar_image": result.existing_image,
                                "title_score": result.title_score,
                                "ingredient_score": result.ingredient_score,
                            },
                        ),
                    )
                    return
                job.status = "completed"
                job.error_message = None
                await db.commit()
                logger.info(f"Job {job_id} terminé avec succès.")
                await job_event_bus.publish(job_id, JobEvent(status="completed", message="Recette ajoutée avec succès !"))
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)[:700]
                await db.commit()
                logger.error(f"Échec du job {job_id}: {exc}", exc_info=True)
                await job_event_bus.publish(
                    job_id,
                    JobEvent(status="failed", message=job.error_message),
                )


@router.post("/scrape", response_model=ScrapeResponse)
async def enqueue_scrape(
    payload: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    safe_url = await validate_public_http_url(str(payload.url))

    existing = await db.scalar(select(Recipe).where(Recipe.url == safe_url))
    if existing:
        return ScrapeResponse(message="Recipe already exists", url=safe_url, status="completed")

    job = ScrapeJob(url=safe_url, status="pending")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(_run_scrape_job(job.id, force=payload.force))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return ScrapeResponse(message="Scrape job queued", url=safe_url, job_id=job.id, status="pending")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    _valid: set[JobStatus] = {"pending", "running", "completed", "failed", "duplicate_warning"}
    status: JobStatus = job.status if job.status in _valid else "pending"  # type: ignore[assignment]

    return JobStatusResponse(
        job_id=job.id,
        status=status,
        error_message=job.error_message,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        async for queue in job_event_bus.subscribe(job_id):
            # Le session de db de FastAPI Dependency se ferme parfois avant que le flux ne finisse, 
            # on ouvre une session autonome pour lire l'état de la base de données de manière asynchrone sécurisée:
            async with SessionLocal() as stream_db:
                stream_job = await stream_db.get(ScrapeJob, job_id)
                if not stream_job:
                    return
                    
                yield _format_sse(
                    "status",
                    {
                        "job_id": stream_job.id,
                        "status": stream_job.status,
                        "message": "Abonnement au flux...",
                        "error_message": stream_job.error_message,
                    },
                )

                if stream_job.status in {"completed", "failed"}:
                    return

            # Écoute en direct
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                    payload: dict = {
                        "job_id": job_id,
                        "status": event.status,
                        "message": event.message,
                        "error_message": event.message if event.status == "failed" else None,
                    }
                    if event.extra:
                        payload.update(event.extra)
                    yield _format_sse("status", payload)
                    if event.status in {"completed", "failed", "duplicate_warning"}:
                        return
                except TimeoutError:
                    # Si un événement est raté (race condition), on lit la DB et on force le statut final.
                    async with SessionLocal() as heartbeat_db:
                        heartbeat_job = await heartbeat_db.get(ScrapeJob, job_id)
                        if not heartbeat_job:
                            return

                        if heartbeat_job.status in {"completed", "failed", "duplicate_warning"}:
                            yield _format_sse(
                                "status",
                                {
                                    "job_id": heartbeat_job.id,
                                    "status": heartbeat_job.status,
                                    "message": (
                                        "Recette ajoutée avec succès !"
                                        if heartbeat_job.status == "completed"
                                        else heartbeat_job.error_message
                                    ),
                                    "error_message": heartbeat_job.error_message,
                                },
                            )
                            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
