from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..services.images import resolve_image_url
from ..utils.format_qty import format_qty as _format_qty


def pick_display_name(name_en: str, name_fr: str | None, language: str) -> str:
    return name_fr if (language == "fr" and name_fr) else name_en


# ── Shared mixins ──────────────────────────────────────────────────────────────

class NutritionFields(BaseModel):
    kcal: int | None = Field(default=None, ge=0)
    protein_g: int | None = Field(default=None, ge=0)
    carbs_g: int | None = Field(default=None, ge=0)
    fat_g: int | None = Field(default=None, ge=0)


class BilingualNamedItem(BaseModel):
    name: str
    name_fr: str | None = None
    display_name: str | None = None


class RecipeBase(NutritionFields):
    id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None
    image_original_url: str | None = None
    base_servings: int
    prep_time_minutes: int | None
    is_favorite_by_me: bool = False
    recommenders: list[RecommenderOut] = []
    tags: list["TagOut"] = []  # noqa: F821 — resolved at model_rebuild time

    model_config = ConfigDict(from_attributes=True)


# ── Creation / patch ─────────────────────────────────────────────────────────

class RecipeIngredientCreate(BaseModel):
    raw_string: str = Field(min_length=1, max_length=400)
    quantity: float = Field(default=1, ge=0)
    unit: str = Field(default="item", max_length=30)
    ingredient_name: str = Field(min_length=1, max_length=200)
    ingredient_name_fr: str | None = Field(default=None, max_length=200)
    category: str = Field(default="Other", max_length=80)


class RecipeCreate(NutritionFields):
    title: str = Field(min_length=1, max_length=300)
    instructions_text: str = Field(default="", max_length=50_000)
    base_servings: int = Field(default=2, ge=1, le=100)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=1440)
    ingredients: list[RecipeIngredientCreate] = Field(default_factory=list, max_length=100)


class RecipePatch(NutritionFields):
    instructions_text: str | None = Field(default=None, max_length=50_000)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=1440)


# ── Output ────────────────────────────────────────────────────────────────────

class RecipeIngredientOut(BaseModel):
    raw_string: str
    quantity: float
    unit: str
    needs_review: bool
    ingredient_name: str | None = None
    ingredient_name_fr: str | None = None
    display_name: str | None = None
    category: str | None = None

    @computed_field
    @property
    def quantity_display(self) -> str:
        return _format_qty(self.quantity)


class InstructionStep(BaseModel):
    text: str
    image_url: str | None = None


class RecommenderOut(BaseModel):
    username: str
    avatar_url: str | None = None


class RecipeListItem(RecipeBase):
    @computed_field
    @property
    def image_url(self) -> str | None:
        return resolve_image_url(self.image_local_path, self.image_original_url, thumb=True)


class RecipeDetail(RecipeBase):
    instructions_text: str
    ingredients: list[RecipeIngredientOut]
    instruction_steps: list[InstructionStep] = []

    @computed_field
    @property
    def image_url(self) -> str | None:
        return resolve_image_url(self.image_local_path, self.image_original_url, thumb=False)


class RecipeTagsUpdate(BaseModel):
    tag_ids: list[int]


# Avoid circular import: TagOut is defined in tags.py and injected here.
# The annotation string "TagOut" is fine because Pydantic resolves it lazily.
from .tags import TagOut  # noqa: E402 — needed for model_rebuild

RecipeListItem.model_rebuild()
RecipeDetail.model_rebuild()
