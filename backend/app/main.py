import logging
import sys

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:\t  %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from .api.dependencies import require_auth
from .api.routers import auth_router, cart_router, health_router, images_router, recipes_router, scrape_router
from .config import settings

app = FastAPI(title="BrunoFresh API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=list(settings.allowed_methods),
    allow_headers=list(settings.allowed_headers),
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(images_router, dependencies=[Depends(require_auth)])
app.include_router(recipes_router, dependencies=[Depends(require_auth)])
app.include_router(scrape_router, dependencies=[Depends(require_auth)])
app.include_router(cart_router, dependencies=[Depends(require_auth)])

from .spa import register_spa
register_spa(app)
