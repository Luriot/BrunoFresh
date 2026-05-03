/** Fraction symbols ordered by value. */
const FRACTIONS: [number, string][] = [
  [1 / 8, "⅛"],
  [1 / 4, "¼"],
  [1 / 3, "⅓"],
  [3 / 8, "⅜"],
  [1 / 2, "½"],
  [5 / 8, "⅝"],
  [2 / 3, "⅔"],
  [3 / 4, "¾"],
  [7 / 8, "⅞"],
];

const TOLERANCE = 0.02;

/**
 * Format a recipe quantity for display.
 * - Recognises common fractions (¼ ⅓ ½ ⅔ ¾ …) within a small tolerance.
 * - Falls back to at most 2 decimal places, trailing zeros stripped.
 * - Returns "" for null/undefined/non-finite values.
 */
export function formatQty(qty: number | null | undefined): string {
  if (qty == null || !Number.isFinite(qty)) return "";

  const whole = Math.floor(qty);
  const frac = qty - whole;

  if (frac < TOLERANCE) return whole.toString();
  if (frac > 1 - TOLERANCE) return (whole + 1).toString();

  for (const [val, sym] of FRACTIONS) {
    if (Math.abs(frac - val) < TOLERANCE) {
      return whole > 0 ? `${whole}${sym}` : sym;
    }
  }

  // Fallback: round to 2 decimal places, strip trailing zeros
  return parseFloat(qty.toFixed(2)).toString();
}
