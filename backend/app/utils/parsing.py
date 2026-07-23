"""Shared parsing helpers for scraped recipe data (nutrition, name normalisation)."""
from __future__ import annotations

import re

NUTRITION_JSONLD_KEY_MAP = {
    "calories": "kcal",
    "fatContent": "fat_g",
    "proteinContent": "protein_g",
    "carbohydrateContent": "carbs_g",
}


def parse_nutrition_int(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
        if digits:
            try:
                return int(round(float(digits)))
            except ValueError:
                return None
    return None


def extract_nutrition_from_jsonld(jsonld: dict | None) -> dict[str, int | None]:
    if not jsonld or not isinstance(jsonld, dict):
        return {}
    nutrition = jsonld.get("nutrition")
    if not isinstance(nutrition, dict):
        return {}
    result: dict[str, int | None] = {}
    for jsonld_key, field in NUTRITION_JSONLD_KEY_MAP.items():
        parsed = parse_nutrition_int(nutrition.get(jsonld_key))
        if parsed is not None:
            result[field] = parsed
    return result


_WS_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")


def normalize_name(text: str) -> str:
    """Lowercase, strip punctuation (keeps accented chars), collapse whitespace."""
    return _WS_RE.sub(" ", _NON_WORD_RE.sub(" ", text.lower().strip())).strip()
