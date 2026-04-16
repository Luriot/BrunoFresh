from dataclasses import dataclass


@dataclass
class NormalizedIngredient:
    name_en: str
    quantity: float
    unit: str
    category: str


def normalize_fallback(raw_string: str, quantity: float, unit: str) -> NormalizedIngredient | None:
    text = raw_string.lower()
    if "garlic" in text or "ail" in text:
        return NormalizedIngredient("garlic", quantity, "piece", "Produce")
    if "tomato" in text or "tomate" in text:
        return NormalizedIngredient("tomato", quantity, "g", "Produce")
    if "olive oil" in text or "huile" in text:
        return NormalizedIngredient("olive oil", quantity, "ml", "Pantry")
    return None
