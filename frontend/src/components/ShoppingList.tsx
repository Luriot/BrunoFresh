import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ShoppingList as ShoppingListType } from "../types";

type Props = {
  data: ShoppingListType | null;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (name: string) => Promise<void>;
};

export function ShoppingList({ data, onToggleOwned, onAddCustomItem }: Props) {
  const { t, i18n } = useTranslation();
  const [customName, setCustomName] = useState("");

  if (!data) {
    return <p className="text-sm text-gray-600 dark:text-gray-400">{t("shopping.empty")}</p>;
  }

  const toBuy = data.items.filter((item) => !item.is_already_owned);
  const alreadyOwned = data.items.filter((item) => item.is_already_owned);

  async function onCustomSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = customName.trim();
    if (!trimmed) {
      return;
    }
    await onAddCustomItem(trimmed);
    setCustomName("");
  }

  function renderItems(items: ShoppingListType["items"], isOwnedTarget: boolean) {
    if (items.length === 0) {
      return <p className="text-sm text-gray-500 dark:text-gray-400">{t("shopping.none")}</p>;
    }

    return (
      <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
        {items.map((item) => (
          <li key={item.id}>
            <button
              className="flex w-full items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-left transition hover:bg-green-50 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30]"
              onClick={() => onToggleOwned(item.id, isOwnedTarget)}
              type="button"
            >
              <span className="font-medium text-ink dark:text-gray-200">
                {i18n.language === "fr" && item.name_fr ? item.name_fr : item.name}
              </span>
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {item.quantity} {item.unit}
              </span>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h4 className="mb-2 font-heading text-lg font-semibold text-ink dark:text-gray-100">{t("shopping.toBuy")}</h4>
        {renderItems(toBuy, true)}
      </section>

      <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900/30 dark:bg-emerald-900/10">
        <h4 className="mb-2 font-heading text-lg font-semibold text-emerald-900 dark:text-emerald-400">
          {t("shopping.alreadyOwned")}
        </h4>
        {renderItems(alreadyOwned, false)}
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h4 className="mb-2 font-heading text-lg font-semibold text-ink dark:text-gray-100">{t("shopping.addManual")}</h4>
        <form className="flex gap-2" onSubmit={onCustomSubmit}>
          <input
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
            maxLength={200}
            onChange={(event) => setCustomName(event.target.value)}
            placeholder={t("shopping.manualPlaceholder")}
            value={customName}
          />
          <button className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white" type="submit">
            +
          </button>
        </form>
      </section>

      {data.recipes.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
          <h4 className="mb-2 font-heading text-lg font-semibold text-ink dark:text-gray-100">{t("shopping.recipesToCook")}</h4>
          <ul className="space-y-2">
            {data.recipes.map((recipe) => (
              <li
                key={`${recipe.recipe_id}-${recipe.target_servings}`}
                className="rounded-lg border border-green-100 bg-green-50 px-3 py-2 dark:border-green-900/30 dark:bg-green-900/10"
              >
                <p className="text-sm font-semibold text-ink dark:text-gray-200">{recipe.title}</p>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                  {t("shopping.targetServings", { count: recipe.target_servings })}
                </p>
                <a
                  className="mt-2 inline-flex text-xs font-semibold text-accent underline-offset-2 hover:underline"
                  href={recipe.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("recipe.viewOriginal")}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.needs_review.length > 0 && (
        <section className="rounded-2xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-700/30 dark:bg-amber-900/10">
          <h4 className="mb-2 font-heading text-lg font-semibold text-amber-900 dark:text-amber-400">
            {t("shopping.needsReview")}
          </h4>
          <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-300">
            {data.needs_review.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
