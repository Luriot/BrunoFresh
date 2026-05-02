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


_NOT_FOUND = "Not Found"


def register_spa(app: FastAPI) -> None:
    frontend_dist_dir = _resolve_frontend_dist_dir()

    if frontend_dist_dir:
        assets_dir = frontend_dist_dir / "assets"
        if assets_dir.exists() and assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Ne pas intercepter les appels d'API non résolus ni l'admin SQL
        if full_path.startswith("api") or full_path.startswith("dbadmin"):
            raise HTTPException(status_code=404, detail=_NOT_FOUND)

        if not frontend_dist_dir:
            raise HTTPException(status_code=404, detail=_NOT_FOUND)

        if full_path:
            # Guard against null-byte injection before constructing the path.
            if "\x00" in full_path:
                raise HTTPException(status_code=400, detail="Bad Request")
            requested_file = frontend_dist_dir / full_path
            if requested_file.exists() and requested_file.is_file():
                # .webmanifest is not in Python's mimetypes DB; serve it correctly
                # so Chrome accepts it as a PWA manifest.
                if requested_file.suffix == ".webmanifest":
                    return FileResponse(requested_file, media_type="application/manifest+json")
                return FileResponse(requested_file)

        index_file = frontend_dist_dir / "index.html"
        if index_file.exists() and index_file.is_file():
            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail=_NOT_FOUND)