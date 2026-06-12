from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field

import httpx
from rapidfuzz import fuzz

from .dedupe import extract_image_base_key

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
_HF_HOME_URL = "https://www.hellofresh.fr/"
_HF_SEARCH_URL = "https://gw.hellofresh.com/api/recipes/search"
# Fallback CDN base used when the API omits the full imageLink field.
_HF_IMAGE_BASE = "https://img.hellofresh.com/f_auto,fl_lossy,q_auto,w_500/hellofresh_s3"
_HF_RECIPE_BASE = "https://www.hellofresh.fr/recettes"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# ─── Guest token cache (extracted from hellofresh.fr __NEXT_DATA__) ───────────
_token_cache: dict[str, object] = {}
_token_lock = asyncio.Lock()


async def _fetch_guest_token() -> tuple[str | None, float]:
    """Scrape the guest JWT embedded in hellofresh.fr's __NEXT_DATA__."""
    try:
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(_HF_HOME_URL)
            resp.raise_for_status()
            html = resp.text

        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not m:
            logger.warning("HF: __NEXT_DATA__ not found on homepage")
            return None, 0.0

        data = json.loads(m.group(1))
        server_auth = (
            data.get("props", {})
            .get("pageProps", {})
            .get("ssrPayload", {})
            .get("serverAuth", {})
        )
        token: str | None = server_auth.get("access_token")
        expires_in = int(server_auth.get("expires_in", 3600))
        issued_at = int(server_auth.get("issued_at", time.time()))
        expires_at = issued_at + expires_in - 60
        return token, float(expires_at)
    except Exception as exc:
        logger.warning("HF guest token fetch failed: %s", exc)
        return None, 0.0


async def _get_hf_token() -> str | None:
    async with _token_lock:
        now = time.time()
        if _token_cache.get("token") and float(_token_cache.get("expires_at", 0)) > now:
            return str(_token_cache["token"])
        token, expires_at = await _fetch_guest_token()
        _token_cache["token"] = token
        _token_cache["expires_at"] = expires_at
        return token


# ─── Data model ───────────────────────────────────────────────────────────────
@dataclass
class HFRecipeHit:
    id: str
    name: str
    image_url: str | None
    tags: list[str] = field(default_factory=list)
    total_time_minutes: int | None = None
    hf_url: str = ""
    kcal: int | None = None
    protein_g: int | None = None
    carbs_g: int | None = None
    fat_g: int | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _build_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"{_HF_IMAGE_BASE}/{image_path.lstrip('/')}"


def _parse_iso_duration(value: object) -> int | None:
    """Convert ISO 8601 duration (PT30M, PT1H15M) or plain int to minutes."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        m = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?", value)
        if m:
            hours = int(m.group(1) or 0)
            minutes = int(m.group(2) or 0)
            return hours * 60 + minutes
    return None


def _normalize_name(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)  # remove punctuation (,  & ' etc.) but keep accented chars
    text = re.sub(r"\s+", " ", text)
    return text.strip()


_LABEL_ROUGE_RE = re.compile(r"\blabel\s+rouge\b", re.IGNORECASE)


def _is_label_rouge(hit: HFRecipeHit) -> bool:
    """Return True if the hit is a 'Label Rouge' variant (name or tags)."""
    if _LABEL_ROUGE_RE.search(hit.name):
        return True
    return any(_LABEL_ROUGE_RE.search(t) for t in hit.tags)


def _dedupe_by_name_similarity(
    hits: list[HFRecipeHit],
    threshold: int = 80,
) -> list[HFRecipeHit]:
    """Remove hits whose image or name is too similar to an already-accepted hit.

    **Tier 1 – image base key** (zero cost, no downloads): if two hits share the
    same stable image filename (after stripping the CDN version-hash suffix), they
    are the same recipe regardless of their title.

    **Tier 2 – name similarity**: uses fuzz.token_set_ratio so that subset-names
    (e.g. 'Poulet rôti' vs 'Poulet rôti aux herbes de Provence') are also caught.
    """
    accepted: list[HFRecipeHit] = []
    accepted_base_keys: list[str | None] = []

    # Label Rouge variants are deprioritised: sort them to the end so that when
    # a duplicate is detected the non-label-rouge version is always kept first.
    hits = sorted(hits, key=_is_label_rouge)

    for hit in hits:
        hit_key = extract_image_base_key(hit.image_url)

        # ── Tier 1: identical image base key → definite duplicate ────────────
        if hit_key and any(hit_key == k for k in accepted_base_keys if k):
            logger.debug("HF dedup (image key): skipping '%s' (key=%s)", hit.name, hit_key)
            continue

        # ── Tier 2: name similarity ───────────────────────────────────────────
        norm = _normalize_name(hit.name)
        if any(fuzz.token_set_ratio(norm, _normalize_name(a.name)) >= threshold for a in accepted):
            logger.debug("HF dedup (name): skipping '%s'", hit.name)
            continue

        accepted.append(hit)
        accepted_base_keys.append(hit_key)

    return accepted


def _parse_nutrition_int(value: object) -> int | None:
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


def _items_to_hits(items: list[dict]) -> list[HFRecipeHit]:
    seen_slugs: set[str] = set()
    hits: list[HFRecipeHit] = []
    for item in items:
        slug: str = item.get("slug", "")
        # Deduplicate variant products sharing the same slug
        if slug and slug in seen_slugs:
            continue
        if slug:
            seen_slugs.add(slug)

        recipe_id: str = str(item.get("id", ""))
        # Prefer the direct websiteUrl from the API; fall back to constructing it
        hf_url: str = (
            item.get("websiteUrl")
            or (f"{_HF_RECIPE_BASE}/{slug}" if slug else "")
        )
        # Prefer imagePath → img.hellofresh.com (reliable) over imageLink which
        # currently returns a broken CloudFront distribution (502).
        image_url: str | None = (
            _build_image_url(item.get("imagePath"))
            or item.get("imageLink")
        )
        tags = [t.get("name", "") for t in item.get("tags", []) if t.get("name")]
        total_time = _parse_iso_duration(item.get("totalTime"))
        nutrition = item.get("nutrition") or {}
        if not nutrition:
            nutrition = item.get("calories") or {}
        kcal = _parse_nutrition_int(nutrition.get("kcal") or nutrition.get("calories") or nutrition.get("caloriesPerServing"))
        protein_g = _parse_nutrition_int(nutrition.get("protein") or nutrition.get("proteinContent"))
        carbs_g = _parse_nutrition_int(nutrition.get("carbs") or nutrition.get("carbohydrateContent"))
        fat_g = _parse_nutrition_int(nutrition.get("fat") or nutrition.get("fatContent"))
        hits.append(HFRecipeHit(
            id=recipe_id,
            name=item.get("name", ""),
            image_url=image_url,
            tags=tags,
            total_time_minutes=total_time,
            hf_url=hf_url,
            kcal=kcal,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
        ))
    return hits


# ─── Primary: official API ────────────────────────────────────────────────────
async def _search_via_api(query: str, take: int) -> list[HFRecipeHit] | None:
    token = await _get_hf_token()
    if not token:
        return None
    params = {
        "q": query,
        "country": "fr",
        "locale": "fr-FR",
        "take": take,
        "skip": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            resp = await client.get(
                _HF_SEARCH_URL,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not isinstance(items, list):
                return None
            return _items_to_hits(items)
    except Exception as exc:
        logger.warning("HF API search failed: %s", exc)
        return None


# ─── Public API ───────────────────────────────────────────────────────────────
async def search_hf_recipes(query: str, take: int = 20) -> list[HFRecipeHit]:
    """Search HelloFresh recipes (fr-FR). Fetches guest token from hellofresh.fr.

    Fetches up to take*3 results from the HF API (capped at 60) so that
    name-similarity deduplication still yields ~take distinct recipes.
    """
    fetch = min(take * 3, 60)
    result = await _search_via_api(query, fetch)
    if result is None:
        return []
    unique = _dedupe_by_name_similarity(result)
    return unique[:take]
