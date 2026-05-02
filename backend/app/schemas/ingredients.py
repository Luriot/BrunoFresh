from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IngredientNamePatch(BaseModel):
    """Patch an ingredient by providing a name in any supported language.

    The backend auto-translates to all other configured languages via Ollama.
    """
    name: str = Field(min_length=1, max_length=200)
    lang: str = Field(default="en", min_length=2, max_length=10)
    category: str = Field(max_length=80)


class IngredientDetail(BaseModel):
    id: int
    name_en: str
    name_fr: str | None = None
    category: str | None = None
    is_normalized: bool
    needs_review: bool = False
    usage_count: int = 0
    translations: dict[str, str] = {}

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
