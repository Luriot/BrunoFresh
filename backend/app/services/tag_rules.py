"""Tag auto-detection rules.

Each entry maps a canonical tag name (as stored in the DB) to a list of
trigger keywords.  All matching is case-insensitive substring search against
the concatenation of the recipe title and normalised ingredient names.

The tag name itself is *always* an implicit keyword – no need to repeat it.
"""

from __future__ import annotations

from ..models import Tag

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RAPIDE_MAX_MINUTES: int = 30
"""Recipes with prep_time_minutes ≤ this value receive the "Rapide" tag."""

KEYWORDS: dict[str, list[str]] = {
    # "Rapide" is handled separately via prep_time_minutes – no text keywords.
    "Rapide": [],

    "Végétarien": [
        "vegetarian", "veggie", "sans viande", "tofu",
        "quiche", "gratin", "ratatouille", "tarte aux légumes",
    ],
    "Végan": [
        "vegan", "plant-based",
    ],
    "Épicé": [
        "spicy", "piment", "harissa", "curry", "chili",
        "jalapeño", "sambal", "sriracha", "cayenne",
    ],
    "Peu de vaisselle": [
        "une poêle", "one pan", "one-pan", "one pot", "one-pot", "tout-en-un",
    ],
    "Healthy": [
        "light", "équilibré", "diète", "salade", "smoothie", "bowl",
    ],
    "Comfort food": [
        "gratin", "lasagne", "lasagna", "mac and cheese", "burger",
        "réconfort", "tarte flamb",
    ],
    "Pâtes": [
        "pasta", "spaghetti", "tagliatelle", "linguine", "penne",
        "rigatoni", "fettuccine", "fusilli", "gnocchi",
        "lasagne", "lasagna", "macaroni", "ravioli", "tortellini",
    ],
    "Riz": [
        "rice", "risotto", "paella", "pilaf", "biryani", "fried rice", "arroz",
    ],
    "Poulet": [
        "chicken", "volaille", "dinde", "turkey",
    ],
    "Poisson": [
        "fish", "saumon", "salmon", "thon", "tuna", "cabillaud", "cod",
        "sole", "truite", "trout", "crevette", "shrimp", "prawn",
        "fruits de mer", "seafood", "coquille",
    ],
    "Dessert": [
        "gâteau", "cake", "tarte", "pie", "crème", "mousse",
        "biscuit", "cookie", "chocolat", "chocolate", "tiramisu",
        "brownie", "muffin", "cupcake", "glace", "sorbet",
        "compote", "crumble",
    ],
    "Petit-déjeuner": [
        "breakfast", "brunch", "pancake", "crêpe", "granola",
        "muesli", "porridge", "tartine", "smoothie bowl",
        "œuf brouillé", "scrambled egg", "french toast",
    ],
    "Batch cooking": [
        "meal prep", "grande quantité", "congélation", "à congeler",
    ],
}

# ---------------------------------------------------------------------------
# Phrase exclusions
# ---------------------------------------------------------------------------
# Before keyword-matching a tag, these phrases are stripped from the search
# text so that ingredient names like "fish sauce" don't falsely trigger the
# "Poisson" tag when no actual fish is present.

STRIP_PHRASES: dict[str, list[str]] = {
    "Poisson": [
        "fish sauce", "sauce poisson", "nuoc mam", "nuoc-mam", "nam pla",
    ],
}


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def match_tags(
    tags: list[Tag],
    title: str,
    ingredient_names: list[str],
    prep_time_minutes: int | None,
) -> list[Tag]:
    """Return the subset of *tags* that apply to this recipe."""
    search_text = f"{title.lower()} {' '.join(ingredient_names).lower()}"

    matched: list[Tag] = []
    for tag in tags:
        name = tag.name

        if name == "Rapide":
            if prep_time_minutes is not None and prep_time_minutes <= RAPIDE_MAX_MINUTES:
                matched.append(tag)
            continue

        # Strip exclusion phrases so e.g. "fish sauce" doesn't trigger Poisson
        effective_text = search_text
        for phrase in STRIP_PHRASES.get(name, []):
            effective_text = effective_text.replace(phrase, "")

        keywords = [name.lower()] + [kw.lower() for kw in KEYWORDS.get(name, [])]
        if any(kw in effective_text for kw in keywords):
            matched.append(tag)

    return matched
