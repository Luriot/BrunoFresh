import ast
from dataclasses import dataclass
import asyncio
import json
import logging
import re

import httpx

from ..config import settings
from .scrapers.types import ScrapedIngredient

logger = logging.getLogger(__name__)

# On limite à 3 requêtes simultanées pour ne pas noyer Ollama (surtout avec un modèle 14b)
ollama_semaphore = asyncio.Semaphore(3)


@dataclass
class NormalizedIngredient:
    name_en: str
    name_fr: str
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


# ── Canonical units (metric / European) ─────────────────────────────────────
CANONICAL_UNITS: dict[str, list[str]] = {
    "Poids":   ["g", "kg"],
    "Volume":  ["ml", "cl", "L"],
    "Cuisine": ["c. à soupe", "c. à thé", "tasse"],
    "Compte":  ["piece", "botte", "tranche", "boîte", "paquet", "gousse"],
    "Autre":   ["pincée", "au goût", "filet"],
}

_ALL_CANONICAL: frozenset[str] = frozenset(u for units in CANONICAL_UNITS.values() for u in units)
_CANONICAL_LOWER: dict[str, str] = {u.lower(): u for u in _ALL_CANONICAL}

# Alias map: non-canonical string → canonical unit (no quantity conversion)
_UNIT_ALIASES: dict[str, str] = {
    "piece": "piece", "pieces": "piece", "pcs": "piece", "pc": "piece",
    "pièce": "piece", "pièces": "piece", "item": "piece", "items": "piece",
    "unit": "piece", "units": "piece", "unité": "piece", "unités": "piece",
    "bunch": "botte", "bouquet": "botte",
    "slice": "tranche", "slices": "tranche",
    "can": "boîte", "cans": "boîte", "tin": "boîte", "tins": "boîte",
    "package": "paquet", "packages": "paquet", "pack": "paquet", "sachet": "paquet",
    "clove": "gousse", "cloves": "gousse",
    "pinch": "pincée", "pinches": "pincée",
    "to taste": "au goût", "as needed": "au goût", "as required": "au goût",
    "drizzle": "filet",
    "tablespoon": "c. à soupe", "tablespoons": "c. à soupe", "tbsp": "c. à soupe",
    "teaspoon": "c. à thé", "teaspoons": "c. à thé", "tsp": "c. à thé",
    "cup": "tasse", "cups": "tasse",
    "gram": "g", "grams": "g", "gramme": "g", "grammes": "g",
    "kilogram": "kg", "kilograms": "kg", "kilogramme": "kg", "kilogrammes": "kg",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "centiliter": "cl", "centiliters": "cl", "centilitre": "cl", "centilitres": "cl",
    "liter": "L", "liters": "L", "litre": "L", "litres": "L",
}

# Conversion map: non-metric unit → (canonical unit, conversion factor)
_UNIT_CONVERSIONS: dict[str, tuple[str, float]] = {
    "oz":           ("g",  28.3495),
    "ounce":        ("g",  28.3495),
    "ounces":       ("g",  28.3495),
    "lb":           ("kg", 0.453592),
    "lbs":          ("kg", 0.453592),
    "pound":        ("kg", 0.453592),
    "pounds":       ("kg", 0.453592),
    "fl oz":        ("ml", 29.5735),
    "fl. oz":       ("ml", 29.5735),
    "fluid ounce":  ("ml", 29.5735),
    "fluid ounces": ("ml", 29.5735),
}


def normalize_unit(unit: str, quantity: float) -> tuple[str, float]:
    """Return (canonical_unit, converted_quantity) for the given raw unit string."""
    raw = (unit or "").strip().lower()

    # Already canonical?
    if raw in _CANONICAL_LOWER:
        return _CANONICAL_LOWER[raw], quantity

    # Non-metric → metric conversion
    if raw in _UNIT_CONVERSIONS:
        canonical, factor = _UNIT_CONVERSIONS[raw]
        return canonical, round(quantity * factor, 4)

    # Alias without quantity conversion
    if raw in _UNIT_ALIASES:
        return _UNIT_ALIASES[raw], quantity

    # Unknown unit: default to "piece"
    return "piece", quantity


# ── Unit group helpers (for cross-unit aggregation in shopping lists) ────────
# Maps canonical unit → (group_name, base_unit, factor_to_base)
_UNIT_TO_GROUP_INFO: dict[str, tuple[str, str, float]] = {
    "g":   ("Poids",  "g",  1.0),
    "kg":  ("Poids",  "g",  1000.0),
    "ml":  ("Volume", "ml", 1.0),
    "cl":  ("Volume", "ml", 10.0),
    "L":   ("Volume", "ml", 1000.0),
}


def get_unit_group(unit: str) -> str | None:
    """Return the aggregation group name for a canonical unit, or None if not cross-mergeable."""
    info = _UNIT_TO_GROUP_INFO.get(unit)
    return info[0] if info else None


def to_base_unit(unit: str, qty: float) -> tuple[str, float]:
    """Convert qty from the given canonical unit to its group's base unit.

    Returns (base_unit, converted_qty). If the unit is not in a mergeable group
    the unit and qty are returned unchanged.
    """
    info = _UNIT_TO_GROUP_INFO.get(unit)
    if info is None:
        return unit, qty
    _, base_unit, factor = info
    return base_unit, qty * factor


def smart_display_unit(base_unit: str, total_qty: float) -> tuple[str, float]:
    """Rescale a base-unit quantity to the most readable display unit.

    - g  → kg  when total ≥ 1 000
    - ml → cl  when total ≥ 100
    - ml → L   when total ≥ 1 000
    """
    if base_unit == "g" and total_qty >= 1000:
        return "kg", round(total_qty / 1000, 2)
    if base_unit == "ml":
        if total_qty >= 1000:
            return "L", round(total_qty / 1000, 2)
        if total_qty >= 100:
            return "cl", round(total_qty / 10, 1)
    return base_unit, total_qty


# ── Ingredient-specific density table (culinary unit → grams) ───────────────
# Maps name_en → { canonical_unit → grams_per_1_unit }
# Only covers the most common ingredients where mixing g + c. à soupe is realistic.
_CULINARY_UNIT_DENSITIES: dict[str, dict[str, float]] = {
    "butter":          {"c. à soupe": 14.2, "c. à thé": 4.7,  "tasse": 227.0},
    "flour":           {"c. à soupe": 7.8,  "c. à thé": 2.6,  "tasse": 125.0},
    "all-purpose flour": {"c. à soupe": 7.8, "c. à thé": 2.6, "tasse": 125.0},
    "sugar":           {"c. à soupe": 12.5, "c. à thé": 4.2,  "tasse": 200.0},
    "brown sugar":     {"c. à soupe": 13.8, "c. à thé": 4.6,  "tasse": 220.0},
    "powdered sugar":  {"c. à soupe": 7.5,  "c. à thé": 2.5,  "tasse": 120.0},
    "icing sugar":     {"c. à soupe": 7.5,  "c. à thé": 2.5,  "tasse": 120.0},
    "salt":            {"c. à soupe": 18.0, "c. à thé": 6.0,  "pincée": 0.4},
    "black pepper":    {"c. à soupe": 6.0,  "c. à thé": 2.0,  "pincée": 0.3},
    "olive oil":       {"c. à soupe": 13.5, "c. à thé": 4.5,  "tasse": 216.0},
    "oil":             {"c. à soupe": 13.5, "c. à thé": 4.5,  "tasse": 218.0},
    "vegetable oil":   {"c. à soupe": 13.5, "c. à thé": 4.5,  "tasse": 218.0},
    "honey":           {"c. à soupe": 21.0, "c. à thé": 7.0,  "tasse": 336.0},
    "maple syrup":     {"c. à soupe": 20.0, "c. à thé": 6.7,  "tasse": 320.0},
    "cream":           {"c. à soupe": 15.0, "c. à thé": 5.0,  "tasse": 240.0},
    "heavy cream":     {"c. à soupe": 15.0, "c. à thé": 5.0,  "tasse": 240.0},
    "milk":            {"c. à soupe": 15.3, "c. à thé": 5.1,  "tasse": 245.0},
    "cocoa powder":    {"c. à soupe": 7.5,  "c. à thé": 2.5,  "tasse": 120.0},
    "baking powder":   {"c. à thé": 4.0},
    "baking soda":     {"c. à thé": 6.0},
    "cornstarch":      {"c. à soupe": 9.0,  "c. à thé": 3.0,  "tasse": 128.0},
    "vinegar":         {"c. à soupe": 15.0, "c. à thé": 5.0,  "tasse": 240.0},
    "soy sauce":       {"c. à soupe": 16.0, "c. à thé": 5.3},
    "mustard":         {"c. à soupe": 17.0, "c. à thé": 5.7},
    "tomato paste":    {"c. à soupe": 16.5, "c. à thé": 5.5},
    "cream cheese":    {"c. à soupe": 14.5, "c. à thé": 4.8,  "tasse": 232.0},
    "sour cream":      {"c. à soupe": 14.4, "c. à thé": 4.8,  "tasse": 230.0},
    "yogurt":          {"c. à soupe": 15.3, "c. à thé": 5.1,  "tasse": 245.0},
    "peanut butter":   {"c. à soupe": 16.0, "c. à thé": 5.3,  "tasse": 256.0},
    "almond flour":    {"c. à soupe": 7.0,  "c. à thé": 2.3,  "tasse": 112.0},
    "breadcrumbs":     {"c. à soupe": 7.5,  "c. à thé": 2.5,  "tasse": 120.0},
    "parmesan":        {"c. à soupe": 5.0,  "c. à thé": 1.7,  "tasse": 80.0},
    "cheddar":         {"c. à soupe": 7.0,  "c. à thé": 2.3,  "tasse": 113.0},
}


def culinary_to_grams(name_en: str, unit: str, qty: float) -> tuple[str, float] | None:
    """Convert a culinary unit to grams using per-ingredient density data.

    Returns ``("g", qty_in_grams)`` if a conversion is known, otherwise ``None``.
    Only applies to culinary units (c. à soupe, c. à thé, tasse, pincée) — metric
    units are left unchanged.
    """
    densities = _CULINARY_UNIT_DENSITIES.get(name_en.strip().lower())
    if not densities:
        return None
    grams_per_unit = densities.get(unit)
    if grams_per_unit is None:
        return None
    return "g", round(qty * grams_per_unit, 2)


def _coerce_unit(value: str) -> str:
    canonical, _ = normalize_unit(value or "", 1.0)
    return canonical


def _coerce_name_fr(value: str, fallback_name_en: str) -> str:
    candidate = (value or "").strip().lower()
    if candidate:
        return candidate
    return fallback_name_en


async def normalize_with_ollama(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    safe_raw = _sanitize_raw_ingredient(raw_string)
    raw = ""
    categories = ", ".join(settings.categories)
    canonical_units = ", ".join(u for units in CANONICAL_UNITS.values() for u in units)
    prompt = (
        "You are an ingredient parser. Return strict JSON only with keys: "
        "name_en, name_fr, quantity, unit, category. "
        f"Allowed units (metric/European only): {canonical_units}. "
        f"Allowed categories: {categories}. "
        "Translate ingredient names to both English and French. "
        "Do not return markdown. "
        f"Input ingredient: {safe_raw}. "
        f"Hint quantity={quantity}, unit={unit}."
    )

    try:
        async with ollama_semaphore:
            logger.debug(f"Demande de normalisation Ollama pour: '{safe_raw}'")
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": settings.ollama_temperature,
                            "num_predict": settings.ollama_num_predict,
                            "num_ctx": settings.ollama_num_ctx,
                        },
                    },
                )
                response.raise_for_status()
                
        payload = response.json()
        raw = payload.get("response", "")
        
        # Les modèles qwen/deepseek placent parfois le retour JSON dans la clé "thinking" 
        # quand ils sont contraints par "format": "json" (ou en raison d'un bug de l'API)
        if not raw.strip():
            raw = payload.get("thinking", "")
        
        # L'API publique peut parfois renvoyer une réponse complètement vide, ou encapsulée
        if not raw or not raw.strip():
            logger.warning(f"Ollama a répondu avec un contenu vide pour '{safe_raw}'. Payload: {payload}")
            return None
            
        # Nettoyer un éventuel markdown "```json" si Ollama force le formatage malgré "format: json"
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        
        parsed = json.loads(raw)

        name = str(parsed.get("name_en", "")).strip().lower()
        name_fr = _coerce_name_fr(str(parsed.get("name_fr", "")), name)
        parsed_qty = float(parsed.get("quantity", quantity))
        parsed_unit = _coerce_unit(str(parsed.get("unit", unit)))
        parsed_category = _coerce_category(str(parsed.get("category", "Other")))

        if not name:
            logger.warning(f"Ollama a retourné un nom vide pour l'ingrédient '{safe_raw}'")
            return None

        if parsed_qty < 0:
            parsed_qty = abs(parsed_qty)

        result = NormalizedIngredient(name, name_fr, parsed_qty, parsed_unit, parsed_category)
        logger.debug(f"Succès Ollama: '{safe_raw}' -> {result}")
        return result
        
    except json.JSONDecodeError:
        logger.error(f"Le JSON renvoyé par Ollama est invalide pour '{safe_raw}' : {raw}")
        return None
    except Exception as exc:
        logger.error(f"Erreur Ollama lors de la normalisation de '{safe_raw}': {exc}", exc_info=True)
        return None


_SECTION_HEADER_RE = re.compile(
    r"^(pour|for|sauce|marinade|garniture|dressing|topping|filling|croûte|crust|glaze|glaçage|base|pastry)",
    re.IGNORECASE,
)

# ── Unicode fraction normalisation (mirrored from scrapers/base.py) ──────────
_NORM_UNICODE_FRACS: dict[str, str] = {
    "½": "0.5", "⅓": "0.3333", "⅔": "0.6667", "¼": "0.25", "¾": "0.75",
    "⅛": "0.125", "⅜": "0.375", "⅝": "0.625", "⅞": "0.875",
    "⅙": "0.1667", "⅚": "0.8333", "⅕": "0.2", "⅖": "0.4", "⅗": "0.6", "⅘": "0.8",
}
_NORM_INT_FRAC_RE = re.compile(r"(\d+)([" + "".join(_NORM_UNICODE_FRACS) + r"])")
_NORM_FRAC_RE = re.compile("[" + "".join(_NORM_UNICODE_FRACS) + "]")


def _normalizer_preprocess_fractions(text: str) -> str:
    """Replace unicode fractions and ASCII fractions (1/2) with decimal strings."""
    def _merge(m: re.Match) -> str:
        return str(float(m.group(1)) + float(_NORM_UNICODE_FRACS[m.group(2)]))

    text = _NORM_INT_FRAC_RE.sub(_merge, text)
    text = _NORM_FRAC_RE.sub(lambda m: _NORM_UNICODE_FRACS[m.group(0)], text)
    return text


# Matches a leading number (integer, decimal with . or ,, or simple fraction like 1/2)
_LEADING_QTY_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)")
# Optionally also captures the unit that immediately follows the quantity
_LEADING_QTY_UNIT_RE = re.compile(
    r"^\s*\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?\s*(g|kg|ml|cl|L|l|piece|tranche|botte|c\.?\s*à\s*\w+)\b",
    re.IGNORECASE,
)


def _parse_qty_from_raw(raw: str) -> float:
    """Extract a leading numeric quantity from a raw ingredient string."""
    preprocessed = _normalizer_preprocess_fractions(raw.strip())
    m = _LEADING_QTY_RE.match(preprocessed)
    if not m:
        return 0.0
    qty_str = m.group(1)
    if "/" in qty_str:
        parts = qty_str.split("/")
        try:
            return float(parts[0].strip()) / float(parts[1].strip())
        except (ValueError, ZeroDivisionError):
            return 0.0
    return float(qty_str.replace(",", "."))


def _parse_unit_from_raw(raw: str) -> str:
    """Extract the canonical unit that immediately follows the leading number, or empty string."""
    preprocessed = _normalizer_preprocess_fractions(raw.strip())
    m = _LEADING_QTY_UNIT_RE.match(preprocessed)
    if not m:
        return ""
    canonical, _ = normalize_unit(m.group(1).strip(), 1.0)
    return canonical


def normalize_fallback(raw_string: str, quantity: float) -> NormalizedIngredient | None:
    # If the scraper left quantity=0, try to parse it from the raw string itself
    if quantity == 0:
        parsed = _parse_qty_from_raw(raw_string)
        if parsed > 0:
            quantity = parsed
    # Detect the unit from the raw string (used in last-resort and liquid ingredients)
    raw_unit = _parse_unit_from_raw(raw_string)

    text = raw_string.lower()

    def fallback(name_en: str, name_fr: str, qty: float, unit_value: str, category: str) -> NormalizedIngredient:
        return NormalizedIngredient(name_en, name_fr, qty, unit_value, category)

    # Ignorer les en-têtes de sections (multilingue)
    if _SECTION_HEADER_RE.match(raw_string.strip()):
        return fallback("section_header_ignore", "section_header_ignore", 0, "piece", "Other")

    if "garlic" in text or "ail" in text:
        return fallback("garlic", "ail", quantity, "piece", "Produce")
    if "tomato" in text or "tomate" in text:
        return fallback("tomato", "tomate", quantity, "g", "Produce")
    if "olive oil" in text or "huile" in text:
        return fallback("olive oil", "huile d olive", quantity, "ml", "Pantry")
    if "sel" in text or "salt" in text:
        return fallback("salt", "sel", max(1, quantity), "g", "Spices")
    if "poivre" in text or "pepper" in text:
        return fallback("black pepper", "poivre noir", max(1, quantity), "g", "Spices")
    if "beurre" in text or "butter" in text:
        return fallback("butter", "beurre", quantity, "g", "Dairy")
    if "oignon" in text or "onion" in text:
        return fallback("onion", "oignon", quantity, "piece", "Produce")
    if "lait" in text or "milk" in text:
        return fallback("milk", "lait", quantity, "ml", "Dairy")
    if "farine" in text or "flour" in text:
        return fallback("flour", "farine", quantity, "g", "Pantry")
    if "sucre" in text or "sugar" in text:
        return fallback("sugar", "sucre", quantity, "g", "Pantry")
    if "boeuf" in text or "bœuf" in text or "beef" in text:
        return fallback("ground beef", "boeuf hache", quantity, "g", "Meat")
    if "gruyère" in text or "gruyere" in text:
        return fallback("gruyere cheese", "fromage gruyere", quantity, "g", "Dairy")
    if "parmesan" in text:
        return fallback("parmesan cheese", "parmesan", quantity, "g", "Dairy")
    if "muscade" in text or "nutmeg" in text:
        return fallback("nutmeg", "muscade", max(1, quantity), "g", "Spices")
    if "herbe" in text or "herb" in text:
        return fallback("mixed herbs", "herbes melangees", max(1, quantity), "g", "Spices")
    if "lasagne" in text or "pâte" in text or "pasta" in text:
        return fallback("lasagna sheets", "feuilles de lasagne", quantity, "piece", "Pantry")
    if "œuf" in text or "oeuf" in text or "egg" in text:
        return fallback("egg", "oeuf", quantity, "piece", "Dairy")
    if "mascarpone" in text:
        return fallback("mascarpone", "mascarpone", quantity, "g", "Dairy")
    if "crème" in text or "creme" in text or "cream" in text:
        return fallback("cream", "crème", quantity, "ml", "Dairy")
    if "boudoir" in text or "biscuit" in text or "cookie" in text:
        return fallback("biscuit", "biscuit boudoir", quantity, "piece", "Pantry")
    if "citron" in text or "lemon" in text:
        is_juice = "jus" in text or "juice" in text
        u = raw_unit if raw_unit and raw_unit in ("ml", "cl", "L") else ("ml" if is_juice else "piece")
        return fallback(
            "lemon juice" if is_juice else "lemon",
            "jus de citron" if is_juice else "citron",
            quantity, u, "Produce"
        )
    if "fraise" in text or "strawberr" in text or "fraisier" in text:
        return fallback("strawberry", "fraise", quantity, "g", "Produce")
    if "vanille" in text or "vanilla" in text:
        return fallback("vanilla", "vanille", max(1, quantity), "piece", "Spices")
    if "chocolat" in text or "chocolate" in text:
        return fallback("chocolate", "chocolat", quantity, "g", "Pantry")
    if "vinaigre" in text or "vinegar" in text:
        return fallback("vinegar", "vinaigre", quantity, "ml", "Pantry")
    if "miel" in text or "honey" in text:
        return fallback("honey", "miel", quantity, "g", "Pantry")
    if "poulet" in text or "chicken" in text:
        return fallback("chicken", "poulet", quantity, "g", "Meat")
    if "porc" in text or "pork" in text or "lardons" in text:
        return fallback("pork", "porc", quantity, "g", "Meat")
    if "saumon" in text or "salmon" in text:
        return fallback("salmon", "saumon", quantity, "g", "Fish")
    if "thon" in text or "tuna" in text:
        return fallback("tuna", "thon", quantity, "g", "Fish")
    if "carotte" in text or "carrot" in text:
        return fallback("carrot", "carotte", quantity, raw_unit or "piece", "Produce")
    if "courgette" in text or "zucchini" in text:
        return fallback("zucchini", "courgette", quantity, raw_unit or "piece", "Produce")
    if "champignon" in text or "mushroom" in text:
        return fallback("mushroom", "champignon", quantity, raw_unit or "g", "Produce")
    if "pomme de terre" in text or "pommes de terre" in text or "potato" in text:
        return fallback("potato", "pomme de terre", quantity, raw_unit or "piece", "Produce")
    if "riz" in text or "rice" in text:
        return fallback("rice", "riz", quantity, "g", "Pantry")
    if "fromage" in text or "cheese" in text:
        return fallback("cheese", "fromage", quantity, "g", "Dairy")
    if "yaourt" in text or "yogurt" in text or "yoghurt" in text:
        return fallback("yogurt", "yaourt", quantity, "g", "Dairy")
    # Last resort: preserve the parsed quantity with a cleaned name rather than losing it
    clean_name = re.sub(r'^[\d\s.,/]+(?:g|kg|ml|cl|l|piece|tranche|botte)?\s*', '', raw_string, flags=re.I).strip()
    clean_name = re.sub(r'\(s\)', '', clean_name).strip()
    name = clean_name.lower()[:100] if clean_name else raw_string.strip().lower()[:100]
    u = raw_unit or "piece"
    return fallback(name, name, quantity, u, "Other")


# Nombre maximum d'ingrédients par appel Ollama.
# Au-delà, le modèle tend à ne retourner que le premier item ou à "penser" à voix haute.
_OLLAMA_BATCH_CHUNK_SIZE = 8


async def _ollama_parse_chunk(
    chunk: list[dict],
    categories_str: str,
    units_str: str,
) -> list[dict]:
    """Envoie un chunk d'ingrédients à Ollama et retourne la liste d'items parsés.

    Retourne une liste vide en cas d'erreur (l'appelant appliquera le fallback).
    """
    prompt = (
        "You are an ingredient parser. Return strict JSON ONLY. "
        "The root MUST be a JSON object with a single key 'ingredients' containing an array. "
        "Each object must have exactly these keys: idx, name_en, name_fr, quantity, unit, category. "
        'Example: {"ingredients": [{"idx": 0, "name_en": "tomato", "name_fr": "tomate", "quantity": 300.0, "unit": "g", "category": "Produce"}]}\n'
        f"Allowed units (metric/European only): {units_str}. "
        f"Allowed categories: {categories_str}. "
        "Translate ALL ingredient names to both English and French. "
        f"Process ALL {len(chunk)} items. Maintain the exact idx.\n\n"
        f"Input:\n{json.dumps(chunk, ensure_ascii=False)}"
    )

    try:
        async with ollama_semaphore:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": settings.ollama_temperature,
                            "num_predict": settings.ollama_num_predict,
                            "num_ctx": settings.ollama_num_ctx,
                        },
                    },
                )
                response.raise_for_status()

        payload = response.json()
        raw = (payload.get("response", "") or payload.get("thinking", "")).strip()
        if not raw:
            logger.warning("Chunk Ollama : réponse vide.")
            return []

        # Nettoyer un éventuel bloc markdown
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(raw)
                logger.warning("Chunk Ollama : ast.literal_eval utilisé (JSON strict invalide).")
            except Exception:
                logger.error(f"Chunk Ollama : JSON invalide. Brut (200 premiers chars) : {raw[:200]}")
                return []

        if isinstance(parsed, list):
            return parsed

        if isinstance(parsed, dict):
            # Cas normal : {"ingredients": [...]}
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            # Modèle n'a traité qu'un seul ingrédient
            if "idx" in parsed:
                logger.warning(
                    f"Chunk Ollama : un seul ingrédient retourné (idx={parsed.get('idx')}), "
                    f"{len(chunk) - 1} manquant(s) → fallback."
                )
                return [parsed]
            logger.warning(f"Chunk Ollama : dict sans liste ni idx. Clés : {list(parsed.keys())[:6]}")

        return []

    except Exception as exc:
        logger.error(f"Chunk Ollama : erreur inattendue : {exc}", exc_info=True)
        return []


async def normalize_ingredients_batch(ingredients: list[ScrapedIngredient]) -> list[NormalizedIngredient | None]:
    if not ingredients:
        return []

    input_list: list[dict[str, float | str | int] | None] = []
    for i, ing in enumerate(ingredients):
        safe_raw = _sanitize_raw_ingredient(ing.raw)
        # On pré-filtre les en-têtes de section directement ici (multilingue)
        if _SECTION_HEADER_RE.match(safe_raw.strip()):
            input_list.append(None)
            continue

        input_list.append({
            "idx": i,
            "raw": safe_raw,
            "quantity": ing.quantity,
            "unit": ing.unit
        })

    # Si tous les blocs étaient des en-têtes, pas besoin d'appeler Ollama
    if not any(item is not None for item in input_list):
        return [
            NormalizedIngredient("section_header_ignore", "section_header_ignore", 0, "piece", "Other")
            if item is None
            else None
            for item in input_list
        ]

    valid_inputs = [item for item in input_list if item is not None]

    categories_str = ", ".join(settings.categories)
    units_str = ", ".join(u for units in CANONICAL_UNITS.values() for u in units)

    # Découper en chunks pour éviter que le modèle ne tronque les grands lots
    chunks = [
        valid_inputs[i:i + _OLLAMA_BATCH_CHUNK_SIZE]
        for i in range(0, len(valid_inputs), _OLLAMA_BATCH_CHUNK_SIZE)
    ]
    logger.info(
        f"Demande de normalisation Ollama par LOT "
        f"({len(valid_inputs)} ingrédients, {len(chunks)} chunk(s) de ≤{_OLLAMA_BATCH_CHUNK_SIZE})..."
    )

    results: list[NormalizedIngredient | None] = [None] * len(ingredients)

    # Pré-remplir les en-têtes de section
    for pos, item in enumerate(input_list):
        if item is None:
            results[pos] = NormalizedIngredient(
                "section_header_ignore", "section_header_ignore", 0, "piece", "Other"
            )

    for chunk_no, chunk in enumerate(chunks, start=1):
        parsed_items = await _ollama_parse_chunk(chunk, categories_str, units_str)

        returned_idxs: set[int] = set()
        for item in parsed_items:
            if not isinstance(item, dict):
                continue

            idx = item.get("idx")
            if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(ingredients):
                continue

            name = str(item.get("name_en", "")).strip().lower()
            name_fr = _coerce_name_fr(str(item.get("name_fr", "")), name)
            try:
                qty = float(item.get("quantity", ingredients[idx].quantity))
            except (TypeError, ValueError):
                qty = float(ingredients[idx].quantity)
            parsed_unit = _coerce_unit(str(item.get("unit", ingredients[idx].unit)))
            parsed_category = _coerce_category(str(item.get("category", "Other")))

            if name:
                results[idx] = NormalizedIngredient(name, name_fr, abs(qty), parsed_unit, parsed_category)
                returned_idxs.add(idx)

        expected_idxs = {int(item["idx"]) for item in chunk}
        missing = expected_idxs - returned_idxs
        if missing:
            logger.warning(
                f"Chunk {chunk_no}/{len(chunks)} : {len(missing)} ingrédient(s) non retourné(s) "
                f"(idx={sorted(missing)}) → fallback keyword appliqué."
            )

    # Fallback pour tout ce qui n'a pas été résolu par Ollama
    for idx, res in enumerate(results):
        if res is None:
            orig = ingredients[idx]
            results[idx] = normalize_fallback(orig.raw, orig.quantity)

    logger.info("Normalisation batch terminée avec succès.")
    return results


# ── Name translation ──────────────────────────────────────────────────────

_LANG_NAMES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
}


async def translate_ingredient_name(
    name: str,
    from_lang: str,
    target_langs: list[str],
) -> dict[str, str]:
    """Translate a food ingredient name to multiple languages using Ollama.

    Returns a dict mapping lang_code → translated name.  The source language
    is always included unchanged.  On any Ollama failure the original name is
    used as the fallback for all target languages.
    """
    result: dict[str, str] = {from_lang: name}
    to_translate = [lang for lang in target_langs if lang != from_lang]
    if not to_translate:
        return result

    # Pre-populate fallbacks so we always return every requested lang
    for lang in to_translate:
        result[lang] = name

    from_name = _LANG_NAMES.get(from_lang, from_lang)
    targets_desc = ", ".join(
        f"{lang} ({_LANG_NAMES.get(lang, lang)})" for lang in to_translate
    )
    safe_name = _sanitize_raw_ingredient(name)
    prompt = (
        f"Translate this food ingredient name from {from_name} to: {targets_desc}. "
        f"Ingredient: \"{safe_name}\". "
        "Reply with JSON only — no markdown, no explanation. "
        "Example: {\"en\": \"flour\", \"fr\": \"farine\"}. "
        "Use the most common culinary name."
    )

    try:
        async with ollama_semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": settings.ollama_temperature,
                            "num_predict": settings.ollama_num_predict,
                            "num_ctx": settings.ollama_num_ctx,
                        },
                    },
                )
        resp.raise_for_status()
        raw_text = resp.json().get("response", "")

        # Strip markdown code fences if present
        raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()
        parsed = json.loads(raw_text)

        for lang in to_translate:
            val = parsed.get(lang, "")
            if isinstance(val, str) and val.strip():
                result[lang] = val.strip()

    except Exception:
        logger.warning(
            "translate_ingredient_name failed for '%s' — using original name as fallback", name
        )

    return result
