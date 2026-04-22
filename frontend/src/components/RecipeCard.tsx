import type { RecipeListItem } from "../types";
import { useTranslation } from "react-i18next";
import { buildImageUrl } from "../api/client";

type Props = {
  recipe: RecipeListItem;
  onAdd: (recipe: RecipeListItem) => void;
};

export function RecipeCard({ recipe, onAdd }: Props) {
  const { t } = useTranslation();

  return (
    <article className="rounded-2xl border border-orange-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="mb-3 h-36 w-full overflow-hidden rounded-xl bg-orange-50">
        {recipe.image_local_path ? (
          <img
            className="h-full w-full object-cover"
            src={buildImageUrl(recipe.image_local_path)}
            alt={recipe.title}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-orange-600">
            {t("recipe.noImage")}
          </div>
        )}
      </div>
      <h3 className="font-heading text-lg font-semibold text-ink">{recipe.title}</h3>
      <p className="mb-3 text-sm text-gray-600">{recipe.source_domain}</p>
      <a
        className="mb-3 inline-flex text-sm font-semibold text-accent underline-offset-2 hover:underline"
        href={recipe.url}
        target="_blank"
        rel="noreferrer"
      >
        {t("recipe.viewOriginal")}
      </a>
      <button
        className="w-full rounded-xl bg-accent px-3 py-2 text-sm font-semibold text-white"
        onClick={() => onAdd(recipe)}
      >
        {t("recipe.addToCart")}
      </button>
    </article>
  );
}
