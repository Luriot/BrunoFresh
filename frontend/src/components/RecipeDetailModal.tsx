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
        if (cancelled) {
          return;
        }
        setRecipe(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        console.error("Failed to fetch recipe detail", err);
        setError(true);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  return (
    <dialog open tabIndex={-1} className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6" onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}>
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative flex max-h-full w-full max-w-2xl flex-col overflow-y-auto rounded-2xl bg-white shadow-2xl">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <svg
              className="h-8 w-8 animate-spin text-accent"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>
        ) : null}
        {!loading && (error || !recipe) ? (
          <div className="flex pl-6 pr-6 pt-6 pb-6 h-64 flex-col items-center justify-center gap-4 text-center">
            <p className="text-red-500">{t("error.loadFailed")}</p>
            <button
              className="rounded-xl border border-gray-300 px-4 py-2 font-semibold hover:bg-gray-50 text-black"
              onClick={onClose}
            >
              {t("app.close")}
            </button>
          </div>
        ) : null}
        {!loading && recipe ? (
          <>
            <div className="relative h-64 w-full shrink-0 bg-green-50 sm:h-80">
              {recipe.image_local_path ? (
                <img
                  className="h-full w-full object-cover"
                  src={buildImageUrl(recipe.image_local_path)}
                  alt={recipe.title}
                />
              ) : (
                <div className="flex h-full items-center justify-center text-green-600">
                  {t("recipe.noImage")}
                </div>
              )}
              <button
                className="absolute right-4 top-4 rounded-full bg-black/40 p-2 text-white hover:bg-black/60 transition"
                onClick={onClose}
                aria-label={t("app.close")}
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="mb-6">
                <h2 className="font-heading text-2xl font-bold text-ink sm:text-3xl">{recipe.title}</h2>
                <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-600">
                  <span>{recipe.source_domain}</span>
                  {Boolean(recipe.base_servings) && (
                    <span className="font-medium text-accent">
                      {recipe.base_servings} {t("recipe.servings")}
                    </span>
                  )}
                  {recipe.prep_time_minutes && (
                    <span>
                      {recipe.prep_time_minutes} {t("recipe.minutes")}
                    </span>
                  )}
                </div>
              </div>

              <div className="mb-8">
                <h3 className="mb-4 font-heading text-xl font-semibold text-ink">
                  {t("recipe.ingredients")}
                </h3>
                {recipe.ingredients.length > 0 ? (
                  <ul className="space-y-3">
                    {recipe.ingredients.map((ing, i) => (
                      <li key={`${ing.ingredient_name || ing.raw_string || "ingredient"}-${i}`} className="flex items-start gap-3 rounded-xl bg-green-50/50 p-3">
                        <div className="flex h-6 items-center">
                          <div className="h-2 w-2 rounded-full bg-accent"></div>
                        </div>
                        <div className="flex flex-col">
                          <span className="font-medium text-ink">
                            {ing.ingredient_name || ing.raw_string}
                            {ing.ingredient_name_fr && (
                              <span className="ml-1 text-sm text-gray-500">({ing.ingredient_name_fr})</span>
                            )}
                          </span>
                          {(ing.quantity || ing.unit) && (
                            <span className="text-sm text-gray-600">
                              {ing.quantity} {ing.unit}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">{t("recipe.noIngredients")}</p>
                )}
              </div>

              {recipe.instructions_text && (
                <div>
                  <h3 className="mb-4 font-heading text-xl font-semibold text-ink">
                    {t("recipe.instructions")}
                  </h3>
                  <div className="whitespace-pre-wrap text-gray-700">{recipe.instructions_text}</div>
                </div>
              )}
            </div>

            <div className="border-t border-gray-100 bg-gray-50 p-4 sm:p-6 flex justify-end gap-3">
              <button
                className="rounded-xl border border-gray-300 px-5 py-2.5 font-semibold text-gray-700 hover:bg-gray-100 transition"
                onClick={onClose}
              >
                {t("app.close")}
              </button>
              <button
                className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-white hover:bg-accent/90 transition shadow-sm"
                onClick={onAddToCart}
              >
                {t("recipe.addToCart")}
              </button>
            </div>
          </>
        ) : null}
      </div>
    </dialog>
  );
}
