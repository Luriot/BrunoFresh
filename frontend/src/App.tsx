import { useEffect, useMemo, useState } from "react";
import {
  fetchRecipes,
  generateCart,
  loginWithPasscode,
  logout,
  setUnauthorizedHandler,
  verifySession,
} from "./api/client";
import { Login } from "./components/Login";
import { RecipeCard } from "./components/RecipeCard";
import { ShoppingList } from "./components/ShoppingList";
import { useCart } from "./hooks/useCart";
import { useScrape } from "./hooks/useScrape";
import type { CartResponse, RecipeListItem } from "./types";
import { useTranslation } from "react-i18next";

function App() {
  const { t, i18n } = useTranslation();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const { cart, addToCart, updateServings, toCartInput } = useCart();
  const { loading, scrapeState, startScrape } = useScrape();
  const [list, setList] = useState<CartResponse | null>(null);
  const [url, setUrl] = useState("");

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setIsAuthenticated(false);
      setRecipes([]);
      setList(null);
      setAuthError("Session expired. Sign in again.");
    });

    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setRecipes([]);
      setList(null);
      return;
    }
    void loadRecipes();
  }, [isAuthenticated]);

  useEffect(() => {
    let canceled = false;

    async function bootstrapSession() {
      try {
        const authenticated = await verifySession();
        if (!canceled) {
          setIsAuthenticated(authenticated);
        }
      } catch {
        if (!canceled) {
          setIsAuthenticated(false);
        }
      }
    }

    void bootstrapSession();

    return () => {
      canceled = true;
    };
  }, []);

  async function onLogin(passcode: string) {
    try {
      await loginWithPasscode(passcode);
      setIsAuthenticated(true);
      setAuthError(null);
      await loadRecipes();
    } catch {
      setAuthError("Invalid passcode.");
    }
  }

  async function onLogout() {
    try {
      await logout();
    } catch {
      // Treat client-side logout as complete even if the request fails.
    }
    setIsAuthenticated(false);
    setAuthError(null);
    setRecipes([]);
    setList(null);
    setUrl("");
  }

  async function loadRecipes() {
    try {
      const data = await fetchRecipes();
      setRecipes(data);
    } catch {
      setRecipes([]);
    }
  }

  async function onScrape() {
    if (!isAuthenticated) {
      return;
    }

    const started = await startScrape(url, loadRecipes);
    if (started) {
      setUrl("");
    }
  }

  async function onGenerateList() {
    const data = await generateCart(toCartInput());
    setList(data);
  }

  const recipeCount = useMemo(() => recipes.length, [recipes.length]);

  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <p className="text-sm text-gray-600">Checking session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLogin={onLogin} error={authError} />;
  }

  return (
    <div className="min-h-screen text-ink">
      <header className="mx-auto max-w-7xl px-4 pb-4 pt-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="font-heading text-4xl font-bold">{t("app.title")}</h1>
            <p className="mt-2 text-sm text-gray-600">{t("app.subtitle")}</p>
          </div>
          <div className="flex rounded-xl border border-orange-200 bg-white p-1">
            <button className="rounded-lg px-3 py-1 text-sm text-gray-700" onClick={onLogout}>
              Logout
            </button>
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "en" ? "bg-accent text-white" : "text-gray-700"
              }`}
              onClick={() => void i18n.changeLanguage("en")}
            >
              {t("lang.switchToEn")}
            </button>
            <button
              className={`rounded-lg px-3 py-1 text-sm ${
                i18n.language === "fr" ? "bg-accent text-white" : "text-gray-700"
              }`}
              onClick={() => void i18n.changeLanguage("fr")}
            >
              {t("lang.switchToFr")}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-10 sm:px-6 lg:grid-cols-3 lg:px-8">
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
                onClick={onScrape}
                disabled={loading}
              >
                {loading ? t("app.scraping") : t("app.scrape")}
              </button>
              <button className="rounded-xl border border-orange-300 px-4 py-2" onClick={loadRecipes}>
                {t("app.refresh")}
              </button>
            </div>
            <p className="mt-2 text-xs text-gray-500">{t("app.recipesLoaded", { count: recipeCount })}</p>
            {scrapeState && (
              <div className="mt-3 flex items-center gap-2 rounded-lg bg-orange-50 p-2 border border-orange-100">
                {loading && (
                  <svg className="h-4 w-4 animate-spin text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                <p className="text-sm text-gray-700 font-medium">{scrapeState}</p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} onAdd={addToCart} />
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-orange-200 bg-white p-4">
            <h2 className="font-heading text-xl font-semibold">{t("cart.title")}</h2>
            <div className="mt-3 space-y-3">
              {cart.length === 0 && <p className="text-sm text-gray-600">{t("cart.empty")}</p>}
              {cart.map((entry) => (
                <div key={entry.recipe.id} className="rounded-xl bg-orange-50 p-3">
                  <p className="text-sm font-semibold">{entry.recipe.title}</p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-gray-700">
                    {t("cart.servings")}
                    <input
                      className="w-20 rounded-lg border border-orange-200 px-2 py-1"
                      type="number"
                      min={1}
                      value={entry.target_servings}
                      onChange={(e) => updateServings(entry.recipe.id, Number(e.target.value))}
                    />
                  </label>
                </div>
              ))}
            </div>
            <button
              className="mt-4 w-full rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white"
              onClick={onGenerateList}
              disabled={cart.length === 0}
            >
              {t("cart.generate")}
            </button>
          </section>

          <section className="rounded-2xl border border-orange-200 bg-white p-4">
            <h2 className="mb-2 font-heading text-xl font-semibold">{t("shopping.title")}</h2>
            <ShoppingList data={list} />
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
