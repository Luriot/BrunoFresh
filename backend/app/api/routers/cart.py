from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models import Recipe, RecipeIngredient
from ...schemas import CartGroupItem, CartRequest, CartResponse

router = APIRouter(prefix="/api", tags=["cart"])


@router.post("/cart/generate", response_model=CartResponse)
async def generate_cart(payload: CartRequest, db: AsyncSession = Depends(get_db)):
    grouped: dict[str, dict[tuple[str, str], float]] = defaultdict(lambda: defaultdict(float))
    needs_review: list[str] = []

    if not payload.items:
        return CartResponse(grouped={}, needs_review=[])

    recipe_ids = list({item.recipe_id for item in payload.items})
    recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
            .where(Recipe.id.in_(recipe_ids))
        )
    ).all()
    recipes_by_id = {recipe.id: recipe for recipe in recipes}

    for item in payload.items:
        recipe = recipes_by_id.get(item.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {item.recipe_id} not found")

        multiplier = item.target_servings / max(recipe.base_servings, 1)

        for link in recipe.recipe_ingredients:
            if link.needs_review or not link.ingredient:
                needs_review.append(f"{recipe.title}: {link.raw_string}")
                continue

            category = link.ingredient.category
            key = (link.ingredient.name_en, link.unit)
            grouped[category][key] += link.quantity * multiplier

    response_grouped: dict[str, list[CartGroupItem]] = {}
    for category, values in grouped.items():
        response_grouped[category] = [
            CartGroupItem(name=name, quantity=round(qty, 2), unit=unit)
            for (name, unit), qty in sorted(values.items(), key=lambda kv: kv[0][0])
        ]

    return CartResponse(grouped=response_grouped, needs_review=sorted(set(needs_review)))
