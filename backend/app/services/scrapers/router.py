from __future__ import annotations

from urllib.parse import urlparse

from .hellofresh import HelloFreshScraper
from .static_sites import AllRecipesFrScraper, CuisineAzScraper, JowScraper
from .types import ScrapedRecipe


def scrape_recipe_url(url: str) -> ScrapedRecipe:
    domain = urlparse(url).netloc.replace("www.", "")

    if "hellofresh" in domain:
        return HelloFreshScraper(url).scrape()
    if "cuisineaz" in domain:
        return CuisineAzScraper(url).scrape()
    if "allrecipes" in domain:
        return AllRecipesFrScraper(url).scrape()
    if "jow" in domain:
        return JowScraper(url).scrape()

    # Fallback for unsupported domains currently routes to CuisineAz parser logic.
    return CuisineAzScraper(url).scrape()
