"""Shared pytest fixtures for the BrunoFresh backend test suite.

Strategy:
- Each test gets a fresh in-memory SQLite database (function scope) → perfect isolation.
- `client`     : authenticated (require_auth bypassed) — use for testing business logic.
- `anon_client`: no auth bypass — use for testing auth protection / login flow.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import models so their metadata is registered on Base before create_all.
from app.models import (  # noqa: F401
    Ingredient,
    IngredientTranslation,
    MealPlan,
    MealPlanEntry,
    PantryItem,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    ShoppingListItem,
    ShoppingListRecipe,
    ScrapeJob,
    Tag,
)
from app.database import Base, get_db
from app.api.dependencies import require_auth
from app.main import app


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
    """AsyncClient with auth bypassed and DB pointing at the in-memory test DB."""

    async def _override_get_db():
        yield db_session

    async def _override_require_auth():
        pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_auth] = _override_require_auth
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def anon_client(db_session: AsyncSession):
    """AsyncClient without auth override — use for testing auth endpoints themselves."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
