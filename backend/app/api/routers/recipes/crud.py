"""CRUD endpoints: list, get, create, patch, delete recipes."""
from __future__ import annotations

import uuid
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....database import get_db
from ....models import Ingredient, Recipe, RecipeIngredient, Tag, User, UserFavorite
from ....models import recipe_tags as recipe_tags_table
from ....schemas import (
    RecipeCreate,
    RecipeDetail,
    RecipeListItem,
    RecipePatch,
)
from ....schemas.recipes import RecommenderOut
from ....services.auth import UserClaims
from ...dependencies import require_auth
from .utils import _RECIPE_NOT_FOUND, _escape_like, _recipe_detail_opts, _recipe_to_detail

router = APIRouter()


async def _load_favorites_data(
    recipe_ids: list[int],
    user_id: int,
    db: AsyncSession,
) -> tuple[set[int], dict[int, list[RecommenderOut]]]:
    """Return (user_fav_set, recommenders_map) for the given recipe_ids."""
    if not recipe_ids:
        return set(), {}

    rows = (
        await db.execute(
            select(UserFavorite.recipe_id, UserFavorite.user_id, User.username, User.avatar_url)
            .join(User, UserFavorite.user_id == User.id)
            .where(UserFavorite.recipe_id.in_(recipe_ids))
        )
    ).all()

    user_fav_set: set[int] = set()
    recommenders_map: dict[int, list[RecommenderOut]] = defaultdict(list)
    for row in rows:
        if row.user_id == user_id:
            user_fav_set.add(row.recipe_id)
        recommenders_map[row.recipe_id].append(
            RecommenderOut(username=row.username, avatar_url=row.avatar_url)
        )

    return user_fav_set, dict(recommenders_map)


def _build_list_item(
    r: Recipe,
    user_fav_set: set[int],
    recommenders_map: dict[int, list[RecommenderOut]],
) -> RecipeListItem:
    from ....schemas import TagOut  # local to avoid circular import
    return RecipeListItem(
        id=r.id,
        title=r.title,
        url=r.url,
        source_domain=r.source_domain,
        image_local_path=r.image_local_path,
        image_original_url=r.image_original_url,
        base_servings=r.base_servings,
        prep_time_minutes=r.prep_time_minutes,
        is_favorite_by_me=r.id in user_fav_set,
        recommenders=recommenders_map.get(r.id, []),
        tags=[TagOut.model_validate(t) for t in r.tags],
    )


@router.get("/recipes", response_model=list[RecipeListItem])
async def list_recipes(
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    is_favorite: bool | None = Query(default=None),
    ingredients: str | None = Query(default=None, description="Comma-separated ingredient keywords"),
    tags: str | None = Query(default=None, description="Comma-separated tag names (any match)"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe).options(selectinload(Recipe.tags))

    if q:
        q_safe = _escape_like(q)
        ingredient_recipe_ids = select(RecipeIngredient.recipe_id).join(
            Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).where(
            Ingredient.name_en.ilike(f"%{q_safe}%", escape="\\") | Ingredient.name_fr.ilike(f"%{q_safe}%", escape="\\")
        )
        stmt = stmt.where(Recipe.title.ilike(f"%{q_safe}%", escape="\\") | Recipe.id.in_(ingredient_recipe_ids))

    if source:
        stmt = stmt.where(Recipe.source_domain == source)

    if is_favorite is not None and is_favorite:
        fav_subq = select(UserFavorite.recipe_id).where(UserFavorite.user_id == claims.user_id)
        stmt = stmt.where(Recipe.id.in_(fav_subq))

    if ingredients:
        keywords = [kw.strip() for kw in ingredients.split(",") if kw.strip()]
        for kw in keywords:
            kw_safe = _escape_like(kw)
            subq = select(RecipeIngredient.recipe_id).join(
                Ingredient, RecipeIngredient.ingredient_id == Ingredient.id
            ).where(
                Ingredient.name_en.ilike(f"%{kw_safe}%", escape="\\") | Ingredient.name_fr.ilike(f"%{kw_safe}%", escape="\\")
            )
            stmt = stmt.where(Recipe.id.in_(subq))

    if tags:
        raw_parts = [t.strip() for t in tags.split(",") if t.strip()]
        # Frontend sends numeric IDs; fall back to name-based matching if not numeric
        if all(p.lstrip("-").isdigit() for p in raw_parts):
            tag_ids = [int(p) for p in raw_parts]
            tag_subq = (
                select(recipe_tags_table.c.recipe_id)
                .where(recipe_tags_table.c.tag_id.in_(tag_ids))
            )
        else:
            tag_subq = (
                select(recipe_tags_table.c.recipe_id)
                .join(Tag, recipe_tags_table.c.tag_id == Tag.id)
                .where(Tag.name.in_(raw_parts))
            )
        stmt = stmt.where(Recipe.id.in_(tag_subq))

    recipes = (await db.scalars(
        stmt.order_by(func.lower(Recipe.title).asc()).offset(offset).limit(limit)
    )).all()

    recipe_ids = [r.id for r in recipes]
    user_fav_set, recommenders_map = await _load_favorites_data(recipe_ids, claims.user_id, db)
    return [_build_list_item(r, user_fav_set, recommenders_map) for r in recipes]


@router.get("/recipes/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(
    recipe_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    user_fav_set, recommenders_map = await _load_favorites_data([recipe_id], claims.user_id, db)
    return _recipe_to_detail(
        recipe,
        is_favorite_by_me=recipe_id in user_fav_set,
        recommenders=recommenders_map.get(recipe_id, []),
        language=claims.language,
    )


@router.post("/recipes", response_model=RecipeDetail)
async def create_custom_recipe(
    payload: RecipeCreate,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    unique_url = f"custom://recipe-{uuid.uuid4()}"
    new_recipe = Recipe(
        title=payload.title,
        url=unique_url,
        source_domain="custom",
        instructions_text=payload.instructions_text,
        base_servings=payload.base_servings,
        prep_time_minutes=payload.prep_time_minutes,
    )
    db.add(new_recipe)

    for ing_in in payload.ingredients:
        ing_obj = await db.scalar(select(Ingredient).where(Ingredient.name_en == ing_in.ingredient_name))
        if not ing_obj:
            ing_obj = Ingredient(
                name_en=ing_in.ingredient_name,
                name_fr=ing_in.ingredient_name_fr,
                category=ing_in.category or "Other",
            )
            db.add(ing_obj)
            await db.flush()

        link = RecipeIngredient(
            recipe=new_recipe,
            ingredient=ing_obj,
            raw_string=ing_in.raw_string,
            quantity=ing_in.quantity,
            unit=ing_in.unit,
        )
        db.add(link)

    await db.commit()

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == new_recipe.id)
    )
    if not recipe:
        raise HTTPException(status_code=500, detail="Failed to retrieve created recipe")
    return _recipe_to_detail(recipe, language=claims.language)


# ── Recipe image upload ───────────────────────────────────────────────────────

_IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_IMAGE_ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _check_image_magic(data: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return data[:3] == b"\xff\xd8\xff"
    if content_type == "image/png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


@router.post("/recipes/{recipe_id}/image", response_model=RecipeDetail)
async def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    from ....config import settings

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _IMAGE_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported image type. Use JPEG, PNG, or WebP.",
        )

    data = await file.read(_IMAGE_MAX_BYTES + 1)
    if len(data) > _IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (max 10 MB).",
        )

    if not _check_image_magic(data, content_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content does not match declared type.",
        )

    ext = _IMAGE_ALLOWED[content_type]
    filename = f"recipe_{recipe_id}.webp"  # always WebP for consistent storage
    dest = settings.images_dir / filename

    # Remove any previously stored image and its thumbnail (extension may differ)
    if recipe.image_local_path:
        from ....services.images import thumb_path_for  # noqa: PLC0415
        old_file = settings.images_dir / Path(recipe.image_local_path).name
        thumb_path_for(old_file).unlink(missing_ok=True)
        old_file.unlink(missing_ok=True)

    dest.write_bytes(data)

    import asyncio  # noqa: PLC0415
    from ....services.images import process_uploaded_image  # noqa: PLC0415
    await asyncio.get_running_loop().run_in_executor(None, process_uploaded_image, dest)

    recipe.image_local_path = f"images/{filename}"
    await db.commit()

    updated = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated recipe")
    return _recipe_to_detail(updated, language=claims.language)


@router.patch("/recipes/{recipe_id}", response_model=RecipeDetail)
async def patch_recipe(
    recipe_id: int,
    payload: RecipePatch,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    if payload.instructions_text is not None:
        recipe.instructions_text = payload.instructions_text
    if payload.prep_time_minutes is not None:
        recipe.prep_time_minutes = payload.prep_time_minutes
    await db.commit()

    recipe = await db.scalar(
        select(Recipe).options(*_recipe_detail_opts()).where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    user_fav_set, recommenders_map = await _load_favorites_data([recipe_id], claims.user_id, db)
    return _recipe_to_detail(
        recipe,
        is_favorite_by_me=recipe_id in user_fav_set,
        recommenders=recommenders_map.get(recipe_id, []),
        language=claims.language,
    )


@router.post("/recipes/{recipe_id}/favorite", response_model=dict)
async def toggle_favorite(
    recipe_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    recipe = await db.scalar(select(Recipe.id).where(Recipe.id == recipe_id))
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)

    existing = await db.scalar(
        select(UserFavorite).where(
            UserFavorite.user_id == claims.user_id,
            UserFavorite.recipe_id == recipe_id,
        )
    )
    if existing:
        await db.delete(existing)
        is_favorite_by_me = False
    else:
        db.add(UserFavorite(user_id=claims.user_id, recipe_id=recipe_id))
        is_favorite_by_me = True

    await db.commit()
    return {"is_favorite_by_me": is_favorite_by_me}


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: int,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=404, detail=_RECIPE_NOT_FOUND)
    await db.delete(recipe)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

