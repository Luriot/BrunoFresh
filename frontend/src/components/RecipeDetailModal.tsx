import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { buildImageUrl, fetchRecipeDetail } from "../api/client";
import type { RecipeDetail } from "../types";

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

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    fetchRecipeDetail(recipeId)
      .then((data) => {
        if (cancelled) return;
        setRecipe(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to fetch recipe detail", err);
        setError(true);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [recipeId]);

  return (
    <dialog
      open
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
                <div className="mb-5">
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
                  <div>
                    <h3 className="mb-3 font-heading text-lg font-semibold text-ink dark:text-gray-100">
                      {t("recipe.instructions")}
                    </h3>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                      {recipe.instructions_text}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Sticky footer */}
            <div className="shrink-0 rounded-b-2xl border-t border-gray-100 bg-gray-50 p-3 dark:border-[#3e3e42] dark:bg-[#1e1e1e] sm:p-4">
              <div className="flex justify-end gap-2">
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
