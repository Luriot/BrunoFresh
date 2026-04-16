from __future__ import annotations

import re

from rapidfuzz import fuzz


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    return inter / max(union, 1)


def looks_like_duplicate(
    existing_title: str,
    existing_ingredient_names: list[str],
    new_title: str,
    new_ingredient_names: list[str],
    title_threshold: int = 85,
    ingredients_threshold: float = 0.7,
) -> bool:
    title_score = fuzz.token_set_ratio(_normalize_text(existing_title), _normalize_text(new_title))
    if title_score < title_threshold:
        return False

    existing_set = {_normalize_text(x) for x in existing_ingredient_names if x.strip()}
    new_set = {_normalize_text(x) for x in new_ingredient_names if x.strip()}
    ingredient_score = _jaccard_similarity(existing_set, new_set)
    return ingredient_score >= ingredients_threshold
