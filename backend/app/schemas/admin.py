from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


# ── Admin user management ─────────────────────────────────────────────────────


class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    avatar_url: str | None = None
    language: str = "en"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserPatch(BaseModel):
    role: str | None = None

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str | None) -> str | None:
        if v is not None and v not in {"admin", "user"}:
            raise ValueError("role must be 'admin' or 'user'")
        return v


class AdminResetPassword(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)