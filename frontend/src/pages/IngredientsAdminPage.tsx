import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchIngredientsAdmin, mergeIngredients, patchIngredient } from "../api/client";
import type { IngredientDetail } from "../types";

const CATEGORIES = [
  "Produce", "Meat", "Fish", "Dairy", "Pantry",
  "Spices", "Bakery", "Frozen", "Beverages", "Condiments", "Other",
];

type EditDraft = { id: number; name_en: string; name_fr: string; category: string };
type StatusMsg = { text: string; isError: boolean } | null;

export function IngredientsAdminPage() {
  const { t } = useTranslation();
  const [ingredients, setIngredients] = useState<IngredientDetail[]>([]);
  const [search, setSearch] = useState("");
  const [needsReview, setNeedsReview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null);
  const [mergeSourceId, setMergeSourceId] = useState<number | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState<number | null>(null);
  const [status, setStatus] = useState<StatusMsg>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setStatus(null);
    try {
      const data = await fetchIngredientsAdmin({
        q: search || undefined,
        needs_review: needsReview || undefined,
        limit: 100,
      });
      setIngredients(data);
    } catch {
      setIngredients([]);
    } finally {
      setLoading(false);
    }
  }, [search, needsReview]);

  useEffect(() => { void load(); }, [load]);

  function startEdit(ing: IngredientDetail) {
    setEditDraft({ id: ing.id, name_en: ing.name_en, name_fr: ing.name_fr ?? "", category: ing.category ?? "Other" });
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!editDraft) return;
    try {
      const updated = await patchIngredient(editDraft.id, {
        name_en: editDraft.name_en.trim(),
        name_fr: editDraft.name_fr.trim() || undefined,
        category: editDraft.category,
      });
      setIngredients((prev) => prev.map((i) => i.id === editDraft.id ? updated : i));
      setEditDraft(null);
      setStatus({ text: t("ingredients.saveSuccess"), isError: false });
    } catch {
      setStatus({ text: t("ingredients.saveError"), isError: true });
    }
  }

  async function handleMerge() {
    if (!mergeSourceId || !mergeTargetId) return;
    const source = ingredients.find((i) => i.id === mergeSourceId);
    const target = ingredients.find((i) => i.id === mergeTargetId);
    if (!source || !target) return;
    if (!confirm(t("ingredients.confirmMerge", { source: source.name_en, target: target.name_en }))) return;
    try {
      await mergeIngredients(mergeSourceId, mergeTargetId);
      setIngredients((prev) => prev.filter((i) => i.id !== mergeSourceId));
      setMergeSourceId(null);
      setMergeTargetId(null);
      setStatus({ text: t("ingredients.merged"), isError: false });
    } catch {
      setStatus({ text: t("ingredients.mergeError"), isError: true });
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
      <h1 className="mb-6 font-heading text-2xl font-bold text-ink dark:text-gray-100">{t("ingredients.title")}</h1>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="min-w-0 flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          placeholder={t("ingredients.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm dark:border-[#3e3e42] dark:text-gray-300">
          <input
            type="checkbox"
            checked={needsReview}
            onChange={(e) => setNeedsReview(e.target.checked)}
          />
          {t("ingredients.needsReview")}
        </label>
      </div>

      {/* Merge tool */}
      <div className="mb-6 flex flex-wrap items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-700/30 dark:bg-amber-900/10">
        <span className="text-sm font-semibold text-amber-700 dark:text-amber-400">{t("ingredients.mergeLabel")}</span>
        <select
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          value={mergeSourceId ?? ""}
          onChange={(e) => setMergeSourceId(Number(e.target.value) || null)}
        >
          <option value="">{t("ingredients.sourcePlaceholder")}</option>
          {ingredients.map((i) => <option key={i.id} value={i.id}>{i.name_en}</option>)}
        </select>
        <span className="text-sm text-gray-500">→</span>
        <select
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          value={mergeTargetId ?? ""}
          onChange={(e) => setMergeTargetId(Number(e.target.value) || null)}
        >
          <option value="">{t("ingredients.targetPlaceholder")}</option>
          {ingredients.map((i) => <option key={i.id} value={i.id}>{i.name_en}</option>)}
        </select>
        <button
          type="button"
          disabled={!mergeSourceId || !mergeTargetId || mergeSourceId === mergeTargetId}
          onClick={() => void handleMerge()}
          className="rounded-xl bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-amber-400 disabled:opacity-40"
        >
          {t("ingredients.mergeInto")}
        </button>
      </div>

      {status && (
        <p className={`mb-4 text-sm font-medium ${status.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {status.text}
        </p>
      )}

      {loading && <p className="text-sm text-gray-500">{t("app.loading")}</p>}

      {!loading && ingredients.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("ingredients.noResults")}</p>
      )}

      {/* Table */}
      {ingredients.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-[#1e1e1e]">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">#</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.nameEn")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.nameFr")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.category")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.usages")}</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
              {ingredients.map((ing) =>
                editDraft?.id === ing.id ? (
                  <tr key={ing.id} className="bg-green-50 dark:bg-green-900/10">
                    <td className="px-4 py-2 text-gray-400">{ing.id}</td>
                    <td className="px-4 py-2">
                      <input
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                        value={editDraft.name_en}
                        onChange={(e) => setEditDraft((d) => d ? { ...d, name_en: e.target.value } : d)}
                        maxLength={200}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                        value={editDraft.name_fr}
                        onChange={(e) => setEditDraft((d) => d ? { ...d, name_fr: e.target.value } : d)}
                        maxLength={200}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <select
                        className="rounded border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                        value={editDraft.category}
                        onChange={(e) => setEditDraft((d) => d ? { ...d, category: e.target.value } : d)}
                      >
                        {CATEGORIES.map((c) => <option key={c} value={c}>{t(`category.${c}`)}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-2 text-gray-400">{ing.usage_count}</td>
                    <td className="px-4 py-2">
                      <form onSubmit={(e) => void handleSave(e)} className="flex gap-1">
                        <button type="submit" className="rounded-lg bg-accent px-2 py-1 text-xs font-semibold text-white">
                          {t("ingredients.save")}
                        </button>
                        <button type="button" onClick={() => setEditDraft(null)} className="rounded-lg border border-gray-200 px-2 py-1 text-xs dark:border-[#3e3e42] dark:text-gray-300">
                          ✕
                        </button>
                      </form>
                    </td>
                  </tr>
                ) : (
                  <tr key={ing.id} className={`hover:bg-gray-50 dark:hover:bg-[#2d2d30] ${ing.needs_review ? "bg-amber-50 dark:bg-amber-900/10" : ""}`}>
                    <td className="px-4 py-2 text-gray-400">{ing.id}</td>
                    <td className="px-4 py-2 font-medium text-ink dark:text-gray-200">{ing.name_en}</td>
                    <td className="px-4 py-2 text-gray-500 dark:text-gray-400">{ing.name_fr ?? "—"}</td>
                    <td className="px-4 py-2">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs dark:bg-[#3e3e42] dark:text-gray-300">
                        {t(`category.${ing.category ?? "Other"}`)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-500">{ing.usage_count}</td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={() => startEdit(ing)}
                        className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-400 dark:hover:bg-[#2d2d30]"
                      >
                        ✏️ {t("ingredients.edit")}
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
