import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse

from ...config import settings
from ..dependencies import require_auth

router = APIRouter(prefix="/api/admin/db", tags=["admin"], dependencies=[Depends(require_auth)])


@router.get("/export")
async def export_db():
    if not settings.db_file.exists():
        raise HTTPException(status_code=404, detail="Database file not found.")
    return FileResponse(
        path=settings.db_file,
        filename="app.db",
        media_type="application/x-sqlite3",
    )


@router.post("/import")
async def import_db(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not (filename.endswith(".db") or filename.endswith(".sqlite") or filename.endswith(".sqlite3")):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a SQLite database file.")

    temp_path = settings.db_file.with_suffix(".temp")
    try:
        content = await file.read()
        await asyncio.to_thread(temp_path.write_bytes, content)
        await asyncio.to_thread(shutil.move, str(temp_path), str(settings.db_file))
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to import database.")
    finally:
        await file.close()

    return {"message": "Database imported successfully."}
