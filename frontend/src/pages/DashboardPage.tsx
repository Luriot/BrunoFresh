import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { RecipeCard } from "../components/RecipeCard";
import { ShoppingList } from "../components/ShoppingList";
import { CartPanel } from "../components/CartPanel";
import { RecipeDetailModal } from "../components/RecipeDetailModal";
import { CustomRecipeModal } from "../components/CustomRecipeModal";
import type { CartEntry } from "../hooks/useCart";
import type { RecipeListItem, ShoppingList as ShoppingListType, StatsOut, Tag } from "../types";
import { fetchStats, fetchTags, fetchRecipes } from "../api/client";

type Props = {
  loading: boolean;
  scrapeState: string | null;
  recipes: RecipeListItem[];
  cart: CartEntry[];
  list: ShoppingListType | null;
  onScrape: (urls: string[]) => Promise<void>;
  onRefreshRecipes: () => Promise<void>;
  onAddToCart: (recipe: RecipeListItem) => void;
  onUpdateServings: (recipeId: number, servings: number) => void;
  onClearCart: () => void;
  onGenerateList: () => Promise<void>;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (payload: { name: string; quantity: number; unit: string }) => Promise<void>;
  onRecipesChanged: (recipes: RecipeListItem[]) => void;
};

export function DashboardPage({
  loading,
  scrapeState,
  recipes,
  cart,
  list,
  onScrape,
  onRefreshRecipes,
  onAddToCart,
  onUpdateServings,
  onClearCart,
  onGenerateList,
  onToggleOwned,
  onAddCustomItem,
  onRecipesChanged,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState(false);
  const [isCustomRecipeModalOpen, setIsCustomRecipeModalOpen] = useState(false);
  const [selectedRecipeToView, setSelectedRecipeToView] = useState<RecipeListItem | null>(null);

  // Search + filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [stats, setStats] = useState<StatsOut | null>(null);

  // URL input (managed locally — no need to lift to App)
  const [urlInput, setUrlInput] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchTags().then(setAllTags).catch(() => {});
    fetchStats().then(setStats).catch(() => {});
  }, []);

  // Debounced server-side filter — runs only after user interacts (skips first render)
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void fetchRecipes({
        q: searchQuery || undefined,
        is_favorite: showFavoritesOnly || undefined,
        tags: selectedTagIds.length > 0 ? selectedTagIds.join(",") : undefined,
      }).then(onRecipesChanged).catch(() => {});
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [searchQuery, selectedTagIds, showFavoritesOnly, onRecipesChanged]);

  function toggleTagFilter(tagId: number) {
    setSelectedTagIds((prev) => prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]);
  }

  async function handleMultiScrape() {
    const urls = urlInput.split(/\n|,/).map((u) => u.trim()).filter(Boolean);
    if (urls.length === 0) return;
    setUrlInput("");
    await onScrape(urls);
  }

  const recipeCount = recipes.length;

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-28 sm:px-6 lg:grid-cols-3 lg:px-8 lg:pb-10">
      <section className="space-y-4 lg:col-span-2">
        {/* Stats mini-widget */}
        {stats && (
          <div className="flex flex-wrap gap-3">
            <div className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-center shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
              <p className="text-2xl font-bold text-accent">{stats.total_recipes}</p>
              <p className="text-xs text-gray-500">{t("stats.totalRecipes")}</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-center shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
              <p className="text-2xl font-bold text-accent">{stats.total_lists}</p>
              <p className="text-xs text-gray-500">{t("stats.totalLists")}</p>
            </div>
            {stats.recipes_by_source[0] && (
              <div className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-center shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
                <p className="text-sm font-bold text-ink dark:text-gray-100">{stats.recipes_by_source[0].source_domain}</p>
                <p className="text-xs text-gray-500">{t("stats.topSource")} ({stats.recipes_by_source[0].count})</p>
              </div>
            )}
          </div>
        )}

        {/* Scrape input card */}
        <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
          <div className="flex flex-col gap-2">
            <textarea
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
              placeholder={`${t("app.urlPlaceholder")} (${t("app.urlPerLine")})`}
              rows={2}
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button
                className="shrink-0 whitespace-nowrap rounded-xl bg-accent px-4 py-2 font-semibold text-white"
                onClick={() => void handleMultiScrape()}
                disabled={loading}
                type="button"
              >
                {loading ? t("app.scraping") : t("app.scrape")}
              </button>
              <button
                className="shrink-0 whitespace-nowrap rounded-xl border border-gray-300 px-4 py-2 dark:border-[#3e3e42] dark:text-gray-200"
                onClick={() => void onRefreshRecipes()}
                type="button"
              >
                {t("app.refresh")}
              </button>
              <button
                className="shrink-0 whitespace-nowrap rounded-xl border border-gray-300 bg-gray-50 px-4 py-2 font-medium hover:bg-gray-100 dark:border-[#3e3e42] dark:bg-[#2d2d30] dark:hover:bg-[#3e3e42] dark:text-gray-200"
                onClick={() => setIsCustomRecipeModalOpen(true)}
                type="button"
              >
                {t("app.customRecipe")}
              </button>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{t("app.recipesLoaded", { count: recipeCount })}</p>
          {scrapeState && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-green-100 bg-green-50 p-2 dark:border-accent/30 dark:bg-accent/10">
              {loading && (
                <svg
                  className="h-4 w-4 animate-spin text-accent"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              )}
              <p className="text-sm font-medium text-gray-700">{scrapeState}</p>
            </div>
          )}
        </div>

        {/* Search + filter bar */}
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="min-w-0 flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
            placeholder={`🔍 ${t("app.searchPlaceholder")}`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button
            type="button"
            onClick={() => setShowFavoritesOnly((v) => !v)}
            className={`rounded-xl border px-3 py-2 text-sm font-semibold transition ${showFavoritesOnly ? "border-red-300 bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400" : "border-gray-200 text-gray-600 dark:border-[#3e3e42] dark:text-gray-400"}`}
          >
            ♥ {t("app.favoritesFilter")}
          </button>
        </div>

        {/* Tag filter chips */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {allTags.map((tag) => {
              const active = selectedTagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => toggleTagFilter(tag.id)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${active ? "text-white" : "border border-gray-300 text-gray-600 dark:border-[#3e3e42] dark:text-gray-400"}`}
                  style={active ? { backgroundColor: tag.color ?? "#6b7280" } : undefined}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {recipes.map((recipe) => (
            <RecipeCard
               key={recipe.id}
               recipe={recipe}
               onAdd={onAddToCart}
               onClick={setSelectedRecipeToView}
               onFavoriteToggled={(updated) => {
                 onRecipesChanged(recipes.map((r) => r.id === updated.id ? updated : r));
               }}
            />
          ))}
        </div>
      </section>

      <aside className="hidden space-y-4 lg:block">
        <CartPanel
          cart={cart}
          onUpdateServings={onUpdateServings}
          onClearCart={onClearCart}
          onGenerateList={onGenerateList}
        />
        <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]">
          <h2 className="mb-2 font-heading text-xl font-semibold text-ink dark:text-white">{t("shopping.title")}</h2>
          <ShoppingList data={list} onAddCustomItem={onAddCustomItem} onToggleOwned={onToggleOwned} />
        </section>
      </aside>

      <button
        className="fixed bottom-4 left-4 right-4 z-40 rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white shadow-xl lg:hidden"
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
          <div className="absolute bottom-0 left-0 right-0 max-h-[85vh] overflow-y-auto rounded-t-2xl bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-heading text-xl font-semibold">{t("cart.title")}</h2>
              <button
                className="rounded-lg border border-gray-200 px-2 py-1 text-sm"
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
            <section className="mt-4 rounded-2xl border border-gray-200 bg-white p-4">
              <h2 className="mb-2 font-heading text-xl font-semibold">{t("shopping.title")}</h2>
              <ShoppingList data={list} onAddCustomItem={onAddCustomItem} onToggleOwned={onToggleOwned} />
            </section>
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
