from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ...config import settings

router = APIRouter(prefix="/api/images", tags=["images"])

_INVALID_PATH_DETAIL = "Invalid image path"


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

    # Use FileResponse directly — any TOCTOU race (file deleted between the
    # .exists() check and the response) is handled by catching FileNotFoundError.
    try:
        return FileResponse(resolved)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found") from exc
