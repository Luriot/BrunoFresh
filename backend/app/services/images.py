from __future__ import annotations

from pathlib import Path

import httpx

from ..config import settings
from .network import validate_public_host_for_download


async def download_image(image_url: str | None, recipe_id: int) -> str | None:
    if not image_url:
        return None

    is_safe_target = await validate_public_host_for_download(image_url)
    if not is_safe_target:
        return None

    target = settings.images_dir / f"recipe_{recipe_id}.jpg"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            target.write_bytes(response.content)
        rel = Path("images") / target.name
        return rel.as_posix()
    except Exception:
        return None
