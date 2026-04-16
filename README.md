# MealCart

MealCart is a self-hosted recipe and shopping list app.
This first implementation provides:

- A FastAPI backend with SQLite storage
- Recipe ingestion via a scrape queue endpoint
- Ingredient normalization fallback logic
- Cart aggregation with serving-based scaling
- A React + Vite + Tailwind frontend to scrape URLs, browse recipes, and generate shopping lists

## Repository Layout

- `backend/`: FastAPI API, SQLAlchemy models, scraper/normalizer services
- `frontend/`: React app for recipe browsing and shopping list generation

## Backend Quick Start

1. Open terminal in `backend/`
2. Create and activate a virtual environment
3. Install dependencies
4. Run API server

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend will run at `http://127.0.0.1:8000`.

## Frontend Quick Start

1. Open terminal in `frontend/`
2. Install dependencies
3. Run dev server

```powershell
cd frontend
npm install
npm run dev
```

Frontend will run at `http://127.0.0.1:5173`.

## Implemented API Endpoints

- `GET /api/health`
- `GET /api/recipes`
- `GET /api/recipes/{recipe_id}`
- `POST /api/scrape`
- `PATCH /api/ingredients/{ingredient_id}`
- `POST /api/cart/generate`

## Current Notes

- `/api/scrape` currently uses a deterministic placeholder scraper service. This is intentional for step 1.
- Site-specific scrapers (HelloFresh Playwright auth flow, CuisineAZ, 750g, etc.) should replace the placeholder service in the next phase.
- LLM normalization is currently represented by a fallback normalizer. Ollama integration is next.

## Next Implementation Milestones

1. Real multi-site scraping engine with domain-specific extractors
2. HelloFresh authenticated session persistence (`hf_state.json`)
3. Ollama normalization pipeline with strict schema validation and retry logic
4. Ingredient review dashboard for unresolved items
5. Internationalization strings (EN then FR)
