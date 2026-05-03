import { describe, it, expect } from "vitest";
import { formatQty } from "../../utils/format";

describe("formatQty", () => {
  // ── Edge cases ─────────────────────────────────────────────────────────────
  it("returns empty string for null", () => {
    expect(formatQty(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(formatQty(undefined)).toBe("");
  });

  it("returns empty string for NaN", () => {
    expect(formatQty(NaN)).toBe("");
  });

  it("returns empty string for Infinity", () => {
    expect(formatQty(Infinity)).toBe("");
  });

  it("returns empty string for -Infinity", () => {
    expect(formatQty(-Infinity)).toBe("");
  });

  // ── Whole numbers ──────────────────────────────────────────────────────────
  it("returns '0' for 0", () => {
    expect(formatQty(0)).toBe("0");
  });

  it("returns '1' for 1", () => {
    expect(formatQty(1)).toBe("1");
  });

  it("returns '4' for 4", () => {
    expect(formatQty(4)).toBe("4");
  });

  // ── Near-whole rounding ────────────────────────────────────────────────────
  it("rounds 0.999 up to '1'", () => {
    expect(formatQty(0.999)).toBe("1");
  });

  it("rounds 0.001 down to '0'", () => {
    expect(formatQty(0.001)).toBe("0");
  });

  // ── Pure fractions ────────────────────────────────────────────────────────
  it("returns '½' for 0.5", () => {
    expect(formatQty(0.5)).toBe("½");
  });

  it("returns '¼' for 0.25", () => {
    expect(formatQty(0.25)).toBe("¼");
  });

  it("returns '¾' for 0.75", () => {
    expect(formatQty(0.75)).toBe("¾");
  });

  it("returns '⅓' for 1/3", () => {
    expect(formatQty(1 / 3)).toBe("⅓");
  });

  it("returns '⅔' for 2/3", () => {
    expect(formatQty(2 / 3)).toBe("⅔");
  });

  it("returns '⅛' for 0.125", () => {
    expect(formatQty(0.125)).toBe("⅛");
  });

  it("returns '⅜' for 3/8", () => {
    expect(formatQty(3 / 8)).toBe("⅜");
  });

  it("returns '⅝' for 5/8", () => {
    expect(formatQty(5 / 8)).toBe("⅝");
  });

  it("returns '⅞' for 7/8", () => {
    expect(formatQty(7 / 8)).toBe("⅞");
  });

  // ── Mixed numbers ─────────────────────────────────────────────────────────
  it("returns '1½' for 1.5", () => {
    expect(formatQty(1.5)).toBe("1½");
  });

  it("returns '2¼' for 2.25", () => {
    expect(formatQty(2.25)).toBe("2¼");
  });

  it("returns '3⅔' for 3 + 2/3", () => {
    expect(formatQty(3 + 2 / 3)).toBe("3⅔");
  });

  // ── Decimal fallback ───────────────────────────────────────────────────────
  it("returns decimal string for unrecognised fractions", () => {
    expect(formatQty(1.23)).toBe("1.23");
  });

  it("strips trailing zeros from decimal fallback", () => {
    // 1.20 has no fraction match → toFixed(2) → "1.20" → parseFloat → 1.2
    expect(formatQty(1.2)).toBe("1.2");
  });
});
