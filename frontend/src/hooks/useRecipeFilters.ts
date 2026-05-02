import { useEffect, useRef, useState } from "react";
import { fetchRecipes, fetchTags } from "../api/client";
import type { Tag } from "../types";

type OnRecipesChanged = (recipes: import("../types").RecipeListItem[]) => void;

export function useRecipeFilters(onRecipesChanged: OnRecipesChanged) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [allTags, setAllTags] = useState<Tag[]>([]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    fetchTags().then(setAllTags).catch(() => {});
  }, []);

  // Debounced server-side filter — skips the initial render to avoid an
  // extra network request on mount (App.tsx already fetches all recipes).
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void fetchRecipes({
        q: searchQuery || undefined,
        is_favorite: showFavoritesOnly || undefined,
        tags: selectedTagIds.length > 0 ? selectedTagIds.join(",") : undefined,
      }).then(onRecipesChanged).catch(() => {});
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [searchQuery, selectedTagIds, showFavoritesOnly, onRecipesChanged]);

  function toggleTagFilter(tagId: number) {
    setSelectedTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId],
    );
  }

  function clearTagFilters() {
    setSelectedTagIds([]);
  }

  return {
    searchQuery,
    setSearchQuery,
    selectedTagIds,
    toggleTagFilter,
    clearTagFilters,
    showFavoritesOnly,
    setShowFavoritesOnly,
    allTags,
  };
}
