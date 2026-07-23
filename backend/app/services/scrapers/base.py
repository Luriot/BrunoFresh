"""Shared helpers for the recipe scrapers: JSON-LD extraction, step/ingredient parsing."""
from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

from .types import ScrapedIngredient, ScrapedRecipe
from ...utils.fractions import preprocess_fractions as _preprocess_fractions
from ..network import create_ssrf_safe_client

logger = logging.getLogger(__name__)


async def get_html(url: str) -> str:
    logger.debug(f"[get_html] Lancement du Web Scraping de la page web sur: {url}")
    async with create_ssrf_safe_client(timeout=30, user_agent="BrunoFreshBot/1.0") as client:
        response = await client.get(url)
        logger.debug(f"[{response.status_code}] Récupération de la page HTML terminée.")
        response.raise_for_status()
        return response.text


def find_recipe_jsonld(soup: BeautifulSoup) -> dict | None:
    """Return the first JSON-LD ``Recipe`` object found in the page, or None."""
    for script in soup.select('script[type="application/ld+json"]'):
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


def _extract_step_image_url(image_raw: object) -> str | None:
    """Extract a URL string from a JSON-LD image field (string, ImageObject dict, or list)."""
    if isinstance(image_raw, str):
        return image_raw
    if isinstance(image_raw, dict):
        return image_raw.get("url")
    if isinstance(image_raw, list) and image_raw:
        first = image_raw[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url")
    return None


def _parse_step_text(text: str, image_url: str | None) -> list[dict]:
    """Convert a step text (possibly HTML) to a single plain-text step dict.

    If the text is an HTML list, <li> items are joined with newlines into
    one step so that the 1-to-1 mapping between JSON-LD HowToStep and cook
    mode step is preserved (together with the step image).
    """
    if "<" not in text:
        return [{"text": text, "image_url": image_url}] if text.strip() else []
    soup = BeautifulSoup(text, "html.parser")
    li_items = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
    if li_items:
        plain = "\n".join(f"• {item}" for item in li_items)
    else:
        plain = soup.get_text(" ", strip=True)
    return [{"text": plain, "image_url": image_url}] if plain.strip() else []


def _steps_from_instructions_list(raw: list) -> list[dict]:
    """Recursively extract steps from a JSON-LD recipeInstructions list.

    Handles plain strings, HowToStep dicts, and HowToSection dicts
    (which nest steps inside ``itemListElement``).
    """
    steps: list[dict] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            steps.extend(_parse_step_text(item.strip(), None))
        elif isinstance(item, dict):
            item_type = item.get("@type", "")
            # HowToSection nests steps inside itemListElement — recurse
            if item_type == "HowToSection":
                nested = item.get("itemListElement", [])
                if isinstance(nested, list):
                    steps.extend(_steps_from_instructions_list(nested))
                continue
            text = item.get("text", "").strip()
            if not text:
                continue
            image_url = _extract_step_image_url(item.get("image"))
            steps.extend(_parse_step_text(text, image_url))
    return steps


def extract_instruction_steps(jsonld: dict) -> list[dict]:
    """Extract structured steps with optional images from JSON-LD recipeInstructions."""
    raw = jsonld.get("recipeInstructions")
    if not isinstance(raw, list):
        return []
    return _steps_from_instructions_list(raw)


def _extract_step_images_from_nextdata(html: str) -> list[str | None]:
    """Extract ordered step image URLs from HelloFresh __NEXT_DATA__ SSR JSON.

    Returns a list of URLs (or None) in step order, or an empty list if not found.
    """
    _HF_STEP_CDN = "https://img.hellofresh.com/f_auto,fl_lossy,q_auto,w_640/hellofresh_s3"
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    ssr = data.get("props", {}).get("pageProps", {}).get("ssrPayload", {})
    recipe_data = ssr.get("recipe", {})
    steps_raw = recipe_data.get("steps", [])
    if not isinstance(steps_raw, list) or not steps_raw:
        return []
    # Sort by index field so order is reliable
    steps_sorted = sorted(steps_raw, key=lambda s: s.get("index", 0))
    result: list[str | None] = []
    for step in steps_sorted:
        imgs = step.get("images", [])
        url: str | None = None
        if isinstance(imgs, list) and imgs:
            first = imgs[0]
            if isinstance(first, dict):
                path = first.get("path") or first.get("link") or ""
                if path:
                    url = f"{_HF_STEP_CDN}/{path.lstrip('/')}"
            elif isinstance(first, str):
                url = first if first.startswith("http") else f"{_HF_STEP_CDN}/{first.lstrip('/')}"
        result.append(url)
    return result


def extract_steps_from_html(html: str) -> list[dict]:
    """Parse JSON-LD from raw HTML and return instruction steps with optional image_url."""
    soup = BeautifulSoup(html, "html.parser")
    jsonld = find_recipe_jsonld(soup)
    if not jsonld:
        return []
    steps = extract_instruction_steps(jsonld)

    # If JSON-LD yielded no step images, try to pull them from __NEXT_DATA__ (HelloFresh SSR)
    has_any_image = any(s.get("image_url") for s in steps)
    if not has_any_image and steps:
        next_images = _extract_step_images_from_nextdata(html)
        if next_images:
            for i, step in enumerate(steps):
                if i < len(next_images):
                    step["image_url"] = next_images[i]

    return steps


def parse_ingredient_line(line: str) -> ScrapedIngredient:
    cleaned = re.sub(r"\s+", " ", line).strip()
    if not cleaned:
        return ScrapedIngredient(raw="", quantity=0, unit="unparsed")

    cleaned_for_parse = _preprocess_fractions(cleaned)
    match = re.match(r"^(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]+)?\s*(.*)$", cleaned_for_parse)
    if not match:
        return ScrapedIngredient(raw=cleaned, quantity=0, unit="unparsed")

    qty = float(match.group(1).replace(",", "."))
    unit = (match.group(2) or "piece").lower()
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

    return ScrapedIngredient(raw=cleaned, quantity=qty, unit=normalized_unit)


def fallback_recipe(domain: str) -> ScrapedRecipe:
    return ScrapedRecipe(
        title=f"Imported recipe from {domain}",
        source_domain=domain,
        image_url=None,
        instructions_text="1. Prep ingredients\n2. Cook\n3. Serve",
        base_servings=2,
        prep_time_minutes=None,
        ingredients=[
            ScrapedIngredient(raw="2 cloves garlic", quantity=2, unit="piece"),
            ScrapedIngredient(raw="400 g tomatoes", quantity=400, unit="g"),
        ],
    )
