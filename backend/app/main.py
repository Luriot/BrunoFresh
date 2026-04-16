from collections import defaultdict

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import Ingredient, Recipe, RecipeIngredient
from .schemas import (
    CartGroupItem,
    CartRequest,
    CartResponse,
    IngredientPatch,
    RecipeDetail,
    RecipeIngredientOut,
    RecipeListItem,
    ScrapeRequest,
    ScrapeResponse,
)
from .services.dedupe import looks_like_duplicate
from .services.images import download_image
from .services.normalizer import normalize_ingredient
from .services.scraper import scrape_recipe_url


Base.metadata.create_all(bind=engine)

app = FastAPI(title="MealCart API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="data/images"), name="images")


def _ing_to_out(link: RecipeIngredient) -> RecipeIngredientOut:
    return RecipeIngredientOut(
        raw_string=link.raw_string,
        quantity=link.quantity,
        unit=link.unit,
        needs_review=link.needs_review,
        ingredient_name=link.ingredient.name_en if link.ingredient else None,
        category=link.ingredient.category if link.ingredient else None,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recipes", response_model=list[RecipeListItem])
def list_recipes(
    q: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Recipe)
    if q:
        stmt = stmt.where(Recipe.title.ilike(f"%{q}%"))
    if source:
        stmt = stmt.where(Recipe.source_domain == source)
    recipes = db.scalars(stmt.offset(offset).limit(limit)).all()
    return recipes


@app.get("/api/recipes/{recipe_id}", response_model=RecipeDetail)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.scalar(
        select(Recipe)
        .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
        .where(Recipe.id == recipe_id)
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeDetail(
        id=recipe.id,
        title=recipe.title,
        url=recipe.url,
        source_domain=recipe.source_domain,
        image_local_path=recipe.image_local_path,
        image_original_url=recipe.image_original_url,
        instructions_text=recipe.instructions_text,
        base_servings=recipe.base_servings,
        prep_time_minutes=recipe.prep_time_minutes,
        ingredients=[_ing_to_out(link) for link in recipe.recipe_ingredients],
    )


def _persist_scraped_recipe(url: str, db: Session):
    existing = db.scalar(select(Recipe).where(Recipe.url == url))
    if existing:
        return

    scraped = scrape_recipe_url(url)

    incoming_names: list[str] = []
    for ing in scraped.ingredients:
        normalized_probe = normalize_ingredient(ing.raw, ing.quantity, ing.unit)
        incoming_names.append(normalized_probe.name_en if normalized_probe else ing.raw)

    existing_recipes = db.scalars(
        select(Recipe).options(
            selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient)
        )
    ).all()
    for candidate in existing_recipes:
        candidate_names = [
            link.ingredient.name_en if link.ingredient else link.raw_string
            for link in candidate.recipe_ingredients
        ]
        if looks_like_duplicate(candidate.title, candidate_names, scraped.title, incoming_names):
            return

    recipe = Recipe(
        title=scraped.title,
        url=url,
        source_domain=scraped.source_domain,
        image_local_path=None,
        image_original_url=scraped.image_url,
        instructions_text=scraped.instructions_text,
        base_servings=scraped.base_servings,
        prep_time_minutes=scraped.prep_time_minutes,
    )
    db.add(recipe)
    db.flush()

    local_image_path = download_image(scraped.image_url, recipe.id)
    if local_image_path:
        recipe.image_local_path = local_image_path
    db.flush()

    for ing in scraped.ingredients:
        normalized = normalize_ingredient(ing.raw, ing.quantity, ing.unit)
        ingredient = None
        needs_review = False
        quantity = ing.quantity
        unit = ing.unit

        if normalized:
            ingredient = db.scalar(select(Ingredient).where(Ingredient.name_en == normalized.name_en))
            if not ingredient:
                ingredient = Ingredient(
                    name_en=normalized.name_en,
                    category=normalized.category,
                    is_normalized=True,
                )
                db.add(ingredient)
                db.flush()
            quantity = normalized.quantity
            unit = normalized.unit
        else:
            needs_review = True

        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id if ingredient else None,
                raw_string=ing.raw,
                quantity=quantity,
                unit=unit,
                needs_review=needs_review,
            )
        )

    db.commit()


@app.post("/api/scrape", response_model=ScrapeResponse)
def enqueue_scrape(
    payload: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Do immediate dedupe check for cleaner UX.
    existing = db.scalar(select(Recipe).where(Recipe.url == payload.url))
    if existing:
        return ScrapeResponse(message="Recipe already exists", url=payload.url)

    # SQLAlchemy session is not thread-safe; open a fresh session in worker.
    def _worker(target_url: str):
        from .database import SessionLocal

        worker_db = SessionLocal()
        try:
            _persist_scraped_recipe(target_url, worker_db)
        finally:
            worker_db.close()

    background_tasks.add_task(_worker, payload.url)
    return ScrapeResponse(message="Scrape job queued", url=payload.url)


@app.patch("/api/ingredients/{ingredient_id}")
def patch_ingredient(ingredient_id: int, payload: IngredientPatch, db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    ingredient.name_en = payload.name_en
    ingredient.category = payload.category
    ingredient.is_normalized = True
    db.commit()
    return {"status": "updated"}


@app.post("/api/cart/generate", response_model=CartResponse)
def generate_cart(payload: CartRequest, db: Session = Depends(get_db)):
    grouped: dict[str, dict[tuple[str, str], float]] = defaultdict(lambda: defaultdict(float))
    needs_review: list[str] = []

    for item in payload.items:
        recipe = db.scalar(
            select(Recipe)
            .options(selectinload(Recipe.recipe_ingredients).selectinload(RecipeIngredient.ingredient))
            .where(Recipe.id == item.recipe_id)
        )
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
