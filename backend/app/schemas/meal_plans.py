from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MealPlanCreate(BaseModel):
    label: str | None = Field(default=None, max_length=160)
    week_start_date: date | None = None


class MealPlanEntryCreate(BaseModel):
    recipe_id: int
    day_of_week: int = Field(ge=0, le=6)
    meal_slot: str | None = Field(default=None, max_length=40)
    target_servings: int = Field(default=2, ge=1, le=20)


class MealPlanEntryOut(BaseModel):
    id: int
    recipe_id: int
    recipe_title: str
    recipe_image_local_path: str | None
    day_of_week: int
    meal_slot: str | None
    target_servings: int

    model_config = ConfigDict(from_attributes=True)


class MealPlanOut(BaseModel):
    id: int
    label: str | None
    week_start_date: date | None
    created_at: datetime
    entries: list[MealPlanEntryOut]

    model_config = ConfigDict(from_attributes=True)


class MealPlanSummaryOut(BaseModel):
    id: int
    label: str | None
    week_start_date: date | None
    created_at: datetime
    entry_count: int
    preview_images: list[str | None] = []


class MealPlanPatch(BaseModel):
    label: str | None = Field(default=None, max_length=120)


class MealPlanEntryPatch(BaseModel):
    target_servings: int = Field(ge=1, le=20)
