from __future__ import annotations

from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from ...config import settings
from .base import BaseScraper
from .types import ScrapedIngredient, ScrapedRecipe


class HelloFreshScraper(BaseScraper):
    async def scrape(self) -> ScrapedRecipe:
        domain = urlparse(self.url).netloc.replace("www.", "") or "hellofresh"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            if settings.hf_state_file.exists():
                context = await browser.new_context(storage_state=str(settings.hf_state_file))
            else:
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto("https://www.hellofresh.fr/login", wait_until="domcontentloaded")
                if settings.hf_email and settings.hf_password:
                    await page.fill("input[type='email']", settings.hf_email)
                    await page.fill("input[type='password']", settings.hf_password)
                    await page.click("button[type='submit']")
                    try:
                        await page.wait_for_url("**/recipes/**", timeout=10000)
                    except PlaywrightTimeoutError:
                        # Some sessions land on pages outside /recipes while still authenticated.
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    await context.storage_state(path=str(settings.hf_state_file))

            page = await context.new_page()
            await page.goto(self.url, wait_until="domcontentloaded")

            title = (await page.locator("h1").first.text_content()) or f"Imported recipe from {domain}"
            image_url = None
            image = page.locator("img").first
            if await image.count() > 0:
                image_url = await image.get_attribute("src")

            ingredient_lines = [x.strip() for x in await page.locator("li").all_inner_texts() if x.strip()]
            step_lines = [x.strip() for x in await page.locator("ol li").all_inner_texts() if x.strip()]

            await context.close()
            await browser.close()

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
