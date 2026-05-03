import { describe, it, expect } from "vitest";
import { isSafeUrl } from "../../utils/url";

describe("isSafeUrl", () => {
  // ── Falsy inputs ──────────────────────────────────────────────────────────
  it("returns false for null", () => {
    expect(isSafeUrl(null)).toBe(false);
  });

  it("returns false for undefined", () => {
    expect(isSafeUrl(undefined)).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isSafeUrl("")).toBe(false);
  });

  // ── Dangerous / disallowed schemes ───────────────────────────────────────
  it("returns false for javascript: scheme", () => {
    expect(isSafeUrl("javascript:alert(1)")).toBe(false);
  });

  it("returns false for ftp:// scheme", () => {
    expect(isSafeUrl("ftp://files.example.com/file.txt")).toBe(false);
  });

  it("returns false for data: URI", () => {
    expect(isSafeUrl("data:text/html,<h1>hi</h1>")).toBe(false);
  });

  it("returns false for protocol-relative URL (//host)", () => {
    // new URL("//host") throws, so this should return false
    expect(isSafeUrl("//example.com/path")).toBe(false);
  });

  it("returns false for a plain hostname without scheme", () => {
    expect(isSafeUrl("example.com")).toBe(false);
  });

  it("returns false for a random non-URL string", () => {
    expect(isSafeUrl("not a url at all")).toBe(false);
  });

  // ── Safe URLs ─────────────────────────────────────────────────────────────
  it("returns true for a plain http URL", () => {
    expect(isSafeUrl("http://example.com")).toBe(true);
  });

  it("returns true for a plain https URL", () => {
    expect(isSafeUrl("https://example.com")).toBe(true);
  });

  it("returns true for https URL with path, query and fragment", () => {
    expect(isSafeUrl("https://example.com/path?q=1#section")).toBe(true);
  });

  it("returns true for https localhost (still http/https scheme)", () => {
    // isSafeUrl only checks scheme, not whether host is safe
    expect(isSafeUrl("http://localhost:3000/api")).toBe(true);
  });
});
