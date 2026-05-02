from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=30)


class TagOut(BaseModel):
    id: int
    name: str
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)
