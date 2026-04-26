import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { createTag, deleteTag, deleteRecipe, exportDb, fetchIngredientsAdmin, fetchTags, findDuplicateRecipes, importDb, mergeIngredients, patchIngredient, suggestIngredientMerges } from "../api/client";
import type { IngredientDetail, MergeSuggestion, RecipeSimilarPair, Tag } from "../types";

type AdminTab = "ingredients" | "tags" | "duplicates" | "database";

const CATEGORIES = [
  "Produce", "Meat", "Fish", "Dairy", "Pantry",
  "Spices", "Bakery", "Frozen", "Beverages", "Condiments", "Other",
];

type EditDraft = { id: number; name: string; category: string };
type StatusMsg = { text: string; isError: boolean } | null;

export function AdminPage() {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<AdminTab>("ingredients");
  const [ingredients, setIngredients] = useState<IngredientDetail[]>([]);
  const [search, setSearch] = useState("");
  const [needsReview, setNeedsReview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null);
  const [mergeSourceId, setMergeSourceId] = useState<number | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState<number | null>(null);
  const [status, setStatus] = useState<StatusMsg>(null);

  // Tag management state
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState("");
  const [newTagColor, setNewTagColor] = useState("#6b7280");
  const [tagLoading, setTagLoading] = useState(false);

  useEffect(() => {
    fetchTags().then(setTags).catch(() => {});
  }, []);

  async function handleCreateTag(e: FormEvent) {
    e.preventDefault();
    const name = newTagName.trim();
    if (!name) return;
    setTagLoading(true);
    try {
      const tag = await createTag(name, newTagColor);
      setTags((prev) => [...prev, tag]);
      setNewTagName("");
      setNewTagColor("#6b7280");
    } catch {
      setStatus({ text: t("tags.createError"), isError: true });
    } finally {
      setTagLoading(false);
    }
  }

  async function handleDeleteTag(tagId: number) {
    if (!confirm(t("tags.confirmDelete"))) return;
    try {
      await deleteTag(tagId);
      setTags((prev) => prev.filter((tg) => tg.id !== tagId));
    } catch {
      setStatus({ text: t("tags.deleteError"), isError: true });
    }
  }

  // Recipe duplicate scan state
  const [recipePairs, setRecipePairs] = useState<RecipeSimilarPair[]>([]);
  const [scanLoading, setScanLoading] = useState(false);
  const [showScanPanel, setShowScanPanel] = useState(false);
  // AI merge suggestions state
  const [aiSuggestions, setAiSuggestions] = useState<MergeSuggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());

  async function handleScanRecipes() {
    setScanLoading(true);
    setShowScanPanel(true);
    setStatus(null);
    try {
      const res = await findDuplicateRecipes();
      setRecipePairs(res.pairs);
    } catch {
      setStatus({ text: t("recipes.scanError"), isError: true });
      setShowScanPanel(false);
    } finally {
      setScanLoading(false);
    }
  }

  async function handleDeleteRecipeFromPair(recipeId: number) {
    if (!confirm(t("recipes.confirmDelete"))) return;
    try {
      await deleteRecipe(recipeId);
      setRecipePairs((prev) => prev.filter((p) => p.recipe_a_id !== recipeId && p.recipe_b_id !== recipeId));
      setStatus({ text: t("recipes.deleted"), isError: false });
    } catch {
      setStatus({ text: t("recipes.deleteError"), isError: true });
    }
  }
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);

  // Database tab state
  const [dbExporting, setDbExporting] = useState(false);
  const [dbImporting, setDbImporting] = useState(false);
  const [dbStatus, setDbStatus] = useState<StatusMsg>(null);
  const importFileRef = useRef<HTMLInputElement>(null);

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

  async function handleExportDb() {
    setDbExporting(true);
    setDbStatus(null);
    try {
      const blob = await exportDb();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "brunofresh_backup.db";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDbStatus({ text: t("admin.db.importError"), isError: true });
    } finally {
      setDbExporting(false);
    }
  }

  async function handleImportDb(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm(t("admin.db.importDesc"))) {
      if (importFileRef.current) importFileRef.current.value = "";
      return;
    }
    setDbImporting(true);
    setDbStatus(null);
    try {
      await importDb(file);
      setDbStatus({ text: t("admin.db.importSuccess"), isError: false });
    } catch {
      setDbStatus({ text: t("admin.db.importError"), isError: true });
    } finally {
      setDbImporting(false);
      if (importFileRef.current) importFileRef.current.value = "";
    }
  }

  const TABS: { key: AdminTab; label: string }[] = [
    { key: "ingredients", label: t("admin.tabs.ingredients") },
    { key: "tags", label: t("admin.tabs.tags") },
    { key: "duplicates", label: t("admin.tabs.duplicates") },
    { key: "database", label: t("admin.tabs.database") },
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
      {/* Tab bar */}
      <div className="mb-6 flex flex-wrap gap-1 rounded-2xl border border-gray-200 bg-gray-50 p-1 dark:border-[#3e3e42] dark:bg-[#252526]">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.key
                ? "bg-accent text-white shadow"
                : "text-gray-600 hover:text-ink dark:text-gray-400 dark:hover:text-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Ingredients tab ──────────────────────────────────────────────── */}
      {activeTab === "ingredients" && (
        <>

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

      {/* Manual merge tool */}
      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-700/30 dark:bg-amber-900/10">
        <span className="text-sm font-semibold text-amber-700 dark:text-amber-400">{t("ingredients.mergeLabel")}</span>
        <select
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          value={mergeSourceId ?? ""}
          onChange={(e) => setMergeSourceId(Number(e.target.value) || null)}
        >
          <option value="">{t("ingredients.sourcePlaceholder")}</option>
          {ingredients.map((i) => <option key={i.id} value={i.id}>{getDisplayName(i)}</option>)}
        </select>
        <span className="text-sm text-gray-500">→</span>
        <select
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
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
          className="rounded-xl bg-amber-500 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-amber-400 disabled:opacity-40"
        >
          {t("ingredients.mergeInto")}
        </button>
        <button
          type="button"
          disabled={aiLoading}
          onClick={() => void handleAiSuggest()}
          className="ml-auto rounded-xl border border-amber-300 bg-white px-3 py-1.5 text-sm font-semibold text-amber-700 transition hover:bg-amber-50 disabled:opacity-40 dark:border-amber-700/40 dark:bg-[#252526] dark:text-amber-400"
        >
          {aiLoading ? t("ingredients.aiMerging") : `✨ ${t("ingredients.aiSuggestMerges")}`}
        </button>
      </div>

      {/* AI merge suggestions panel */}
      {showAiPanel && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-700/30 dark:bg-amber-900/10">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-semibold text-amber-800 dark:text-amber-300">
              ✨ {t("ingredients.aiSuggestMergesTitle")}
            </span>
            <button type="button" onClick={() => setShowAiPanel(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">✕</button>
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
                          className="flex-1 rounded border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                          value={editDraft.name}
                          onChange={(e) => setEditDraft((d) => d ? { ...d, name: e.target.value } : d)}
                          maxLength={200}
                          placeholder={t("ingredients.name")}
                        />
                        <select
                          className="rounded border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
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
                          ✕
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
        </>
      )}

      {/* ── Duplicates tab ───────────────────────────────────────────────── */}
      {activeTab === "duplicates" && (
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-heading text-base font-bold text-ink dark:text-gray-100">
            🔍 {t("recipes.findDuplicates")}
          </h2>
          <button
            type="button"
            onClick={() => void handleScanRecipes()}
            disabled={scanLoading}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {scanLoading ? t("recipes.scanning") : t("recipes.scan")}
          </button>
        </div>

        {showScanPanel && !scanLoading && (
          <div>
            {recipePairs.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">{t("recipes.noDuplicates")}</p>
            ) : (
              <p className="mb-3 text-sm text-gray-600 dark:text-gray-400">
                {t("recipes.duplicatePairs", { count: recipePairs.length })}
              </p>
            )}
            <div className="flex flex-col gap-4">
              {recipePairs.map((pair) => (
                <div
                  key={`${pair.recipe_a_id}-${pair.recipe_b_id}`}
                  className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-700/30 dark:bg-amber-900/10"
                >
                  <div className="mb-2 text-xs text-gray-500 dark:text-gray-400">
                    {t("scrape.titleScore")}: {pair.title_score}% &nbsp;·&nbsp;
                    {t("scrape.ingredientScore")}: {Math.round(pair.ingredient_score * 100)}%
                  </div>
                  <div className="flex flex-col gap-3 sm:flex-row">
                    {([
                      { id: pair.recipe_a_id, title: pair.recipe_a_title, image: pair.recipe_a_image },
                      { id: pair.recipe_b_id, title: pair.recipe_b_title, image: pair.recipe_b_image },
                    ] as { id: number; title: string; image: string | null }[]).map((recipe) => (
                      <div key={recipe.id} className="flex flex-1 items-center gap-3 rounded-xl bg-white p-3 dark:bg-[#1e1e1e]">
                        {recipe.image && (
                          <img
                            src={`/images/${recipe.image}`}
                            alt=""
                            className="h-12 w-12 rounded-lg object-cover"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-ink dark:text-gray-100">{recipe.title}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleDeleteRecipeFromPair(recipe.id)}
                          className="ml-2 rounded-lg bg-red-100 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
                        >
                          {t("recipes.delete")}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
      )}

      {/* ── Tags tab ─────────────────────────────────────────────────────── */}
      {activeTab === "tags" && (
      <section>
        <h2 className="mb-4 font-heading text-base font-bold text-ink dark:text-gray-100">
          🏷 {t("tags.manage")}
        </h2>
        <form onSubmit={(e) => void handleCreateTag(e)} className="mb-4 flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder={t("tags.namePlaceholder")}
            className="flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            required
          />
          <input
            type="color"
            value={newTagColor}
            onChange={(e) => setNewTagColor(e.target.value)}
            className="h-9 w-10 cursor-pointer rounded-lg border border-gray-200 p-0.5 dark:border-[#3e3e42]"
            title={t("tags.colorLabel")}
          />
          <button
            type="submit"
            disabled={tagLoading || !newTagName.trim()}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {t("tags.add")}
          </button>
        </form>

        {tags.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t("tags.empty")}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag.id}
                className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-white"
                style={{ backgroundColor: tag.color ?? "#6b7280" }}
              >
                {tag.name}
                <button
                  type="button"
                  onClick={() => void handleDeleteTag(tag.id)}
                  className="ml-0.5 opacity-70 hover:opacity-100"
                  aria-label={t("tags.delete")}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        )}
      </section>
      )}

      {/* ── Database tab ─────────────────────────────────────────────────── */}
      {activeTab === "database" && (
        <div className="space-y-6">
          <h2 className="font-heading text-base font-bold text-ink dark:text-gray-100">
            🗄 {t("admin.db.title")}
          </h2>

          {dbStatus && (
            <p className={`text-sm font-medium ${dbStatus.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
              {dbStatus.text}
            </p>
          )}

          {/* Export */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-[#3e3e42] dark:bg-[#252526]">
            <h3 className="mb-1 text-sm font-semibold text-ink dark:text-gray-200">{t("admin.db.exportBtn")}</h3>
            <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">{t("admin.db.exportDesc")}</p>
            <button
              type="button"
              disabled={dbExporting}
              onClick={() => void handleExportDb()}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
            >
              {dbExporting ? t("app.loading") : `⬇ ${t("admin.db.exportBtn")}`}
            </button>
          </div>

          {/* Import */}
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5 dark:border-red-700/30 dark:bg-red-900/10">
            <h3 className="mb-1 text-sm font-semibold text-red-800 dark:text-red-300">{t("admin.db.importBtn")}</h3>
            <p className="mb-3 text-xs text-red-600 dark:text-red-400">{t("admin.db.importDesc")}</p>
            <label className="flex cursor-pointer items-center gap-3">
              <span className="rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 dark:border-red-700/40 dark:bg-[#252526] dark:text-red-400 dark:hover:bg-[#2d2d30]">
                {dbImporting ? t("app.loading") : `⬆ ${t("admin.db.importBtn")}`}
              </span>
              <input
                ref={importFileRef}
                type="file"
                accept=".db"
                disabled={dbImporting}
                onChange={(e) => void handleImportDb(e)}
                className="sr-only"
                aria-label={t("admin.db.importFileLabel")}
              />
            </label>
          </div>
        </div>
      )}
    </main>
  );
}
