from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routers import cart_router, health_router, recipes_router, scrape_router
from .config import settings

app = FastAPI(title="BrunoFresh API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory=str(settings.images_dir)), name="images")


app.include_router(health_router)
app.include_router(recipes_router)
app.include_router(scrape_router)
app.include_router(cart_router)
