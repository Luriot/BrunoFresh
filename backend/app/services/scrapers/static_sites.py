"""Generic JSON-LD fallback scraper for sites the recipe-scrapers library misses."""
from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import (
    extract_instruction_steps,
    fallback_recipe,
    find_recipe_jsonld,
    get_html,
    parse_ingredient_line,
)
from .types import ScrapedIngredient, ScrapedRecipe
from ...utils.parsing import extract_nutrition_from_jsonld


async def scrape_static(url: str) -> ScrapedRecipe:
    domain = urlparse(url).netloc.replace("www.", "")
    soup = BeautifulSoup(await get_html(url), "html.parser")
    jsonld = find_recipe_jsonld(soup)

    title = ""
    image_url = None
    ingredient_lines: list[str] = []
    instruction_lines: list[str] = []
    base_servings = 2

    if jsonld:
        title = jsonld.get("name", "")
        image_data = jsonld.get("image")
        if isinstance(image_data, list) and image_data:
            image_url = image_data[0]
        elif isinstance(image_data, str):
            image_url = image_data
        if isinstance(jsonld.get("recipeIngredient"), list):
            ingredient_lines = [str(item) for item in jsonld["recipeIngredient"]]
        if isinstance(jsonld.get("recipeInstructions"), list):
            instruction_lines = [
                step if isinstance(step, str) else step.get("text", "")
                for step in jsonld["recipeInstructions"]
                if isinstance(step, str) or (isinstance(step, dict) and step.get("text"))
            ]
        if isinstance(jsonld.get("recipeYield"), str):
            digits = "".join(ch for ch in jsonld["recipeYield"] if ch.isdigit())
            if digits:
                base_servings = max(1, int(digits))

    if not title:
        return fallback_recipe(domain)

    ingredients: list[ScrapedIngredient] = [
        parse_ingredient_line(line) for line in ingredient_lines if line.strip()
    ]
    instruction_steps = extract_instruction_steps(jsonld) if jsonld else []
    nutrition = extract_nutrition_from_jsonld(jsonld)

    return ScrapedRecipe(
        title=title,
        source_domain=domain,
        image_url=image_url,
        instructions_text="\n".join(instruction_lines),
        base_servings=base_servings,
        prep_time_minutes=None,
        ingredients=ingredients or fallback_recipe(domain).ingredients,
        instruction_steps=instruction_steps,
        **nutrition,
    )
