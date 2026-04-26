import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  createMealPlan,
  deleteMealPlan,
  fetchMealPlans,
  buildImageUrl,
} from "../api/client";
import type { MealPlanSummary, ShoppingList } from "../types";

type Props = {
  onListGenerated: (list: ShoppingList) => void;
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function MealPlannerPage({ onListGenerated: _onListGenerated }: Readonly<Props>) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<MealPlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const loadPlans = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchMealPlans();
      setPlans(data);
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);

  async function handleCreatePlan() {
    setCreating(true);
    try {
      const plan = await createMealPlan({});
      navigate(`/planner/${plan.id}`);
    } catch {
      /* empty */
    } finally {
      setCreating(false);
    }
  }

  async function handleDeletePlan(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm(t("mealPlanner.confirmDelete"))) return;
    try {
      await deleteMealPlan(id);
      setPlans((prev) => prev.filter((p) => p.id !== id));
    } catch {
      /* empty */
    }
  }

  function renderBody() {
    if (loading) {
      return <p className="text-sm text-gray-500 dark:text-gray-400">{t("app.loading")}</p>;
    }
    if (plans.length === 0) {
      return (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-gray-500 dark:text-gray-400">{t("mealPlanner.noPlans")}</p>
          <button
            type="button"
            onClick={() => void handleCreatePlan()}
            disabled={creating}
            className="rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
          >
            {creating ? "..." : `+ ${t("mealPlanner.newPlanBtn")}`}
          </button>
        </div>
      );
    }
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {plans.map((plan) => (
          <button
            key={plan.id}
            type="button"
            onClick={() => navigate(`/planner/${plan.id}`)}
            className="group relative flex flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white text-left shadow-sm transition hover:shadow-md dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
          >
            {/* 2x2 image mosaic */}
            <div className="grid h-36 grid-cols-2 grid-rows-2 overflow-hidden">
              {[0, 1, 2, 3].map((i) => {
                const imgPath = plan.preview_images[i];
                return imgPath ? (
                  <img
                    key={i}
                    src={buildImageUrl(imgPath)}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div
                    key={i}
                    className="flex h-full w-full items-center justify-center bg-gray-100 dark:bg-[#2d2d30]"
                  >
                    <span className="text-2xl opacity-20">&#x1F957;</span>
                  </div>
                );
              })}
            </div>

            {/* Card body */}
            <div className="flex flex-1 flex-col gap-1 p-3">
              <p className="line-clamp-2 font-semibold text-gray-800 dark:text-gray-100">
                {plan.label ?? t("mealPlanner.planDetail")}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {t("mealPlanner.mealsCount", { count: plan.entry_count })}
                {" · "}
                {formatDate(plan.created_at)}
              </p>
            </div>

            {/* Delete button */}
            <button
              type="button"
              aria-label="delete"
              onClick={(e) => void handleDeletePlan(e, plan.id)}
              className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/40 text-white opacity-0 transition hover:bg-red-600 group-hover:opacity-100"
            >
              &#x2715;
            </button>
          </button>
        ))}
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-heading text-2xl font-bold dark:text-gray-100">
          {t("mealPlanner.title")}
        </h1>
        <button
          type="button"
          onClick={() => void handleCreatePlan()}
          disabled={creating}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
        >
          {creating ? "..." : `+ ${t("mealPlanner.newPlanBtn")}`}
        </button>
      </div>
      {renderBody()}
    </main>
  );
}