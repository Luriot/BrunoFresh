from dataclasses import dataclass
import json

import httpx

from ..config import settings


@dataclass
class NormalizedIngredient:
    name_en: str
    quantity: float
    unit: str
    category: str


def _sanitize_raw_ingredient(value: str) -> str:
    # Keep only short, plain text snippets to reduce prompt-injection surface.
    cleaned = (value or "").replace("`", " ").replace("\n", " ").replace("\r", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned[:200]


def _coerce_category(value: str) -> str:
    value = (value or "Other").strip()
    if value in settings.categories:
        return value
    lowered = value.lower()
    for category in settings.categories:
        if category.lower() == lowered:
            return category
    return "Other"


def _coerce_unit(value: str) -> str:
    unit = (value or "piece").lower().strip()
    if unit in {"g", "gram", "grams"}:
        return "g"
    if unit in {"ml", "milliliter", "milliliters"}:
        return "ml"
    if unit in {"piece", "pieces", "pc"}:
        return "piece"
    return "piece"


def normalize_with_ollama(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    safe_raw = _sanitize_raw_ingredient(raw_string)
    categories = ", ".join(settings.categories)
    prompt = (
        "You are an ingredient parser. Return strict JSON only with keys: "
        "name_en, quantity, unit, category. "
        "Allowed units: g, ml, piece. "
        f"Allowed categories: {categories}. "
        "Translate ingredient names to English. "
        "Do not return markdown. "
        f"Input ingredient: {safe_raw}. "
        f"Hint quantity={quantity}, unit={unit}."
    )

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = response.json()
            raw = payload.get("response", "{}")
            parsed = json.loads(raw)

        name = str(parsed.get("name_en", "")).strip().lower()
        parsed_qty = float(parsed.get("quantity", quantity))
        parsed_unit = _coerce_unit(str(parsed.get("unit", unit)))
        parsed_category = _coerce_category(str(parsed.get("category", "Other")))

        if not name:
            return None

        if parsed_qty < 0:
            parsed_qty = abs(parsed_qty)

        return NormalizedIngredient(name, parsed_qty, parsed_unit, parsed_category)
    except Exception:
        return None


def normalize_fallback(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    text = raw_string.lower()
    if "garlic" in text or "ail" in text:
        return NormalizedIngredient("garlic", quantity, "piece", "Produce")
    if "tomato" in text or "tomate" in text:
        return NormalizedIngredient("tomato", quantity, "g", "Produce")
    if "olive oil" in text or "huile" in text:
        return NormalizedIngredient("olive oil", quantity, "ml", "Pantry")
    if "sel" in text or "salt" in text:
        return NormalizedIngredient("salt", max(1, quantity), "g", "Spices")
    if "poivre" in text or "pepper" in text:
        return NormalizedIngredient("black pepper", max(1, quantity), "g", "Spices")
    if "beurre" in text or "butter" in text:
        return NormalizedIngredient("butter", quantity, "g", "Dairy")
    if "oignon" in text or "onion" in text:
        return NormalizedIngredient("onion", quantity, "piece", "Produce")
    return None


def normalize_ingredient(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    llm_value = normalize_with_ollama(raw_string, quantity, unit)
    if llm_value:
        return llm_value
    return normalize_fallback(raw_string, quantity, unit)
