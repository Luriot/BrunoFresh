import { FormEvent, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { createCustomRecipe } from "../api/client";
import type { RecipeCreate, RecipeIngredientCreate, RecipeDetail } from "../types";
import { UnitSelector } from "./UnitSelector";

type Props = {
  onClose: () => void;
  onCreated: (recipe: RecipeDetail) => void;
};

const MAX_TITLE_LENGTH = 140;
const MAX_ERROR_LENGTH = 180;

function sanitizeInlineMessage(value: string): string {
  return value
    .replace(/[<>"'`]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_ERROR_LENGTH);
}

function extractApiDetail(error: unknown): string | null {
  if (!error || typeof error !== "object") {
    return null;
  }

  const response = (error as { response?: { data?: { detail?: unknown } } }).response;
  if (typeof response?.data?.detail === "string") {
    return sanitizeInlineMessage(response.data.detail);
  }

  const message = (error as { message?: unknown }).message;
  if (typeof message === "string") {
    return sanitizeInlineMessage(message);
  }

  return null;
}

export function CustomRecipeModal({ onClose, onCreated }: Readonly<Props>) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [servings, setServings] = useState(2);
  const [prepTime, setPrepTime] = useState<number | "">("");

  const [ingredients, setIngredients] = useState<RecipeIngredientCreate[]>([]);
  const [ingRaw, setIngRaw] = useState("");
  const [ingQty, setIngQty] = useState<number | "">(1);
  const [ingUnit, setIngUnit] = useState("unité");
  const [ingName, setIngName] = useState("");
  const [ingCat, setIngCat] = useState("Other");

  const canSubmit = useMemo(() => title.trim().length > 0 && !loading, [title, loading]);

  const addIngredient = () => {
    const cleanName = ingName.trim();
    if (!cleanName) {
      setError(t("customRecipe.errors.ingredientNameRequired"));
      return;
    }

    setError(null);
    const safeQty = Number(ingQty);
    setIngredients((prev) => [
      ...prev,
      {
        raw_string: ingRaw.trim() || `${safeQty || 1} ${ingUnit} ${cleanName}`,
        quantity: Number.isFinite(safeQty) && safeQty > 0 ? safeQty : 1,
        unit: ingUnit,
        ingredient_name: cleanName,
        category: ingCat,
      },
    ]);
    setIngRaw("");
    setIngQty(1);
    setIngUnit("unité");
    setIngName("");
    setIngCat("Other");
  };

  const removeIngredient = (idx: number) => {
    setIngredients((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setError(t("customRecipe.errors.titleRequired"));
      return;
    }

    if (cleanTitle.length > MAX_TITLE_LENGTH) {
      setError(t("customRecipe.errors.titleTooLong", { count: MAX_TITLE_LENGTH }));
      return;
    }

    try {
      setLoading(true);

      const normalizedIngredients: RecipeIngredientCreate[] = ingredients.map((ingredient) => ({
        ...ingredient,
        raw_string: (ingredient.raw_string || "").trim(),
        unit: ingredient.unit,
        ingredient_name: (ingredient.ingredient_name || "").trim(),
      }));

      const payload: RecipeCreate = {
        title: cleanTitle,
        instructions_text: instructions,
        base_servings: Number.isFinite(servings) && servings > 0 ? servings : 1,
        prep_time_minutes: prepTime === "" ? null : Math.max(0, Number(prepTime)),
        ingredients: normalizedIngredients,
      };
      const detail = await createCustomRecipe(payload);
      onCreated(detail);
    } catch (err: unknown) {
      console.error("Custom recipe creation failed", err);
      const safeDetail = extractApiDetail(err);
      setError(safeDetail || t("customRecipe.errors.createFailed"));
    } finally {
      setLoading(false);
    }
  };

  // dialog is an interactive element; onKeyDown for Escape is intentional
  return (
    <dialog
      open
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
    >
      <div
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-xl dark:bg-[#252526] dark:text-gray-100">
        <div className="flex items-center justify-between border-b p-4 dark:border-[#3e3e42]">
          <h2 className="text-xl font-bold">{t("customRecipe.title")}</h2>
          <button
            onClick={onClose}
            className="rounded-xl p-2 hover:bg-gray-100 dark:hover:bg-[#3e3e42]"
            type="button"
            aria-label={t("app.close")}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto p-4">
          {error && <div className="mb-4 rounded bg-red-100 p-3 text-red-700">{error}</div>}

          <form id="create-recipe-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">{t("customRecipe.fields.title")}</label>
              <input
                className="w-full rounded-xl border border-gray-300 p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={MAX_TITLE_LENGTH}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium">{t("customRecipe.fields.servings")}</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  className="w-full rounded-xl border border-gray-300 p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                  value={servings}
                  onChange={(e) => setServings(Math.max(1, Number(e.target.value) || 1))}
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("customRecipe.fields.prepTime")}</label>
                <input
                  type="number"
                  min="0"
                  max="1440"
                  className="w-full rounded-xl border border-gray-300 p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                  value={prepTime}
                  onChange={(e) => setPrepTime(e.target.value ? Number(e.target.value) : "")}
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">{t("customRecipe.fields.instructions")}</label>
              <textarea
                className="w-full rounded-xl border border-gray-300 p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                rows={4}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
              />
            </div>

            <div className="border-t pt-4 dark:border-[#3e3e42]">
              <h3 className="mb-2 text-lg font-semibold">{t("customRecipe.fields.ingredients")}</h3>
              {ingredients.length > 0 && (
                <ul className="mb-4 space-y-2">
                  {ingredients.map((ing, i) => (
                    <li key={`${ing.ingredient_name}-${i}`} className="flex items-center justify-between rounded-lg bg-gray-50 p-2 dark:bg-[#1e1e1e]">
                      <span>{ing.quantity} {ing.unit} {ing.ingredient_name}</span>
                      <button
                        type="button"
                        className="text-red-500 hover:text-red-700"
                        onClick={() => removeIngredient(i)}
                      >
                        {t("customRecipe.actions.remove")}
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                <input
                  placeholder={t("customRecipe.fields.ingredientName")}
                  className="rounded border p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                  value={ingName}
                  onChange={(e) => setIngName(e.target.value)}
                />
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  placeholder={t("customRecipe.fields.quantity")}
                  className="rounded border p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e]"
                  value={ingQty}
                  onChange={(e) => setIngQty(e.target.value ? Number(e.target.value) : "")}
                />
                <UnitSelector
                  value={ingUnit}
                  onChange={setIngUnit}
                  className="rounded border p-2 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
                />
                <button
                  type="button"
                  className="rounded bg-gray-200 px-3 py-2 font-medium hover:bg-gray-300 dark:bg-[#3e3e42] dark:hover:bg-[#4a4a4f]"
                  onClick={addIngredient}
                >
                  {t("customRecipe.actions.add")}
                </button>
              </div>
            </div>
          </form>
        </div>

        <div className="flex justify-end gap-3 rounded-b-2xl border-t bg-gray-50 p-4 dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
          <button
            type="button"
            className="rounded-xl border border-gray-300 px-4 py-2 hover:bg-gray-100 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30]"
            onClick={onClose}
          >
            {t("customRecipe.actions.cancel")}
          </button>
          <button
            type="submit"
            form="create-recipe-form"
            disabled={!canSubmit}
            className="rounded-xl bg-accent px-4 py-2 font-semibold text-white hover:bg-accent/90"
          >
            {loading ? t("customRecipe.actions.creating") : t("customRecipe.actions.create")}
          </button>
        </div>
      </div>
    </dialog>
  );
}