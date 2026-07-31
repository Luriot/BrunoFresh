# BrunoFresh — Agent Guide

Self-hosted recipe scraper + shopping-list generator. Python/FastAPI backend, React/Vite frontend served by the same FastAPI app in a single Docker container. Single-household shared-passcode auth (HttpOnly cookie session), not multi-user SaaS.

## Commands

### Backend (from `backend/`)
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head           # use `alembic stamp head` if DB pre-dates Alembic
.\venv\Scripts\python.exe -m pytest -q            # asyncio_mode=auto, testpaths=tests
.\venv\Scripts\python.exe -m pytest tests/unit/test_normalizer.py -q
uvicorn app.main:app --reload                     # http://127.0.0.1:8000
```

### Frontend (from `frontend/`)
```powershell
npm install
npm run dev          # http://127.0.0.1:5173
npm run test:run     # vitest
npm run e2e          # playwright
```

### Docker
```bash
docker build -t brunofresh .
docker run -p 8000:8000 -v ./backend/data:/app/data -e APP_PASSCODE=changeme -e AUTH_SECRET=<32+ chars> brunofresh
```

## Architecture map

- `backend/app/api/routers/` — FastAPI routers (`admin`, `auth`, `cart`, `lists`, `meal_plans`, `pantry`, `recipes/`, `scrape`, `tags`, `users`, `hellofresh`)
- `backend/app/services/scrapers/` — per-domain + base scrapers, JSON-LD fallback
- `backend/app/services/normalizer.py` — Ollama-based ingredient parser + deterministic fallback; canonical unit tables (`_UNIT_ALIASES`, `_UNIT_CONVERSIONS`, `_UNIT_TO_GROUP_INFO`, `_CULINARY_UNIT_DENSITIES`, `_PACK_GRAMS`) and `extract_pack_grams_from_raw` (retro-calibration from a recipe's own raw text)
- `backend/app/services/aggregator.py` — single source of truth for ingredient aggregation used by both `/api/cart/generate` and `/api/lists`
- `backend/app/services/orchestrator.py` — scrape → normalize → dedupe → persist pipeline, fuzzy ingredient match (rapidfuzz WRatio ≥ 90) at insert time
- `backend/app/models.py` — SQLAlchemy ORM
- `backend/alembic/versions/` — dated migrations (`YYYYMMDD_NNNN_slug.py`)
- `backend/app/main.py` — app bootstrap, middleware (CORS, Session), default tag seeding, `/dbadmin` gating, SPA catch-all
- `frontend/src/` — `pages/`, `components/`, `api/`, `hooks/`, `i18n/{en,fr}.json`
- `Dockerfile` / `docker-entrypoint.sh` / `DEPLOYMENT.md` — single-container build + Unraid/GHCR deployment notes

## Gotchas

- Tests are `async def` (pytest `asyncio_mode=auto`). Use the shared fixtures from `backend/tests/conftest.py`: `db_session` (in-memory SQLite), `client` (user role, auth bypassed), `admin_client`, `anon_client`.
- Ollama is required for AI normalization but tests mock/fallback gracefully. Batch chunk size `_OLLAMA_BATCH_CHUNK_SIZE` in `normalizer.py` — bumping past 8 tends to truncate larger lots.
- Unit conversions live in static dicts inside `normalizer.py`; the aggregation pipeline (`aggregator.py`) is `normalize_unit → culinary_to_grams → pack_to_grams → to_base_unit → group by (category, name_en, name_fr, agg_unit, ingredient_id) → smart_display_unit`. Non-mergeable units (piece, botte, tranche, boîte, paquet non-converti, pincée) keep separate rows.
- `pack_to_grams` resolution order: retro-calibration from `link.raw_string` (regex `extract_pack_grams_from_raw`, "1 sachet (7 g)") → admin override via `Ingredient.grams_per_paquet` / `grams_per_boite` columns → static `_PACK_GRAMS` table. First hit wins; if none, the row stays as `paquet`/`boîte`.
- `Ingredient.grams_per_paquet` / `grams_per_boite` are admin-set via `PATCH /api/ingredients/{id}` (no name/category needed to set them). Frontend admin UI bytes still pending; the API and TS types (`IngredientDetail`, `patchIngredient` payload) already accept them.
- Default tags are auto-seeded from `services/tag_rules.py::KEYWORDS` at startup; color map lives in `main.py::_TAG_COLORS`.
- `/dbadmin` (sqladmin) is enabled by default in dev, blocked by middleware in prod (`DBADMIN_ENABLED=true` overrides — never enable in prod without network-level protection).
- Two venvs may coexist: `backend/venv/` is canonical for the backend; `.venv/` at repo root may be vestigial.
- ENV (see `backend/app/config.py`): `AUTH_SECRET` ≥ 32 chars required in prod; `APP_PASSCODE` must be changed; `OLLAMA_MODEL` defaults to `qwen2.5:14b-instruct`; `APP_ENV=prod` enforces `AUTH_COOKIE_SECURE=true` and forbids `/dbadmin`.

## Style

- Backend: `from __future__ import annotations` at top of modules; async-first SQLAlchemy with `selectinload` to avoid lazy-load in async context; Pydantic schemas per domain in `app/schemas/<domain>.py`.
- Frontend: full i18n via `react-i18next` (EN + FR); unit names and category names are translation keys (see `i18n/{en,fr}.json`).
- No new comments unless explaining non-obvious intent.
- Database schema changes require an Alembic migration (dated filename prefix).
- Security: never log secrets; never commit `AUTH_SECRET`. Always set `AUTH_COOKIE_SECURE=true` when serving over HTTPS.