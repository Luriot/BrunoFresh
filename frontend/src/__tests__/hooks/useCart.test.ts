import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCart } from "../../hooks/useCart";
import type { RecipeListItem } from "../../types";

const STORAGE_KEY = "brunofresh.cart.v1";

/** Minimal valid RecipeListItem for testing purposes. */
function makeRecipe(overrides: Partial<RecipeListItem> = {}): RecipeListItem {
  return {
    id: 1,
    title: "Test Recipe",
    url: "http://example.com/recipe",
    source_domain: "example.com",
    image_local_path: null,
    base_servings: 4,
    prep_time_minutes: null,
    is_favorite: false,
    tags: [],
    ...overrides,
  };
}

describe("useCart", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  // ── Initial state ──────────────────────────────────────────────────────────
  it("starts with an empty cart when localStorage is empty", () => {
    const { result } = renderHook(() => useCart());
    expect(result.current.cart).toEqual([]);
  });

  it("loads valid cart data from localStorage on mount", () => {
    const recipe = makeRecipe();
    const stored = [{ recipe, target_servings: 2 }];
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));

    const { result } = renderHook(() => useCart());
    expect(result.current.cart).toHaveLength(1);
    expect(result.current.cart[0].recipe.id).toBe(1);
    expect(result.current.cart[0].target_servings).toBe(2);
  });

  it("clears localStorage and starts empty if stored data is malformed JSON", () => {
    window.localStorage.setItem(STORAGE_KEY, "not-valid-json{{{");
    const { result } = renderHook(() => useCart());
    expect(result.current.cart).toEqual([]);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("[]");
  });

  it("clears localStorage and starts empty if stored data has invalid shape", () => {
    // Missing `recipe.title` — fails isValidCartData check
    const bad = [{ recipe: { id: 1 }, target_servings: 2 }];
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(bad));
    const { result } = renderHook(() => useCart());
    expect(result.current.cart).toEqual([]);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("[]");
  });

  // ── addToCart ──────────────────────────────────────────────────────────────
  it("addToCart: new recipe uses base_servings", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe({ id: 10, base_servings: 3 });

    act(() => result.current.addToCart(recipe));

    expect(result.current.cart).toHaveLength(1);
    expect(result.current.cart[0].target_servings).toBe(3);
  });

  it("addToCart: adding the same recipe twice increments servings by 1", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe({ id: 5, base_servings: 2 });

    act(() => result.current.addToCart(recipe));
    act(() => result.current.addToCart(recipe));

    expect(result.current.cart).toHaveLength(1);
    expect(result.current.cart[0].target_servings).toBe(3);
  });

  it("addToCart: different recipes accumulate independently", () => {
    const { result } = renderHook(() => useCart());
    const r1 = makeRecipe({ id: 1, base_servings: 2 });
    const r2 = makeRecipe({ id: 2, base_servings: 4, title: "Recipe 2" });

    act(() => result.current.addToCart(r1));
    act(() => result.current.addToCart(r2));

    expect(result.current.cart).toHaveLength(2);
  });

  // ── updateServings ─────────────────────────────────────────────────────────
  it("updateServings: changes the serving count for a recipe", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe({ id: 1, base_servings: 2 });

    act(() => result.current.addToCart(recipe));
    act(() => result.current.updateServings(1, 6));

    expect(result.current.cart[0].target_servings).toBe(6);
  });

  it("updateServings: clamps to minimum of 1", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe({ id: 1, base_servings: 2 });

    act(() => result.current.addToCart(recipe));
    act(() => result.current.updateServings(1, 0));

    expect(result.current.cart[0].target_servings).toBe(1);
  });

  // ── clearCart ──────────────────────────────────────────────────────────────
  it("clearCart: empties the cart", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe();

    act(() => result.current.addToCart(recipe));
    expect(result.current.cart).toHaveLength(1);

    act(() => result.current.clearCart());
    expect(result.current.cart).toHaveLength(0);
  });

  it("clearCart: persists empty array to localStorage", () => {
    const { result } = renderHook(() => useCart());
    act(() => result.current.addToCart(makeRecipe()));
    act(() => result.current.clearCart());

    const stored = window.localStorage.getItem(STORAGE_KEY);
    expect(JSON.parse(stored!)).toEqual([]);
  });

  // ── localStorage persistence ───────────────────────────────────────────────
  it("persists cart changes to localStorage automatically", () => {
    const { result } = renderHook(() => useCart());
    const recipe = makeRecipe({ id: 42, base_servings: 2 });

    act(() => result.current.addToCart(recipe));

    const raw = window.localStorage.getItem(STORAGE_KEY)!;
    const parsed = JSON.parse(raw);
    expect(parsed).toHaveLength(1);
    expect(parsed[0].recipe.id).toBe(42);
  });
});
