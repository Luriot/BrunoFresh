from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .recipes import BilingualNamedItem


class PantryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    lang: str = Field(default="en", min_length=2, max_length=10)
    ingredient_id: int | None = None
    category: str | None = Field(default=None, max_length=80)


class PantryItemOut(BilingualNamedItem):
    id: int
    ingredient_id: int | None = None
    category: str | None = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)
