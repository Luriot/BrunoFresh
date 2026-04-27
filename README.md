# BrunoFresh

BrunoFresh is a self-hosted recipe and shopping list app.
This first implementation provides:

- A FastAPI backend with SQLite storage
- Recipe ingestion via a scrape queue endpoint
- Domain-aware scraper routing for HelloFresh, CuisineAZ, AllRecipes, and Jow
- Ingredient normalization with Ollama first, then deterministic fallback
- Cart aggregation with serving-based scaling
- A React + Vite + Tailwind frontend to scrape URLs, browse recipes, and generate shopping lists
- EN/FR frontend internationalization with category translations

## Repository Layout

- `backend/`: FastAPI API, SQLAlchemy models, scraper/normalizer services
- `frontend/`: React app for recipe browsing and shopping list generation

## Backend Quick Start

1. Open terminal in `backend/`
2. Create and activate a virtual environment
3. Install dependencies
4. Run DB migrations
5. Run API server

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Set `APP_PASSCODE` before exposing the API. By default the project uses a placeholder passcode for local development only.
Set a strong `AUTH_SECRET` in production so token signing is stable across restarts.

If you already have a local `backend/data/database.db` created before Alembic was added, run `alembic stamp head` once instead of `alembic upgrade head`.

Backend will run at `http://127.0.0.1:8000`.

## Frontend Quick Start

1. Open terminal in `frontend/`
2. Install dependencies
3. Run dev server

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend will run at `http://127.0.0.1:5173`.

## Implemented API Endpoints

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/images/{file_name}`
- `GET /api/recipes`
- `GET /api/recipes/{recipe_id}`
- `POST /api/scrape`
- `GET /api/jobs/{job_id}/stream` (Server-Sent Events)
- `PATCH /api/ingredients/{ingredient_id}`
- `POST /api/cart/generate`

## Current Notes

- `/api/scrape` now routes scrapers by domain (`hellofresh`, `cuisineaz`, `allrecipes`, `jow`).
- All API endpoints except `/api/health`, `/api/auth/login`, and `/api/auth/logout` require an authenticated `HttpOnly` cookie.
- SSE auth no longer uses query-string tokens; `/api/jobs/{job_id}/stream` authenticates via cookie.
- Images are no longer served through a public static mount. Use `/api/images/{file_name}` with auth.
- HelloFresh uses Playwright auth via `.env` credentials and persistent state in `backend/data/hf_state.json`.
- Set `OLLAMA_MODEL=qwen2.5:14b-instruct` for best parsing quality on 16GB VRAM.
- Deduplication now checks title similarity + ingredient overlap, not only URL equality.

## Security Deployment Notes

- Place BrunoFresh behind an HTTPS reverse proxy (Caddy, Nginx, Traefik) before exposing it beyond LAN.
- Set `AUTH_COOKIE_SECURE=true` when HTTPS is enabled so auth cookies are never sent over plain HTTP.
- Keep `ALLOWED_ORIGINS` minimal and explicit.
- Keep access logs enabled for auditing, but avoid logging full query strings in reverse proxy logs.
