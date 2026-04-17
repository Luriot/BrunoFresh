import { useEffect, useState } from "react";

import type { CartInput, RecipeListItem } from "../types";

const CART_STORAGE_KEY = "brunofresh.cart.v1";

export type CartEntry = {
  recipe: RecipeListItem;
  target_servings: number;
};

export function useCart() {
  const [cart, setCart] = useState<CartEntry[]>([]);

  useEffect(() => {
    const raw = window.localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw) as CartEntry[];
      setCart(parsed);
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
    toCartInput,
  };
}
