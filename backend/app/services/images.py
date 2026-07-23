from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from ..config import settings
from .network import SSRFGuardedTransport

logger = logging.getLogger(__name__)


_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Thumbnails: max side 400 px, WebP quality 82
_THUMB_MAX_SIZE = (400, 400)
_THUMB_WEBP_QUALITY = 82

# Originals are capped to this size on download to avoid storing enormous sources
_FULL_MAX_SIDE = 1200


def thumb_path_for(image_path: Path) -> Path:
    """Return the expected thumbnail path for a given full-size image path.

    Thumbnails are stored as WebP next to the original:
    ``recipe_1.jpg`` → ``recipe_1_thumb.webp``
    """
    return image_path.with_name(f"{image_path.stem}_thumb.webp")


def process_image(src: Path, *, thumb_only: bool = False) -> Path | None:
    """Cap the original at 1200 px, convert to WebP, and (re)generate the WebP
    thumbnail next to it. With ``thumb_only=True`` the original is left untouched
    and only the thumbnail is regenerated.

    Run inside a thread executor to avoid blocking the event loop.
    """
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        if not thumb_only:
            with PILImage.open(src) as img:
                if img.width > _FULL_MAX_SIDE or img.height > _FULL_MAX_SIDE:
                    img.thumbnail((_FULL_MAX_SIDE, _FULL_MAX_SIDE), PILImage.LANCZOS)
                if img.mode not in {"RGB", "RGBA"}:
                    img = img.convert("RGB")
                img.save(src, "WEBP", quality=88, method=4)

        dest = thumb_path_for(src)
        # Clean up any legacy _thumb.jpg that may exist from a previous version
        src.with_name(f"{src.stem}_thumb.jpg").unlink(missing_ok=True)

        with PILImage.open(src) as img:
            img.thumbnail(_THUMB_MAX_SIZE, PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=_THUMB_WEBP_QUALITY, method=4)
        return dest

    except Exception as exc:
        logger.warning("Impossible de traiter l'image %s : %s", src, exc)
        return None


def migrate_to_webp(src: Path) -> Path | None:
    """Convert an existing image to WebP in place, rename to ``.webp`` if needed.

    The thumbnail name is stem-based, so it stays valid across the rename.
    Run inside a thread executor to avoid blocking the event loop.
    """
    dest = src.with_suffix(".webp")
    if process_image(src) is None:
        return None
    if dest != src:
        src.replace(dest)
        logger.debug("Migré %s → %s", src.name, dest.name)
    return dest


async def download_image(image_url: str | None, recipe_id: int) -> str | None:
    if not image_url:
        logger.debug(f"Aucune URL d'image fournie pour la recette {recipe_id}.")
        return None

    logger.info(f"Tentative de téléchargement de l'image ({image_url}) pour la recette {recipe_id}...")
    target = settings.images_dir / f"recipe_{recipe_id}.webp"
    try:
        # SSRFGuardedTransport validates the resolved IP at connect time,
        # preventing SSRF including via DNS rebinding.
        transport = SSRFGuardedTransport()
        async with httpx.AsyncClient(transport=transport, timeout=20, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in _ALLOWED_CONTENT_TYPES:
                logger.warning(f"Type de contenu non accepté '{content_type}' pour l'image de la recette {recipe_id}.")
                return None

            content = response.content
            if len(content) > _MAX_IMAGE_BYTES:
                logger.warning(f"Image trop volumineuse ({len(content)} octets) pour la recette {recipe_id}.")
                return None

            target.write_bytes(content)

        await asyncio.get_running_loop().run_in_executor(None, process_image, target)

        rel = Path("images") / target.name
        logger.info(f"Image téléchargée avec succès et sauvegardée sous {rel}")
        return rel.as_posix()
    except httpx.ConnectError as exc:
        logger.warning(f"Connexion bloquée pour la recette {recipe_id}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Erreur lors du téléchargement de l'image de la recette {recipe_id}: {exc}", exc_info=True)
        return None


def resolve_image_url(local_path: str | None, original_url: str | None, *, thumb: bool) -> str | None:
    """Return a ready-to-use image URL.

    Prefers the locally-cached copy (served via /api/images/); falls back to
    the original remote URL stored at scrape time.  Returns None if neither is
    available.
    """
    if local_path:
        name = Path(local_path).name
        if thumb:
            return f"/api/images/{Path(name).stem}_thumb.webp"
        return f"/api/images/{name}"
    return original_url
