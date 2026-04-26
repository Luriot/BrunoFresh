from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseScraper
from .types import ScrapedIngredient, ScrapedRecipe


class StaticRecipeScraper(BaseScraper):
    ingredient_selectors: tuple[str, ...] = ()
    instruction_selectors: tuple[str, ...] = ()
    title_selectors: tuple[str, ...] = ()
    image_selectors: tuple[str, ...] = ()

    def _find_text_by_selectors(self, soup: BeautifulSoup, selectors: tuple[str, ...], default: str = "") -> str:
        for selector in selectors:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                return node.get_text(strip=True)
        return default

    def _find_image_by_selectors(self, soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                src = node.get("src") or node.get("data-src")
                if src:
                    return src
        return None

    def _extract_lines(self, soup: BeautifulSoup, selectors: tuple[str, ...]) -> list[str]:
        for selector in selectors:
            nodes = soup.select(selector)
            lines = [node.get_text(" ", strip=True) for node in nodes if node.get_text(strip=True)]
            if lines:
                return lines
        return []

    async def scrape(self) -> ScrapedRecipe:
        html = await self._get_html()
        soup = BeautifulSoup(html, "html.parser")
        jsonld = self._extract_jsonld(soup)

        title = self._find_text_by_selectors(soup, self.title_selectors, default="")
        image_url = self._find_image_by_selectors(soup, self.image_selectors)
        ingredient_lines = self._extract_lines(soup, self.ingredient_selectors)
        instruction_lines = self._extract_lines(soup, self.instruction_selectors)
        base_servings = 2

        if jsonld:
            title = title or jsonld.get("name", "")
            if not image_url:
                image_data = jsonld.get("image")
                if isinstance(image_data, list) and image_data:
                    image_url = image_data[0]
                elif isinstance(image_data, str):
                    image_url = image_data
            if not ingredient_lines and isinstance(jsonld.get("recipeIngredient"), list):
                ingredient_lines = [str(item) for item in jsonld["recipeIngredient"]]
            if not instruction_lines and isinstance(jsonld.get("recipeInstructions"), list):
                collected: list[str] = []
                for step in jsonld["recipeInstructions"]:
                    if isinstance(step, str):
                        collected.append(step)
                    elif isinstance(step, dict) and step.get("text"):
                        collected.append(step["text"])
                instruction_lines = collected
            if isinstance(jsonld.get("recipeYield"), str):
                digits = "".join(ch for ch in jsonld["recipeYield"] if ch.isdigit())
                if digits:
                    base_servings = max(1, int(digits))
        ingredients: list[ScrapedIngredient] = [
            self._parse_ingredient_line(line) for line in ingredient_lines if line.strip()
        ]

        if not title:
            return self._fallback_recipe()

        instruction_steps = self._extract_instruction_steps(jsonld) if jsonld else []

        return ScrapedRecipe(
            title=title,
            source_domain=self.domain,
            image_url=image_url,
            instructions_text="\n".join(instruction_lines) if instruction_lines else "",
            base_servings=base_servings,
            prep_time_minutes=None,
            ingredients=ingredients or self._fallback_recipe().ingredients,
            instruction_steps=instruction_steps,
        )
