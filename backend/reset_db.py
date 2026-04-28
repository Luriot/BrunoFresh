"""
Supprime toutes les données scrappées (recettes, ingrédients, listes, meal plans,
pantry, scrape jobs, images) sans toucher aux tags ni à la structure de la base.
"""

import asyncio
import shutil
from pathlib import Path

from sqlalchemy import text

from app.database import engine


# Tables à vider dans l'ordre respectant les contraintes FK.
# Les tags (tags, recipe_tags) sont intentionnellement exclus.
_TABLES_IN_ORDER = [
    "meal_plan_entries",
    "meal_plans",
    "shopping_list_items",
    "shopping_list_recipes",
    "shopping_lists",
    "recipe_tags",           # association recette↔tag — les tags eux-mêmes sont conservés
    "recipe_ingredients",
    "scrape_jobs",
    "recipes",
    "pantry_items",
    "ingredient_translations",
    "ingredients",
]

_IMAGES_DIR = Path(__file__).resolve().parent / "data" / "images"


async def reset_scraped_data() -> None:
    async with engine.begin() as conn:
        # SQLite n'applique pas les FK par défaut — on l'active pour la session
        await conn.execute(text("PRAGMA foreign_keys = OFF"))
        for table in _TABLES_IN_ORDER:
            await conn.execute(text(f"DELETE FROM {table}"))  # noqa: S608
            print(f"  ✓ {table} vidée")
        await conn.execute(text("PRAGMA foreign_keys = ON"))

    # Supprime les images téléchargées
    if _IMAGES_DIR.exists():
        for f in _IMAGES_DIR.iterdir():
            if f.is_file():
                f.unlink()
        print(f"  ✓ images supprimées ({_IMAGES_DIR})")
    else:
        print(f"  ⚠ dossier images introuvable : {_IMAGES_DIR}")

    print("\nReset terminé — tags conservés.")


if __name__ == "__main__":
    asyncio.run(reset_scraped_data())
