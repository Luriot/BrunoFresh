from .auth import router as auth_router
from .cart import router as cart_router
from .health import router as health_router
from .images import router as images_router
from .lists import router as lists_router
from .recipes import router as recipes_router
from .scrape import router as scrape_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "cart_router",
    "health_router",
    "images_router",
    "lists_router",
    "recipes_router",
    "scrape_router",
    "admin_router",
]
