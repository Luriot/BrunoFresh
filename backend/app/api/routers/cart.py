from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...schemas import CartGroupItem, CartRequest, CartResponse
from ...services.aggregator import aggregate_recipe_ingredients

router = APIRouter(prefix="/api", tags=["cart"])


@router.post("/cart/generate", response_model=CartResponse)
async def generate_cart(payload: CartRequest, db: AsyncSession = Depends(get_db)):
    rows, needs_review = await aggregate_recipe_ingredients(payload.items, db)

    response_grouped: dict[str, list[CartGroupItem]] = {}
    for row in rows:
        category = row["category"]
        if category not in response_grouped:
            response_grouped[category] = []
        response_grouped[category].append(
            CartGroupItem(name=row["name"], quantity=row["quantity"], unit=row["unit"])
        )

    return CartResponse(grouped=response_grouped, needs_review=needs_review)
