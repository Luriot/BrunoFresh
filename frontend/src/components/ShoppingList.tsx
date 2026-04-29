import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ShoppingList as ShoppingListType } from "../types";
import { UnitSelector } from "./UnitSelector";

type CustomItemPayload = { name: string; quantity: number; unit: string };

type Props = {
  data: ShoppingListType | null;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onToggleExcluded: (itemId: number, isExcluded: boolean) => void;
  onAddCustomItem: (payload: CustomItemPayload) => Promise<void>;
  onDeleteItem?: (itemId: number) => void;
};

export function ShoppingList({ data, onToggleOwned, onToggleExcluded, onAddCustomItem, onDeleteItem }: Readonly<Props>) {
  const { t, i18n } = useTranslation();
  const [customName, setCustomName] = useState("");
  const [customQty, setCustomQty] = useState<number>(1);
  const [customUnit, setCustomUnit] = useState("piece");
  const [copied, setCopied] = useState(false);

  if (!data) {
    return <p className="text-sm text-gray-600 dark:text-gray-400">{t("shopping.empty")}</p>;
  }

  const toBuy = data.items.filter((item) => !item.is_already_owned && !item.is_excluded);
  const alreadyOwned = data.items.filter((item) => item.is_already_owned);
  const excluded = data.items.filter((item) => item.is_excluded);

  async function onCustomSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = customName.trim();
    if (!trimmed) {
      return;
    }
    await onAddCustomItem({ name: trimmed, quantity: customQty, unit: customUnit });
    setCustomName("");
    setCustomQty(1);
    setCustomUnit("piece");
  }

  async function handleCopy() {
    const grouped = toBuy.reduce<Record<string, typeof toBuy>>((acc, item) => {
      const cat = item.category || "Other";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(item);
      return acc;
    }, {});

    const lines: string[] = [];
    for (const [cat, items] of Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b))) {
      const catLabel = t(`category.${cat}`);
      lines.push(`── ${catLabel} ──`);
      for (const item of items) {
        const name = i18n.language === "fr" && item.name_fr ? item.name_fr : item.name;
        lines.push(`• ${item.quantity} ${item.unit} ${name}`);
      }
    }

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }

  function renderItems(items: ShoppingListType["items"], isOwnedTarget: boolean, showExcludeBtn = false) {
    if (items.length === 0) {
      return <p className="text-sm text-gray-500 dark:text-gray-400">{t("shopping.none")}</p>;
    }

    return (
      <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-2">
            <button
              className="flex flex-1 items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-left transition hover:bg-green-50 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30]"
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
            {showExcludeBtn && (
              <button
                type="button"
                aria-label={t("shopping.excludeItem")}
                title={t("shopping.excludeItem")}
                onClick={() => onToggleExcluded(item.id, true)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-gray-200 text-gray-400 transition hover:border-orange-300 hover:text-orange-500 dark:border-[#3e3e42] dark:hover:border-orange-700 dark:hover:text-orange-400"
              >
                {/* Ban / slash-circle icon */}
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                </svg>
              </button>
            )}
          </li>
        ))}
      </ul>
    );
  }

  function renderExcludedItems(items: ShoppingListType["items"]) {
    if (items.length === 0) {
      return <p className="text-sm text-gray-500 dark:text-gray-400">{t("shopping.none")}</p>;
    }

    return (
      <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-2">
            <span className="flex flex-1 items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 opacity-60 dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
              <span className="font-medium line-through text-gray-500 dark:text-gray-500">
                {i18n.language === "fr" && item.name_fr ? item.name_fr : item.name}
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {item.quantity} {item.unit}
              </span>
            </span>
            <button
              type="button"
              aria-label={t("shopping.restoreItem")}
              title={t("shopping.restoreItem")}
              onClick={() => onToggleExcluded(item.id, false)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-gray-200 text-gray-400 transition hover:border-green-300 hover:text-green-600 dark:border-[#3e3e42] dark:hover:border-green-700 dark:hover:text-green-400"
            >
              {/* Undo / restore icon */}
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 .49-4" />
              </svg>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="font-heading text-lg font-semibold text-ink dark:text-gray-100">{t("shopping.toBuy")}</h4>
            <button
              type="button"
              onClick={() => void handleCopy()}
              disabled={toBuy.length === 0}
              className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 transition hover:bg-gray-50 disabled:opacity-40 dark:border-[#3e3e42] dark:text-gray-400 dark:hover:bg-[#2d2d30]"
            >
              {copied ? (
                <svg className="h-4 w-4 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} aria-label={t("shopping.copied")}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-label={t("shopping.copy")}>
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
              )}
            </button>
          </div>
          {renderItems(toBuy, true, true)}
        </section>

        <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900/30 dark:bg-emerald-900/10">
          <h4 className="mb-2 font-heading text-lg font-semibold text-emerald-900 dark:text-emerald-400">
            {t("shopping.alreadyOwned")}
          </h4>
          {renderItems(alreadyOwned, false)}
        </section>
      </div>

      {excluded.length > 0 && (
        <section className="rounded-2xl border border-orange-200 bg-orange-50 p-4 dark:border-orange-900/30 dark:bg-orange-900/10">
          <h4 className="mb-2 font-heading text-lg font-semibold text-orange-900 dark:text-orange-400">
            {t("shopping.excluded")}
          </h4>
          {renderExcludedItems(excluded)}
        </section>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h4 className="mb-2 font-heading text-lg font-semibold text-ink dark:text-gray-100">{t("shopping.addManual")}</h4>
        <form className="flex flex-wrap gap-2" onSubmit={onCustomSubmit}>
          <input
            className="min-w-0 flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
            maxLength={200}
            onChange={(event) => setCustomName(event.target.value)}
            placeholder={t("shopping.manualPlaceholder")}
            value={customName}
          />
          <input
            type="number"
            step="0.1"
            min="0.1"
            max="9999"
            className="w-20 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            value={customQty}
            onChange={(e) => setCustomQty(Math.max(0.1, Number(e.target.value) || 1))}
          />
          <UnitSelector
            value={customUnit}
            onChange={setCustomUnit}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
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
