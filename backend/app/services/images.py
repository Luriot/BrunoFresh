from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ..config import settings
from .network import validate_public_host_for_download

logger = logging.getLogger(__name__)


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
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            target.write_bytes(response.content)
        rel = Path("images") / target.name
        logger.info(f"Image téléchargée avec succès et sauvegardée sous {rel}")
        return rel.as_posix()
    except Exception as exc:
        logger.error(f"Erreur lors du téléchargement de l'image de la recette {recipe_id}: {exc}", exc_info=True)
        return None
