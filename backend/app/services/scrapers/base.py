from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .types import ScrapedIngredient, ScrapedRecipe


class BaseScraper(ABC):
    def __init__(self, url: str):
        self.url = url
        self.domain = urlparse(url).netloc.replace("www.", "")

    async def _get_html(self) -> str:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            response = await client.get(self.url, headers={"User-Agent": "BrunoFreshBot/1.0"})
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

    def _parse_ingredient_line(self, line: str) -> ScrapedIngredient:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if not cleaned:
            return ScrapedIngredient(raw="", quantity=0, unit="unparsed")

        match = re.match(r"^(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]+)?\s*(.*)$", cleaned)
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
