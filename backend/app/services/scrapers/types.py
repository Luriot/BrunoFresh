from dataclasses import dataclass


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
