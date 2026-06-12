from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .recipes import BilingualNamedItem
from ..services.images import resolve_image_url
from ..utils.format_qty import format_qty as _format_qty


class CartRecipeIn(BaseModel):
    recipe_id: int
    target_servings: int = Field(ge=1, le=20)


class CartRequest(BaseModel):
    items: list[CartRecipeIn]


class CartGroupItem(BaseModel):
    name: str
    quantity: float
    unit: str


class CartResponse(BaseModel):
    grouped: dict[str, list[CartGroupItem]]
    needs_review: list[str]


class ShoppingListCustomItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    name_fr: str | None = Field(default=None, max_length=200)
    quantity: float = Field(default=1, gt=0, le=9999)
    unit: str = Field(default="item", min_length=1, max_length=30)
    category: str = Field(default="Other", min_length=1, max_length=80)


class ShoppingListCreateRequest(BaseModel):
    items: list[CartRecipeIn]
    label: str | None = Field(default=None, max_length=160)
    extra_items: list[ShoppingListCustomItemIn] = Field(default_factory=list)


class ShoppingListItemPatch(BaseModel):
    is_already_owned: bool | None = None
    is_excluded: bool | None = None


class ShoppingListPatch(BaseModel):
    label: str | None = Field(default=None, max_length=160)


class ShoppingListItemOut(BilingualNamedItem):
    id: int
    quantity: float
    unit: str
    category: str
    is_custom: bool
    is_already_owned: bool
    is_excluded: bool = False

    @computed_field
    @property
    def quantity_display(self) -> str:
        return _format_qty(self.quantity)

    model_config = ConfigDict(from_attributes=True)


class ShoppingListSummaryOut(BaseModel):
    id: int
    label: str | None
    created_at: datetime
    total_items: int
    already_owned_items: int


class ShoppingListRecipeOut(BaseModel):
    recipe_id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None = Field(default=None, exclude=True)
    image_original_url: str | None = None
    target_servings: int

    @computed_field
    @property
    def image_url(self) -> str | None:
        return resolve_image_url(self.image_local_path, self.image_original_url, thumb=True)


class ShoppingListOut(BaseModel):
    id: int
    label: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ShoppingListItemOut]
    recipes: list[ShoppingListRecipeOut]
    needs_review: list[str]
