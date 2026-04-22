import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import {
  addShoppingListCustomItem,
  createShoppingList,
  fetchRecipes,
  fetchShoppingList,
  fetchShoppingLists,
  loginWithPasscode,
  logout,
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
import type { RecipeListItem, ShoppingList as ShoppingListType, ShoppingListSummary } from "./types";
import { useTranslation } from "react-i18next";

function App() {
  const { t } = useTranslation();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const { cart, addToCart, updateServings, toCartInput } = useCart();
  const { loading, scrapeState, startScrape } = useScrape();
  const [list, setList] = useState<ShoppingListType | null>(null);
  const [listHistory, setListHistory] = useState<ShoppingListSummary[]>([]);
  const [url, setUrl] = useState("");

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
      setAuthError("Session expired. Sign in again.");
    });

    return () => setUnauthorizedHandler(null);
  }, []);

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
      await loadRecipes();
      await loadShoppingListHistory();
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
    setListHistory([]);
    setUrl("");
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
    const cartInput = toCartInput();
    if (cartInput.length === 0) {
      return;
    }

    const data = await createShoppingList(cartInput);
    setList(data);
    await loadShoppingListHistory();
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

  async function onAddCustomItem(name: string) {
    if (!list) {
      return;
    }

    try {
      const item = await addShoppingListCustomItem(list.id, {
        name,
        quantity: 1,
        unit: "item",
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
      <Navbar onLogout={onLogout} />
      <Routes>
        <Route
          path="/"
          element={
            <DashboardPage
              url={url}
              setUrl={setUrl}
              loading={loading}
              scrapeState={scrapeState}
              recipes={recipes}
              cart={cart}
              list={list}
              onScrape={onScrape}
              onRefreshRecipes={loadRecipes}
              onAddToCart={addToCart}
              onUpdateServings={updateServings}
              onGenerateList={onGenerateList}
              onToggleOwned={onToggleOwned}
              onAddCustomItem={onAddCustomItem}
            />
          }
        />
        <Route path="/history" element={<HistoryPage lists={listHistory} />} />
        <Route
          path="/lists/:listId"
          element={
            <ShoppingListViewPage
              list={list}
              onOpenShoppingList={openShoppingList}
              onToggleOwned={onToggleOwned}
              onAddCustomItem={onAddCustomItem}
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;
