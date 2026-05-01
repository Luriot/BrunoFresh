from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Recipe
from ...schemas import HFSearchResultResponse
from ...services.hellofresh_api import search_hf_recipes

router = APIRouter(prefix="/api", tags=["hellofresh"])


@router.get("/hellofresh/search", response_model=list[HFSearchResultResponse])
async def search_hellofresh(
    q: str = Query(min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
) -> list[HFSearchResultResponse]:
    hits = await search_hf_recipes(q)

    hf_urls = [h.hf_url for h in hits if h.hf_url]
    imported_urls: set[str] = set()
    if hf_urls:
        result = await db.execute(select(Recipe.url).where(Recipe.url.in_(hf_urls)))
        imported_urls = {row[0] for row in result}

    return [
        HFSearchResultResponse(
            id=h.id,
            name=h.name,
            image_url=h.image_url,
            tags=h.tags,
            total_time_minutes=h.total_time_minutes,
            hf_url=h.hf_url,
            already_imported=h.hf_url in imported_urls,
        )
        for h in hits
    ]
