import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchIngredientsAdmin, mergeIngredients, patchIngredient, suggestIngredientMerges } from "../../api/client";
import type { IngredientDetail, MergeSuggestion } from "../../types";
import { ArrowRight, Pencil, Sparkles, X } from "lucide-react";

const CATEGORIES = [
  "Produce", "Meat", "Fish", "Dairy", "Pantry",
  "Spices", "Bakery", "Frozen", "Beverages", "Condiments", "Other",
];

type EditDraft = { id: number; name: string; category: string };
type StatusMsg = { text: string; isError: boolean } | null;

export function IngredientsTab() {
  const { t, i18n } = useTranslation();
  const [ingredients, setIngredients] = useState<IngredientDetail[]>([]);
  const [search, setSearch] = useState("");
  const [needsReview, setNeedsReview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null);
  const [mergeSourceId, setMergeSourceId] = useState<number | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState<number | null>(null);
  const [status, setStatus] = useState<StatusMsg>(null);
  const [aiSuggestions, setAiSuggestions] = useState<MergeSuggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);

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

  function getDisplayName(ing: IngredientDetail): string {
    return ing.translations[i18n.language] ?? ing.name_en;
  }

  function startEdit(ing: IngredientDetail) {
    setEditDraft({ id: ing.id, name: getDisplayName(ing), category: ing.category ?? "Other" });
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!editDraft) return;
    try {
      const updated = await patchIngredient(editDraft.id, {
        name: editDraft.name.trim(),
        lang: i18n.language,
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
    if (!confirm(t("ingredients.confirmMerge", { source: getDisplayName(source), target: getDisplayName(target) }))) return;
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

  async function handleAiSuggest() {
    setAiLoading(true);
    setStatus(null);
    setAiSuggestions([]);
    setSelectedSuggestions(new Set());
    setShowAiPanel(true);
    try {
      const res = await suggestIngredientMerges();
      setAiSuggestions(res.suggestions);
    } catch {
      setStatus({ text: t("ingredients.aiUnavailable"), isError: true });
      setShowAiPanel(false);
    } finally {
      setAiLoading(false);
    }
  }

  async function handleApplySuggestions() {
    const toApply = aiSuggestions.filter((_, i) => selectedSuggestions.has(i));
    let applied = 0;
    for (const s of toApply) {
      try {
        await mergeIngredients(s.source_id, s.target_id);
        setIngredients((prev) => prev.filter((i) => i.id !== s.source_id));
        applied++;
      } catch {
        // continue with others
      }
    }
    setAiSuggestions([]);
    setSelectedSuggestions(new Set());
    setShowAiPanel(false);
    setStatus({ text: t("ingredients.mergeApplied", { count: applied }), isError: false });
  }

  return (
    <>
      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
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

      {/* Manual merge tool */}
      <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-700/30 dark:bg-amber-900/10">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-amber-700 dark:text-amber-400">{t("ingredients.mergeLabel")}</span>
          <button
            type="button"
            disabled={aiLoading}
            onClick={() => void handleAiSuggest()}
            className="flex shrink-0 items-center gap-1.5 rounded-xl border border-amber-300 bg-white px-3 py-1.5 text-sm font-semibold text-amber-700 transition hover:bg-amber-50 disabled:opacity-40 dark:border-amber-700/40 dark:bg-[#252526] dark:text-amber-400"
          >
            {aiLoading ? t("ingredients.aiMerging") : <><Sparkles className="h-4 w-4" aria-hidden="true" /> {t("ingredients.aiSuggestMerges")}</>}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            value={mergeSourceId ?? ""}
            onChange={(e) => setMergeSourceId(Number(e.target.value) || null)}
          >
            <option value="">{t("ingredients.sourcePlaceholder")}</option>
            {ingredients.map((i) => <option key={i.id} value={i.id}>{getDisplayName(i)}</option>)}
          </select>
          <ArrowRight className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
          <select
            className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            value={mergeTargetId ?? ""}
            onChange={(e) => setMergeTargetId(Number(e.target.value) || null)}
          >
            <option value="">{t("ingredients.targetPlaceholder")}</option>
            {ingredients.map((i) => <option key={i.id} value={i.id}>{getDisplayName(i)}</option>)}
          </select>
          <button
            type="button"
            disabled={!mergeSourceId || !mergeTargetId || mergeSourceId === mergeTargetId}
            onClick={() => void handleMerge()}
            className="shrink-0 rounded-xl bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-amber-400 disabled:opacity-40"
          >
            {t("ingredients.mergeInto")}
          </button>
        </div>
      </div>

      {/* AI merge suggestions panel */}
      {showAiPanel && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-700/30 dark:bg-amber-900/10">
          <div className="mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-semibold text-amber-800 dark:text-amber-300">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              {t("ingredients.aiSuggestMergesTitle")}
            </span>
            <button type="button" onClick={() => setShowAiPanel(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-4 w-4" aria-hidden="true" /></button>
          </div>
          {aiSuggestions.length === 0 ? (
            <p className="text-sm text-gray-500">{t("ingredients.noSuggestions")}</p>
          ) : (
            <>
              <ul className="mb-3 space-y-2">
                {aiSuggestions.map((s, i) => (
                  <li key={`${s.source_id}-${s.target_id}`} className="flex items-center gap-3 rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm dark:border-amber-700/20 dark:bg-[#252526]">
                    <input
                      type="checkbox"
                      checked={selectedSuggestions.has(i)}
                      onChange={(e) => setSelectedSuggestions((prev) => {
                        const next = new Set(prev);
                        if (e.target.checked) next.add(i); else next.delete(i);
                        return next;
                      })}
                    />
                    <span className="font-medium text-red-600 dark:text-red-400">{s.source_name}</span>
                    <span className="text-gray-400">→</span>
                    <span className="font-medium text-green-700 dark:text-green-400">{s.target_name}</span>
                    <span className="ml-auto text-xs text-gray-400 italic">{s.reason}</span>
                  </li>
                ))}
              </ul>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={selectedSuggestions.size === 0}
                  onClick={() => void handleApplySuggestions()}
                  className="rounded-xl bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-amber-400 disabled:opacity-40"
                >
                  {t("ingredients.applyMerges", { count: selectedSuggestions.size })}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const all = new Set(aiSuggestions.map((_, i) => i));
                    setSelectedSuggestions(selectedSuggestions.size === aiSuggestions.length ? new Set() : all);
                  }}
                  className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm dark:border-[#3e3e42] dark:text-gray-300"
                >
                  {selectedSuggestions.size === aiSuggestions.length ? t("shopping.cancel") : t("app.favoritesFilter").replace("Favoris", "Tout").replace("Favorites", "All")}
                </button>
              </div>
            </>
          )}
        </div>
      )}

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
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.name")}</th>
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
                    <td className="px-4 py-2" colSpan={2}>
                      <div className="flex gap-2">
                        <input
                          className="flex-1 rounded border border-gray-200 bg-white px-2 py-1 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                          value={editDraft.name}
                          onChange={(e) => setEditDraft((d) => d ? { ...d, name: e.target.value } : d)}
                          maxLength={200}
                          placeholder={t("ingredients.name")}
                        />
                        <select
                          className="rounded border border-gray-200 bg-white px-2 py-1 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                          value={editDraft.category}
                          onChange={(e) => setEditDraft((d) => d ? { ...d, category: e.target.value } : d)}
                        >
                          {CATEGORIES.map((c) => <option key={c} value={c}>{t(`category.${c}`)}</option>)}
                        </select>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-gray-400">{ing.usage_count}</td>
                    <td className="px-4 py-2">
                      <form onSubmit={(e) => void handleSave(e)} className="flex gap-1">
                        <button type="submit" className="rounded-lg bg-accent px-2 py-1 text-xs font-semibold text-white">
                          {t("ingredients.save")}
                        </button>
                        <button type="button" onClick={() => setEditDraft(null)} className="rounded-lg border border-gray-200 px-2 py-1 text-xs dark:border-[#3e3e42] dark:text-gray-300">
                          <X className="h-3.5 w-3.5" aria-hidden="true" />
                        </button>
                      </form>
                    </td>
                  </tr>
                ) : (
                  <tr key={ing.id} className={`hover:bg-gray-50 dark:hover:bg-[#2d2d30] ${ing.needs_review ? "bg-amber-50 dark:bg-amber-900/10" : ""}`}>
                    <td className="px-4 py-2 text-gray-400">{ing.id}</td>
                    <td className="px-4 py-2 font-medium text-ink dark:text-gray-200">{getDisplayName(ing)}</td>
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
                        className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-400 dark:hover:bg-[#2d2d30]"
                      >
                        <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                        {t("ingredients.edit")}
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
