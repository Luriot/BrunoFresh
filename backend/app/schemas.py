from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RecipeIngredientCreate(BaseModel):
    raw_string: str = Field(min_length=1, max_length=400)
    quantity: float = Field(default=1, ge=0)
    unit: str = Field(default="item", max_length=30)
    ingredient_name: str = Field(min_length=1, max_length=200)
    ingredient_name_fr: str | None = Field(default=None, max_length=200)
    category: str = Field(default="Other", max_length=80)


class RecipeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    instructions_text: str = Field(default="", max_length=50_000)
    base_servings: int = Field(default=2, ge=1, le=100)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=1440)
    ingredients: list[RecipeIngredientCreate] = Field(default_factory=list, max_length=100)


class RecipeListItem(BaseModel):
    id: int
    title: str
    url: str
    source_domain: str
    image_local_path: str | None
    base_servings: int
    prep_time_minutes: int | None
    is_favorite: bool = False
    tags: list["TagOut"] = []

    model_config = ConfigDict(from_attributes=True)


class IngredientOut(BaseModel):
    name: str
    name_fr: str | None = None
    quantity: float
    unit: str
    category: str


class RecipeIngredientOut(BaseModel):
    raw_string: str
    quantity: float
    unit: str
    needs_review: bool
    ingredient_name: str | None = None
    ingredient_name_fr: str | None = None
    category: str | None = None


class InstructionStep(BaseModel):
    text: str
    image_url: str | None = None


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
    is_favorite: bool = False
    tags: list["TagOut"] = []
    ingredients: list[RecipeIngredientOut]
    instruction_steps: list[InstructionStep] = []


class ScrapeRequest(BaseModel):
    url: HttpUrl
    force: bool = False


JobStatus = Literal["pending", "running", "completed", "failed", "duplicate_warning"]


class DuplicateWarningInfo(BaseModel):
    id: int
    title: str
    url: str
    image_local_path: str | None = None
    title_score: float
    ingredient_score: float


class ScrapeResponse(BaseModel):
    message: str
    url: str
    job_id: int | None = None
    status: JobStatus
    similar_recipe: DuplicateWarningInfo | None = None


class RecipeSimilarPair(BaseModel):
    recipe_a_id: int
    recipe_a_title: str
    recipe_a_url: str
    recipe_a_image: str | None = None
    recipe_b_id: int
    recipe_b_title: str
    recipe_b_url: str
    recipe_b_image: str | None = None
    title_score: float
    ingredient_score: float


class RecipeSimilarPairsResponse(BaseModel):
    pairs: list[RecipeSimilarPair]


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


class ShoppingListItemOut(BaseModel):
    id: int
    name: str
    name_fr: str | None = None
    quantity: float
    unit: str
    category: str
    is_custom: bool
    is_already_owned: bool
    is_excluded: bool = False

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
    image_local_path: str | None
    target_servings: int


class ShoppingListOut(BaseModel):
    id: int
    label: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ShoppingListItemOut]
    recipes: list[ShoppingListRecipeOut]
    needs_review: list[str]


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


# ── Merge suggestions ────────────────────────────────────────────────────────

class MergeSuggestion(BaseModel):
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    reason: str


class MergeSuggestionResponse(BaseModel):
    suggestions: list[MergeSuggestion]


# ── Tags ────────────────────────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=30)


class TagOut(BaseModel):
    id: int
    name: str
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RecipeTagsUpdate(BaseModel):
    tag_ids: list[int]


# ── Favorites ───────────────────────────────────────────────────────────────

class RecipePatch(BaseModel):
    is_favorite: bool | None = None
    instructions_text: str | None = Field(default=None, max_length=50_000)


# ── Pantry ──────────────────────────────────────────────────────────────────

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
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Stats ───────────────────────────────────────────────────────────────────

class RecipeSourceStat(BaseModel):
    source_domain: str
    count: int


class TopRecipeStat(BaseModel):
    recipe_id: int
    title: str
    appearance_count: int


class TopIngredientStat(BaseModel):
    name: str
    count: int


class StatsOut(BaseModel):
    total_recipes: int
    total_lists: int
    recipes_by_source: list[RecipeSourceStat]
    top_recipes_in_lists: list[TopRecipeStat]
    top_ingredients: list[TopIngredientStat]


# ── Ingredient admin ────────────────────────────────────────────────────────

class IngredientMergeRequest(BaseModel):
    source_id: int
    target_id: int


# ── Meal Planner ────────────────────────────────────────────────────────────

class MealPlanCreate(BaseModel):
    label: str | None = Field(default=None, max_length=160)
    week_start_date: date | None = None


class MealPlanEntryCreate(BaseModel):
    recipe_id: int
    day_of_week: int = Field(ge=0, le=6)
    meal_slot: str | None = Field(default=None, max_length=40)
    target_servings: int = Field(default=2, ge=1, le=20)


class MealPlanEntryOut(BaseModel):
    id: int
    recipe_id: int
    recipe_title: str
    recipe_image_local_path: str | None
    day_of_week: int
    meal_slot: str | None
    target_servings: int

    model_config = ConfigDict(from_attributes=True)


class MealPlanOut(BaseModel):
    id: int
    label: str | None
    week_start_date: date | None
    created_at: datetime
    entries: list[MealPlanEntryOut]

    model_config = ConfigDict(from_attributes=True)


class MealPlanSummaryOut(BaseModel):
    id: int
    label: str | None
    week_start_date: date | None
    created_at: datetime
    entry_count: int
    preview_images: list[str | None] = []


class MealPlanPatch(BaseModel):
    label: str | None = Field(default=None, max_length=120)


class MealPlanEntryPatch(BaseModel):
    target_servings: int = Field(ge=1, le=20)
