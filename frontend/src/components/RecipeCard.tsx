import type { RecipeListItem } from "../types";
import { useTranslation } from "react-i18next";
import { buildImageUrl, patchRecipe } from "../api/client";

type Props = {
  recipe: RecipeListItem;
  onAdd: (recipe: RecipeListItem) => void;
  onClick?: (recipe: RecipeListItem) => void;
  onFavoriteToggled?: (updated: RecipeListItem) => void;
};

export function RecipeCard({ recipe, onAdd, onClick, onFavoriteToggled }: Readonly<Props>) {
  const { t } = useTranslation();

  async function handleFavorite(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const updated = await patchRecipe(recipe.id, { is_favorite: !recipe.is_favorite });
      onFavoriteToggled?.({ ...recipe, is_favorite: updated.is_favorite });
    } catch {
      // silently fail
    }
  }

  return (
    <article
      className="cursor-pointer group flex flex-col rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-[#3e3e42] dark:bg-[#252526]"
      onClick={() => onClick?.(recipe)}
    >
      <div className="relative mb-3 h-36 w-full overflow-hidden rounded-xl bg-green-50 dark:bg-[#1e1e1e]">
        {recipe.image_local_path ? (
          <img
            className="h-full w-full object-cover"
            src={buildImageUrl(recipe.image_local_path)}
            alt={recipe.title}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-green-600 dark:text-gray-500">
            {t("recipe.noImage")}
          </div>
        )}
        {/* Favorite button */}
        <button
          type="button"
          aria-label={recipe.is_favorite ? t("recipe.unfavorite") : t("recipe.favorite")}
          className="absolute right-2 top-2 rounded-full bg-white/80 p-1 text-gray-600 shadow transition hover:bg-white dark:bg-[#252526]/80 dark:text-gray-300 dark:hover:bg-[#252526]"
          onClick={handleFavorite}
        >
          {recipe.is_favorite ? (
            <svg className="h-4 w-4 text-red-500" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
            </svg>
          ) : (
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
            </svg>
          )}
        </button>
      </div>

      <h3 className="font-heading text-lg font-semibold text-ink dark:text-gray-100">{recipe.title}</h3>
      <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">{recipe.source_domain}</p>

      {recipe.tags.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {recipe.tags.map((tag) => (
            <span
              key={tag.id}
              className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
              style={{ backgroundColor: tag.color ?? "#6b7280" }}
            >
              {t(`tags.names.${tag.name}`, { defaultValue: tag.name })}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto">
        <div className="mb-3 flex items-center justify-between gap-3">
          <a
            className="inline-flex text-sm font-semibold text-accent underline-offset-2 hover:underline dark:text-accent/80"
            href={recipe.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            {t("recipe.viewOriginal")}
          </a>
          {recipe.prep_time_minutes != null && (
            <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path strokeLinecap="round" d="M12 6v6l4 2" />
              </svg>
              {recipe.prep_time_minutes} {t("recipe.minutes")}
            </span>
          )}
        </div>
        <button
          className="mt-2 w-full rounded-xl bg-accent px-3 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/50 dark:hover:bg-accent/80"
          onClick={(e) => {
            e.stopPropagation();
            onAdd(recipe);
          }}
        >
          {t("recipe.addToCart")}
        </button>
      </div>
    </article>
  );
}
