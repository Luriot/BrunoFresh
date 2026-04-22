import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { RecipeCard } from "../components/RecipeCard";
import { ShoppingList } from "../components/ShoppingList";
import { CartPanel } from "../components/CartPanel";
import type { CartEntry } from "../hooks/useCart";
import type { RecipeListItem, ShoppingList as ShoppingListType } from "../types";

type Props = {
  url: string;
  setUrl: (value: string) => void;
  loading: boolean;
  scrapeState: string | null;
  recipes: RecipeListItem[];
  cart: CartEntry[];
  list: ShoppingListType | null;
  onScrape: () => Promise<void>;
  onRefreshRecipes: () => Promise<void>;
  onAddToCart: (recipe: RecipeListItem) => void;
  onUpdateServings: (recipeId: number, servings: number) => void;
  onGenerateList: () => Promise<void>;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (name: string) => Promise<void>;
};

export function DashboardPage({
  url,
  setUrl,
  loading,
  scrapeState,
  recipes,
  cart,
  list,
  onScrape,
  onRefreshRecipes,
  onAddToCart,
  onUpdateServings,
  onGenerateList,
  onToggleOwned,
  onAddCustomItem,
}: Props) {
  const { t } = useTranslation();
  const [isMobilePanelOpen, setIsMobilePanelOpen] = useState(false);
  const recipeCount = useMemo(() => recipes.length, [recipes.length]);

  return (
    <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-28 sm:px-6 lg:grid-cols-3 lg:px-8 lg:pb-10">
      <section className="space-y-4 lg:col-span-2">
        <div className="rounded-2xl border border-orange-200 bg-white p-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="w-full rounded-xl border border-orange-200 px-3 py-2 outline-none focus:border-accent"
              placeholder={t("app.urlPlaceholder")}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button
              className="rounded-xl bg-accent px-4 py-2 font-semibold text-white"
              onClick={() => void onScrape()}
              disabled={loading}
              type="button"
            >
              {loading ? t("app.scraping") : t("app.scrape")}
            </button>
            <button
              className="rounded-xl border border-orange-300 px-4 py-2"
              onClick={() => void onRefreshRecipes()}
              type="button"
            >
              {t("app.refresh")}
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500">{t("app.recipesLoaded", { count: recipeCount })}</p>
          {scrapeState && (
            <div className="mt-3 flex items-center gap-2 rounded-lg border border-orange-100 bg-orange-50 p-2">
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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {recipes.map((recipe) => (
            <RecipeCard key={recipe.id} recipe={recipe} onAdd={onAddToCart} />
          ))}
        </div>
      </section>

      <aside className="hidden space-y-4 lg:block">
        <CartPanel cart={cart} onUpdateServings={onUpdateServings} onGenerateList={onGenerateList} />
        <section className="rounded-2xl border border-orange-200 bg-white p-4">
          <h2 className="mb-2 font-heading text-xl font-semibold">{t("shopping.title")}</h2>
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
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setIsMobilePanelOpen(false)}
            role="button"
            tabIndex={0}
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
                className="rounded-lg border border-orange-200 px-2 py-1 text-sm"
                onClick={() => setIsMobilePanelOpen(false)}
                type="button"
              >
                {t("cart.closeMobile")}
              </button>
            </div>
            <CartPanel cart={cart} onUpdateServings={onUpdateServings} onGenerateList={onGenerateList} />
            <section className="mt-4 rounded-2xl border border-orange-200 bg-white p-4">
              <h2 className="mb-2 font-heading text-xl font-semibold">{t("shopping.title")}</h2>
              <ShoppingList data={list} onAddCustomItem={onAddCustomItem} onToggleOwned={onToggleOwned} />
            </section>
          </div>
        </div>
      )}
    </main>
  );
}
