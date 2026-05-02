import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Heart, SlidersHorizontal, Search, LayoutGrid, List, Plus, Clock, Link } from "lucide-react";
import { RecipeCard } from "../components/RecipeCard";
import { CartPanel } from "../components/CartPanel";
import { RecipeDetailModal } from "../components/RecipeDetailModal";
import { CustomRecipeModal } from "../components/CustomRecipeModal";
import { buildImageUrl, patchRecipe, searchHelloFresh } from "../api/client";
import { useRecipeFilters } from "../hooks/useRecipeFilters";
import type { CartEntry } from "../hooks/useCart";
import type { HFSearchResult, RecipeListItem } from "../types";

type Props = {
  loading: boolean;
  scrapeState: string | null;
  recipes: RecipeListItem[];
  cart: CartEntry[];
  onScrape: (urls: string[]) => Promise<boolean>;
  onRefreshRecipes: () => Promise<void>;
  onAddToCart: (recipe: RecipeListItem) => void;
  onUpdateServings: (recipeId: number, servings: number) => void;
  onClearCart: () => void;
  onGenerateList: () => Promise<void>;
  onRecipesChanged: (recipes: RecipeListItem[]) => void;
};

type RecipeRowProps = {
  recipe: RecipeListItem;
  onAdd: (recipe: RecipeListItem) => void;
  onClick?: (recipe: RecipeListItem) => void;
  onFavoriteToggled?: (updated: RecipeListItem) => void;
};

function RecipeListRow({ recipe, onAdd, onClick, onFavoriteToggled }: Readonly<RecipeRowProps>) {
  const { t } = useTranslation();

  async function handleFavorite(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const updated = await patchRecipe(recipe.id, { is_favorite: !recipe.is_favorite });
      onFavoriteToggled?.({ ...recipe, is_favorite: updated.is_favorite });
    } catch {
      // silently fail
    }
  }

  return (
    <article
      className="flex cursor-pointer items-center gap-3 rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm transition hover:shadow-md dark:border-[#3e3e42] dark:bg-[#252526]"
      onClick={() => onClick?.(recipe)}
    >
      <div className="h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-green-50 dark:bg-[#1e1e1e]">
        {recipe.image_local_path ? (
          <img className="h-full w-full object-cover" src={buildImageUrl(recipe.image_local_path)} alt="" />
        ) : (
          <div className="flex h-full items-center justify-center text-[9px] text-green-600 dark:text-gray-500">
            {t("recipe.noImage")}
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-heading text-sm font-semibold text-ink dark:text-gray-100">{recipe.title}</p>
        <div className="flex flex-wrap items-center gap-1 mt-0.5">
          {recipe.tags.map((tag) => (
            <span
              key={tag.id}
              className="rounded-full px-1.5 py-0.5 text-[10px] font-medium text-white"
              style={{ backgroundColor: tag.color ?? "#6b7280" }}
            >
              {t(`tags.names.${tag.name}`, { defaultValue: tag.name })}
            </span>
          ))}
        </div>
      </div>
      <button
        type="button"
        aria-label={recipe.is_favorite ? t("recipe.unfavorite") : t("recipe.favorite")}
        className="shrink-0 rounded-full p-1 text-gray-400 transition hover:text-red-500 dark:text-gray-500"
        onClick={handleFavorite}
      >
        {recipe.is_favorite ? (
          <svg className="h-4 w-4 text-red-500" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
          </svg>
        ) : (
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
          </svg>
        )}
      </button>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onAdd(recipe); }}
        className="shrink-0 rounded-xl bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90"
      >
        {t("recipe.addToCart")}
      </button>
    </article>
  );
}

function SpinnerIcon() {
  return (
    <svg className="h-4 w-4 animate-spin text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

function filterButtonClass(tagCount: number, filtersOpen: boolean, selectedCount: number): string {
  if (tagCount === 0) {
    return "cursor-not-allowed border-gray-200 text-gray-400 opacity-50 dark:border-[#3e3e42] dark:text-gray-600";
  }
  if (filtersOpen || selectedCount > 0) {
    return "border-accent bg-accent/10 text-accent dark:bg-accent/20";
  }
  return "border-gray-200 text-gray-600 dark:border-[#3e3e42] dark:text-gray-400";
}

export function DashboardPage({
  loading,
  scrapeState,
  recipes,
  cart,
  onScrape,
  onRefreshRecipes,
  onAddToCart,
  onUpdateServings,
  onClearCart,
  onGenerateList,
  onRecipesChanged,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState(false);
  const [isCustomRecipeModalOpen, setIsCustomRecipeModalOpen] = useState(false);
  const [selectedRecipeToView, setSelectedRecipeToView] = useState<RecipeListItem | null>(null);

  // Infinite scroll
  const [visibleCount, setVisibleCount] = useState(20);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVisibleCount(20);
  }, [recipes]);

  // View mode toggle (tiles / list)
  const [viewMode, setViewMode] = useState<"tiles" | "list">(() => {
    const stored = localStorage.getItem("brunofresh.recipeView");
    return stored === "list" ? "list" : "tiles";
  });

  function toggleViewMode(mode: "tiles" | "list") {
    setViewMode(mode);
    localStorage.setItem("brunofresh.recipeView", mode);
  }

  // Search + filter state (managed by hook)
  const {
    searchQuery,
    setSearchQuery,
    selectedTagIds,
    toggleTagFilter,
    clearTagFilters,
    showFavoritesOnly,
    setShowFavoritesOnly,
    allTags,
  } = useRecipeFilters(onRecipesChanged);

  const [showFilters, setShowFilters] = useState(false);

  // URL input (managed locally — no need to lift to App)
  const [urlInput, setUrlInput] = useState("");

  // HF discovery state
  const [hfQuery, setHfQuery] = useState("");
  const [hfResults, setHfResults] = useState<HFSearchResult[]>([]);
  const [hfLoading, setHfLoading] = useState(false);
  const [hfError, setHfError] = useState<string | null>(null);
  const [importingUrls, setImportingUrls] = useState<Set<string>>(new Set());
  const [importedUrls, setImportedUrls] = useState<Set<string>>(new Set());

  // Import card tab
  const [importTab, setImportTab] = useState<"hf" | "url">("hf");

  async function runHfSearch() {
    if (!hfQuery.trim()) {
      setHfResults([]);
      setHfError(null);
      return;
    }
    setHfLoading(true);
    setHfError(null);
    try {
      const results = await searchHelloFresh(hfQuery.trim());
      setHfResults(results);
    } catch {
      setHfError(t("hfDiscovery.searchError"));
      setHfResults([]);
    } finally {
      setHfLoading(false);
    }
  }

  async function handleHfImport(hfUrl: string) {
    setImportingUrls((prev) => new Set(prev).add(hfUrl));
    try {
      const success = await onScrape([hfUrl]);
      if (success) {
        setImportedUrls((prev) => new Set(prev).add(hfUrl));
        setHfResults((prev) =>
          prev.map((r) => r.hf_url === hfUrl ? { ...r, already_imported: true } : r)
        );
      }
    } finally {
      setImportingUrls((prev) => { const s = new Set(prev); s.delete(hfUrl); return s; });
    }
  }

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((c) => c + 20);
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [recipes]);

  function sortRecipes(list: RecipeListItem[]): RecipeListItem[] {
    return [...list].sort((a, b) => {
      // Favorites first, then alphabetical
      if (a.is_favorite !== b.is_favorite) return a.is_favorite ? -1 : 1;
      return a.title.localeCompare(b.title, undefined, { sensitivity: "base" });
    });
  }

  async function handleMultiScrape() {
    const urls = urlInput.split(/[\n,]/).map((u) => u.trim()).filter(Boolean);
    if (urls.length === 0) return;
    setUrlInput("");
    await onScrape(urls);
  }

  const recipeCount = recipes.length;

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-28 sm:px-6 lg:grid-cols-3 lg:px-8 lg:pb-10">
      <section className="space-y-4 lg:col-span-2">
        {/* Import card — 2 tabs */}
        <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
          {/* Tab bar */}
          <div className="mb-3 flex gap-1 rounded-xl bg-gray-100 p-1 dark:bg-[#1e1e1e]">
            <button
              type="button"
              onClick={() => setImportTab("hf")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5 text-sm font-semibold transition ${
                importTab === "hf"
                  ? "bg-white shadow text-ink dark:bg-[#252526] dark:text-gray-100"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              <Search className="h-3.5 w-3.5" aria-hidden="true" />
              {t("hfDiscovery.tabLabel")}
            </button>
            <button
              type="button"
              onClick={() => setImportTab("url")}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-1.5 text-sm font-semibold transition ${
                importTab === "url"
                  ? "bg-white shadow text-ink dark:bg-[#252526] dark:text-gray-100"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              <Link className="h-3.5 w-3.5" aria-hidden="true" />
              {t("hfDiscovery.tabUrl")}
            </button>
          </div>

          {importTab === "hf" ? (
            <div className="flex flex-col gap-3">
              {/* HF search input */}
              <form
                className="flex gap-2"
                onSubmit={(e) => { e.preventDefault(); void runHfSearch(); }}
              >
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" aria-hidden="true" />
                  <input
                    className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
                    placeholder={t("hfDiscovery.searchPlaceholder")}
                    value={hfQuery}
                    onChange={(e) => {
                      setHfQuery(e.target.value);
                      if (!e.target.value.trim()) { setHfResults([]); setHfError(null); }
                    }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={hfLoading || !hfQuery.trim()}
                  className="shrink-0 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
                >
                  {t("hfDiscovery.search")}
                </button>
              </form>

              {/* Status */}
              {hfLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <SpinnerIcon />
                  {t("hfDiscovery.searching")}
                </div>
              )}
              {hfError && <p className="text-sm text-red-500">{hfError}</p>}
              {!hfLoading && !hfError && hfQuery.trim() && hfResults.length === 0 && (
                <p className="text-sm text-gray-400 dark:text-gray-500">{t("hfDiscovery.noResults")}</p>
              )}

              {/* Results */}
              {hfResults.length > 0 && (
                <div className="flex flex-col gap-2 max-h-[480px] overflow-y-auto pr-1">
                  {hfResults.map((hit) => {
                    const isAlreadyImported = hit.already_imported || importedUrls.has(hit.hf_url);
                    const isImporting = importingUrls.has(hit.hf_url);
                    return (
                      <div
                        key={hit.id}
                        className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                      >
                        {/* Thumbnail */}
                        <div className="h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-green-50 dark:bg-[#252526]">
                          {hit.image_url ? (
                            <img
                              src={hit.image_url}
                              alt=""
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center text-[9px] text-green-600 dark:text-gray-500">
                              {t("recipe.noImage")}
                            </div>
                          )}
                        </div>

                        {/* Content */}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-ink dark:text-gray-100">{hit.name}</p>
                          <div className="mt-0.5 flex flex-wrap items-center gap-1">
                            {hit.total_time_minutes != null && (
                              <span className="flex items-center gap-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                                <Clock className="h-3 w-3" aria-hidden="true" />
                                {hit.total_time_minutes} {t("recipe.minutes")}
                              </span>
                            )}
                            {hit.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-800 dark:bg-green-900/30 dark:text-green-300"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Action */}
                        <div className="flex shrink-0 items-center gap-1.5">
                          {isAlreadyImported ? (
                            <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-400">
                              {t("hfDiscovery.alreadyImported")}
                            </span>
                          ) : (
                            <button
                              type="button"
                              disabled={isImporting}
                              onClick={() => void handleHfImport(hit.hf_url)}
                              className="rounded-xl bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
                            >
                              {isImporting ? t("hfDiscovery.importing") : t("hfDiscovery.import")}
                            </button>
                          )}
                          <a
                            href={hit.hf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-xl border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-400 dark:hover:bg-[#2d2d30]"
                          >
                            {t("recipe.viewOriginal")}
                          </a>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              <p className="text-xs text-gray-500 dark:text-gray-400">{t("app.recipesLoaded", { count: recipeCount })}</p>
              {scrapeState && (
                <div className="flex items-center gap-2 rounded-lg border border-green-100 bg-green-50 p-2 dark:border-accent/30 dark:bg-accent/10">
                  {loading && <SpinnerIcon />}
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{scrapeState}</p>
                </div>
              )}
            </div>
          ) : (
            /* URL directe tab */
            <div className="flex flex-col gap-2">
              <textarea
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
                placeholder={`${t("app.urlPlaceholder")} (${t("app.urlPerLine")})`}
                rows={2}
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  className="flex flex-1 items-center justify-center rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white"
                  onClick={() => void handleMultiScrape()}
                  disabled={loading}
                  type="button"
                >
                  {loading ? t("app.scraping") : t("app.scrape")}
                </button>
                <button
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-gray-300 bg-gray-50 px-4 py-2 text-sm font-medium hover:bg-gray-100 dark:border-[#3e3e42] dark:bg-[#2d2d30] dark:hover:bg-[#3e3e42] dark:text-gray-200"
                  onClick={() => setIsCustomRecipeModalOpen(true)}
                  type="button"
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  {t("app.customRecipe")}
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{t("app.recipesLoaded", { count: recipeCount })}</p>
              {scrapeState && (
                <div className="mt-1 flex items-center gap-2 rounded-lg border border-green-100 bg-green-50 p-2 dark:border-accent/30 dark:bg-accent/10">
                  {loading && <SpinnerIcon />}
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{scrapeState}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Search + filter bar */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" aria-hidden="true" />
            <input
              className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
              placeholder={t("app.searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button
              type="button"
              onClick={() => allTags.length > 0 && setShowFilters((v) => !v)}
              disabled={allTags.length === 0}
              title={allTags.length === 0 ? t("tags.empty") : undefined}
              className={`relative flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm font-semibold transition ${filterButtonClass(allTags.length, showFilters, selectedTagIds.length)}`}
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              {t("app.filtersLabel")}
              {selectedTagIds.length > 0 && (
                <span className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-white">
                  {selectedTagIds.length}
                </span>
              )}
            </button>
          <button
            type="button"
            onClick={() => setShowFavoritesOnly((v) => !v)}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm font-semibold transition ${showFavoritesOnly ? "border-red-300 bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400" : "border-gray-200 text-gray-600 dark:border-[#3e3e42] dark:text-gray-400"}`}
          >
            <Heart className="h-4 w-4" aria-hidden="true" />
            {t("app.favoritesFilter")}
          </button>
          {/* View mode toggle */}
          <div className="flex overflow-hidden rounded-xl border border-gray-200 dark:border-[#3e3e42]">
            <button
              type="button"
              aria-label={t("app.viewTiles")}
              onClick={() => toggleViewMode("tiles")}
              className={`flex items-center justify-center px-2.5 py-2 transition ${viewMode === "tiles" ? "bg-accent text-white" : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2d2d30]"}`}
            >
              <LayoutGrid className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label={t("app.viewList")}
              onClick={() => toggleViewMode("list")}
              className={`flex items-center justify-center border-l border-gray-200 px-2.5 py-2 transition dark:border-[#3e3e42] ${viewMode === "list" ? "bg-accent text-white" : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-[#2d2d30]"}`}
            >
              <List className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Collapsible tag filter panel */}
        {showFilters && allTags.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-3 dark:border-[#3e3e42] dark:bg-[#252526]">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {t("app.filterByTag")}
              </span>
              {selectedTagIds.length > 0 && (
                <button
                  type="button"
                  onClick={() => clearTagFilters()}
                  className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {t("app.clearFilters")}
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {allTags.map((tag) => {
                const active = selectedTagIds.includes(tag.id);
                return (
                  <button
                    key={tag.id}
                    type="button"
                    onClick={() => toggleTagFilter(tag.id)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${active ? "text-white" : "border border-gray-300 text-gray-600 hover:border-gray-400 dark:border-[#3e3e42] dark:text-gray-400"}`}
                    style={active ? { backgroundColor: tag.color ?? "#6b7280" } : undefined}
                  >
                    {t(`tags.names.${tag.name}`, { defaultValue: tag.name })}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {viewMode === "tiles" ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recipes.slice(0, visibleCount).map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                onAdd={onAddToCart}
                onClick={setSelectedRecipeToView}
                onFavoriteToggled={(updated) => {
                  onRecipesChanged(sortRecipes(recipes.map((r) => r.id === updated.id ? updated : r)));
                }}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {recipes.slice(0, visibleCount).map((recipe) => (
              <RecipeListRow
                key={recipe.id}
                recipe={recipe}
                onAdd={onAddToCart}
                onClick={setSelectedRecipeToView}
                onFavoriteToggled={(updated) => {
                  onRecipesChanged(sortRecipes(recipes.map((r) => r.id === updated.id ? updated : r)));
                }}
              />
            ))}
          </div>
        )}

        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} className="flex justify-center py-4">
          {visibleCount < recipes.length && (
            <svg className="h-5 w-5 animate-spin text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-label="Loading more recipes">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
        </div>
      </section>

      <aside className="hidden space-y-4 lg:block">
        <CartPanel
          cart={cart}
          onUpdateServings={onUpdateServings}
          onClearCart={onClearCart}
          onGenerateList={onGenerateList}
        />
      </aside>

      <button
        className="fixed left-4 right-4 z-40 rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white shadow-xl lg:hidden"
        style={{ bottom: "max(1rem, calc(0.5rem + var(--sab, 0px)))" }}
        onClick={() => setIsMobilePanelOpen(true)}
        type="button"
      >
        {t("cart.openMobile", { count: cart.length })}
      </button>

      {isMobilePanelOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/50 cursor-default"
            onClick={() => setIsMobilePanelOpen(false)}
            aria-label={t("app.close")}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setIsMobilePanelOpen(false);
              }
            }}
          />
          <div className="absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-y-auto rounded-t-2xl border border-b-0 border-gray-200 bg-white p-4 dark:border-[#3e3e42] dark:bg-[#252526]">
            <div className="mb-3 flex justify-end">
              <button
                className="rounded-lg border border-gray-200 px-2 py-1 text-sm dark:border-[#3e3e42] dark:text-gray-300"
                onClick={() => setIsMobilePanelOpen(false)}
                type="button"
              >
                {t("cart.closeMobile")}
              </button>
            </div>
            <CartPanel
              cart={cart}
              onUpdateServings={onUpdateServings}
              onClearCart={onClearCart}
              onGenerateList={onGenerateList}
            />
          </div>
        </div>
      )}

      {selectedRecipeToView && (
        <RecipeDetailModal
          recipeId={selectedRecipeToView.id}
          onClose={() => setSelectedRecipeToView(null)}
          onAddToCart={() => {
            onAddToCart(selectedRecipeToView);
            setSelectedRecipeToView(null);
          }}
        />
      )}

      {isCustomRecipeModalOpen && (
        <CustomRecipeModal
          onClose={() => setIsCustomRecipeModalOpen(false)}
          onCreated={(_newRecipe) => {
            setIsCustomRecipeModalOpen(false);
            void onRefreshRecipes();
          }}
        />
      )}
    </main>
  );
}
