from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models import Recipe, RecipeIngredient
from ...schemas import CartGroupItem, CartRequest, CartResponse
from ...services.normalizer import culinary_to_grams, get_unit_group, normalize_unit, smart_display_unit, to_base_unit

router = APIRouter(prefix="/api", tags=["cart"])


@router.post("/cart/generate", response_model=CartResponse)
async def generate_cart(payload: CartRequest, db: AsyncSession = Depends(get_db)):
    grouped: dict[str, dict[tuple[str, str, str], float]] = defaultdict(lambda: defaultdict(float))
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

            raw_qty = link.quantity * multiplier
            norm_unit, norm_qty = normalize_unit(link.unit, raw_qty)
            # Ingredient-specific density conversion: c. à soupe / c. à thé / tasse → g
            density_result = culinary_to_grams(link.ingredient.name_en, norm_unit, norm_qty)
            if density_result:
                norm_unit, norm_qty = density_result
            # Convert to base unit so g + kg, ml + L, etc. merge into a single row
            base_unit, base_qty = to_base_unit(norm_unit, norm_qty)
            agg_unit = get_unit_group(norm_unit) or norm_unit
            category = link.ingredient.category
            key = (link.ingredient.name_en, agg_unit, base_unit)
            grouped[category][key] += base_qty

    response_grouped: dict[str, list[CartGroupItem]] = {}
    for category, values in grouped.items():
        items: list[CartGroupItem] = []
        for (name, _agg_unit, base_unit), total_base_qty in sorted(values.items(), key=lambda kv: kv[0][0]):
            display_unit, display_qty = smart_display_unit(base_unit, round(total_base_qty, 2))
            items.append(CartGroupItem(name=name, quantity=display_qty, unit=display_unit))
        response_grouped[category] = items

    return CartResponse(grouped=response_grouped, needs_review=sorted(set(needs_review)))
