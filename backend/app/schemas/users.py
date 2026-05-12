from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserPatch(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=80)
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str | None = Field(default=None, min_length=8, max_length=256)
