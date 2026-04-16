import { useMemo, useState } from "react";
import { fetchRecipes, generateCart, queueScrape } from "./api/client";
import { RecipeCard } from "./components/RecipeCard";
import { ShoppingList } from "./components/ShoppingList";
import type { CartInput, CartResponse, RecipeListItem } from "./types";

type CartEntry = {
  recipe: RecipeListItem;
  target_servings: number;
};

function App() {
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [cart, setCart] = useState<CartEntry[]>([]);
  const [list, setList] = useState<CartResponse | null>(null);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadRecipes() {
    const data = await fetchRecipes();
    setRecipes(data);
  }

  async function onScrape() {
    if (!url.trim()) return;
    setLoading(true);
    try {
      await queueScrape(url.trim());
      setUrl("");
      // Basic wait-free UX: user can click refresh once scraping background task has run.
      await loadRecipes();
    } finally {
      setLoading(false);
    }
  }

  function addToCart(recipe: RecipeListItem) {
    setCart((prev) => {
      const existing = prev.find((e) => e.recipe.id === recipe.id);
      if (existing) {
        return prev.map((e) =>
          e.recipe.id === recipe.id ? { ...e, target_servings: e.target_servings + 1 } : e
        );
      }
      return [...prev, { recipe, target_servings: recipe.base_servings }];
    });
  }

  function updateServings(recipeId: number, servings: number) {
    setCart((prev) =>
      prev.map((entry) =>
        entry.recipe.id === recipeId ? { ...entry, target_servings: Math.max(1, servings) } : entry
      )
    );
  }

  async function onGenerateList() {
    const payload: CartInput[] = cart.map((entry) => ({
      recipe_id: entry.recipe.id,
      target_servings: entry.target_servings,
    }));
    const data = await generateCart(payload);
    setList(data);
  }

  const recipeCount = useMemo(() => recipes.length, [recipes.length]);

  return (
    <div className="min-h-screen text-ink">
      <header className="mx-auto max-w-7xl px-4 pb-4 pt-8 sm:px-6 lg:px-8">
        <h1 className="font-heading text-4xl font-bold">MealCart</h1>
        <p className="mt-2 text-sm text-gray-600">Scrape recipes, build a smart grocery list.</p>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-4 pb-10 sm:px-6 lg:grid-cols-3 lg:px-8">
        <section className="space-y-4 lg:col-span-2">
          <div className="rounded-2xl border border-orange-200 bg-white p-4">
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                className="w-full rounded-xl border border-orange-200 px-3 py-2 outline-none focus:border-accent"
                placeholder="Paste recipe URL"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <button
                className="rounded-xl bg-accent px-4 py-2 font-semibold text-white"
                onClick={onScrape}
                disabled={loading}
              >
                {loading ? "Scraping..." : "Scrape"}
              </button>
              <button className="rounded-xl border border-orange-300 px-4 py-2" onClick={loadRecipes}>
                Refresh
              </button>
            </div>
            <p className="mt-2 text-xs text-gray-500">Recipes loaded: {recipeCount}</p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {recipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} onAdd={addToCart} />
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-orange-200 bg-white p-4">
            <h2 className="font-heading text-xl font-semibold">Cart</h2>
            <div className="mt-3 space-y-3">
              {cart.length === 0 && <p className="text-sm text-gray-600">No recipes selected yet.</p>}
              {cart.map((entry) => (
                <div key={entry.recipe.id} className="rounded-xl bg-orange-50 p-3">
                  <p className="text-sm font-semibold">{entry.recipe.title}</p>
                  <label className="mt-2 flex items-center gap-2 text-xs text-gray-700">
                    Servings
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
              Generate Shopping List
            </button>
          </section>

          <section className="rounded-2xl border border-orange-200 bg-white p-4">
            <h2 className="mb-2 font-heading text-xl font-semibold">Shopping List</h2>
            <ShoppingList data={list} />
          </section>
        </aside>
      </main>
    </div>
  );
}

export default App;
