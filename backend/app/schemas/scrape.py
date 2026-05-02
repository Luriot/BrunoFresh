from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


JobStatus = Literal["pending", "running", "completed", "failed", "duplicate_warning"]


class HFSearchResultResponse(BaseModel):
    id: str
    name: str
    image_url: str | None
    tags: list[str]
    total_time_minutes: int | None
    hf_url: str
    already_imported: bool


class ScrapeRequest(BaseModel):
    url: HttpUrl
    force: bool = False


class DuplicateWarningInfo(BaseModel):
    id: int
    title: str
    url: str
    image_local_path: str | None = None
    title_score: float
    ingredient_score: float


class ScrapeResponse(BaseModel):
    message: str
    url: str
    job_id: int | None = None
    status: JobStatus
    similar_recipe: DuplicateWarningInfo | None = None


class RecipeSimilarPair(BaseModel):
    recipe_a_id: int
    recipe_a_title: str
    recipe_a_url: str
    recipe_a_image: str | None = None
    recipe_b_id: int
    recipe_b_title: str
    recipe_b_url: str
    recipe_b_image: str | None = None
    title_score: float
    ingredient_score: float


class RecipeSimilarPairsResponse(BaseModel):
    pairs: list[RecipeSimilarPair]


class JobStatusResponse(BaseModel):
    job_id: int
    status: JobStatus
    error_message: str | None = None
