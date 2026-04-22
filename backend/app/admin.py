from __future__ import annotations

from fastapi import FastAPI
from starlette.requests import Request
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from .config import settings
from .database import engine
from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    ScrapeJob,
    ShoppingList,
    ShoppingListItem,
    ShoppingListRecipe,
)
from .services.auth import verify_passcode


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str):
        super().__init__(secret_key=secret_key)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))

        if username != settings.admin_username:
            return False
        if not verify_passcode(password):
            return False

        request.session.update({"admin": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin"))


class RecipeAdmin(ModelView, model=Recipe):
    column_list = [Recipe.id, Recipe.title, Recipe.source_domain, Recipe.base_servings]
    column_searchable_list = [Recipe.title, Recipe.url]


class IngredientAdmin(ModelView, model=Ingredient):
    column_list = [Ingredient.id, Ingredient.name_en, Ingredient.name_fr, Ingredient.category, Ingredient.is_normalized]
    column_searchable_list = [Ingredient.name_en]


class RecipeIngredientAdmin(ModelView, model=RecipeIngredient):
    column_list = [
        RecipeIngredient.id,
        RecipeIngredient.recipe_id,
        RecipeIngredient.ingredient_id,
        RecipeIngredient.raw_string,
        RecipeIngredient.quantity,
        RecipeIngredient.unit,
        RecipeIngredient.needs_review,
    ]


class ScrapeJobAdmin(ModelView, model=ScrapeJob):
    can_create = False
    column_list = [ScrapeJob.id, ScrapeJob.url, ScrapeJob.status, ScrapeJob.created_at]


class ShoppingListAdmin(ModelView, model=ShoppingList):
    column_list = [ShoppingList.id, ShoppingList.label, ShoppingList.created_at, ShoppingList.updated_at]


class ShoppingListItemAdmin(ModelView, model=ShoppingListItem):
    column_list = [
        ShoppingListItem.id,
        ShoppingListItem.shopping_list_id,
        ShoppingListItem.name,
        ShoppingListItem.name_fr,
        ShoppingListItem.quantity,
        ShoppingListItem.unit,
        ShoppingListItem.category,
        ShoppingListItem.is_custom,
        ShoppingListItem.is_already_owned,
    ]


class ShoppingListRecipeAdmin(ModelView, model=ShoppingListRecipe):
    column_list = [
        ShoppingListRecipe.id,
        ShoppingListRecipe.shopping_list_id,
        ShoppingListRecipe.recipe_id,
        ShoppingListRecipe.target_servings,
    ]


def setup_admin(app: FastAPI) -> None:
    authentication_backend = AdminAuth(secret_key=settings.auth_secret)
    admin = Admin(app, engine, authentication_backend=authentication_backend)
    admin.add_view(RecipeAdmin)
    admin.add_view(IngredientAdmin)
    admin.add_view(RecipeIngredientAdmin)
    admin.add_view(ScrapeJobAdmin)
    admin.add_view(ShoppingListAdmin)
    admin.add_view(ShoppingListItemAdmin)
    admin.add_view(ShoppingListRecipeAdmin)
