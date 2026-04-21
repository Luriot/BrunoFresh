import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _resolve_frontend_dist_dir() -> Path | None:
    backend_dir = Path(__file__).resolve().parent.parent
    project_root = backend_dir.parent

    configured = os.getenv("FRONTEND_DIST_DIR", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            project_root / "frontend" / "dist",
            project_root / "dist",
        ]
    )

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def register_spa(app: FastAPI) -> None:
    frontend_dist_dir = _resolve_frontend_dist_dir()
    
    if frontend_dist_dir:
        assets_dir = frontend_dist_dir / "assets"
        if assets_dir.exists() and assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Redirection automatique pour /admin (sans slash terminal)
        if full_path == "admin":
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/admin/")

        # Ne pas intercepter les appels d'API non résolus ni l'admin SQL
        if full_path.startswith("api") or full_path.startswith("admin"):
            raise HTTPException(status_code=404, detail="Not Found")

        if not frontend_dist_dir:
            raise HTTPException(status_code=404, detail="Not Found")

        if full_path:
            requested_file = frontend_dist_dir / full_path
            if requested_file.exists() and requested_file.is_file():
                return FileResponse(requested_file)

        index_file = frontend_dist_dir / "index.html"
        if index_file.exists() and index_file.is_file():
            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail="Not Found")