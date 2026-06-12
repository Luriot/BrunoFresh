from __future__ import annotations

from pydantic import BaseModel


class ImageRetryResult(BaseModel):
    recipe_id: int
    success: bool
    image_local_path: str | None = None
    error: str | None = None


class BulkImageRetryResult(BaseModel):
    retried: int
    success: int
    failed: list[ImageRetryResult]


class ConvertImagesResult(BaseModel):
    converted: int
    skipped: int
    failed: int
    image_local_path: str | None = None