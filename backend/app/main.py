import logging
import sys

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

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
    recipes_router,
    scrape_router,
)
from .config import settings
from .admin import setup_admin

app = FastAPI(title="BrunoFresh API", version="0.1.0")

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

# SQLAdmin DOIT être initialisé AVANT d'enregistrer le catch-all du SPA
setup_admin(app)

from .spa import register_spa
register_spa(app)
