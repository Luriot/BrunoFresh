from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ..config import settings
from .network import SSRFGuardedTransport, validate_public_host_for_download

logger = logging.getLogger(__name__)


_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


async def download_image(image_url: str | None, recipe_id: int) -> str | None:
    if not image_url:
        logger.debug(f"Aucune URL d'image fournie pour la recette {recipe_id}.")
        return None

    logger.info(f"Tentative de téléchargement de l'image ({image_url}) pour la recette {recipe_id}...")
    is_safe_target = await validate_public_host_for_download(image_url)
    if not is_safe_target:
        logger.warning(f"Cible non sécurisée ou nom d'hôte invalide pour le téléchargement: {image_url}")
        return None

    target = settings.images_dir / f"recipe_{recipe_id}.jpg"
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
        rel = Path("images") / target.name
        logger.info(f"Image téléchargée avec succès et sauvegardée sous {rel}")
        return rel.as_posix()
    except httpx.ConnectError as exc:
        logger.warning(f"Connexion bloquée pour la recette {recipe_id}: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Erreur lors du téléchargement de l'image de la recette {recipe_id}: {exc}", exc_info=True)
        return None
