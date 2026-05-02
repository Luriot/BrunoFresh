"""Combine all sub-routers into a single router exported as `router`."""
from __future__ import annotations

from fastapi import APIRouter

from .crud import router as _crud_router
from .recipe_tags import router as _tags_router
from .similarity import router as _similarity_router
from .rescrape import router as _rescrape_router
from .ingredients import router as _ingredients_router

router = APIRouter(prefix="/api", tags=["recipes"])

router.include_router(_crud_router)
router.include_router(_tags_router)
router.include_router(_similarity_router)
router.include_router(_rescrape_router)
router.include_router(_ingredients_router)
