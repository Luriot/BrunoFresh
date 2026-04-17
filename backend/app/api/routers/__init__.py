from .cart import router as cart_router
from .health import router as health_router
from .recipes import router as recipes_router
from .scrape import router as scrape_router

__all__ = [
    "cart_router",
    "health_router",
    "recipes_router",
    "scrape_router",
]
