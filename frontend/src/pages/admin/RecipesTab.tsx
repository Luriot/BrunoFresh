import { type ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { buildJobStreamUrl, convertImagesToWebp, convertSingleImageToWebp, deleteRecipe, fetchRecipes, findDuplicateRecipes, formatRecipeInstructions, rescrapeRecipe, retryAllMissingImages, retryRecipeImage, uploadRecipeImage } from "../../api/client";
import type { RecipeListItem, RecipeSimilarPair } from "../../types";
import { AlertTriangle, BookOpen, Check, CheckCircle, ChevronDown, Image, RefreshCw, Search, Sparkles, Trash2, Upload, Wand2, XCircle } from "lucide-react";

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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const [showImagesPanel, setShowImagesPanel] = useState(false);
  const [imageRowStatus, setImageRowStatus] = useState<Record<number, RowStatus>>({});
  const [bulkRetryMsg, setBulkRetryMsg] = useState<string | null>(null);
  const [bulkRetryLoading, setBulkRetryLoading] = useState(false);
  const [convertWebpMsg, setConvertWebpMsg] = useState<string | null>(null);
  const [convertWebpLoading, setConvertWebpLoading] = useState(false);
  const uploadRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const [showFetchPanel, setShowFetchPanel] = useState(false);
  const [imageSearch, setImageSearch] = useState("");
  const [imgConvertStatus, setImgConvertStatus] = useState<Record<number, RowStatus>>({});

  function setRowStatus(id: number, patch: Partial<RowStatus>) {
    setRecipeRowStatus((prev) => {
      const existing: RowStatus = prev[id] ?? { loading: false, msg: "", isError: false };
      return { ...prev, [id]: { ...existing, ...patch } };
    });
  }

  function setImgStatus(id: number, patch: Partial<RowStatus>) {
    setImageRowStatus((prev) => {
      const existing: RowStatus = prev[id] ?? { loading: false, msg: "", isError: false };
      return { ...prev, [id]: { ...existing, ...patch } };
    });
  }

  async function handleRetryImage(id: number) {
    setImgStatus(id, { loading: true, msg: "", isError: false });
    try {
      const res = await retryRecipeImage(id);
      if (res.success && res.image_local_path) {
        setAdminRecipes((prev) =>
          prev.map((r) => (r.id === id ? { ...r, image_local_path: res.image_local_path } : r)),
        );
        setImgStatus(id, { loading: false, msg: "Image téléchargée", isError: false });
      } else {
        setImgStatus(id, { loading: false, msg: res.error ?? "Échec du téléchargement", isError: true });
      }
    } catch {
      setImgStatus(id, { loading: false, msg: "Erreur", isError: true });
    }
  }

  async function handleUploadImage(id: number, file: File) {
    setImgStatus(id, { loading: true, msg: "", isError: false });
    try {
      const updated = await uploadRecipeImage(id, file);
      setAdminRecipes((prev) =>
        prev.map((r) => (r.id === id ? { ...r, image_local_path: updated.image_local_path } : r)),
      );
      setImgStatus(id, { loading: false, msg: "Image mise à jour", isError: false });
    } catch {
      setImgStatus(id, { loading: false, msg: "Erreur lors de l'upload", isError: true });
    }
  }

  async function handleBulkRetryImages() {
    setBulkRetryLoading(true);
    setBulkRetryMsg(null);
    try {
      const res = await retryAllMissingImages();
      setBulkRetryMsg(`${res.success} / ${res.retried} téléchargées`);
      if (res.success > 0) {
        // Reload recipe list to get updated image_local_path values
        const updated = await fetchRecipes({ limit: 1000 });
        setAdminRecipes(updated);
      }
    } catch {
      setBulkRetryMsg("Erreur lors du retry");
    } finally {
      setBulkRetryLoading(false);
    }
  }

  async function handleConvertToWebp() {
    setConvertWebpLoading(true);
    setConvertWebpMsg(null);
    try {
      const res = await convertImagesToWebp();
      setConvertWebpMsg(t("admin.images.convertResult", { converted: res.converted, skipped: res.skipped, failed: res.failed }));
      if (res.converted > 0) {
        const updated = await fetchRecipes({ limit: 1000 });
        setAdminRecipes(updated);
      }
    } catch {
      setConvertWebpMsg(t("admin.images.convertError"));
    } finally {
      setConvertWebpLoading(false);
    }
  }

  async function handleConvertSingleImage(id: number) {
    setImgConvertStatus((prev) => ({ ...prev, [id]: { loading: true, msg: "", isError: false } }));
    try {
      const res = await convertSingleImageToWebp(id);
      if (res.converted === 1 && res.image_local_path) {
        setAdminRecipes((prev) => prev.map((r) => r.id === id ? { ...r, image_local_path: res.image_local_path! } : r));
        setImgConvertStatus((prev) => ({ ...prev, [id]: { loading: false, msg: "→ WebP", isError: false } }));
      } else if (res.skipped === 1) {
        setImgConvertStatus((prev) => ({ ...prev, [id]: { loading: false, msg: "", isError: false } }));
      } else {
        setImgConvertStatus((prev) => ({ ...prev, [id]: { loading: false, msg: t("admin.images.convertError"), isError: true } }));
      }
    } catch {
      setImgConvertStatus((prev) => ({ ...prev, [id]: { loading: false, msg: t("admin.images.convertError"), isError: true } }));
    }
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
      const es = new EventSource(buildJobStreamUrl(job_id), { withCredentials: true });
      es.addEventListener("status", (e: MessageEvent) => {
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
        const es = new EventSource(buildJobStreamUrl(job_id), { withCredentials: true });
        es.addEventListener("status", (e: MessageEvent) => {
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

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    const allSelected =
      filteredAdminRecipes.length > 0 &&
      filteredAdminRecipes.every((r) => selectedIds.has(r.id));
    setSelectedIds(allSelected ? new Set() : new Set(filteredAdminRecipes.map((r) => r.id)));
  }

  function handleBulkFastFetch() {
    const ids = [...selectedIds];
    setSelectedIds(new Set());
    ids.forEach((id) => void handleAdminRescrape(id));
  }

  async function handleBulkFullUpdate() {
    const ids = [...selectedIds];
    setSelectedIds(new Set());
    for (const id of ids) {
      await handleAdminRescrapeWithAI(id);
    }
  }

  return (
    <>
      <section>
        <button
          type="button"
          onClick={() => setShowFetchPanel((v) => !v)}
          className="mb-4 flex w-full items-center justify-between rounded-xl px-1 py-1 text-left transition hover:bg-gray-50 dark:hover:bg-[#252526]"
        >
          <span className="flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
            <BookOpen className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            {t("admin.recipes.title")}
          </span>
          <ChevronDown className={`h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200 ${showFetchPanel ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>

        {showFetchPanel && (
          <div className={selectedIds.size > 0 ? "pb-32 sm:pb-0" : ""}>
            <input
              type="search"
              value={recipeSearch}
              onChange={(e) => setRecipeSearch(e.target.value)}
              placeholder={t("admin.recipes.searchPlaceholder")}
              className="mb-4 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            />

        {selectedIds.size > 0 && (
          <div className="fixed bottom-0 inset-x-0 z-40 flex flex-col gap-2 border-t border-gray-200 bg-white px-4 pb-8 pt-3 shadow-2xl dark:border-[#3e3e42] dark:bg-[#252526] sm:static sm:inset-auto sm:z-auto sm:mb-3 sm:flex-row sm:items-center sm:rounded-xl sm:border sm:border-accent/30 sm:bg-accent/5 sm:px-3 sm:py-2 sm:shadow-none sm:dark:border-accent/20 sm:dark:bg-accent/10">
            <span className="text-sm font-semibold text-accent sm:mr-auto">
              {t("admin.recipes.selectedCount", { count: selectedIds.size })}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleBulkFastFetch}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-gray-200 px-3 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30] sm:flex-none sm:py-1.5"
              >
                <RefreshCw className="h-4 w-4 shrink-0" aria-hidden="true" />
                {t("admin.recipes.update")}
              </button>
              <button
                type="button"
                onClick={() => void handleBulkFullUpdate()}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-gray-200 px-3 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30] sm:flex-none sm:py-1.5"
              >
                <Sparkles className="h-4 w-4 shrink-0" aria-hidden="true" />
                {t("admin.recipes.reformat")}
              </button>
              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                aria-label={t("app.close")}
                className="rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-500 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-400 dark:hover:bg-[#2d2d30] sm:py-1.5"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {recipesLoading ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t("app.loading")}</p>
        ) : (
          <div className="max-h-[520px] overflow-y-auto overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10">
                <tr className="bg-gray-50 text-left text-xs text-gray-500 dark:bg-[#252526] dark:text-gray-400">
                  <th className="w-14 px-2 py-2">
                    <label className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-lg transition hover:bg-gray-200 dark:hover:bg-[#3e3e42]" aria-label={t("admin.recipes.selectAll")}>
                      <input
                        type="checkbox"
                        ref={(el) => {
                          if (el) el.indeterminate = selectedIds.size > 0 && !filteredAdminRecipes.every((r) => selectedIds.has(r.id));
                        }}
                        checked={filteredAdminRecipes.length > 0 && filteredAdminRecipes.every((r) => selectedIds.has(r.id))}
                        onChange={toggleAll}
                        className="h-5 w-5 rounded border-gray-300 accent-accent"
                      />
                    </label>
                  </th>
                  <th className="px-3 py-2">{t("admin.recipes.recipes")}</th>
                  <th className="hidden px-3 py-2 sm:table-cell">{t("admin.recipes.sources")}</th>
                  <th className="px-3 py-2 text-center">{t("admin.recipes.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
                {filteredAdminRecipes.map((recipe) => {
                  const row = recipeRowStatus[recipe.id];
                  const isLoading = row?.loading ?? false;
                  return (
                    <tr key={recipe.id} className={`hover:bg-gray-50 dark:hover:bg-[#252526] ${selectedIds.has(recipe.id) ? "bg-accent/5 dark:bg-accent/10" : "bg-white dark:bg-[#1e1e1e]"}`}>
                      <td
                        className="cursor-pointer select-none px-2 py-2"
                        onClick={() => toggleSelect(recipe.id)}
                      >
                        <div className="relative h-10 w-10">
                          {recipe.image_url ? (
                            <img
                              src={recipe.image_url}
                              alt=""
                              className="h-full w-full rounded-lg object-cover"
                            />
                          ) : (
                            <div className="h-full w-full rounded-lg bg-gray-100 dark:bg-[#3e3e42]" />
                          )}
                          <div
                            className={`absolute inset-0 flex items-center justify-center rounded-lg transition-opacity ${
                              selectedIds.has(recipe.id)
                                ? "bg-accent/70 opacity-100"
                                : selectedIds.size > 0
                                ? "bg-black/20 opacity-100 dark:bg-black/40"
                                : "opacity-0"
                            }`}
                          >
                            {selectedIds.has(recipe.id) && (
                              <Check className="h-5 w-5 text-white" strokeWidth={3} aria-hidden="true" />
                            )}
                          </div>
                        </div>
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
          </div>
        )}
      </section>

      {/* Images section */}
      <section className="mt-8 border-t border-gray-200 pt-6 dark:border-[#3e3e42]">
        <button
          type="button"
          onClick={() => setShowImagesPanel((v) => !v)}
          className="mb-4 flex w-full items-center justify-between rounded-xl px-1 py-1 text-left transition hover:bg-gray-50 dark:hover:bg-[#252526]"
        >
          <span className="flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
            <Image className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            {t("admin.images.title")}
          </span>
          <ChevronDown className={`h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200 ${showImagesPanel ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>

        {showImagesPanel && (
          <div>
            <input
              type="search"
              value={imageSearch}
              onChange={(e) => setImageSearch(e.target.value)}
              placeholder={t("admin.images.searchPlaceholder")}
              className="mb-4 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
            />
            {/* Bulk action buttons */}
            {(() => {
              const canRetry = adminRecipes.some((r) => !r.image_local_path && r.image_original_url);
              const canConvert = adminRecipes.some((r) => r.image_local_path && !r.image_local_path.endsWith(".webp"));
              return (
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    disabled={bulkRetryLoading || !canRetry}
                    onClick={() => void handleBulkRetryImages()}
                    className="flex items-center gap-1.5 rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  >
                    <RefreshCw className={`h-4 w-4 ${bulkRetryLoading ? "animate-spin" : ""}`} aria-hidden="true" />
                    {t("admin.images.retryAll")}
                  </button>
                  {bulkRetryMsg && (
                    <span className="text-sm text-gray-600 dark:text-gray-400">{bulkRetryMsg}</span>
                  )}
                  <button
                    type="button"
                    disabled={convertWebpLoading || !canConvert}
                    onClick={() => void handleConvertToWebp()}
                    className="flex items-center gap-1.5 rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  >
                    <Wand2 className={`h-4 w-4 ${convertWebpLoading ? "animate-spin" : ""}`} aria-hidden="true" />
                    {t("admin.images.convertToWebp")}
                  </button>
                  {convertWebpMsg && (
                    <span className="text-sm text-gray-600 dark:text-gray-400">{convertWebpMsg}</span>
                  )}
                </div>
              );
            })()}

            <div className="max-h-[520px] overflow-y-auto overflow-x-auto rounded-2xl border border-gray-200 dark:border-[#3e3e42]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10">
                  <tr className="bg-gray-50 text-left text-xs text-gray-500 dark:bg-[#252526] dark:text-gray-400">
                    <th className="w-12 px-2 py-2" />
                    <th className="px-3 py-2">{t("admin.recipes.recipes")}</th>
                    <th className="px-3 py-2 text-right">{t("admin.recipes.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-[#3e3e42]">
                  {adminRecipes
                    .filter((r) => !imageSearch || r.title.toLowerCase().includes(imageSearch.toLowerCase()))
                    .map((recipe) => {
                    const hasLocal = !!recipe.image_local_path;
                    const hasUrl = !!recipe.image_original_url;
                    const isWebp = hasLocal && recipe.image_local_path!.endsWith(".webp");
                    const row = imageRowStatus[recipe.id];
                    const convertRow = imgConvertStatus[recipe.id];
                    const isLoading = row?.loading ?? false;
                    const isConverting = convertRow?.loading ?? false;

                    let statusIcon: ReactNode;
                    let statusColor: string;
                    let statusText: string;
                    if (hasLocal) {
                      statusIcon = <CheckCircle className="h-3.5 w-3.5 text-green-500" aria-hidden="true" />;
                      statusColor = "text-green-600 dark:text-green-400";
                      statusText = t("admin.images.statusOk");
                    } else if (hasUrl) {
                      statusIcon = <AlertTriangle className="h-3.5 w-3.5 text-amber-500" aria-hidden="true" />;
                      statusColor = "text-amber-600 dark:text-amber-400";
                      statusText = t("admin.images.statusMissing");
                    } else {
                      statusIcon = <XCircle className="h-3.5 w-3.5 text-red-500" aria-hidden="true" />;
                      statusColor = "text-red-600 dark:text-red-400";
                      statusText = t("admin.images.statusNoUrl");
                    }

                    return (
                      <tr
                        key={recipe.id}
                        className="bg-white hover:bg-gray-50 dark:bg-[#1e1e1e] dark:hover:bg-[#252526]"
                      >
                        <td className="px-2 py-2">
                          {recipe.image_url ? (
                            <img
                              src={recipe.image_url}
                              alt=""
                              className="h-10 w-10 rounded-lg object-cover"
                            />
                          ) : (
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-[#3e3e42]">
                              {statusIcon}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <p className="font-medium text-ink dark:text-gray-200 line-clamp-1">{recipe.title}</p>
                          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                            <span className={`flex items-center gap-1 text-xs ${statusColor}`}>
                              {statusIcon}{statusText}
                            </span>
                            {hasLocal && (
                              <span className={`flex items-center gap-1 text-xs ${
                                isWebp ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"
                              }`}>
                                {isWebp
                                  ? <><CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />WebP</>                                  : <><AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />Non-WebP</>
                                }
                              </span>
                            )}
                          </div>
                          {row?.msg && (
                            <p className={`mt-0.5 text-xs ${row.isError ? "text-red-500" : "text-green-600 dark:text-green-400"}`}>
                              {row.msg}
                            </p>
                          )}
                          {convertRow?.msg && (
                            <p className={`mt-0.5 text-xs ${convertRow.isError ? "text-red-500" : "text-green-600 dark:text-green-400"}`}>
                              {convertRow.msg}
                            </p>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-end gap-1.5">
                            {hasUrl && !hasLocal && (
                              <button
                                type="button"
                                title={t("admin.images.retry")}
                                disabled={isLoading}
                                onClick={() => void handleRetryImage(recipe.id)}
                                className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                              >
                                <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
                                <span className="hidden sm:inline">{t("admin.images.retry")}</span>
                              </button>
                            )}
                            <button
                              type="button"
                              title={t("admin.images.upload")}
                              disabled={isLoading}
                              onClick={() => uploadRefs.current[recipe.id]?.click()}
                              className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                            >
                              <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                              <span className="hidden sm:inline">{t("admin.images.upload")}</span>
                            </button>
                            <input
                              ref={(el) => { uploadRefs.current[recipe.id] = el; }}
                              type="file"
                              accept="image/jpeg,image/png,image/webp"
                              className="sr-only"
                              onChange={(e) => {
                                const f = e.target.files?.[0];
                                if (f) void handleUploadImage(recipe.id, f);
                                e.target.value = "";
                              }}
                            />
                            {hasLocal && (
                              <button
                                type="button"
                                title={t("admin.images.convertToWebp")}
                                disabled={isWebp || isConverting}
                                onClick={() => void handleConvertSingleImage(recipe.id)}
                                className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs text-gray-700 transition hover:bg-gray-100 disabled:opacity-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                              >
                                <Wand2 className={`h-3.5 w-3.5 ${isConverting ? "animate-spin" : ""}`} aria-hidden="true" />
                                <span className="hidden sm:inline">WebP</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
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
                            src={recipe.image}
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
