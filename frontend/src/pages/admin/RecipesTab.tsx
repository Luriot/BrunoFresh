import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { buildImageUrl, buildJobStreamUrl, deleteRecipe, fetchRecipes, findDuplicateRecipes, formatRecipeInstructions, rescrapeRecipe } from "../../api/client";
import type { RecipeListItem, RecipeSimilarPair } from "../../types";
import { BookOpen, RefreshCw, Search, Sparkles, Trash2 } from "lucide-react";

type RowStatus = { loading: boolean; msg: string; isError: boolean };

export function RecipesTab() {
  const { t } = useTranslation();
  const [adminRecipes, setAdminRecipes] = useState<RecipeListItem[]>([]);
  const [recipesLoading, setRecipesLoading] = useState(false);
  const [recipeSearch, setRecipeSearch] = useState("");
  const [recipeRowStatus, setRecipeRowStatus] = useState<Record<number, RowStatus>>({});

  const [recipePairs, setRecipePairs] = useState<RecipeSimilarPair[]>([]);
  const [scanLoading, setScanLoading] = useState(false);
  const [showScanPanel, setShowScanPanel] = useState(false);

  function setRowStatus(id: number, patch: Partial<RowStatus>) {
    setRecipeRowStatus((prev) => {
      const existing: RowStatus = prev[id] ?? { loading: false, msg: "", isError: false };
      return { ...prev, [id]: { ...existing, ...patch } };
    });
  }

  useEffect(() => {
    setRecipesLoading(true);
    fetchRecipes({ limit: 1000 })
      .then(setAdminRecipes)
      .catch(() => {})
      .finally(() => setRecipesLoading(false));
  }, []);

  async function handleScanRecipes() {
    setScanLoading(true);
    setShowScanPanel(true);
    try {
      const res = await findDuplicateRecipes();
      setRecipePairs(res.pairs);
    } catch {
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
    } catch {
      // silently fail
    }
  }

  async function handleAdminRescrape(id: number) {
    setRowStatus(id, { loading: true, msg: "", isError: false });
    try {
      const { job_id } = await rescrapeRecipe(id);
      if (job_id == null) {
        setRowStatus(id, { loading: false, msg: t("admin.recipes.updateError"), isError: true });
        return;
      }
      const es = new EventSource(buildJobStreamUrl(job_id));
      es.addEventListener("message", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data as string) as { status: string; error_message?: string };
          if (data.status === "completed" || data.status === "done") {
            es.close();
            setRowStatus(id, { loading: false, msg: t("admin.recipes.updateDone"), isError: false });
          } else if (data.status === "failed") {
            es.close();
            setRowStatus(id, { loading: false, msg: data.error_message ?? t("admin.recipes.updateError"), isError: true });
          }
        } catch { /* ignore */ }
      });
      es.onerror = () => {
        es.close();
        setRowStatus(id, { loading: false, msg: t("admin.recipes.updateError"), isError: true });
      };
    } catch {
      setRowStatus(id, { loading: false, msg: t("admin.recipes.updateError"), isError: true });
    }
  }

  async function handleAdminRescrapeWithAI(id: number) {
    setRowStatus(id, { loading: true, msg: "", isError: false });
    try {
      const { job_id } = await rescrapeRecipe(id);
      if (job_id == null) {
        setRowStatus(id, { loading: false, msg: t("admin.recipes.updateError"), isError: true });
        return;
      }
      // Wait for rescrape SSE to finish
      await new Promise<void>((resolve, reject) => {
        const es = new EventSource(buildJobStreamUrl(job_id));
        es.addEventListener("message", (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data as string) as { status: string; error_message?: string };
            if (data.status === "completed" || data.status === "done") { es.close(); resolve(); }
            else if (data.status === "failed") { es.close(); reject(new Error(data.error_message ?? "")); }
          } catch { /* ignore */ }
        });
        es.onerror = () => { es.close(); reject(new Error("")); };
      });
      // Now run AI formatting
      setRowStatus(id, { loading: true, msg: t("admin.recipes.reformatting"), isError: false });
      await formatRecipeInstructions(id);
      setRowStatus(id, { loading: false, msg: t("admin.recipes.updateDone"), isError: false });
    } catch (err) {
      setRowStatus(id, { loading: false, msg: err instanceof Error && err.message ? err.message : t("admin.recipes.updateError"), isError: true });
    }
  }

  async function handleAdminReformat(id: number) {
    setRowStatus(id, { loading: true, msg: "", isError: false });
    try {
      await formatRecipeInstructions(id);
      setRowStatus(id, { loading: false, msg: t("admin.recipes.reformatDone"), isError: false });
    } catch {
      setRowStatus(id, { loading: false, msg: t("admin.recipes.reformatError"), isError: true });
    }
  }

  async function handleAdminDeleteRecipe(id: number, title: string) {
    if (!confirm(`${t("recipes.confirmDelete") ?? "Delete"} "${title}"?`)) return;
    try {
      await deleteRecipe(id);
      setAdminRecipes((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setRowStatus(id, { loading: false, msg: t("admin.recipes.updateError"), isError: true });
    }
  }

  const filteredAdminRecipes = adminRecipes.filter((r) =>
    r.title.toLowerCase().includes(recipeSearch.toLowerCase()) ||
    r.source_domain.toLowerCase().includes(recipeSearch.toLowerCase()),
  );

  return (
    <>
      <section>
        <h2 className="mb-4 flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
          <BookOpen className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          {t("admin.recipes.title")}
        </h2>

        <input
          type="search"
          value={recipeSearch}
          onChange={(e) => setRecipeSearch(e.target.value)}
          placeholder={t("admin.recipes.searchPlaceholder")}
          className="mb-4 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
        />

        {recipesLoading ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t("app.loading")}</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs text-gray-500 dark:bg-[#252526] dark:text-gray-400">
                  <th className="w-12 px-3 py-2"></th>
                  <th className="px-3 py-2">{t("admin.tabs.recipes")}</th>
                  <th className="hidden px-3 py-2 sm:table-cell">Source</th>
                  <th className="px-3 py-2 text-right">{t("admin.tabs.database")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
                {filteredAdminRecipes.map((recipe) => {
                  const row = recipeRowStatus[recipe.id];
                  const isLoading = row?.loading ?? false;
                  return (
                    <tr key={recipe.id} className="bg-white hover:bg-gray-50 dark:bg-[#1e1e1e] dark:hover:bg-[#252526]">
                      <td className="px-3 py-2">
                        {recipe.image_local_path ? (
                          <img
                            src={buildImageUrl(recipe.image_local_path)}
                            alt=""
                            className="h-10 w-10 rounded-lg object-cover"
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-lg bg-gray-100 dark:bg-[#3e3e42]" />
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <p className="font-medium text-ink dark:text-gray-200 line-clamp-2">{recipe.title}</p>
                        {row?.msg && (
                          <p className={`mt-0.5 text-xs ${row.isError ? "text-red-500" : "text-green-600 dark:text-green-400"}`}>
                            {row.msg}
                          </p>
                        )}
                      </td>
                      <td className="hidden px-3 py-2 text-gray-500 dark:text-gray-400 sm:table-cell">
                        {recipe.source_domain}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            title={t("admin.recipes.update")}
                            disabled={isLoading}
                            onClick={() => void handleAdminRescrape(recipe.id)}
                            className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
                            <span className="hidden sm:inline">{t("admin.recipes.update")}</span>
                          </button>
                          <button
                            type="button"
                            title={t("admin.recipes.reformat")}
                            disabled={isLoading}
                            onClick={() => void handleAdminRescrapeWithAI(recipe.id)}
                            className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                          >
                            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                            <span className="hidden sm:inline">{t("admin.recipes.reformat")}</span>
                          </button>
                          <button
                            type="button"
                            title={t("admin.recipes.delete")}
                            disabled={isLoading}
                            onClick={() => void handleAdminDeleteRecipe(recipe.id, recipe.title)}
                            className="flex items-center gap-1 rounded-lg border border-red-200 px-2 py-1.5 text-xs text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-800/40 dark:text-red-400 dark:hover:bg-red-900/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Duplicate scan */}
      <section className="mt-8 border-t border-gray-200 pt-6 dark:border-[#3e3e42]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
            <Search className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            {t("recipes.findDuplicates")}
          </h2>
          <button
            type="button"
            onClick={() => void handleScanRecipes()}
            disabled={scanLoading}
            className="flex items-center gap-1.5 rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
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
                            src={buildImageUrl(recipe.image)}
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
    </>
  );
}
