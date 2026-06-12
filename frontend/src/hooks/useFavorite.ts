import { useCallback } from "react";
import { toggleFavorite } from "../api/client";
import type { RecipeListItem } from "../types";

export function useFavorite(onFavoriteToggled?: (updated: RecipeListItem) => void) {
  const handleFavorite = useCallback(
    async (recipe: RecipeListItem, e?: React.MouseEvent) => {
      e?.stopPropagation();
      try {
        const { is_favorite_by_me } = await toggleFavorite(recipe.id);
        onFavoriteToggled?.({ ...recipe, is_favorite_by_me });
      } catch {
        // silently fail
      }
    },
    [onFavoriteToggled],
  );

  return handleFavorite;
}