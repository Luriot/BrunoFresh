from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import require_auth
from ...config import settings
from ...database import get_db
from ...models import User
from ...schemas import UserOut, UserPatch
from ...services.auth import UserClaims, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])

_AVATAR_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_AVATAR_ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _check_magic_bytes(data: bytes, content_type: str) -> bool:
    """Verify that the file content actually matches the declared content-type."""
    if content_type == "image/jpeg":
        return data[:3] == b"\xff\xd8\xff"
    if content_type == "image/png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


@router.patch("/me", response_model=UserOut)
async def patch_me(
    payload: UserPatch,
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await db.get(User, claims.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")

    if payload.username is not None:
        existing = await db.scalar(
            select(User).where(User.username == payload.username, User.id != claims.user_id)
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
        user.username = payload.username

    if payload.new_password is not None:
        user.hashed_password = hash_password(payload.new_password)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    claims: UserClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _AVATAR_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported image type. Use JPEG, PNG, or WebP.",
        )

    data = await file.read(_AVATAR_MAX_BYTES + 1)
    if len(data) > _AVATAR_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (max 5 MB).",
        )

    if not _check_magic_bytes(data, content_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File content does not match declared type.",
        )

    ext = _AVATAR_ALLOWED[content_type]
    filename = f"avatar_{claims.user_id}{ext}"
    dest = settings.images_dir / filename
    dest.write_bytes(data)

    user = await db.get(User, claims.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    user.avatar_url = f"images/{filename}"
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
