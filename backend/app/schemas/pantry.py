from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    lang: str = Field(default="en", min_length=2, max_length=10)
    ingredient_id: int | None = None
    category: str | None = Field(default=None, max_length=80)


class PantryItemOut(BaseModel):
    id: int
    name: str
    name_fr: str | None = None
    ingredient_id: int | None = None
    category: str | None = None
    added_at: str

    model_config = ConfigDict(from_attributes=True)
