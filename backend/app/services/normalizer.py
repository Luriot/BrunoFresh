from dataclasses import dataclass
import asyncio
import json
import logging

import httpx

from ..config import settings
from .scrapers.types import ScrapedIngredient

logger = logging.getLogger(__name__)

# On limite à 3 requêtes simultanées pour ne pas noyer Ollama (surtout avec un modèle 14b)
ollama_semaphore = asyncio.Semaphore(3)


@dataclass
class NormalizedIngredient:
    name_en: str
    quantity: float
    unit: str
    category: str


def _sanitize_raw_ingredient(value: str) -> str:
    # Keep only short, plain text snippets to reduce prompt-injection surface.
    cleaned = (value or "").replace("`", " ").replace("\n", " ").replace("\r", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned[:200]


def _coerce_category(value: str) -> str:
    value = (value or "Other").strip()
    if value in settings.categories:
        return value
    lowered = value.lower()
    for category in settings.categories:
        if category.lower() == lowered:
            return category
    return "Other"


def _coerce_unit(value: str) -> str:
    unit = (value or "piece").lower().strip()
    if unit in {"g", "gram", "grams"}:
        return "g"
    if unit in {"ml", "milliliter", "milliliters"}:
        return "ml"
    if unit in {"piece", "pieces", "pc"}:
        return "piece"
    return "piece"


async def normalize_with_ollama(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    safe_raw = _sanitize_raw_ingredient(raw_string)
    raw = ""
    categories = ", ".join(settings.categories)
    prompt = (
        "You are an ingredient parser. Return strict JSON only with keys: "
        "name_en, quantity, unit, category. "
        "Allowed units: g, ml, piece. "
        f"Allowed categories: {categories}. "
        "Translate ingredient names to English. "
        "Do not return markdown. "
        f"Input ingredient: {safe_raw}. "
        f"Hint quantity={quantity}, unit={unit}."
    )

    try:
        async with ollama_semaphore:
            logger.debug(f"Demande de normalisation Ollama pour: '{safe_raw}'")
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                
        payload = response.json()
        raw = payload.get("response", "")
        
        # Les modèles qwen/deepseek placent parfois le retour JSON dans la clé "thinking" 
        # quand ils sont contraints par "format": "json" (ou en raison d'un bug de l'API)
        if not raw.strip():
            raw = payload.get("thinking", "")
        
        # L'API publique peut parfois renvoyer une réponse complètement vide, ou encapsulée
        if not raw or not raw.strip():
            logger.warning(f"Ollama a répondu avec un contenu vide pour '{safe_raw}'. Payload: {payload}")
            return None
            
        # Nettoyer un éventuel markdown "```json" si Ollama force le formatage malgré "format: json"
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        
        parsed = json.loads(raw)

        name = str(parsed.get("name_en", "")).strip().lower()
        parsed_qty = float(parsed.get("quantity", quantity))
        parsed_unit = _coerce_unit(str(parsed.get("unit", unit)))
        parsed_category = _coerce_category(str(parsed.get("category", "Other")))

        if not name:
            logger.warning(f"Ollama a retourné un nom vide pour l'ingrédient '{safe_raw}'")
            return None

        if parsed_qty < 0:
            parsed_qty = abs(parsed_qty)

        result = NormalizedIngredient(name, parsed_qty, parsed_unit, parsed_category)
        logger.debug(f"Succès Ollama: '{safe_raw}' -> {result}")
        return result
        
    except json.JSONDecodeError:
        logger.error(f"Le JSON renvoyé par Ollama est invalide pour '{safe_raw}' : {raw}")
        return None
    except Exception as exc:
        logger.error(f"Erreur Ollama lors de la normalisation de '{safe_raw}': {exc}", exc_info=True)
        return None


def normalize_fallback(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    text = raw_string.lower()
    
    # Ignorer les en-têtes de sections du type "Pour la sauce..." ou "Pour le gâteau..."
    if text.startswith("pour la ") or text.startswith("pour le ") or text.startswith("pour les "):
        return NormalizedIngredient("section_header_ignore", 0, "piece", "Other")

    if "garlic" in text or "ail" in text:
        return NormalizedIngredient("garlic", quantity, "piece", "Produce")
    if "tomato" in text or "tomate" in text:
        return NormalizedIngredient("tomato", quantity, "g", "Produce")
    if "olive oil" in text or "huile" in text:
        return NormalizedIngredient("olive oil", quantity, "ml", "Pantry")
    if "sel" in text or "salt" in text:
        return NormalizedIngredient("salt", max(1, quantity), "g", "Spices")
    if "poivre" in text or "pepper" in text:
        return NormalizedIngredient("black pepper", max(1, quantity), "g", "Spices")
    if "beurre" in text or "butter" in text:
        return NormalizedIngredient("butter", quantity, "g", "Dairy")
    if "oignon" in text or "onion" in text:
        return NormalizedIngredient("onion", quantity, "piece", "Produce")
    if "lait" in text or "milk" in text:
        return NormalizedIngredient("milk", quantity, "ml", "Dairy")
    if "farine" in text or "flour" in text:
        return NormalizedIngredient("flour", quantity, "g", "Pantry")
    if "sucre" in text or "sugar" in text:
        return NormalizedIngredient("sugar", quantity, "g", "Pantry")
    if "boeuf" in text or "bœuf" in text or "beef" in text:
        return NormalizedIngredient("ground beef", quantity, "g", "Meat")
    if "gruyère" in text or "gruyere" in text:
        return NormalizedIngredient("gruyere cheese", quantity, "g", "Dairy")
    if "parmesan" in text:
        return NormalizedIngredient("parmesan cheese", quantity, "g", "Dairy")
    if "muscade" in text or "nutmeg" in text:
        return NormalizedIngredient("nutmeg", max(1, quantity), "g", "Spices")
    if "herbe" in text or "herb" in text:
        return NormalizedIngredient("mixed herbs", max(1, quantity), "g", "Spices")
    if "lasagne" in text or "pâte" in text or "pasta" in text:
        return NormalizedIngredient("lasagna sheets", quantity, "piece", "Pantry")
        
    return None


async def normalize_ingredients_batch(ingredients: list[ScrapedIngredient]) -> list[NormalizedIngredient | None]:
    if not ingredients:
        return []

    input_list: list[dict[str, float | str | int] | None] = []
    for i, ing in enumerate(ingredients):
        safe_raw = _sanitize_raw_ingredient(ing.raw)
        # On pré-filtre les en-têtes directement ici au lieu de le faire via le LLM
        if safe_raw.lower().startswith("pour la ") or safe_raw.lower().startswith("pour le ") or safe_raw.lower().startswith("pour les "):
            input_list.append(None)
            continue
            
        input_list.append({
            "idx": i,
            "raw": safe_raw,
            "quantity": ing.quantity,
            "unit": ing.unit
        })

    # Si tous les blocs étaient des en-têtes, pas besoin d'appeler Ollama
    if not any(input_list):
        return [NormalizedIngredient("section_header_ignore", 0, "piece", "Other") if item is None else None for item in input_list]

    valid_inputs = [item for item in input_list if item is not None]
    
    categories_str = ", ".join(settings.categories)
    prompt = (
        "You are an ingredient parser. Return strict JSON ONLY. "
        "The root MUST be a JSON object with a single key 'ingredients' containing an array of all processed objects. "
        "Each object must have exactly these keys: idx, name_en, quantity, unit, category. "
        'Example output:\n{"ingredients": [{"idx": 0, "name_en": "tomato", "quantity": 300.0, "unit": "g", "category": "Produce"}]}\n'
        "Allowed units: g, ml, piece. "
        f"Allowed categories: {categories_str}. "
        "Translate ALL ingredient names to English. "
        "Process ALL items from the input array. Maintain the exact idx passed.\n\n"
        f"Input array to process:\n{json.dumps(valid_inputs, ensure_ascii=False)}"
    )

    try:
        async with ollama_semaphore:
            logger.info(f"Demande de normalisation Ollama par LOT ({len(valid_inputs)} ingrédients)...")
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                
        payload = response.json()
        raw = payload.get("response", "")
        
        if not raw.strip():
            raw = payload.get("thinking", "")
        
        if not raw.strip():
            raise ValueError("Réponse vide de la part d'Ollama.")

        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        
        try:
            parsed_array = json.loads(raw)
        except json.JSONDecodeError as jde:
            logger.error(f"Le JSON de retour BATCH est invalide ! Contenu brut Ollama:\n{raw}\n--- Erreur: {jde}")
            # Si c'est juste un problème de guillemets simples (arrive parfois quand "thinking" leak du pseudo code python), on peut tenter eval:
            import ast
            try:
                parsed_array = ast.literal_eval(raw)
                logger.warning("ast.literal_eval a pu récupérer le tableau malgré l'invalidité JSON stricte.")
            except Exception:
                raise ValueError("Impossible de décoder la réponse en JSON.")

        if not isinstance(parsed_array, list):
            logger.warning(f"Ollama n'a pas renvoyé une liste directe. Type reçu: {type(parsed_array)}. Tentative d'extraction...")
            if isinstance(parsed_array, dict):
                # Le modèle respecte souvent la consigne "{"ingredients": [...]}" ou un dérivé
                for k, v in parsed_array.items():
                    if isinstance(v, list):
                        parsed_array = v
                        logger.info(f"Liste extraite depuis la clé '{k}'")
                        break
            
            # S'il a renvoyé uniquement le PREMIER ingrédient au lieu du tableau :
            if isinstance(parsed_array, dict) and "idx" in parsed_array:
                logger.warning(f"Ollama n'a traité qu'un seul ingrédient sur tout le lot ! Contenu: {parsed_array}")
                parsed_array = [parsed_array]

            if not isinstance(parsed_array, list):
                logger.error(f"Structure inattendue renvoyée par Ollama : {parsed_array}")
                raise ValueError("Le JSON renvoyé n'est pas un tableau (list) et ne contient pas de tableau.")

        results: list[NormalizedIngredient | None] = [None] * len(ingredients)
        
        # On replace les en-têtes
        for idx, item in enumerate(input_list):
            if item is None:
                results[idx] = NormalizedIngredient("section_header_ignore", 0, "piece", "Other")

        for item in parsed_array:
            if not isinstance(item, dict):
                continue

            idx = item.get("idx")
            if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(ingredients):
                continue
                
            name = str(item.get("name_en", "")).strip().lower()
            try:
                qty = float(item.get("quantity", ingredients[idx].quantity))
            except (TypeError, ValueError):
                qty = float(ingredients[idx].quantity)
            parsed_unit = _coerce_unit(str(item.get("unit", ingredients[idx].unit)))
            parsed_category = _coerce_category(str(item.get("category", "Other")))

            if name:
                results[idx] = NormalizedIngredient(name, abs(qty), parsed_unit, parsed_category)

        # Fallback pour ceux qui n'ont pas été traduits (LLM truncating, ou erreur)
        for idx, res in enumerate(results):
            if res is None:
                orig = ingredients[idx]
                results[idx] = normalize_fallback(orig.raw, orig.quantity, orig.unit)

        logger.info("Normalisation batch terminée avec succès.")
        return results

    except Exception as exc:
        logger.error(f"Erreur globale lors de la normalisation BATCH: {exc}", exc_info=True)
        # Si globalement pété (réponse bizarre de Ollama), on fallback tout le monde
        logger.warning("Application du fallback sur la totalité du lot...")
        return [normalize_fallback(i.raw, i.quantity, i.unit) for i in ingredients]
