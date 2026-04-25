from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models import PantryItem, Recipe, RecipeIngredient, ShoppingList, ShoppingListItem, ShoppingListRecipe
from ...services.normalizer import normalize_unit
from ...schemas import (
    CartRecipeIn,
    ShoppingListCreateRequest,
    ShoppingListCustomItemIn,
    ShoppingListItemOut,
    ShoppingListItemPatch,
    ShoppingListOut,
    ShoppingListPatch,
    ShoppingListRecipeOut,
    ShoppingListSummaryOut,
)

router = APIRouter(prefix="/api", tags=["lists"])

_LIST_NOT_FOUND = "Shopping list not found"
_ITEM_NOT_FOUND = "Shopping list item not found"


def _parse_needs_review(blob: str | None) -> list[str]:
    if not blob:
        return []
    return [line for line in blob.split("\n") if line]


async def _aggregate_recipe_items(
    payload_items: list[CartRecipeIn],
    db: AsyncSession,
) -> tuple[list[dict], list[str]]:
    grouped: dict[tuple[str, str, str | None, str, int | None], dict] = {}
    needs_review: list[str] = []

    if not payload_items:
        return [], []

    recipe_ids = list({item.recipe_id for item in payload_items})
    recipes = (
        await db.scalars(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
            .where(Recipe.id.in_(recipe_ids))
        )
    ).all()
    recipes_by_id = {recipe.id: recipe for recipe in recipes}

    for payload in payload_items:
        recipe = recipes_by_id.get(payload.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe {payload.recipe_id} not found")

        multiplier = payload.target_servings / max(recipe.base_servings, 1)

        for link in recipe.recipe_ingredients:
            if link.needs_review or not link.ingredient:
                needs_review.append(f"{recipe.title}: {link.raw_string}")
                continue

            raw_qty = link.quantity * multiplier
            norm_unit, norm_qty = normalize_unit(link.unit, raw_qty)
            key = (
                link.ingredient.category,
                link.ingredient.name_en,
                link.ingredient.name_fr,
                norm_unit,
                link.ingredient.id,
            )
            if key not in grouped:
                grouped[key] = {
                    "category": link.ingredient.category,
                    "name": link.ingredient.name_en,
                    "name_fr": link.ingredient.name_fr,
                    "unit": norm_unit,
                    "quantity": 0.0,
                    "ingredient_id": link.ingredient.id,
                }
            grouped[key]["quantity"] += norm_qty

    aggregated_rows = sorted(
        (
            {
                **item,
                "quantity": round(item["quantity"], 2),
            }
            for item in grouped.values()
        ),
        key=lambda item: (item["category"], item["name"]),
    )
    return aggregated_rows, sorted(set(needs_review))


def _list_to_response(entity: ShoppingList) -> ShoppingListOut:
    return ShoppingListOut(
        id=entity.id,
        label=entity.label,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        items=[ShoppingListItemOut.model_validate(item) for item in sorted(entity.items, key=lambda i: i.sort_order)],
        recipes=[
            ShoppingListRecipeOut(
                recipe_id=link.recipe.id,
                title=link.recipe.title,
                url=link.recipe.url,
                source_domain=link.recipe.source_domain,
                image_local_path=link.recipe.image_local_path,
                target_servings=link.target_servings,
            )
            for link in sorted(entity.recipe_links, key=lambda i: i.id)
            if link.recipe
        ],
        needs_review=_parse_needs_review(entity.needs_review_blob),
    )


@router.post("/lists", response_model=ShoppingListOut)
async def create_shopping_list(payload: ShoppingListCreateRequest, db: AsyncSession = Depends(get_db)):
    aggregated_items, needs_review = await _aggregate_recipe_items(payload.items, db)

    # Load pantry for auto-checking items already in stock
    pantry_items = (await db.scalars(select(PantryItem))).all()
    pantry_ingredient_ids: set[int] = {p.ingredient_id for p in pantry_items if p.ingredient_id is not None}
    pantry_names_lower: set[str] = {p.name.strip().lower() for p in pantry_items}

    shopping_list = ShoppingList(
        label=payload.label,
        needs_review_blob="\n".join(needs_review) if needs_review else None,
    )
    db.add(shopping_list)
    await db.flush()

    for item in payload.items:
        db.add(
            ShoppingListRecipe(
                shopping_list_id=shopping_list.id,
                recipe_id=item.recipe_id,
                target_servings=item.target_servings,
            )
        )

    sort_order = 0
    for row in aggregated_items:
        in_pantry = (
            (row["ingredient_id"] is not None and row["ingredient_id"] in pantry_ingredient_ids)
            or row["name"].strip().lower() in pantry_names_lower
        )
        db.add(
            ShoppingListItem(
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
            )
        )
        sort_order += 1

    for extra in payload.extra_items:
        db.add(
            ShoppingListItem(
                shopping_list_id=shopping_list.id,
                name=extra.name.strip(),
                name_fr=extra.name_fr.strip() if extra.name_fr else None,
                quantity=round(extra.quantity, 2),
                unit=extra.unit.strip(),
                category=extra.category.strip(),
                is_custom=True,
                is_already_owned=False,
                sort_order=sort_order,
            )
        )
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
    if not entity:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)
    return _list_to_response(entity)


@router.get("/lists", response_model=list[ShoppingListSummaryOut])
async def list_shopping_lists(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    entities = (
        await db.scalars(
            select(ShoppingList)
            .options(selectinload(ShoppingList.items))
            .order_by(ShoppingList.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()

    return [
        ShoppingListSummaryOut(
            id=item.id,
            label=item.label,
            created_at=item.created_at,
            total_items=len(item.items),
            already_owned_items=sum(1 for entry in item.items if entry.is_already_owned),
        )
        for item in entities
    ]


@router.get("/lists/{list_id}", response_model=ShoppingListOut)
async def get_shopping_list(list_id: int, db: AsyncSession = Depends(get_db)):
    entity = await db.scalar(
        select(ShoppingList)
        .options(
            selectinload(ShoppingList.items),
            selectinload(ShoppingList.recipe_links).selectinload(ShoppingListRecipe.recipe),
        )
        .where(ShoppingList.id == list_id)
    )
    if not entity:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)
    return _list_to_response(entity)


@router.patch("/lists/{list_id}", response_model=ShoppingListOut)
async def patch_shopping_list(
    list_id: int,
    payload: ShoppingListPatch,
    db: AsyncSession = Depends(get_db),
):
    entity = await db.scalar(
        select(ShoppingList)
        .options(
            selectinload(ShoppingList.items),
            selectinload(ShoppingList.recipe_links).selectinload(ShoppingListRecipe.recipe),
        )
        .where(ShoppingList.id == list_id)
    )
    if not entity:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)

    cleaned_label = payload.label.strip() if payload.label else None
    entity.label = cleaned_label if cleaned_label else None
    await db.commit()

    # Re-query with eager loading instead of refresh — db.refresh() expires
    # lazy relationships which cannot be loaded in an async context.
    entity = await db.scalar(
        select(ShoppingList)
        .options(
            selectinload(ShoppingList.items),
            selectinload(ShoppingList.recipe_links).selectinload(ShoppingListRecipe.recipe),
        )
        .where(ShoppingList.id == list_id)
    )
    if not entity:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)
    return _list_to_response(entity)


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_list(list_id: int, db: AsyncSession = Depends(get_db)):
    entity = await db.scalar(select(ShoppingList).where(ShoppingList.id == list_id))
    if not entity:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)

    await db.delete(entity)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/lists/{list_id}/items/{item_id}", response_model=ShoppingListItemOut)
async def patch_shopping_list_item(
    list_id: int,
    item_id: int,
    payload: ShoppingListItemPatch,
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(
        select(ShoppingListItem).where(
            ShoppingListItem.id == item_id,
            ShoppingListItem.shopping_list_id == list_id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail=_ITEM_NOT_FOUND)

    item.is_already_owned = payload.is_already_owned
    await db.commit()
    await db.refresh(item)
    return ShoppingListItemOut.model_validate(item)


@router.delete("/lists/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_list_item(
    list_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(
        select(ShoppingListItem).where(
            ShoppingListItem.id == item_id,
            ShoppingListItem.shopping_list_id == list_id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail=_ITEM_NOT_FOUND)
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/lists/{list_id}/items", response_model=ShoppingListItemOut)
async def add_custom_shopping_list_item(
    list_id: int,
    payload: ShoppingListCustomItemIn,
    db: AsyncSession = Depends(get_db),
):
    exists = await db.scalar(select(ShoppingList.id).where(ShoppingList.id == list_id))
    if not exists:
        raise HTTPException(status_code=404, detail=_LIST_NOT_FOUND)

    current_max = await db.scalar(
        select(func.max(ShoppingListItem.sort_order)).where(ShoppingListItem.shopping_list_id == list_id)
    )
    sort_order = int(current_max or 0) + 1

    item = ShoppingListItem(
        shopping_list_id=list_id,
        name=payload.name.strip(),
        name_fr=payload.name_fr.strip() if payload.name_fr else None,
        quantity=round(payload.quantity, 2),
        unit=payload.unit.strip(),
        category=payload.category.strip(),
        is_custom=True,
        is_already_owned=False,
        sort_order=sort_order,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ShoppingListItemOut.model_validate(item)
