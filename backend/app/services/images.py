from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ..config import settings
from .network import SSRFGuardedTransport, validate_public_host_for_download

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


def _process_image(src: Path) -> Path | None:
    """Cap the original at 1200 px and generate a WebP thumbnail (synchronous).

    Both operations are batched here so the image is only opened twice total.
    Run inside a thread executor to avoid blocking the event loop.
    """
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        # ── 1. Cap original and convert to WebP ────────────────────────────
        with PILImage.open(src) as img:
            if img.width > _FULL_MAX_SIDE or img.height > _FULL_MAX_SIDE:
                img.thumbnail((_FULL_MAX_SIDE, _FULL_MAX_SIDE), PILImage.LANCZOS)
                logger.debug("Original %s capped to %dpx side", src.name, _FULL_MAX_SIDE)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(src, "WEBP", quality=88, method=4)

        # ── 2. Generate WebP thumbnail ────────────────────────────────────────
        dest = thumb_path_for(src)
        # Clean up any legacy _thumb.jpg that may exist from a previous version
        legacy_jpg = src.with_name(f"{src.stem}_thumb.jpg")
        legacy_jpg.unlink(missing_ok=True)

        with PILImage.open(src) as img:
            img.thumbnail(_THUMB_MAX_SIZE, PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=_THUMB_WEBP_QUALITY, method=4)
        return dest

    except Exception as exc:
        logger.warning("Impossible de traiter l'image %s : %s", src, exc)
        return None


def process_uploaded_image(src: Path) -> Path | None:
    """Convert to JPEG, cap at 1200 px, and generate a WebP thumbnail.

    Unlike :func:`_process_image` (used for downloads), this always rewrites
    the file as JPEG so that PNG/WebP uploads are stored in a consistent format.
    Run inside a thread executor to avoid blocking the event loop.
    """
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        # ── 1. Convert + cap → WebP ──────────────────────────────────────────
        with PILImage.open(src) as img:
            if img.width > _FULL_MAX_SIDE or img.height > _FULL_MAX_SIDE:
                img.thumbnail((_FULL_MAX_SIDE, _FULL_MAX_SIDE), PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(src, "WEBP", quality=88, method=4)

        # ── 2. Generate WebP thumbnail ────────────────────────────────────────
        dest = thumb_path_for(src)
        legacy_jpg = src.with_name(f"{src.stem}_thumb.jpg")
        legacy_jpg.unlink(missing_ok=True)

        with PILImage.open(src) as img:
            img.thumbnail(_THUMB_MAX_SIZE, PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=_THUMB_WEBP_QUALITY, method=4)
        return dest

    except Exception as exc:
        logger.warning("Impossible de traiter l'image uploadée %s : %s", src, exc)
        return None


def migrate_to_webp(src: Path) -> Path | None:
    """Convert an existing image to WebP, rename the file if needed, regenerate thumbnail.

    Saves as ``{stem}.webp``, deletes the old file if it had a different extension,
    then regenerates the thumbnail from the new file.
    Run inside a thread executor to avoid blocking the event loop.
    """
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        dest = src.with_suffix(".webp")
        with PILImage.open(src) as img:
            if img.width > _FULL_MAX_SIDE or img.height > _FULL_MAX_SIDE:
                img.thumbnail((_FULL_MAX_SIDE, _FULL_MAX_SIDE), PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=88, method=4)

        # Remove old file if extension changed
        if src.suffix.lower() != ".webp":
            src.unlink(missing_ok=True)

        # Regenerate thumbnail from new file
        old_thumb = thumb_path_for(dest)
        old_thumb.unlink(missing_ok=True)
        generate_thumbnail(dest)

        logger.debug("Migré %s → %s", src.name, dest.name)
        return dest

    except Exception as exc:
        logger.warning("Impossible de migrer %s en WebP : %s", src, exc)
        return None


def generate_thumbnail(src: Path) -> Path | None:
    """Generate a WebP thumbnail only (no cap). Used for lazy generation in the router."""
    try:
        from PIL import Image as PILImage  # noqa: PLC0415

        dest = thumb_path_for(src)
        legacy_jpg = src.with_name(f"{src.stem}_thumb.jpg")
        legacy_jpg.unlink(missing_ok=True)

        with PILImage.open(src) as img:
            img.thumbnail(_THUMB_MAX_SIZE, PILImage.LANCZOS)
            if img.mode not in {"RGB", "RGBA"}:
                img = img.convert("RGB")
            img.save(dest, "WEBP", quality=_THUMB_WEBP_QUALITY, method=4)
        return dest

    except Exception as exc:
        logger.warning("Impossible de générer le thumbnail pour %s : %s", src, exc)
        return None


async def download_image(image_url: str | None, recipe_id: int) -> str | None:
    if not image_url:
        logger.debug(f"Aucune URL d'image fournie pour la recette {recipe_id}.")
        return None

    logger.info(f"Tentative de téléchargement de l'image ({image_url}) pour la recette {recipe_id}...")
    is_safe_target = await validate_public_host_for_download(image_url)
    if not is_safe_target:
        logger.warning(f"Cible non sécurisée ou nom d'hôte invalide pour le téléchargement: {image_url}")
        return None

    target = settings.images_dir / f"recipe_{recipe_id}.webp"
    try:
        # SSRFGuardedTransport re-validates the resolved IP at connect time,
        # preventing DNS rebinding attacks.
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

        import asyncio  # noqa: PLC0415
        await asyncio.get_running_loop().run_in_executor(None, _process_image, target)

        rel = Path("images") / target.name
        logger.info(f"Image téléchargée avec succès et sauvegardée sous {rel}")
        return rel.as_posix()
    except httpx.ConnectError as exc:
        logger.warning(f"Connexion bloquée pour la recette {recipe_id}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Erreur lors du téléchargement de l'image de la recette {recipe_id}: {exc}", exc_info=True)
        return None
