from __future__ import annotations

import re
from urllib.parse import urlparse

from rapidfuzz import fuzz

# Matches the CDN version-hash suffix appended by HelloFresh/Cloudinary:
# "HF_Y25_..._Main_3_high-cf1af71a.jpg"  →  strip "-cf1af71a"
# The hash is 6–16 lowercase hex chars preceded by a hyphen.
_IMAGE_CDN_HASH_RE = re.compile(r"-[0-9a-f]{6,16}(\.[^.]+)$", re.IGNORECASE)


def extract_image_base_key(url: str | None) -> str | None:
    """Return a stable fingerprint for an image URL by stripping CDN version hashes.

    HelloFresh (and other Cloudinary-backed CDNs) append a short hex hash to
    image filenames that changes whenever the asset is re-processed, even though
    the visual content stays identical.  Stripping that suffix gives a key that
    is stable across re-publishes of the same recipe image.

    Examples
    --------
    >>> extract_image_base_key(
    ...     "https://img.hellofresh.com/.../HF_Y25_R202_W40_FR_QFR20943-16_Main_3_high-cf1af71a.jpg"
    ... )
    'HF_Y25_R202_W40_FR_QFR20943-16_Main_3_high'
    >>> extract_image_base_key(None)
    None
    """
    if not url:
        return None
    try:
        path = urlparse(url).path          # e.g. /hellofresh_s3/image/HF_...-cf1af71a.jpg
        filename = path.rsplit("/", 1)[-1]  # HF_...-cf1af71a.jpg
        m = _IMAGE_CDN_HASH_RE.search(filename)
        if m:
            # Remove the "-<hash>" portion → base stem only
            return filename[: m.start()]
        return None  # URL doesn't match the expected pattern → no reliable key
    except Exception:
        return None


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


def similarity_score(
    existing_title: str,
    existing_ingredient_names: list[str],
    new_title: str,
    new_ingredient_names: list[str],
) -> tuple[float, float]:
    """Return (title_score 0–100, ingredient_jaccard 0–1)."""
    title_score = fuzz.token_set_ratio(_normalize_text(existing_title), _normalize_text(new_title))
    existing_set = {_normalize_text(x) for x in existing_ingredient_names if x.strip()}
    new_set = {_normalize_text(x) for x in new_ingredient_names if x.strip()}
    ingredient_score = _jaccard_similarity(existing_set, new_set)
    return float(title_score), ingredient_score


def looks_like_duplicate(
    existing_title: str,
    existing_ingredient_names: list[str],
    new_title: str,
    new_ingredient_names: list[str],
    title_threshold: int = 85,
    ingredients_threshold: float = 0.7,
) -> bool:
    ts, ing = similarity_score(existing_title, existing_ingredient_names, new_title, new_ingredient_names)
    return ts >= title_threshold and ing >= ingredients_threshold
