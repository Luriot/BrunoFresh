from __future__ import annotations

import logging
from urllib.parse import urlparse

from .hellofresh import HelloFreshScraper
from .static_sites import AllRecipesFrScraper, CuisineAzScraper, JowScraper
from .types import ScrapedRecipe

logger = logging.getLogger(__name__)


async def scrape_recipe_url(url: str) -> ScrapedRecipe:
    domain = urlparse(url).netloc.replace("www.", "")
    logger.debug(f"Aiguillage du scraper pour le domaine cible : {domain}")

    if "hellofresh" in domain:
        logger.info(f"Utilisation du scraper HelloFresh pour l'URL : {url}")
        return await HelloFreshScraper(url).scrape()
    if "cuisineaz" in domain:
        logger.info(f"Utilisation du scraper CuisineAZ pour l'URL : {url}")
        return await CuisineAzScraper(url).scrape()
    if "allrecipes" in domain:
        logger.info(f"Utilisation du scraper AllRecipes pour l'URL : {url}")
        return await AllRecipesFrScraper(url).scrape()
    if "jow" in domain:
        logger.info(f"Utilisation du scraper Jow pour l'URL : {url}")
        return await JowScraper(url).scrape()

    logger.warning(f"Aucun scraper spécifique trouvé pour le domaine '{domain}', tentative avec le fallback (CuisineAz parser).")
    # Fallback for unsupported domains currently routes to CuisineAz parser logic.
    return await CuisineAzScraper(url).scrape()
