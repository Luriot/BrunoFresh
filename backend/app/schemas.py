from pydantic import BaseModel, ConfigDict, Field


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
    url: str


class ScrapeResponse(BaseModel):
    message: str
    url: str


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


class IngredientPatch(BaseModel):
    name_en: str
    category: str
