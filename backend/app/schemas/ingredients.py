from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngredientNamePatch(BaseModel):
    """Patch an ingredient. All fields optional; only provided fields are applied.

    - ``name`` + ``lang`` triggers Ollama translation to all supported languages.
    - ``grams_per_paquet`` / ``grams_per_boite`` are admin overrides that win
      over the static ``_PACK_GRAMS`` table (but not over retro-calibration from
      the recipe's own raw text — that always wins per-occurrence).
    """
    name: str | None = Field(default=None, min_length=1, max_length=200)
    lang: str = Field(default="en", min_length=2, max_length=10)
    category: str | None = Field(default=None, max_length=80)
    grams_per_paquet: float | None = Field(default=None, ge=0)
    grams_per_boite: float | None = Field(default=None, ge=0)


class IngredientDetail(BaseModel):
    id: int
    name_en: str
    name_fr: str | None = None
    category: str | None = None
    is_normalized: bool
    needs_review: bool = False
    usage_count: int = 0
    translations: dict[str, str] = {}
    grams_per_paquet: float | None = None
    grams_per_boite: float | None = None

    model_config = ConfigDict(from_attributes=True)


class MergeSuggestion(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    reason: str


class MergeSuggestionResponse(BaseModel):
    suggestions: list[MergeSuggestion]


class IngredientMergeRequest(BaseModel):
    source_id: int
    target_id: int


class IngredientMergeRuleOut(BaseModel):
    id: int
    source_name: str
    canonical_ingredient_id: int
    canonical_name: str
    canonical_category: str | None = None
    category_hint: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngredientMergeRuleCreate(BaseModel):
    source_name: str = Field(min_length=1, max_length=200)
    canonical_ingredient_id: int
    category_hint: str | None = Field(default=None, max_length=80)
