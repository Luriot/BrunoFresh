import re

UNICODE_FRACS: dict[str, str] = {
    "½": "0.5",
    "⅓": "0.3333",
    "⅔": "0.6667",
    "¼": "0.25",
    "¾": "0.75",
    "⅛": "0.125",
    "⅜": "0.375",
    "⅝": "0.625",
    "⅞": "0.875",
    "⅙": "0.1667",
    "⅚": "0.8333",
    "⅕": "0.2",
    "⅖": "0.4",
    "⅗": "0.6",
    "⅘": "0.8",
}

_INT_UNICODE_FRAC_RE = re.compile(r"(\d+)([" + "".join(UNICODE_FRACS) + r"])")
_UNICODE_FRAC_RE = re.compile("[" + "".join(UNICODE_FRACS) + "]")
_ASCII_FRAC_RE = re.compile(r"(\d+)\s*/\s*(\d+)")


def preprocess_fractions(text: str) -> str:
    """Normalise unicode fractions and ASCII fractions to decimal strings.

    Handles:
      - "1½" → "1.5"
      - "½" → "0.5"
      - "1/2" → "0.5"
    """
    # Handle "1½" → "1.5"
    def _merge(m: re.Match) -> str:
        integer = float(m.group(1))
        frac = float(UNICODE_FRACS[m.group(2)])
        return str(integer + frac)

    text = _INT_UNICODE_FRAC_RE.sub(_merge, text)
    # Handle standalone "½" → "0.5"
    text = _UNICODE_FRAC_RE.sub(lambda m: UNICODE_FRACS[m.group(0)], text)
    # Handle ASCII "1/2" → "0.5"
    def _ascii_frac(m: re.Match) -> str:
        denominator = float(m.group(2))
        if denominator == 0:
            return m.group(0)
        return str(round(float(m.group(1)) / denominator, 4))

    text = _ASCII_FRAC_RE.sub(_ascii_frac, text)
    return text