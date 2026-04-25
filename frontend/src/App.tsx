import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import {
  addShoppingListCustomItem,
  createShoppingList,
  deleteShoppingList,
  deleteShoppingListItem,
  fetchRecipes,
  fetchShoppingList,
  fetchShoppingLists,
  loginWithPasscode,
  logout,
  patchShoppingList,
  patchShoppingListItem,
  setUnauthorizedHandler,
  verifySession,
} from "./api/client";
import { Login } from "./components/Login";
import { Navbar } from "./components/Navbar";
import { useCart } from "./hooks/useCart";
import { useScrape } from "./hooks/useScrape";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { ShoppingListViewPage } from "./pages/ShoppingListViewPage";
import { PantryPage } from "./pages/PantryPage";
import { MealPlannerPage } from "./pages/MealPlannerPage";
import { IngredientsAdminPage } from "./pages/IngredientsAdminPage";
import type { RecipeListItem, ShoppingList as ShoppingListType, ShoppingListSummary } from "./types";
import { useTranslation } from "react-i18next";

function getIsoWeekNumber(date: Date): number {
  const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNumber = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - dayNumber);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  return Math.ceil(((utcDate.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

function App() {
  const { t } = useTranslation();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isDark, setIsDark] = useState(() => {
    const stored = localStorage.getItem("brunofresh.theme");
    if (stored) return stored === "dark";
    return globalThis.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("brunofresh.theme", isDark ? "dark" : "light");
  }, [isDark]);

  const toggleDark = useCallback(() => setIsDark((d) => !d), []);
  const [authError, setAuthError] = useState<string | null>(null);
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const { cart, addToCart, updateServings, clearCart, toCartInput } = useCart();
  const { loading, scrapeState, startScrape } = useScrape();
  const [list, setList] = useState<ShoppingListType | null>(null);
  const [listHistory, setListHistory] = useState<ShoppingListSummary[]>([]);

  const loadRecipes = useCallback(async () => {
    try {
      const data = await fetchRecipes();
      setRecipes(data);
    } catch {
      setRecipes([]);
    }
  }, []);

  const loadShoppingListHistory = useCallback(async () => {
    try {
      const data = await fetchShoppingLists();
      setListHistory(data);
    } catch {
      setListHistory([]);
    }
  }, []);

  const openShoppingList = useCallback(async (listId: number) => {
    try {
      const data = await fetchShoppingList(listId);
      setList(data);
    } catch {
      setList(null);
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setIsAuthenticated(false);
      setRecipes([]);
      setList(null);
      setListHistory([]);
      setAuthError(t("auth.sessionExpired"));
    });

    return () => setUnauthorizedHandler(null);
  }, [t]);

  useEffect(() => {
    if (!isAuthenticated) {
      setRecipes([]);
      setList(null);
      setListHistory([]);
      return;
    }
    void loadRecipes();
    void loadShoppingListHistory();
  }, [isAuthenticated, loadRecipes, loadShoppingListHistory]);

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
      // Data loading is handled by the useEffect that watches isAuthenticated.
    } catch {
      setAuthError(t("auth.invalidPasscode"));
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
    setListHistory([]);
    clearCart();
  }

  async function onGenerateList() {
    const cartInput = toCartInput();
    if (cartInput.length === 0) {
      return;
    }

    try {
      const defaultLabel = t("shopping.weekLabel", { week: getIsoWeekNumber(new Date()) });
      const data = await createShoppingList(cartInput, defaultLabel);
      setList(data);
      await loadShoppingListHistory();
    } catch {
      // 401 is handled by the global interceptor; other errors are transient.
    }
  }

  async function onRenameList(listId: number, label: string) {
    try {
      const updated = await patchShoppingList(listId, label || null);
      setList((previous) => (previous?.id === listId ? updated : previous));
      await loadShoppingListHistory();
    } catch {
      if (list?.id === listId) {
        await openShoppingList(list.id);
      }
    }
  }

  async function onDeleteList(listId: number) {
    try {
      await deleteShoppingList(listId);
      setList((previous) => (previous?.id === listId ? null : previous));
      setListHistory((previous) => previous.filter((entry) => entry.id !== listId));
    } catch {
      await loadShoppingListHistory();
    }
  }

  async function onToggleOwned(itemId: number, isAlreadyOwned: boolean) {
    if (!list) {
      return;
    }

    setList((previous) => {
      if (!previous) {
        return previous;
      }
      return {
        ...previous,
        items: previous.items.map((item) =>
          item.id === itemId ? { ...item, is_already_owned: isAlreadyOwned } : item
        ),
      };
    });

    try {
      await patchShoppingListItem(list.id, itemId, isAlreadyOwned);
      await loadShoppingListHistory();
    } catch {
      await openShoppingList(list.id);
    }
  }

  async function onAddCustomItem(payload: { name: string; quantity: number; unit: string }) {
    if (!list) {
      return;
    }

    try {
      const item = await addShoppingListCustomItem(list.id, {
        name: payload.name,
        quantity: payload.quantity,
        unit: payload.unit,
        category: "Other",
      });
      setList((previous) => {
        if (!previous) {
          return previous;
        }
        return {
          ...previous,
          items: [...previous.items, item],
        };
      });
      await loadShoppingListHistory();
    } catch {
      await openShoppingList(list.id);
    }
  }

  async function onDeleteItem(itemId: number) {
    if (!list) return;
    // Optimistic update
    setList((previous) => {
      if (!previous) return previous;
      return { ...previous, items: previous.items.filter((i) => i.id !== itemId) };
    });
    try {
      await deleteShoppingListItem(list.id, itemId);
      await loadShoppingListHistory();
    } catch {
      await openShoppingList(list.id);
    }
  }

  async function onScrape(urls: string[]) {
    if (!isAuthenticated) return;
    for (const u of urls) {
      if (u.trim()) {
        await startScrape(u.trim(), loadRecipes);
      }
    }
  }

  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <p className="text-sm text-gray-600">{t("app.checkingSession")}</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLogin={onLogin} error={authError} />;
  }

  return (
    <div className="min-h-screen text-ink">
      <Navbar onLogout={onLogout} isDark={isDark} onToggleDark={toggleDark} />
      <Routes>
        <Route
          path="/"
          element={
            <DashboardPage
              loading={loading}
              scrapeState={scrapeState}
              recipes={recipes}
              cart={cart}
              list={list}
              onScrape={onScrape}
              onRefreshRecipes={loadRecipes}
              onAddToCart={addToCart}
              onUpdateServings={updateServings}
              onClearCart={clearCart}
              onGenerateList={onGenerateList}
              onToggleOwned={onToggleOwned}
              onAddCustomItem={onAddCustomItem}
              onRecipesChanged={setRecipes}
            />
          }
        />
        <Route path="/history" element={<HistoryPage lists={listHistory} onDeleteList={onDeleteList} />} />
        <Route
          path="/lists/:listId"
          element={
            <ShoppingListViewPage
              list={list}
              onOpenShoppingList={openShoppingList}
              onRenameList={onRenameList}
              onToggleOwned={onToggleOwned}
              onAddCustomItem={onAddCustomItem}
              onDeleteItem={onDeleteItem}
            />
          }
        />
        <Route path="/pantry" element={<PantryPage />} />
        <Route path="/meal-planner" element={<MealPlannerPage onListGenerated={(l: ShoppingListType) => { setList(l); void loadShoppingListHistory(); }} />} />
        <Route path="/admin/ingredients" element={<IngredientsAdminPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
