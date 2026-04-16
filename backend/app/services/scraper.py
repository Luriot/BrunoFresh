from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class ScrapedIngredient:
    raw: str
    quantity: float
    unit: str


@dataclass
class ScrapedRecipe:
    title: str
    source_domain: str
    image_url: str | None
    instructions_text: str
    base_servings: int
    prep_time_minutes: int | None
    ingredients: list[ScrapedIngredient]


def scrape_recipe_url(url: str) -> ScrapedRecipe:
    # Placeholder deterministic parser while real site-specific scrapers are implemented.
    domain = urlparse(url).netloc.replace("www.", "") or "unknown"
    title = f"Imported recipe from {domain}"

    return ScrapedRecipe(
        title=title,
        source_domain=domain,
        image_url=None,
        instructions_text="1. Prep ingredients\n2. Cook\n3. Serve",
        base_servings=2,
        prep_time_minutes=30,
        ingredients=[
            ScrapedIngredient(raw="2 cloves garlic", quantity=2, unit="piece"),
            ScrapedIngredient(raw="400 g tomatoes", quantity=400, unit="g"),
            ScrapedIngredient(raw="2 tbsp olive oil", quantity=30, unit="ml"),
        ],
    )
