from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ── Creation / patch ─────────────────────────────────────────────────────────

class RecipeIngredientCreate(BaseModel):
    raw_string: str = Field(min_length=1, max_length=400)
    quantity: float = Field(default=1, ge=0)
    unit: str = Field(default="item", max_length=30)
    ingredient_name: str = Field(min_length=1, max_length=200)
    ingredient_name_fr: str | None = Field(default=None, max_length=200)
    category: str = Field(default="Other", max_length=80)


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    instructions_text: str = Field(default="", max_length=50_000)
    base_servings: int = Field(default=2, ge=1, le=100)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=1440)
    ingredients: list[RecipeIngredientCreate] = Field(default_factory=list, max_length=100)


class RecipePatch(BaseModel):
    is_favorite: bool | None = None
    instructions_text: str | None = Field(default=None, max_length=50_000)


# ── Output ────────────────────────────────────────────────────────────────────

class IngredientOut(BaseModel):
    name: str
    name_fr: str | None = None
    quantity: float
    unit: str
    category: str


class RecipeIngredientOut(BaseModel):
    raw_string: str
    quantity: float
    unit: str
    needs_review: bool
    ingredient_name: str | None = None
    ingredient_name_fr: str | None = None
    category: str | None = None


class InstructionStep(BaseModel):
    text: str
    image_url: str | None = None


# Forward reference resolved by tags.TagOut
class RecipeListItem(BaseModel):
    id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None
    base_servings: int
    prep_time_minutes: int | None
    is_favorite: bool = False
    tags: list["TagOut"] = []  # noqa: F821 — resolved at model_rebuild time

    model_config = ConfigDict(from_attributes=True)


class RecipeDetail(BaseModel):
    id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None
    image_original_url: str | None
    instructions_text: str
    base_servings: int
    prep_time_minutes: int | None
    is_favorite: bool = False
    tags: list["TagOut"] = []  # noqa: F821 — resolved at model_rebuild time
    ingredients: list[RecipeIngredientOut]
    instruction_steps: list[InstructionStep] = []


class RecipeTagsUpdate(BaseModel):
    tag_ids: list[int]


# Avoid circular import: TagOut is defined in tags.py and injected here.
# The annotation string "TagOut" is fine because Pydantic resolves it lazily.
from .tags import TagOut  # noqa: E402 — needed for model_rebuild

RecipeListItem.model_rebuild()
RecipeDetail.model_rebuild()
