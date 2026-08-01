import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { createMergeRule, deleteMergeRule, fetchIngredientsAdmin, fetchMergeRules } from "../../api/client";
import type { IngredientDetail, IngredientMergeRule, StatusMsg } from "../../types";
import { ArrowRight, Plus, Trash2, X } from "lucide-react";

export function MergeRulesPanel() {
  const { t, i18n } = useTranslation();
  const [rules, setRules] = useState<IngredientMergeRule[]>([]);
  const [ingredients, setIngredients] = useState<IngredientDetail[]>([]);
  const [filterCanonicalId, setFilterCanonicalId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<StatusMsg>(null);

  // Create-rule form state
  const [showForm, setShowForm] = useState(false);
  const [formSource, setFormSource] = useState("");
  const [formCanonicalId, setFormCanonicalId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadRules = useCallback(async () => {
    setLoading(true);
    setStatus(null);
    try {
      const data = await fetchMergeRules(filterCanonicalId ?? undefined);
      setRules(data);
    } catch {
      setRules([]);
      setStatus({ text: t("ingredients.rules.deleteError"), isError: true });
    } finally {
      setLoading(false);
    }
  }, [filterCanonicalId, t]);

  // Load the ingredient catalog once for the canonical picker + the filter dropdown.
  // Lazy-load only when the form opens or the filter is touched.
  const ensureIngredients = useCallback(async () => {
    if (ingredients.length > 0) return;
    try {
      setIngredients(await fetchIngredientsAdmin({ limit: 200 }));
    } catch {
      setIngredients([]);
    }
  }, [ingredients.length]);

  useEffect(() => { void loadRules(); }, [loadRules]);
  useEffect(() => { void ensureIngredients(); }, [ensureIngredients]);

  function getDisplayName(ing: IngredientDetail): string {
    return ing.translations[i18n.language] ?? ing.name_en;
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!formSource.trim() || !formCanonicalId) return;
    setSubmitting(true);
    try {
      await createMergeRule({
        source_name: formSource.trim(),
        canonical_ingredient_id: formCanonicalId,
      });
      setFormSource("");
      setFormCanonicalId(null);
      setShowForm(false);
      setStatus({ text: t("ingredients.rules.createdSuccess"), isError: false });
      await loadRules();
    } catch {
      setStatus({ text: t("ingredients.rules.createError"), isError: true });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(rule: IngredientMergeRule) {
    if (!confirm(t("ingredients.rules.confirmDelete", { source: rule.source_name }))) return;
    try {
      await deleteMergeRule(rule.id);
      setRules((prev) => prev.filter((r) => r.id !== rule.id));
      setStatus({ text: t("ingredients.rules.deleted"), isError: false });
    } catch {
      setStatus({ text: t("ingredients.rules.deleteError"), isError: true });
    }
  }

  const isEmpty = !loading && rules.length === 0;

  return (
    <>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink dark:text-gray-100">{t("ingredients.rules.title")}</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{t("ingredients.rules.subtitle")}</p>
      </div>

      {/* Filter + Add */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          {t("ingredients.rules.filterByCanonical")}
          <select
            className="min-w-0 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            value={filterCanonicalId ?? ""}
            onChange={(e) => setFilterCanonicalId(Number(e.target.value) || null)}
          >
            <option value="">{t("ingredients.rules.allCanonicals")}</option>
            {ingredients.map((ing) => (
              <option key={ing.id} value={ing.id}>{getDisplayName(ing)}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            setShowForm((v) => !v);
            void ensureIngredients();
          }}
          className="flex items-center gap-1.5 rounded-xl bg-accent px-3 py-1.5 text-sm font-semibold text-white transition hover:opacity-90"
        >
          {showForm ? <X className="h-4 w-4" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
          {t("ingredients.rules.add")}
        </button>
      </div>

      {/* Inline create form */}
      {showForm && (
        <form
          onSubmit={(e) => void handleCreate(e)}
          className="mb-5 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
        >
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              required
              maxLength={200}
              value={formSource}
              onChange={(e) => setFormSource(e.target.value)}
              placeholder={t("ingredients.rules.sourceNamePlaceholder")}
              className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-200"
              aria-label={t("ingredients.rules.sourceName")}
            />
            <ArrowRight className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
            <select
              required
              value={formCanonicalId ?? ""}
              onChange={(e) => setFormCanonicalId(Number(e.target.value) || null)}
              className="min-w-0 flex-1 rounded-lg border border-gray-200 bg-white px-2 py-2 text-sm text-gray-900 dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-200"
              aria-label={t("ingredients.rules.canonical")}
            >
              <option value="">{t("ingredients.rules.canonicalPlaceholder")}</option>
              {ingredients.map((ing) => (
                <option key={ing.id} value={ing.id}>{getDisplayName(ing)}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={submitting || !formSource.trim() || !formCanonicalId}
              className="shrink-0 rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-green-500 disabled:opacity-40"
            >
              {submitting ? t("app.loading") : t("ingredients.rules.add")}
            </button>
          </div>
        </form>
      )}

      {status && (
        <p className={`mb-4 text-sm font-medium ${status.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {status.text}
        </p>
      )}

      {loading && <p className="text-sm text-gray-500">{t("app.loading")}</p>}

      {isEmpty && (
        <p className="rounded-xl border border-dashed border-gray-200 p-6 text-center text-sm text-gray-500 dark:border-[#3e3e42] dark:text-gray-400">
          {filterCanonicalId ? t("ingredients.rules.emptyFiltered") : t("ingredients.rules.empty")}
        </p>
      )}

      {rules.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-[#1e1e1e]">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.rules.sourceHeader")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.rules.canonical")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.category")}</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">{t("ingredients.rules.created")}</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50 dark:hover:bg-[#2d2d30]">
                  <td className="px-4 py-2 font-medium text-ink dark:text-gray-200">{rule.source_name}</td>
                  <td className="px-4 py-2 text-green-700 dark:text-green-400">{rule.canonical_name}</td>
                  <td className="px-4 py-2">
                    {rule.canonical_category && (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs dark:bg-[#3e3e42] dark:text-gray-300">
                        {t(`category.${rule.canonical_category}`)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-400">
                    {new Date(rule.created_at).toLocaleDateString(i18n.language)}
                  </td>
                  <td className="px-4 py-2">
                    <button
                      type="button"
                      onClick={() => void handleDelete(rule)}
                      className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-500 transition hover:bg-red-50 dark:border-red-800/40 dark:text-red-400 dark:hover:bg-red-900/20"
                      title={t("ingredients.rules.delete")}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}