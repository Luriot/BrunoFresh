from __future__ import annotations

from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from ...config import settings
from .base import BaseScraper
from .types import ScrapedIngredient, ScrapedRecipe


class HelloFreshScraper(BaseScraper):
    def scrape(self) -> ScrapedRecipe:
        domain = urlparse(self.url).netloc.replace("www.", "") or "hellofresh"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = None

            if settings.hf_state_file.exists():
                context = browser.new_context(storage_state=str(settings.hf_state_file))
            else:
                context = browser.new_context()
                page = context.new_page()
                page.goto("https://www.hellofresh.fr/login", wait_until="domcontentloaded")
                if settings.hf_email and settings.hf_password:
                    page.fill("input[type='email']", settings.hf_email)
                    page.fill("input[type='password']", settings.hf_password)
                    page.click("button[type='submit']")
                    page.wait_for_timeout(3000)
                    context.storage_state(path=str(settings.hf_state_file))

            page = context.new_page()
            page.goto(self.url, wait_until="domcontentloaded")

            title = page.locator("h1").first.text_content() or f"Imported recipe from {domain}"
            image_url = None
            image = page.locator("img").first
            if image.count() > 0:
                image_url = image.get_attribute("src")

            ingredient_lines = [x.strip() for x in page.locator("li").all_inner_texts() if x.strip()]
            step_lines = [x.strip() for x in page.locator("ol li").all_inner_texts() if x.strip()]

            browser.close()

        parsed_ingredients: list[ScrapedIngredient] = [
            self._parse_ingredient_line(line) for line in ingredient_lines[:40]
        ]

        return ScrapedRecipe(
            title=title.strip(),
            source_domain=domain,
            image_url=image_url,
            instructions_text="\n".join(step_lines[:30]),
            base_servings=2,
            prep_time_minutes=None,
            ingredients=parsed_ingredients or self._fallback_recipe().ingredients,
        )
