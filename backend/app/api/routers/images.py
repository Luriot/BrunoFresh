from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ...config import settings
from ...services.images import generate_thumbnail

router = APIRouter(prefix="/api/images", tags=["images"])

_INVALID_PATH_DETAIL = "Invalid image path"
# Serve immediately from cache for 1 h; re-validate silently in background
# for up to 24 h so replaced images are picked up without visible delay.
_CACHE_HEADERS = {"Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"}

# Extensions to search when looking for the original of a missing thumbnail
_ORIGINAL_EXTENSIONS = (".jpg", ".png", ".webp", ".gif")
_THUMB_SUFFIX = "_thumb.webp"

# Per-filename locks to prevent duplicate concurrent thumbnail generation.
_thumb_locks: dict[str, asyncio.Lock] = {}


def _thumb_lock(name: str) -> asyncio.Lock:
    if name not in _thumb_locks:
        _thumb_locks[name] = asyncio.Lock()
    return _thumb_locks[name]


@router.get("/{file_name}")
async def get_image(file_name: str):
    # Reject any component that would escape the images directory.
    safe_name = Path(file_name).name
    if not safe_name or safe_name != file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_PATH_DETAIL)

    image_path = settings.images_dir / safe_name

    # Resolve to an absolute path and verify it is still inside images_dir
    # (guards against symlink-based traversal on all platforms).
    try:
        resolved = image_path.resolve()
        images_root = settings.images_dir.resolve()
        if not resolved.is_relative_to(images_root):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_PATH_DETAIL)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_PATH_DETAIL) from exc

    # Lazy thumbnail generation: if a *_thumb.webp is requested but missing,
    # locate the original and generate it on the fly.
    if not resolved.exists() and safe_name.endswith(_THUMB_SUFFIX):
        base_stem = safe_name[: -len(_THUMB_SUFFIX)]
        original: Path | None = None
        for ext in _ORIGINAL_EXTENSIONS:
            candidate = settings.images_dir / f"{base_stem}{ext}"
            if candidate.exists():
                original = candidate
                break
        if original is not None:
            async with _thumb_lock(safe_name):
                # Re-check: a concurrent request may have already generated it.
                if resolved.exists():
                    return FileResponse(resolved, headers=_CACHE_HEADERS)
                generated = await asyncio.get_running_loop().run_in_executor(
                    None, generate_thumbnail, original
                )
                if generated and generated.exists():
                    return FileResponse(generated, headers=_CACHE_HEADERS)

    try:
        return FileResponse(resolved, headers=_CACHE_HEADERS)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found") from exc
