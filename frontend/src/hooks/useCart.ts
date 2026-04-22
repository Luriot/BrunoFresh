import { useEffect, useState } from "react";

import type { CartInput, RecipeListItem } from "../types";

const CART_STORAGE_KEY = "brunofresh.cart.v1";

export type CartEntry = {
  recipe: RecipeListItem;
  target_servings: number;
};

/** Validate a parsed value has the minimum shape required by CartEntry[]. */
function isValidCartData(value: unknown): value is CartEntry[] {
  if (!Array.isArray(value)) {
    return false;
  }
  return value.every(
    (entry) =>
      entry !== null &&
      typeof entry === "object" &&
      typeof (entry as CartEntry).target_servings === "number" &&
      (entry as CartEntry).recipe !== null &&
      typeof (entry as CartEntry).recipe === "object" &&
      typeof (entry as CartEntry).recipe.id === "number" &&
      typeof (entry as CartEntry).recipe.title === "string"
  );
}

export function useCart() {
  const [cart, setCart] = useState<CartEntry[]>([]);

  useEffect(() => {
    const raw = window.localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return;
    }

    try {
      const parsed: unknown = JSON.parse(raw);
      if (isValidCartData(parsed)) {
        setCart(parsed);
      } else {
        window.localStorage.removeItem(CART_STORAGE_KEY);
      }
    } catch {
      window.localStorage.removeItem(CART_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
  }, [cart]);

  function addToCart(recipe: RecipeListItem) {
    setCart((prev) => {
      const existing = prev.find((entry) => entry.recipe.id === recipe.id);
      if (existing) {
        return prev.map((entry) =>
          entry.recipe.id === recipe.id
            ? { ...entry, target_servings: entry.target_servings + 1 }
            : entry
        );
      }

      return [...prev, { recipe, target_servings: recipe.base_servings }];
    });
  }

  function updateServings(recipeId: number, servings: number) {
    setCart((prev) =>
      prev.map((entry) =>
        entry.recipe.id === recipeId
          ? { ...entry, target_servings: Math.max(1, servings) }
          : entry
      )
    );
  }

  function clearCart() {
    setCart([]);
  }

  function toCartInput(): CartInput[] {
    return cart.map((entry) => ({
      recipe_id: entry.recipe.id,
      target_servings: entry.target_servings,
    }));
  }

  return {
    cart,
    addToCart,
    updateServings,
    clearCart,
    toCartInput,
  };
}
