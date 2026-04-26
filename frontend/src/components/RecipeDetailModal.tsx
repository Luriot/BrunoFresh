import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  buildImageUrl,
  fetchRecipeDetail,
  fetchSimilarRecipes,
  rescrapeRecipe,
  fetchTags,
  setRecipeTags,
} from "../api/client";
import type { RecipeDetail, RecipeListItem, Tag } from "../types";
import { CookModeModal } from "./CookModeModal";

type Props = {
  recipeId: number;
  onClose: () => void;
  onAddToCart: () => void;
};

export function RecipeDetailModal({ recipeId, onClose, onAddToCart }: Readonly<Props>) {
  const { t } = useTranslation();
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Cook mode
  const [cookMode, setCookMode] = useState(false);

  // Tags
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [tagSaving, setTagSaving] = useState(false);

  // Similar recipes
  const [similar, setSimilar] = useState<RecipeListItem[]>([]);

  // Re-scrape
  const [rescraping, setRescraping] = useState(false);
  const [rescrapeMsg, setRescrapeMsg] = useState<string | null>(null);

  const loadRecipe = useCallback((id: number) => {
    setLoading(true);
    setError(false);
    let cancelled = false;

    fetchRecipeDetail(id)
      .then((data) => {
        if (cancelled) return;
        setRecipe(data);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  useEffect(() => loadRecipe(recipeId), [recipeId, loadRecipe]);

  useEffect(() => {
    fetchTags().then(setAllTags).catch(() => {});
    fetchSimilarRecipes(recipeId).then(setSimilar).catch(() => {});
  }, [recipeId]);

  async function handleTagToggle(tag: Tag) {
    if (!recipe) return;
    const current = new Set(recipe.tags.map((rt) => rt.id));
    if (current.has(tag.id)) current.delete(tag.id); else current.add(tag.id);
    setTagSaving(true);
    try {
      const updated = await setRecipeTags(recipe.id, [...current]);
      setRecipe(updated);
    } finally {
      setTagSaving(false);
    }
  }

  async function handleRescrape() {
    if (!recipe) return;
    setRescraping(true);
    setRescrapeMsg(t("recipe.rescrapingInProgress"));
    try {
      await rescrapeRecipe(recipe.id);
      setRescrapeMsg(t("recipe.rescrapeQueued"));
      await new Promise((r) => setTimeout(r, 4000));
      loadRecipe(recipe.id);
      setRescrapeMsg(null);
    } catch {
      setRescrapeMsg(t("recipe.rescrapeError"));
    } finally {
      setRescraping(false);
    }
  }

  if (cookMode && recipe) {
    return (
      <CookModeModal
        recipe={recipe}
        onClose={() => setCookMode(false)}
        onRecipeUpdated={(updated) => setRecipe(updated)}
      />
    );
  }

  return (
    <dialog
      open
      aria-label={recipe?.title ?? t("recipe.cookMode")}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />

      {/* Modal card */}
      <div className="relative z-10 flex w-full max-w-2xl flex-col rounded-2xl border border-gray-200 bg-white dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-100" style={{ maxHeight: "92dvh" }}>

        {/* Loading */}
        {loading && (
          <div className="flex h-64 items-center justify-center">
            <svg className="h-8 w-8 animate-spin text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        )}

        {/* Error */}
        {!loading && (error || !recipe) && (
          <div className="flex h-64 flex-col items-center justify-center gap-4 p-6 text-center">
            <p className="text-red-500">{t("error.loadFailed")}</p>
            <button
              className="rounded-xl border border-gray-300 px-4 py-2 font-semibold hover:bg-gray-50 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30]"
              onClick={onClose}
            >
              {t("app.close")}
            </button>
          </div>
        )}

        {/* Content */}
        {!loading && recipe && (
          <>
            {/* Hero image — fixed height, never scrolls */}
              <div className="relative h-48 w-full shrink-0 overflow-hidden rounded-t-2xl bg-green-50 dark:bg-[#1e1e1e] sm:h-60">
              {recipe.image_local_path ? (
                <img
                  className="h-full w-full object-cover"
                  src={buildImageUrl(recipe.image_local_path)}
                  alt={recipe.title}
                />
              ) : (
                <div className="flex h-full items-center justify-center text-green-600 dark:text-green-400">
                  {t("recipe.noImage")}
                </div>
              )}
              {/* Close button on image */}
              <button
                className="absolute right-3 top-3 rounded-full bg-black/40 p-1.5 text-white transition hover:bg-black/60"
                onClick={onClose}
                aria-label={t("app.close")}
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Scrollable body */}
            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="p-4 sm:p-6">
                {/* Title + meta */}
                <div className="mb-4">
                  <h2 className="font-heading text-xl font-bold text-ink dark:text-gray-100 sm:text-2xl">{recipe.title}</h2>
                  <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-500 dark:text-gray-400">
                    {recipe.source_domain && <span>{recipe.source_domain}</span>}
                    {Boolean(recipe.base_servings) && (
                      <span className="font-medium text-accent">
                        {recipe.base_servings} {t("recipe.servings")}
                      </span>
                    )}
                    {recipe.prep_time_minutes != null && (
                      <span>{recipe.prep_time_minutes} {t("recipe.minutes")}</span>
                    )}
                  </div>
                </div>

                {/* Tags */}
                <div className="mb-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {t("recipe.tags")}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {allTags.map((tag) => {
                      const active = recipe.tags.some((rt) => rt.id === tag.id);
                      return (
                        <button
                          key={tag.id}
                          type="button"
                          disabled={tagSaving}
                          onClick={() => void handleTagToggle(tag)}
                          className={`rounded-full px-2 py-0.5 text-xs font-medium transition ${
                            active
                              ? "text-white"
                              : "border border-gray-300 bg-transparent text-gray-600 dark:border-[#3e3e42] dark:text-gray-400"
                          }`}
                          style={active ? { backgroundColor: tag.color ?? "#6b7280" } : undefined}
                        >
                          {t(`tags.names.${tag.name}`, { defaultValue: tag.name })}
                        </button>
                      );
                    })}
                    {allTags.length === 0 && (
                      <span className="text-xs text-gray-400">{t("recipe.noTags")}</span>
                    )}
                  </div>
                </div>

                {/* Re-scrape notice */}
                {rescrapeMsg && (
                  <p className="mb-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                    {rescrapeMsg}
                  </p>
                )}

                {/* Ingredients */}
                <div className="mb-6">
                  <h3 className="mb-3 font-heading text-lg font-semibold text-ink dark:text-gray-100">
                    {t("recipe.ingredients")}
                  </h3>
                  {recipe.ingredients.length > 0 ? (
                    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {recipe.ingredients.map((ing, i) => (
                        <li
                          key={`${ing.ingredient_name ?? ing.raw_string ?? "ingredient"}-${i}`}
                          className="flex items-start gap-2 rounded-xl bg-green-50 px-3 py-2 dark:bg-green-900/10"
                        >
                          <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-ink dark:text-gray-200">
                              {ing.ingredient_name ?? ing.raw_string}
                              {ing.ingredient_name_fr && (
                                <span className="ml-1 text-sm text-gray-400">({ing.ingredient_name_fr})</span>
                              )}
                            </p>
                            {(ing.quantity != null || ing.unit) && (
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {ing.quantity} {ing.unit}
                              </p>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">{t("recipe.noIngredients")}</p>
                  )}
                </div>

                {/* Instructions */}
                {recipe.instructions_text && (
                  <div className="mb-6">
                    <h3 className="mb-3 font-heading text-lg font-semibold text-ink dark:text-gray-100">
                      {t("recipe.instructions")}
                    </h3>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                      {recipe.instructions_text}
                    </p>
                  </div>
                )}

                {/* Similar recipes */}
                {similar.length > 0 && (
                  <div>
                    <h3 className="mb-3 font-heading text-lg font-semibold text-ink dark:text-gray-100">
                      {t("recipe.similar")}
                    </h3>
                    <div className="space-y-2">
                      {similar.map((s) => (
                        <div
                          key={s.id}
                          className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                        >
                          {s.image_local_path && (
                            <img
                              src={buildImageUrl(s.image_local_path)}
                              alt={s.title}
                              className="h-10 w-10 rounded-lg object-cover"
                            />
                          )}
                          <span className="flex-1 text-sm font-medium text-ink dark:text-gray-200">{s.title}</span>
                          <span className="text-xs text-gray-400">{s.source_domain}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Sticky footer */}
            <div className="shrink-0 rounded-b-2xl border-t border-gray-100 bg-gray-50 p-3 dark:border-[#3e3e42] dark:bg-[#1e1e1e] sm:p-4">
              <div className="flex flex-wrap justify-end gap-2">
                <button
                  type="button"
                  onClick={() => void handleRescrape()}
                  disabled={rescraping}
                  className="rounded-xl border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30] disabled:opacity-50"
                >
                  🔄 {t("recipe.rescrape")}
                </button>
                {recipe.instructions_text && (
                  <button
                    type="button"
                    onClick={() => setCookMode(true)}
                    className="rounded-xl border border-green-400 px-3 py-2 text-sm font-semibold text-green-700 transition hover:bg-green-50 dark:border-green-600 dark:text-green-400 dark:hover:bg-green-900/20"
                  >
                    👨‍🍳 {t("recipe.cookMode")}
                  </button>
                )}
                {recipe.url && (
                  <a
                    href={recipe.url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  >
                    {t("recipe.viewOriginal")}
                  </a>
                )}
                <button
                  className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  onClick={onClose}
                >
                  {t("app.close")}
                </button>
                <button
                  className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90"
                  onClick={onAddToCart}
                >
                  {t("recipe.addToCart")}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </dialog>
  );
}
