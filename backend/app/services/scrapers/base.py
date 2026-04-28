from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

import httpx
from bs4 import BeautifulSoup

from .types import ScrapedIngredient, ScrapedRecipe

# ── Unicode fraction normalisation ────────────────────────────────────────────
_UNICODE_FRACS: dict[str, str] = {
    "½": "0.5",
    "⅓": "0.3333",
    "⅔": "0.6667",
    "¼": "0.25",
    "¾": "0.75",
    "⅛": "0.125",
    "⅜": "0.375",
    "⅝": "0.625",
    "⅞": "0.875",
    "⅙": "0.1667",
    "⅚": "0.8333",
    "⅕": "0.2",
    "⅖": "0.4",
    "⅗": "0.6",
    "⅘": "0.8",
}

# Matches an optional leading integer followed immediately by a unicode fraction (e.g. "1½")
_INT_UNICODE_FRAC_RE = re.compile(r"(\d+)([" + "".join(_UNICODE_FRACS) + r"])")
# Matches a standalone unicode fraction
_UNICODE_FRAC_RE = re.compile("[" + "".join(_UNICODE_FRACS) + "]")
# Matches ASCII fractions like 1/2, 2/3 at the start
_ASCII_FRAC_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def _preprocess_fractions(text: str) -> str:
    """Normalise unicode fractions and ASCII fractions to decimal strings."""
    # Handle "1½" → "1.5"
    def _merge(m: re.Match) -> str:
        integer = float(m.group(1))
        frac = float(_UNICODE_FRACS[m.group(2)])
        return str(integer + frac)

    text = _INT_UNICODE_FRAC_RE.sub(_merge, text)
    # Handle standalone "½" → "0.5"
    text = _UNICODE_FRAC_RE.sub(lambda m: _UNICODE_FRACS[m.group(0)], text)
    # Handle ASCII "1/2" → "0.5"
    def _ascii_frac(m: re.Match) -> str:
        denominator = float(m.group(2))
        if denominator == 0:
            return m.group(0)
        return str(round(float(m.group(1)) / denominator, 4))

    text = _ASCII_FRAC_RE.sub(_ascii_frac, text)
    return text


class BaseScraper(ABC):
    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc.replace("www.", "")

    async def _get_html(self) -> str:
        logger.debug(f"[_get_html] Lancement du Web Scraping de la page web sur: {self.url}")
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(self.url, headers={"User-Agent": "BrunoFreshBot/1.0"})
            logger.debug(f"[{response.status_code}] Récupération de la page HTML terminée.")
            response.raise_for_status()
            return response.text

    def _extract_jsonld(self, soup: BeautifulSoup) -> dict | None:
        scripts = soup.select('script[type="application/ld+json"]')
        for script in scripts:
            try:
                payload = json.loads(script.get_text(strip=True))
            except Exception:
                continue
            candidates = payload if isinstance(payload, list) else [payload]
            for item in candidates:
                if isinstance(item, dict) and (
                    item.get("@type") == "Recipe"
                    or (isinstance(item.get("@type"), list) and "Recipe" in item.get("@type"))
                ):
                    return item
                if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                    for graph_item in item["@graph"]:
                        if isinstance(graph_item, dict) and graph_item.get("@type") == "Recipe":
                            return graph_item
        return None

    def _extract_instruction_steps(self, jsonld: dict) -> list[dict]:
        """Extract structured steps with optional images from JSON-LD recipeInstructions."""
        steps: list[dict] = []
        raw = jsonld.get("recipeInstructions")
        if not isinstance(raw, list):
            return steps
        for item in raw:
            if isinstance(item, str) and item.strip():
                steps.append({"text": item.strip(), "image_url": None})
            elif isinstance(item, dict):
                text = item.get("text", "").strip()
                if not text:
                    continue
                # image may be a string URL or a list/dict with "url"
                image_raw = item.get("image")
                if isinstance(image_raw, str):
                    image_url: str | None = image_raw
                elif isinstance(image_raw, dict):
                    image_url = image_raw.get("url")
                elif isinstance(image_raw, list) and image_raw:
                    first = image_raw[0]
                    if isinstance(first, str):
                        image_url = first
                    elif isinstance(first, dict):
                        image_url = first.get("url")
                    else:
                        image_url = None
                else:
                    image_url = None
                steps.append({"text": text, "image_url": image_url})
        return steps

    def _parse_ingredient_line(self, line: str) -> ScrapedIngredient:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if not cleaned:
            return ScrapedIngredient(raw="", quantity=0, unit="unparsed")

        cleaned_for_parse = _preprocess_fractions(cleaned)
        match = re.match(r"^(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]+)?\s*(.*)$", cleaned_for_parse)
        if not match:
            return ScrapedIngredient(raw=cleaned, quantity=0, unit="unparsed")

        qty = float(match.group(1).replace(",", "."))
        unit = (match.group(2) or "piece").lower()
        raw = cleaned
        unit_map = {
            "g": "g",
            "kg": "g",
            "ml": "ml",
            "l": "ml",
            "cl": "ml",
            "tbsp": "ml",
            "c": "ml",
            "cc": "ml",
            "pcs": "piece",
            "piece": "piece",
        }
        normalized_unit = unit_map.get(unit, "piece")

        if unit == "kg":
            qty *= 1000
        elif unit == "l":
            qty *= 1000
        elif unit == "cl":
            qty *= 10
        elif unit in {"tbsp", "c", "cc"}:
            qty *= 15

        return ScrapedIngredient(raw=raw, quantity=qty, unit=normalized_unit)

    def _fallback_recipe(self) -> ScrapedRecipe:
        title = f"Imported recipe from {self.domain}"
        return ScrapedRecipe(
            title=title,
            source_domain=self.domain,
            image_url=None,
            instructions_text="1. Prep ingredients\n2. Cook\n3. Serve",
            base_servings=2,
            prep_time_minutes=None,
            ingredients=[
                ScrapedIngredient(raw="2 cloves garlic", quantity=2, unit="piece"),
                ScrapedIngredient(raw="400 g tomatoes", quantity=400, unit="g"),
            ],
        )

    @abstractmethod
    async def scrape(self) -> ScrapedRecipe:
        raise NotImplementedError
