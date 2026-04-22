import type { RecipeListItem } from "../types";
import { useTranslation } from "react-i18next";
import { buildImageUrl } from "../api/client";

type Props = {
  recipe: RecipeListItem;
  onAdd: (recipe: RecipeListItem) => void;
  onClick?: (recipe: RecipeListItem) => void;
};

export function RecipeCard({ recipe, onAdd, onClick }: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <article 
      className="cursor-pointer group flex flex-col rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-[#3e3e42] dark:bg-[#252526]"
      onClick={() => onClick?.(recipe)}
    >
      <div className="mb-3 h-36 w-full overflow-hidden rounded-xl bg-green-50 dark:bg-[#1e1e1e]">
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
      </div>
      <h3 className="font-heading text-lg font-semibold text-ink dark:text-gray-100">{recipe.title}</h3>
      <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">{recipe.source_domain}</p>
      <div className="mt-auto">
        <a
          className="mb-3 inline-flex text-sm font-semibold text-accent underline-offset-2 hover:underline dark:text-accent/80"
          href={recipe.url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          {t("recipe.viewOriginal")}
        </a>
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
