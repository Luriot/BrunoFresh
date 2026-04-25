import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  addMealPlanEntry,
  createMealPlan,
  deleteMealPlan,
  deleteMealPlanEntry,
  fetchMealPlan,
  fetchMealPlans,
  fetchRecipes,
  generateListFromMealPlan,
} from "../api/client";
import type { MealPlan, MealPlanSummary, RecipeListItem, ShoppingList } from "../types";

const DAYS = [0, 1, 2, 3, 4, 5, 6] as const;
const SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;

type Props = {
  onListGenerated: (list: ShoppingList) => void;
};

export function MealPlannerPage({ onListGenerated }: Readonly<Props>) {
  const { t } = useTranslation();
  const [plans, setPlans] = useState<MealPlanSummary[]>([]);
  const [activePlan, setActivePlan] = useState<MealPlan | null>(null);
  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [newLabel, setNewLabel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedMsg, setGeneratedMsg] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Recipe drag state
  const [selectedRecipeId, setSelectedRecipeId] = useState<number | null>(null);
  const [targetDay, setTargetDay] = useState<number>(0);
  const [targetSlot, setTargetSlot] = useState<string>("dinner");
  const [targetServings, setTargetServings] = useState(2);

  const loadPlans = useCallback(() => {
    void fetchMealPlans().then(setPlans).catch(() => {});
  }, []);

  const loadRecipes = useCallback(() => {
    void fetchRecipes().then(setRecipes).catch(() => {});
  }, []);

  useEffect(() => { loadPlans(); loadRecipes(); }, [loadPlans, loadRecipes]);

  async function handleCreatePlan(e: FormEvent) {
    e.preventDefault();
    try {
      const plan = await createMealPlan({ label: newLabel.trim() || undefined });
      setPlans((prev) => [...prev, { id: plan.id, label: plan.label, week_start_date: plan.week_start_date, created_at: plan.created_at, entry_count: 0 }]);
      setActivePlan(plan);
      setNewLabel("");
    } catch {
      //
    }
  }

  async function handleSelectPlan(id: number) {
    try {
      const plan = await fetchMealPlan(id);
      setActivePlan(plan);
    } catch {
      //
    }
  }

  async function handleDeletePlan(id: number) {
    if (!confirm(t("mealPlanner.confirmDelete"))) return;
    try {
      await deleteMealPlan(id);
      setPlans((prev) => prev.filter((p) => p.id !== id));
      if (activePlan?.id === id) setActivePlan(null);
    } catch {
      //
    }
  }

  async function handleAddEntry() {
    if (!activePlan || !selectedRecipeId) return;
    try {
      const entry = await addMealPlanEntry(activePlan.id, {
        recipe_id: selectedRecipeId,
        day_of_week: targetDay,
        meal_slot: targetSlot,
        target_servings: targetServings,
      });
      setActivePlan((prev) =>
        prev ? { ...prev, entries: [...(prev.entries ?? []), entry] } : prev
      );
    } catch {
      //
    }
  }

  async function handleRemoveEntry(entryId: number) {
    if (!activePlan) return;
    try {
      await deleteMealPlanEntry(activePlan.id, entryId);
      setActivePlan((prev) =>
        prev ? { ...prev, entries: prev.entries.filter((e) => e.id !== entryId) } : prev
      );
    } catch {
      //
    }
  }

  async function handleGenerateList() {
    if (!activePlan) return;
    setGenerating(true);
    setGeneratedMsg(null);
    setGenerateError(null);
    try {
      const list = await generateListFromMealPlan(activePlan.id);
      onListGenerated(list);
      setGeneratedMsg(t("mealPlanner.listGenerated"));
    } catch {
      setGenerateError(t("mealPlanner.generateError"));
    } finally {
      setGenerating(false);
    }
  }

  // Get entry for a given day+slot
  function getEntries(day: number, slot: string) {
    return (activePlan?.entries ?? []).filter(
      (e) => e.day_of_week === day && e.meal_slot === slot
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
      <h1 className="mb-6 font-heading text-2xl font-bold text-ink dark:text-gray-100">{t("mealPlanner.title")}</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Left sidebar: plans list + create */}
        <aside className="space-y-4 lg:col-span-1">
          <form onSubmit={(e) => void handleCreatePlan(e)} className="flex gap-2">
            <input
              className="min-w-0 flex-1 rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
              placeholder={t("mealPlanner.labelPlaceholder")}
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
            />
            <button type="submit" className="rounded-xl bg-accent px-3 py-2 text-sm font-semibold text-white">
              {t("mealPlanner.newPlan")}
            </button>
          </form>

          <ul className="space-y-1">
            {plans.map((p) => (
              <li key={p.id} className={`flex items-center justify-between rounded-xl border px-3 py-2 text-sm cursor-pointer transition ${activePlan?.id === p.id ? "border-accent bg-accent/10" : "border-gray-200 hover:bg-gray-50 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30]"}`}>
                <button type="button" className="flex-1 text-left font-medium text-ink dark:text-gray-200" onClick={() => void handleSelectPlan(p.id)}>
                  {p.label || `Plan #${p.id}`}
                  <span className="ml-2 text-xs text-gray-400">{t("mealPlanner.mealsCount", { count: p.entry_count })}</span>
                </button>
                <button type="button" onClick={() => void handleDeletePlan(p.id)} className="ml-2 text-gray-400 hover:text-red-500">✕</button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Main: week grid */}
        <div className="lg:col-span-3">
          {activePlan ? (
            <>
              {/* Add-entry row */}
              <div className="mb-4 flex flex-wrap gap-2 rounded-xl border border-gray-200 bg-white p-3 dark:border-[#3e3e42] dark:bg-[#252526]">
                <select
                  className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                  value={selectedRecipeId ?? ""}
                  onChange={(e) => setSelectedRecipeId(Number(e.target.value))}
                >
                  <option value="">{t("mealPlanner.chooseRecipe")}</option>
                  {recipes.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
                </select>
                <select
                  className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                  value={targetDay}
                  onChange={(e) => setTargetDay(Number(e.target.value))}
                >
                  {DAYS.map((d) => <option key={d} value={d}>{t(`mealPlanner.days.${d}`)}</option>)}
                </select>
                <select
                  className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                  value={targetSlot}
                  onChange={(e) => setTargetSlot(e.target.value)}
                >
                  {SLOTS.map((s) => <option key={s} value={s}>{t(`mealPlanner.slots.${s}`)}</option>)}
                </select>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={targetServings}
                  onChange={(e) => setTargetServings(Math.max(1, Number(e.target.value)))}
                  className="w-16 rounded-lg border border-gray-200 px-2 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                />
                <button
                  type="button"
                  disabled={!selectedRecipeId}
                  onClick={() => void handleAddEntry()}
                  className="rounded-xl bg-accent px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  {t("mealPlanner.addEntry")}
                </button>
              </div>

              {/* Week grid */}
              <div className="overflow-x-auto">
                <table className="w-full min-w-[600px] border-collapse text-sm">
                  <thead>
                    <tr>
                      <th className="w-24 border border-gray-200 bg-gray-50 px-2 py-1 text-left text-xs font-semibold text-gray-500 dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
                        {t("mealPlanner.mealHeader")}
                      </th>
                      {DAYS.map((d) => (
                        <th key={d} className="border border-gray-200 bg-gray-50 px-2 py-1 text-center text-xs font-semibold text-gray-700 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-300">
                          {t(`mealPlanner.days.${d}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {SLOTS.map((slot) => (
                      <tr key={slot}>
                        <td className="border border-gray-200 bg-gray-50 px-2 py-2 text-xs font-medium text-gray-500 dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
                          {t(`mealPlanner.slots.${slot}`)}
                        </td>
                        {DAYS.map((day) => {
                          const entries = getEntries(day, slot);
                          return (
                            <td key={day} className="border border-gray-200 px-1 py-1 align-top dark:border-[#3e3e42]">
                              {entries.length === 0 ? (
                                <span className="text-xs text-gray-300 dark:text-gray-600">—</span>
                              ) : (
                                entries.map((e) => (
                                  <div key={e.id} className="mb-1 flex items-start justify-between gap-1 rounded bg-green-50 px-1.5 py-1 dark:bg-green-900/10">
                                    <div className="min-w-0">
                                      <p className="truncate text-xs font-medium text-ink dark:text-gray-200">{e.recipe_title}</p>
                                      <p className="text-xs text-gray-400">{t("mealPlanner.servingsLabel", { count: e.target_servings })}</p>
                                    </div>
                                    <button type="button" onClick={() => void handleRemoveEntry(e.id)} className="shrink-0 text-gray-300 hover:text-red-400">✕</button>
                                  </div>
                                ))
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Generate list */}
              <div className="mt-4 flex items-center gap-4">
                <button
                  type="button"
                  disabled={generating}
                  onClick={() => void handleGenerateList()}
                  className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-white transition hover:bg-accent/90 disabled:opacity-50"
                >
                  {t("mealPlanner.generateList")}
                </button>
                {generatedMsg && (
                  <p className="text-sm text-green-600 dark:text-green-400">
                    {generatedMsg}{" "}
                    <Link to="/history" className="underline">{t("nav.history")}</Link>
                  </p>
                )}
                {generateError && (
                  <p className="text-sm text-red-600 dark:text-red-400">{generateError}</p>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">{t("mealPlanner.noPlanSelected")}</p>
          )}
        </div>
      </div>
    </main>
  );
}
