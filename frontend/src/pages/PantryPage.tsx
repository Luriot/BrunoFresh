import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { addPantryItem, fetchPantry, removePantryItem } from "../api/client";
import type { PantryItem } from "../types";

const CATEGORIES = [
  "Produce", "Meat", "Fish", "Dairy", "Pantry",
  "Spices", "Bakery", "Frozen", "Beverages", "Condiments", "Other",
];

export function PantryPage() {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [nameFr, setNameFr] = useState("");
  const [category, setCategory] = useState("Other");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchPantry();
      setItems(data);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setAdding(true);
    try {
      const item = await addPantryItem({
        name: trimmed,
        name_fr: nameFr.trim() || undefined,
        category,
      });
      setItems((prev) => [...prev, item]);
      setName("");
      setNameFr("");
      setCategory("Other");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(id: number) {
    setItems((prev) => prev.filter((i) => i.id !== id));
    try {
      await removePantryItem(id);
    } catch {
      void load();
    }
  }

  // Group by category
  const grouped = items.reduce<Record<string, PantryItem[]>>((acc, item) => {
    const cat = item.category ?? "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  return (
    <main className="mx-auto max-w-3xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
      <h1 className="mb-1 font-heading text-2xl font-bold text-ink dark:text-gray-100">{t("pantry.title")}</h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">{t("pantry.subtitle")}</p>

      {/* Add form */}
      <form
        onSubmit={(e) => void handleAdd(e)}
        className="mb-8 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]"
      >
        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-0 flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
            placeholder={t("pantry.namePlaceholder")}
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={200}
          />
          <input
            className="w-40 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
            placeholder={t("pantry.nameFrPlaceholder")}
            value={nameFr}
            onChange={(e) => setNameFr(e.target.value)}
            maxLength={200}
          />
          <select
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{t(`category.${c}`)}</option>
            ))}
          </select>
          <button
            type="submit"
            disabled={adding || !name.trim()}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent/90 disabled:opacity-50"
          >
            {t("pantry.add")}
          </button>
        </div>
      </form>

      {loading && <p className="text-sm text-gray-500">{t("app.loading")}</p>}

      {!loading && items.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("pantry.empty")}</p>
      )}

      {/* Grouped items */}
      <div className="space-y-6">
        {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([cat, catItems]) => (
          <section key={cat}>
            <h2 className="mb-2 font-heading text-lg font-semibold text-ink dark:text-gray-100">
              {t(`category.${cat}`)}
            </h2>
            <ul className="space-y-2">
              {catItems.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 dark:border-[#3e3e42] dark:bg-[#252526]"
                >
                  <div>
                    <span className="font-medium text-ink dark:text-gray-100">
                      {i18n.language === "fr" && item.name_fr ? item.name_fr : item.name}
                    </span>
                    {item.name_fr && i18n.language !== "fr" && (
                      <span className="ml-2 text-sm text-gray-400">({item.name_fr})</span>
                    )}
                  </div>
                  <button
                    type="button"
                    aria-label={t("pantry.remove")}
                    onClick={() => void handleRemove(item.id)}
                    className="ml-4 rounded-lg border border-gray-200 p-1.5 text-gray-400 transition hover:border-red-300 hover:text-red-500 dark:border-[#3e3e42]"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14H6L5 6" />
                      <path d="M10 11v6M14 11v6" />
                      <path d="M9 6V4h6v2" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  );
}
