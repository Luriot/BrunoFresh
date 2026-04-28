# BrunoFresh

> **Self-hosted recipe manager & smart grocery list generator**  
> Scrape recipes from any site, organize them by tag, plan your week, and generate one consolidated shopping list — all from a single private app running on your own hardware.

---

## Features

- **Recipe scraping** — paste one or multiple URLs; domain-aware scrapers handle HelloFresh, CuisineAZ, AllRecipes, Jow, and any site publishing JSON-LD Recipe data
- **Ingredient normalization** — Ollama LLM first, deterministic rule-based fallback; converts imperial ↔ metric, resolves unicode fractions (½, ⅓, ¾…)
- **Smart deduplication** — title similarity + ingredient overlap check before importing
- **Cart & servings scaling** — add recipes to cart, adjust servings per recipe, quantities scale automatically
- **Meal planner** — weekly 7-day drag-and-drop agenda (mouse & touch), with snack slot option
- **Shopping list history** — generated lists are persisted; mark items as already owned
- **Pantry management** — track stock to skip owned items when generating lists
- **Tags & filtering** — custom colour-coded tags with tag-based filtering
- **Cook mode** — step-by-step instruction view with optional step images
- **Dark / light theme** — persisted per device, syncs Android PWA status bar
- **EN / FR interface** — full i18n with category and tag name translations
- **PWA** — installable on mobile, works offline for browsing cached recipes
- **Docker-ready** — single-container image with Vite-built frontend served by FastAPI

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, SQLite |
| Scraping | httpx, BeautifulSoup4, JSON-LD parsing |
| AI normalization | Ollama (local LLM, configurable model) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| i18n | react-i18next |
| Auth | HttpOnly cookie session, passcode-based |
| Container | Docker (multi-stage build) |

---

## Quick Start

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

> **First run on an existing DB?** If `backend/data/database.db` was created before Alembic was added, run `alembic stamp head` instead of `alembic upgrade head`.

Backend runs at `http://127.0.0.1:8000`.

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env   # set VITE_API_URL if needed
npm run dev
```

Frontend runs at `http://127.0.0.1:5173`.

---

## Docker

```bash
docker build -t brunofresh .
docker run -d \
  -p 8000:8000 \
  -v ./backend/data:/app/data \
  -e APP_PASSCODE=changeme \
  -e AUTH_SECRET=a-long-random-string \
  brunofresh
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full Unraid / GitHub Actions CI pipeline guide.

---

## Configuration

All settings are environment variables (or a `.env` file in `backend/`):

| Variable | Default | Description |
|---|---|---|
| `APP_PASSCODE` | `dev-only` | Login passcode — **change before exposing** |
| `AUTH_SECRET` | random | JWT signing secret — set to a stable value in production |
| `AUTH_COOKIE_SECURE` | `false` | Set `true` when served over HTTPS |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS origins (comma-separated) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3` | Model name — `qwen2.5:14b-instruct` recommended for 16 GB VRAM |
| `DATABASE_URL` | `sqlite:///./data/database.db` | SQLAlchemy DB URL |

---

## Repository Layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/routers/     # FastAPI route handlers
│   │   ├── services/        # Scraper, normalizer, orchestrator
│   │   │   └── scrapers/    # Per-domain & base scrapers
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── main.py          # App bootstrap
│   ├── alembic/             # DB migrations
│   └── data/                # SQLite DB & recipe images (gitignored)
├── frontend/
│   └── src/
│       ├── pages/           # Route-level components
│       ├── components/      # Shared UI components
│       ├── api/             # Typed API client
│       ├── hooks/           # useCart, useScrape
│       └── i18n/            # EN/FR translation files
├── Dockerfile
└── DEPLOYMENT.md
```

---

## API Overview

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check (no auth) |
| `POST` | `/api/auth/login` | Passcode login → sets HttpOnly cookie |
| `POST` | `/api/auth/logout` | Clear session cookie |
| `GET` | `/api/recipes` | List recipes (filter by tag, search, favorites) |
| `GET` | `/api/recipes/{id}` | Recipe detail with ingredients & steps |
| `POST` | `/api/scrape` | Enqueue a scrape job (returns job ID for SSE) |
| `GET` | `/api/jobs/{id}/stream` | SSE stream for scrape job progress |
| `POST` | `/api/cart/generate` | Generate shopping list from cart |
| `GET/POST/PATCH/DELETE` | `/api/lists/…` | Shopping list CRUD |
| `GET/POST/DELETE` | `/api/meal-plans/…` | Meal plan CRUD |
| `GET/POST/DELETE` | `/api/pantry/…` | Pantry item management |
| `GET/POST/DELETE` | `/api/tags/…` | Tag management |

All endpoints (except `/api/health`, `/api/auth/login`, `/api/auth/logout`) require the authenticated HttpOnly session cookie.

---

## Security Notes

- Place BrunoFresh behind an HTTPS reverse proxy (Caddy, Nginx, Traefik) before exposing it beyond LAN.
- Set `AUTH_COOKIE_SECURE=true` once HTTPS is enabled so auth cookies are never sent over plain HTTP.
- Keep `ALLOWED_ORIGINS` minimal and explicit.
- The app is designed for **single-household use** with a shared passcode — not multi-user production SaaS.

---

## Contributing

1. Fork the repo and create a feature branch
2. Run the backend with `uvicorn app.main:app --reload` and the frontend with `npm run dev`
3. Keep backend changes covered by the existing Alembic migration pattern (add a new version file for schema changes)
4. Open a PR with a clear description of what changed and why

---

## License

[MIT](LICENSE)
