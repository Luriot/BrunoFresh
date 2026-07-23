"""
Backward-compatible barrel export.

All existing `from app.schemas import SomeClass` imports continue to work
without any changes in the rest of the codebase.
"""
from .tags import TagCreate, TagOut
from .users import UserOut, UserPatch, LanguagePatch
from .auth import LoginRequest, AuthStatusResponse
from .admin import ImageRetryResult, BulkImageRetryResult, ConvertImagesResult
from .recipes import (
    NutritionFields,
    BilingualNamedItem,
    RecipeBase,
    RecipeIngredientCreate,
    RecipeCreate,
    RecipePatch,
    RecipeIngredientOut,
    InstructionStep,
    RecommenderOut,
    RecipeListItem,
    RecipeDetail,
    RecipeTagsUpdate,
)
from .scrape import (
    HFSearchResultResponse,
    ScrapeRequest,
    JobStatus,
    DuplicateWarningInfo,
    ScrapeResponse,
    RecipeSimilarPair,
    RecipeSimilarPairsResponse,
    JobStatusResponse,
)
from .shopping import (
    CartRecipeIn,
    CartRequest,
    CartGroupItem,
    CartResponse,
    ShoppingListCustomItemIn,
    ShoppingListCreateRequest,
    ShoppingListItemPatch,
    ShoppingListPatch,
    ShoppingListItemOut,
    ShoppingListSummaryOut,
    ShoppingListRecipeOut,
    ShoppingListOut,
)
from .ingredients import (
    IngredientNamePatch,
    IngredientDetail,
    MergeSuggestion,
    MergeSuggestionResponse,
    IngredientMergeRequest,
)
from .pantry import PantryItemCreate, PantryItemOut
from .stats import RecipeSourceStat, TopRecipeStat, TopIngredientStat, StatsOut
from .meal_plans import (
    MealPlanCreate,
    MealPlanEntryCreate,
    MealPlanEntryOut,
    MealPlanOut,
    MealPlanSummaryOut,
    MealPlanPatch,
    MealPlanEntryPatch,
    MealPlanQuickGenerateIn,
)

__all__ = [
    "TagCreate", "TagOut",
    "UserOut", "UserPatch", "LanguagePatch",
    "LoginRequest", "AuthStatusResponse",
    "ImageRetryResult", "BulkImageRetryResult", "ConvertImagesResult",
    "NutritionFields", "BilingualNamedItem", "RecipeBase",
    "RecipeIngredientCreate", "RecipeCreate", "RecipePatch",
    "RecipeIngredientOut", "InstructionStep",
    "RecommenderOut", "RecipeListItem", "RecipeDetail", "RecipeTagsUpdate",
    "HFSearchResultResponse", "ScrapeRequest", "JobStatus",
    "DuplicateWarningInfo", "ScrapeResponse",
    "RecipeSimilarPair", "RecipeSimilarPairsResponse", "JobStatusResponse",
    "CartRecipeIn", "CartRequest", "CartGroupItem", "CartResponse",
    "ShoppingListCustomItemIn", "ShoppingListCreateRequest",
    "ShoppingListItemPatch", "ShoppingListPatch",
    "ShoppingListItemOut", "ShoppingListSummaryOut",
    "ShoppingListRecipeOut", "ShoppingListOut",
    "IngredientNamePatch", "IngredientDetail",
    "MergeSuggestion", "MergeSuggestionResponse", "IngredientMergeRequest",
    "PantryItemCreate", "PantryItemOut",
    "RecipeSourceStat", "TopRecipeStat", "TopIngredientStat", "StatsOut",
    "MealPlanCreate", "MealPlanEntryCreate", "MealPlanEntryOut", "MealPlanOut",
    "MealPlanSummaryOut", "MealPlanPatch", "MealPlanEntryPatch", "MealPlanQuickGenerateIn",
]
