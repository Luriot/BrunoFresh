from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RecipeListItem(BaseModel):
    id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None
    base_servings: int

    model_config = ConfigDict(from_attributes=True)


class IngredientOut(BaseModel):
    name: str
    quantity: float
    unit: str
    category: str


class RecipeIngredientOut(BaseModel):
    raw_string: str
    quantity: float
    unit: str
    needs_review: bool
    ingredient_name: str | None = None
    category: str | None = None


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
    ingredients: list[RecipeIngredientOut]


class ScrapeRequest(BaseModel):
    url: HttpUrl


JobStatus = Literal["pending", "running", "completed", "failed"]


class ScrapeResponse(BaseModel):
    message: str
    url: str
    job_id: int | None = None
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: int
    status: JobStatus
    error_message: str | None = None


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
    quantity: float = Field(default=1, gt=0, le=9999)
    unit: str = Field(default="item", min_length=1, max_length=30)
    category: str = Field(default="Other", min_length=1, max_length=80)


class ShoppingListCreateRequest(BaseModel):
    items: list[CartRecipeIn]
    label: str | None = Field(default=None, max_length=160)
    extra_items: list[ShoppingListCustomItemIn] = Field(default_factory=list)


class ShoppingListItemPatch(BaseModel):
    is_already_owned: bool


class ShoppingListItemOut(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    category: str
    is_custom: bool
    is_already_owned: bool

    model_config = ConfigDict(from_attributes=True)


class ShoppingListSummaryOut(BaseModel):
    id: int
    label: str | None
    created_at: datetime
    total_items: int
    already_owned_items: int


class ShoppingListOut(BaseModel):
    id: int
    label: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ShoppingListItemOut]
    needs_review: list[str]


class IngredientPatch(BaseModel):
    name_en: str
    category: str
