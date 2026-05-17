from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import MealPlan, MealPlanEntry, PantryItem, Recipe, ShoppingList, ShoppingListItem, ShoppingListRecipe
from ...schemas import (
    CartRecipeIn,
    MealPlanCreate,
    MealPlanEntryCreate,
    MealPlanEntryOut,
    MealPlanEntryPatch,
    MealPlanOut,
    MealPlanPatch,
    MealPlanSummaryOut,
    ShoppingListOut,
)
from ...services.images import resolve_image_url as _resolve_image_url
from ..dependencies import require_auth
from ...services.auth import UserClaims

router = APIRouter(prefix="/api", tags=["meal-plans"])

_NOT_FOUND = "Meal plan not found"
_ENTRY_NOT_FOUND = "Meal plan entry not found"

_DAY_NAMES = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _entry_to_out(entry: MealPlanEntry) -> MealPlanEntryOut:
    recipe = entry.recipe
    return MealPlanEntryOut(
        id=entry.id,
        recipe_id=entry.recipe_id,
        recipe_title=recipe.title if recipe else "",
        recipe_image_url=_resolve_image_url(
            recipe.image_local_path if recipe else None,
            recipe.image_original_url if recipe else None,
            thumb=True,
        ),
        day_of_week=entry.day_of_week,
        meal_slot=entry.meal_slot,
        target_servings=entry.target_servings,
    )


def _plan_to_out(plan: MealPlan) -> MealPlanOut:
    return MealPlanOut(
        id=plan.id,
        label=plan.label,
        week_start_date=plan.week_start_date,
        created_at=plan.created_at,
        entries=[_entry_to_out(e) for e in sorted(plan.entries, key=lambda e: (e.day_of_week, e.id))],
    )


@router.get("/meal-plans", response_model=list[MealPlanSummaryOut])
async def list_meal_plans(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plans = (
        await db.scalars(
            select(MealPlan)
            .options(selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe))
            .where(MealPlan.user_id == claims.user_id)
            .order_by(MealPlan.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    result = []
    for p in plans:
        seen: set[int] = set()
        images: list[str | None] = []
        for e in sorted(p.entries, key=lambda e: (e.day_of_week, e.id)):
            if e.recipe_id not in seen and len(images) < 4:
                seen.add(e.recipe_id)
                images.append(_resolve_image_url(
                    e.recipe.image_local_path if e.recipe else None,
                    e.recipe.image_original_url if e.recipe else None,
                    thumb=True,
                ))
        result.append(
            MealPlanSummaryOut(
                id=p.id,
                label=p.label,
                week_start_date=p.week_start_date,
                created_at=p.created_at,
                entry_count=len(p.entries),
                preview_images=images,
            )
        )
    return result


@router.post("/meal-plans", response_model=MealPlanOut, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    payload: MealPlanCreate,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = MealPlan(user_id=claims.user_id, label=payload.label, week_start_date=payload.week_start_date)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    plan = await db.scalar(
        select(MealPlan).options(selectinload(MealPlan.entries)).where(MealPlan.id == plan.id)
    )
    return _plan_to_out(plan)


@router.get("/meal-plans/{plan_id}", response_model=MealPlanOut)
async def get_meal_plan(
    plan_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(MealPlan)
        .options(selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe))
        .where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return _plan_to_out(plan)


@router.delete("/meal-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    await db.delete(plan)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/meal-plans/{plan_id}", response_model=MealPlanOut)
async def patch_meal_plan(
    plan_id: int,
    payload: MealPlanPatch,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(MealPlan)
        .options(selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe))
        .where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    plan.label = payload.label
    await db.commit()
    plan = await db.scalar(
        select(MealPlan)
        .options(selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe))
        .where(MealPlan.id == plan_id)
    )
    return _plan_to_out(plan)


@router.post("/meal-plans/{plan_id}/entries", response_model=MealPlanEntryOut, status_code=status.HTTP_201_CREATED)
async def add_meal_plan_entry(
    plan_id: int,
    payload: MealPlanEntryCreate,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    recipe = await db.get(Recipe, payload.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    entry = MealPlanEntry(
        meal_plan_id=plan_id,
        recipe_id=payload.recipe_id,
        day_of_week=payload.day_of_week,
        meal_slot=payload.meal_slot,
        target_servings=payload.target_servings,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    entry = await db.scalar(
        select(MealPlanEntry)
        .options(selectinload(MealPlanEntry.recipe))
        .where(MealPlanEntry.id == entry.id)
    )
    return _entry_to_out(entry)


@router.delete("/meal-plans/{plan_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan_entry(
    plan_id: int,
    entry_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Verify plan belongs to user first
    plan_exists = await db.scalar(
        select(MealPlan.id).where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan_exists:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    entry = await db.scalar(
        select(MealPlanEntry).where(
            MealPlanEntry.id == entry_id,
            MealPlanEntry.meal_plan_id == plan_id,
        )
    )
    if not entry:
        raise HTTPException(status_code=404, detail=_ENTRY_NOT_FOUND)
    await db.delete(entry)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/meal-plans/{plan_id}/entries/{entry_id}", response_model=MealPlanEntryOut)
async def patch_meal_plan_entry(
    plan_id: int,
    entry_id: int,
    payload: MealPlanEntryPatch,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Verify plan belongs to user first
    plan_exists = await db.scalar(
        select(MealPlan.id).where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan_exists:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    entry = await db.scalar(
        select(MealPlanEntry)
        .options(selectinload(MealPlanEntry.recipe))
        .where(MealPlanEntry.id == entry_id, MealPlanEntry.meal_plan_id == plan_id)
    )
    if not entry:
        raise HTTPException(status_code=404, detail=_ENTRY_NOT_FOUND)
    entry.target_servings = payload.target_servings
    await db.commit()
    await db.refresh(entry)
    entry = await db.scalar(
        select(MealPlanEntry)
        .options(selectinload(MealPlanEntry.recipe))
        .where(MealPlanEntry.id == entry_id)
    )
    return _entry_to_out(entry)


@router.post("/meal-plans/{plan_id}/generate-list", response_model=ShoppingListOut)
async def generate_list_from_meal_plan(
    plan_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.scalar(
        select(MealPlan)
        .options(selectinload(MealPlan.entries).selectinload(MealPlanEntry.recipe))
        .where(MealPlan.id == plan_id, MealPlan.user_id == claims.user_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if not plan.entries:
        raise HTTPException(status_code=400, detail="Meal plan has no entries")

    # Build CartRecipeIn items from entries
    cart_items = [
        CartRecipeIn(recipe_id=e.recipe_id, target_servings=e.target_servings)
        for e in plan.entries
    ]

    # Reuse list creation logic
    from ...api.routers.lists import _aggregate_recipe_items
    from ...services.normalizer import normalize_unit

    aggregated_items, needs_review = await _aggregate_recipe_items(cart_items, db)

    # Load current user's pantry for auto-checking items already in stock
    pantry_items_db = (await db.scalars(
        select(PantryItem).where(PantryItem.user_id == claims.user_id)
    )).all()
    pantry_ingredient_ids: set[int] = {p.ingredient_id for p in pantry_items_db if p.ingredient_id is not None}
    pantry_names_lower: set[str] = {p.name.strip().lower() for p in pantry_items_db}

    week_label = None
    if plan.week_start_date:
        week_end = plan.week_start_date + timedelta(days=6)
        week_label = f"Semaine {plan.week_start_date.strftime('%d/%m')}–{week_end.strftime('%d/%m')}"
    label = plan.label or week_label or f"Plan repas #{plan_id}"

    shopping_list = ShoppingList(
        user_id=claims.user_id,
        label=label,
        needs_review_blob="\n".join(needs_review) if needs_review else None,
    )
    db.add(shopping_list)
    await db.flush()

    # Add recipe links (deduplicated by recipe_id, sum servings)
    seen_recipes: dict[int, int] = {}
    for entry in plan.entries:
        seen_recipes[entry.recipe_id] = seen_recipes.get(entry.recipe_id, 0) + entry.target_servings
    for recipe_id, total_servings in seen_recipes.items():
        db.add(ShoppingListRecipe(
            shopping_list_id=shopping_list.id,
            recipe_id=recipe_id,
            target_servings=total_servings,
        ))

    sort_order = 0
    for row in aggregated_items:
        in_pantry = (
            (row["ingredient_id"] is not None and row["ingredient_id"] in pantry_ingredient_ids)
            or row["name"].strip().lower() in pantry_names_lower
        )
        db.add(ShoppingListItem(
            shopping_list_id=shopping_list.id,
            ingredient_id=row["ingredient_id"],
            name=row["name"],
            name_fr=row["name_fr"],
            quantity=row["quantity"],
            unit=row["unit"],
            category=row["category"],
            is_custom=False,
            is_already_owned=in_pantry,
            sort_order=sort_order,
        ))
        sort_order += 1

    await db.commit()

    entity = await db.scalar(
        select(ShoppingList)
        .options(
            selectinload(ShoppingList.items),
            selectinload(ShoppingList.recipe_links).selectinload(ShoppingListRecipe.recipe),
        )
        .where(ShoppingList.id == shopping_list.id)
    )

    from ...api.routers.lists import _list_to_response
    return _list_to_response(entity)
