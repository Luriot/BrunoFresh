import math

_FRACTIONS: list[tuple[float, str]] = [
    (1 / 8, "⅛"),
    (1 / 4, "¼"),
    (1 / 3, "⅓"),
    (3 / 8, "⅜"),
    (1 / 2, "½"),
    (5 / 8, "⅝"),
    (2 / 3, "⅔"),
    (3 / 4, "¾"),
    (7 / 8, "⅞"),
]
_TOLERANCE = 0.02


def format_qty(qty: float | None) -> str:
    if qty is None or not math.isfinite(qty):
        return ""
    whole = int(qty)
    frac = qty - whole
    if frac < _TOLERANCE:
        return str(whole)
    if frac > 1 - _TOLERANCE:
        return str(whole + 1)
    for val, sym in _FRACTIONS:
        if abs(frac - val) < _TOLERANCE:
            return f"{whole}{sym}" if whole > 0 else sym
    return str(round(qty, 2)).rstrip("0").rstrip(".")