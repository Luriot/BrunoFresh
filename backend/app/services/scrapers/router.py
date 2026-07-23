from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

from recipe_scrapers import scrape_html  # type: ignore

_PAREN_DUP_RE = re.compile(r'^(.+)\(\1\)\s*$')


def _clean_raw_ingredient(line: str) -> str:
    """Strip duplicate trailing parenthetical: '1 cl citron(1 cl citron)' → '1 cl citron'."""
    stripped = line.strip()
    m = _PAREN_DUP_RE.match(stripped)
    return m.group(1).strip() if m else stripped

from .base import extract_steps_from_html
from .static_sites import scrape_static
from .types import ScrapedIngredient, ScrapedRecipe
from ...utils.parsing import NUTRITION_JSONLD_KEY_MAP, parse_nutrition_int

logger = logging.getLogger(__name__)


def _extract_nutrition(scraper) -> dict[str, int | None]:
    try:
        nutrients = scraper.nutrients()
    except Exception:
        return {}
    if not isinstance(nutrients, dict):
        return {}
    result: dict[str, int | None] = {}
    for api_key, field in NUTRITION_JSONLD_KEY_MAP.items():
        parsed = parse_nutrition_int(nutrients.get(api_key))
        if parsed is not None:
            result[field] = parsed
    return result


def _try_recipe_scrapers(url: str) -> ScrapedRecipe | None:
    """Attempt to scrape using the recipe-scrapers library (600+ sites)."""
    import httpx

    try:
        from ..network import SSRFGuardedSyncTransport

        transport = SSRFGuardedSyncTransport()
        with httpx.Client(transport=transport, timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html_text = resp.text

        scraper = scrape_html(html_text, org_url=url)
        title = scraper.title() or ""
        if not title:
            return None

        raw_ingredients = []
        try:
            raw_ingredients = scraper.ingredients() or []
        except Exception:
            pass

        instructions_text = ""
        try:
            instructions_text = scraper.instructions() or ""
        except Exception:
            pass

        image_url = None
        try:
            image_url = scraper.image()
        except Exception:
            pass

        base_servings = 2
        try:
            yields = scraper.yields() or ""
            digits = "".join(ch for ch in str(yields) if ch.isdigit())
            if digits:
                base_servings = max(1, int(digits))
        except Exception:
            pass

        prep_time_minutes = None
        try:
            prep_time_minutes = scraper.prep_time()
        except Exception:
            pass

        domain = urlparse(url).netloc.replace("www.", "")
        ingredients = [
            ScrapedIngredient(raw=_clean_raw_ingredient(line), quantity=0, unit="")
            for line in raw_ingredients
            if line.strip()
        ]
        instruction_steps = extract_steps_from_html(html_text)
        nutrition = _extract_nutrition(scraper)
        return ScrapedRecipe(
            title=title,
            source_domain=domain,
            image_url=image_url,
            instructions_text=instructions_text,
            base_servings=base_servings,
            prep_time_minutes=prep_time_minutes,
            ingredients=ingredients,
            instruction_steps=instruction_steps,
            **nutrition,
        )
    except Exception as exc:
        logger.debug(f"recipe-scrapers n'a pas pu parser '{url}': {exc}")
        return None


async def scrape_recipe_url(url: str) -> ScrapedRecipe:
    domain = urlparse(url).netloc.replace("www.", "")
    logger.debug(f"Tentative avec recipe-scrapers pour : {domain}")

    # recipe-scrapers covers 600+ sites including HelloFresh, AllRecipes, CuisineAZ, etc.
    rs_result = await asyncio.to_thread(_try_recipe_scrapers, url)
    if rs_result and rs_result.title:
        logger.info(f"recipe-scrapers a réussi pour '{url}' ({len(rs_result.ingredients)} ingrédients)")
        return rs_result

    # Generic JSON-LD fallback for any remaining domain with structured recipe data.
    logger.warning(f"recipe-scrapers n'a pas pu parser '{domain}', tentative avec le parseur JSON-LD générique.")
    return await scrape_static(url)
