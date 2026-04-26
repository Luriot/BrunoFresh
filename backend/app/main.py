import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:\t  %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from .api.dependencies import require_auth
from .api.routers import (
    auth_router,
    cart_router,
    health_router,
    images_router,
    lists_router,
    meal_plans_router,
    pantry_router,
    recipes_router,
    scrape_router,
    tags_router,
    admin_router,
)
from .config import settings
from .admin import setup_admin
from .database import SessionLocal
from .models import Tag

logger = logging.getLogger(__name__)

DEFAULT_TAGS: list[dict] = [
    {"name": "Rapide",          "color": "#16a34a"},
    {"name": "Végétarien",       "color": "#65a30d"},
    {"name": "Végan",            "color": "#4d7c0f"},
    {"name": "Épicé",            "color": "#dc2626"},
    {"name": "Peu de vaisselle", "color": "#2563eb"},
    {"name": "Healthy",          "color": "#0891b2"},
    {"name": "Comfort food",     "color": "#d97706"},
    {"name": "Pâtes",            "color": "#f59e0b"},
    {"name": "Riz",              "color": "#ca8a04"},
    {"name": "Poulet",           "color": "#ea580c"},
    {"name": "Poisson",          "color": "#0284c7"},
    {"name": "Dessert",          "color": "#db2777"},
    {"name": "Petit-déjeuner",   "color": "#7c3aed"},
    {"name": "Batch cooking",    "color": "#64748b"},
]


async def _seed_default_tags() -> None:
    async with SessionLocal() as db:
        existing = (await db.scalars(select(Tag))).all()
        existing_names = {t.name for t in existing}
        new_tags = [
            Tag(name=tag["name"], color=tag["color"])
            for tag in DEFAULT_TAGS
            if tag["name"] not in existing_names
        ]
        if new_tags:
            db.add_all(new_tags)
            await db.commit()
            logger.info(f"Tags par défaut créés: {[t.name for t in new_tags]}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _seed_default_tags()
    yield

app = FastAPI(title="BrunoFresh API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=list(settings.allowed_methods),
    allow_headers=list(settings.allowed_headers),
)
app.add_middleware(SessionMiddleware, secret_key=settings.auth_secret, same_site="lax", https_only=settings.auth_cookie_secure)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(images_router, dependencies=[Depends(require_auth)])
app.include_router(recipes_router, dependencies=[Depends(require_auth)])
app.include_router(scrape_router, dependencies=[Depends(require_auth)])
app.include_router(cart_router, dependencies=[Depends(require_auth)])
app.include_router(lists_router, dependencies=[Depends(require_auth)])
app.include_router(tags_router, dependencies=[Depends(require_auth)])
app.include_router(pantry_router, dependencies=[Depends(require_auth)])
app.include_router(meal_plans_router, dependencies=[Depends(require_auth)])
app.include_router(admin_router, dependencies=[Depends(require_auth)])

# SQLAdmin DOIT être initialisé AVANT d'enregistrer le catch-all du SPA
setup_admin(app)

from .spa import register_spa
register_spa(app)
