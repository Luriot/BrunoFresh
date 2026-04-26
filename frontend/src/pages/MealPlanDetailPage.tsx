import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  addMealPlanEntry,
  deleteMealPlanEntry,
  fetchMealPlan,
  fetchRecipes,
  fetchTags,
  generateListFromMealPlan,
  patchMealPlan,
  patchMealPlanEntry,
  deleteMealPlan,
  buildImageUrl,
} from "../api/client";
import type { MealPlan, MealPlanEntry, RecipeListItem, ShoppingList, Tag } from "../types";

const DAYS = [0, 1, 2, 3, 4, 5, 6] as const;
const BASE_SLOTS = ["lunch", "dinner"] as const;
const SNACK_SLOT = "snack" as const;

const SLOT_COLORS: Record<string, string> = {
  lunch: "border-l-4 border-l-green-400",
  dinner: "border-l-4 border-l-blue-400",
  snack: "border-l-4 border-l-amber-400",
};

type DragSource =
  | { type: "recipe"; recipeId: number }
  | { type: "entry"; recipeId: number; entryId: number; fromDay: number; fromSlot: string };

// ── Sub-components ────────────────────────────────────────────────────────

type EntryCardProps = {
  entry: MealPlanEntry;
  slot: string;
  onServingsChange: (entry: MealPlanEntry, delta: number) => void;
  onDelete: (entryId: number) => void;
  onDragStart: (source: DragSource) => void;
  onDragEnd: () => void;
  servingsLabel: string;
};

function EntryCard({ entry, slot, onServingsChange, onDelete, onDragStart, onDragEnd, servingsLabel }: Readonly<EntryCardProps>) {
  return (
    <li
      draggable
      onDragStart={() =>
        onDragStart({ type: "entry", recipeId: entry.recipe_id, entryId: entry.id, fromDay: entry.day_of_week, fromSlot: slot })
      }
      onDragEnd={onDragEnd}
      className={`mb-1 flex cursor-grab flex-col gap-0.5 list-none rounded-lg bg-white px-2 py-1.5 shadow-sm dark:bg-[#2d2d30] ${SLOT_COLORS[slot] ?? ""}`}
    >
      <p className="line-clamp-2 break-words text-xs font-semibold leading-snug text-gray-800 dark:text-gray-100">
        {entry.recipe_title}
      </p>
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="-"
          onClick={() => onServingsChange(entry, -1)}
          className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs font-bold hover:bg-gray-200 dark:bg-[#3e3e42] dark:hover:bg-[#4a4a50]"
        >
          −
        </button>
        <span className="text-[11px] text-gray-500 dark:text-gray-400">{servingsLabel}</span>
        <button
          type="button"
          aria-label="+"
          onClick={() => onServingsChange(entry, 1)}
          className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs font-bold hover:bg-gray-200 dark:bg-[#3e3e42] dark:hover:bg-[#4a4a50]"
        >
          +
        </button>
        <button
          type="button"
          aria-label="delete entry"
          onClick={() => onDelete(entry.id)}
          className="ml-auto text-xs text-gray-300 hover:text-red-500 dark:text-gray-600"
        >
          ✕
        </button>
      </div>
    </li>
  );
}

type GridCellProps = {
  day: number;
  slot: string;
  entries: MealPlanEntry[];
  isOver: boolean;
  hasDrag: boolean;
  dropHint: string;
  servingsShort: (count: number) => string;
  onDragOver: (day: number, slot: string) => void;
  onDragLeave: () => void;
  onDrop: (day: number, slot: string) => void;
  onServingsChange: (entry: MealPlanEntry, delta: number) => void;
  onDeleteEntry: (entryId: number) => void;
  onDragStartEntry: (source: DragSource) => void;
  onDragEnd: () => void;
  isWeekend: boolean;
};

function GridCell({
  day,
  slot,
  entries,
  isOver,
  hasDrag,
  dropHint,
  servingsShort,
  onDragOver,
  onDragLeave,
  onDrop,
  onServingsChange,
  onDeleteEntry,
  onDragStartEntry,
  onDragEnd,
  isWeekend,
}: Readonly<GridCellProps>) {
  return (
    <section
      aria-label={`${slot} day ${day}`}
      onDragOver={(e) => { e.preventDefault(); onDragOver(day, slot); }}
      onDragLeave={onDragLeave}
      onDrop={() => onDrop(day, slot)}
      className={`min-h-[80px] border border-transparent p-1 transition-colors ${
        isWeekend ? "bg-amber-50/40 dark:bg-amber-900/10" : ""
      } ${isOver ? "rounded-xl bg-green-50 ring-2 ring-green-400 dark:bg-green-900/20" : ""}`}
    >
      {entries.map((entry) => (
        <EntryCard
          key={entry.id}
          entry={entry}
          slot={slot}
          onServingsChange={onServingsChange}
          onDelete={onDeleteEntry}
          onDragStart={onDragStartEntry}
          onDragEnd={onDragEnd}
          servingsLabel={servingsShort(entry.target_servings)}
        />
      ))}
      {entries.length === 0 && !hasDrag && (
        <p className="pt-2 text-center text-[10px] text-gray-300 dark:text-gray-600">{dropHint}</p>
      )}
    </section>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

type Props = {
  onListGenerated: (list: ShoppingList) => void;
};

export function MealPlanDetailPage({ onListGenerated }: Readonly<Props>) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { planId } = useParams<{ planId: string }>();
  const id = Number(planId);

  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [loadError, setLoadError] = useState(false);

  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [labelDraft, setLabelDraft] = useState("");

  const [showSnack, setShowSnack] = useState(false);

  const [generating, setGenerating] = useState(false);
  const [generatedMsg, setGeneratedMsg] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [dragSource, setDragSource] = useState<DragSource | null>(null);
  const [dragOverCell, setDragOverCell] = useState<{ day: number; slot: string } | null>(null);
  const dragSourceRef = useRef<DragSource | null>(null);

  const [recipes, setRecipes] = useState<RecipeListItem[]>([]);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerTagIds, setPickerTagIds] = useState<number[]>([]);
  const [pickerFavOnly, setPickerFavOnly] = useState(false);
  const pickerDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadPlan = useCallback(async () => {
    try {
      const data = await fetchMealPlan(id);
      setPlan(data);
      setLabelDraft(data.label ?? "");
    } catch {
      setLoadError(true);
    }
  }, [id]);

  const loadRecipes = useCallback(() => {
    void fetchRecipes({
      q: pickerSearch || undefined,
      is_favorite: pickerFavOnly || undefined,
      tags: pickerTagIds.length > 0 ? pickerTagIds.join(",") : undefined,
      limit: 200,
    }).then(setRecipes).catch(() => {});
  }, [pickerSearch, pickerFavOnly, pickerTagIds]);

  useEffect(() => {
    void loadPlan();
    fetchTags().then(setAllTags).catch(() => {});
  }, [loadPlan]);

  useEffect(() => {
    if (pickerDebounceRef.current) clearTimeout(pickerDebounceRef.current);
    pickerDebounceRef.current = setTimeout(() => { loadRecipes(); }, 300);
    return () => { if (pickerDebounceRef.current) clearTimeout(pickerDebounceRef.current); };
  }, [loadRecipes]);

  function startEditLabel() {
    setLabelDraft(plan?.label ?? "");
    setIsEditingLabel(true);
  }

  async function submitLabel(e: FormEvent) {
    e.preventDefault();
    if (!plan) return;
    try {
      const updated = await patchMealPlan(plan.id, { label: labelDraft.trim() || null });
      setPlan((prev) => prev ? { ...prev, label: updated.label } : prev);
    } catch {
      /* empty */
    } finally {
      setIsEditingLabel(false);
    }
  }

  async function handleGenerateList() {
    if (!plan) return;
    setGenerating(true);
    setGeneratedMsg(null);
    setGenerateError(null);
    try {
      const list = await generateListFromMealPlan(plan.id);
      setGeneratedMsg(t("mealPlanner.listGenerated"));
      onListGenerated(list);
      setTimeout(() => setGeneratedMsg(null), 4000);
    } catch {
      setGenerateError(t("mealPlanner.generateError"));
    } finally {
      setGenerating(false);
    }
  }

  async function handleDeletePlan() {
    if (!plan) return;
    if (!confirm(t("mealPlanner.confirmDelete"))) return;
    try {
      await deleteMealPlan(plan.id);
      navigate("/planner");
    } catch {
      /* empty */
    }
  }

  function entriesForCell(day: number, slot: string): MealPlanEntry[] {
    if (!plan) return [];
    return plan.entries.filter((e) => e.day_of_week === day && e.meal_slot === slot);
  }

  async function addEntryToCell(recipeId: number, day: number, slot: string) {
    if (!plan) return;
    try {
      const entry = await addMealPlanEntry(plan.id, {
        recipe_id: recipeId,
        day_of_week: day,
        meal_slot: slot,
        target_servings: 2,
      });
      setPlan((prev) => prev ? { ...prev, entries: [...prev.entries, entry] } : prev);
    } catch {
      /* empty */
    }
  }

  async function handleDeleteEntry(entryId: number) {
    if (!plan) return;
    setPlan((prev) => prev ? { ...prev, entries: prev.entries.filter((e) => e.id !== entryId) } : prev);
    try {
      await deleteMealPlanEntry(plan.id, entryId);
    } catch {
      await loadPlan();
    }
  }

  async function handleServingsChange(entry: MealPlanEntry, delta: number) {
    if (!plan) return;
    const next = Math.max(1, Math.min(20, entry.target_servings + delta));
    setPlan((prev) =>
      prev
        ? { ...prev, entries: prev.entries.map((e) => e.id === entry.id ? { ...e, target_servings: next } : e) }
        : prev
    );
    try {
      await patchMealPlanEntry(plan.id, entry.id, { target_servings: next });
    } catch {
      await loadPlan();
    }
  }

  function handleDragStart(source: DragSource) {
    dragSourceRef.current = source;
    setDragSource(source);
  }

  function handleDragEnd() {
    dragSourceRef.current = null;
    setDragSource(null);
    setDragOverCell(null);
  }

  async function handleDrop(day: number, slot: string) {
    const src = dragSourceRef.current;
    setDragOverCell(null);
    if (!src || !plan) return;
    if (src.type === "recipe") {
      await addEntryToCell(src.recipeId, day, slot);
    } else if (src.type === "entry") {
      if (src.fromDay === day && src.fromSlot === slot) return;
      setPlan((prev) =>
        prev
          ? { ...prev, entries: prev.entries.map((e) => e.id === src.entryId ? { ...e, day_of_week: day, meal_slot: slot } : e) }
          : prev
      );
      try {
        await deleteMealPlanEntry(plan.id, src.entryId);
        await addEntryToCell(src.recipeId, day, slot);
      } catch {
        await loadPlan();
      }
    }
  }

  function togglePickerTag(tagId: number) {
    setPickerTagIds((prev) => prev.includes(tagId) ? prev.filter((i) => i !== tagId) : [...prev, tagId]);
  }

  const slots = showSnack ? [...BASE_SLOTS, SNACK_SLOT] : BASE_SLOTS;
  const weekendDays = new Set([5, 6]);

  if (loadError) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <button type="button" onClick={() => navigate("/planner")} className="mb-4 text-sm text-accent underline">
          ← {t("mealPlanner.backToPlans")}
        </button>
        <p className="text-red-500">{t("error.loadFailed")}</p>
      </main>
    );
  }

  if (!plan) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <p className="text-sm text-gray-500 dark:text-gray-400">{t("app.loading")}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-full px-4 py-6 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => navigate("/planner")} className="text-sm text-accent underline hover:no-underline">
          ← {t("mealPlanner.backToPlans")}
        </button>

        {isEditingLabel ? (
          <form onSubmit={(e) => void submitLabel(e)} className="flex gap-2">
            <input
              autoFocus
              value={labelDraft}
              onChange={(e) => setLabelDraft(e.target.value)}
              placeholder={t("mealPlanner.labelPlaceholder")}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1 text-sm dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-100"
            />
            <button type="submit" className="rounded-lg bg-accent px-3 py-1 text-sm text-white">{t("shopping.save")}</button>
            <button type="button" onClick={() => setIsEditingLabel(false)} className="rounded-lg border border-gray-300 px-3 py-1 text-sm dark:border-[#3e3e42] dark:text-gray-300">{t("shopping.cancel")}</button>
          </form>
        ) : (
          <button
            type="button"
            onClick={startEditLabel}
            title={t("mealPlanner.editLabel")}
            className="group flex items-center gap-1 font-heading text-xl font-bold dark:text-gray-100"
          >
            {plan.label || t("mealPlanner.planDetail")}
            <span className="ml-1 text-sm text-gray-400 opacity-0 group-hover:opacity-100">✎</span>
          </button>
        )}

        <div className="ml-auto flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setShowSnack((v) => !v)}
            className={`rounded-xl px-3 py-1 text-sm font-semibold ${showSnack ? "bg-amber-400 text-white" : "border border-gray-300 text-gray-600 dark:border-[#3e3e42] dark:text-gray-300"}`}
          >
            {showSnack ? t("mealPlanner.hideSnack") : t("mealPlanner.showSnack")}
          </button>
          <button
            type="button"
            onClick={() => void handleGenerateList()}
            disabled={generating}
            className="rounded-xl bg-accent px-4 py-1.5 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
          >
            {generating ? t("app.loading") : t("mealPlanner.generateList")}
          </button>
          <button
            type="button"
            onClick={() => void handleDeletePlan()}
            className="rounded-xl border border-red-300 px-3 py-1.5 text-sm font-semibold text-red-500 hover:bg-red-50 dark:border-red-700 dark:hover:bg-red-900/20"
          >
            ✕
          </button>
        </div>
      </div>

      {generatedMsg && (
        <div className="mb-3 rounded-xl bg-green-100 px-4 py-2 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-300">
          ✓ {generatedMsg}
        </div>
      )}
      {generateError && (
        <div className="mb-3 rounded-xl bg-red-100 px-4 py-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {generateError}
        </div>
      )}

      {/* Week grid */}
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          <div className="grid" style={{ gridTemplateColumns: "80px repeat(7, minmax(110px, 1fr))" }}>
            <div />
            {DAYS.map((d) => (
              <div
                key={d}
                className={`border-b border-gray-200 pb-1 text-center text-xs font-semibold uppercase tracking-wide dark:border-[#3e3e42] ${weekendDays.has(d) ? "text-amber-600 dark:text-amber-400" : "text-gray-500 dark:text-gray-400"}`}
              >
                {t(`mealPlanner.days.${d}`)}
              </div>
            ))}
          </div>

          {slots.map((slot) => (
            <div key={slot} className="grid" style={{ gridTemplateColumns: "80px repeat(7, minmax(110px, 1fr))" }}>
              <div className="flex items-center pr-2 pt-1 text-right text-xs font-medium text-gray-400 dark:text-gray-500">
                {t(`mealPlanner.slots.${slot}`)}
              </div>
              {DAYS.map((d) => (
                <GridCell
                  key={d}
                  day={d}
                  slot={slot}
                  entries={entriesForCell(d, slot)}
                  isOver={dragOverCell?.day === d && dragOverCell?.slot === slot}
                  hasDrag={dragSource !== null}
                  dropHint={t("mealPlanner.dropHere")}
                  servingsShort={(count) => t("mealPlanner.servingsShort", { count })}
                  onDragOver={(day, s) => setDragOverCell({ day, slot: s })}
                  onDragLeave={() => setDragOverCell(null)}
                  onDrop={(day, s) => void handleDrop(day, s)}
                  onServingsChange={(entry, delta) => void handleServingsChange(entry, delta)}
                  onDeleteEntry={(entryId) => void handleDeleteEntry(entryId)}
                  onDragStartEntry={handleDragStart}
                  onDragEnd={handleDragEnd}
                  isWeekend={weekendDays.has(d)}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Recipe picker */}
      <section className="mt-8 border-t border-gray-200 pt-6 dark:border-[#3e3e42]">
        <h2 className="mb-3 font-heading text-lg font-bold dark:text-gray-100">
          {t("mealPlanner.recipePicker")}
        </h2>

        <div className="mb-3 flex flex-wrap gap-2">
          <input
            type="search"
            value={pickerSearch}
            onChange={(e) => setPickerSearch(e.target.value)}
            placeholder={t("mealPlanner.searchRecipes")}
            className="w-56 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm dark:border-[#3e3e42] dark:bg-[#252526] dark:text-gray-100 dark:placeholder-gray-500"
          />
          <button
            type="button"
            onClick={() => setPickerFavOnly((v) => !v)}
            className={`rounded-xl px-3 py-1.5 text-sm font-semibold ${pickerFavOnly ? "bg-yellow-400 text-white" : "border border-gray-200 text-gray-600 dark:border-[#3e3e42] dark:text-gray-300"}`}
          >
            ★ {t("app.favoritesFilter")}
          </button>
        </div>

        {allTags.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {allTags.map((tag) => {
              const active = pickerTagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => togglePickerTag(tag.id)}
                  style={{ backgroundColor: active ? (tag.color ?? "#4caf50") : undefined }}
                  className={`rounded-full px-3 py-0.5 text-xs font-semibold transition ${active ? "text-white" : "border border-gray-200 text-gray-600 dark:border-[#3e3e42] dark:text-gray-300"}`}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        )}

        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {recipes.map((recipe) => (
            <RecipePickerRow
              key={recipe.id}
              recipe={recipe}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
            />
          ))}
        </div>
      </section>
    </main>
  );
}

type RecipePickerRowProps = {
  recipe: RecipeListItem;
  onDragStart: (source: DragSource) => void;
  onDragEnd: () => void;
};

function RecipePickerRow({ recipe, onDragStart, onDragEnd }: Readonly<RecipePickerRowProps>) {
  return (
    <li
      draggable
      onDragStart={() => onDragStart({ type: "recipe", recipeId: recipe.id })}
      onDragEnd={onDragEnd}
      className="flex cursor-grab list-none items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm hover:border-accent hover:shadow-sm dark:border-[#3e3e42] dark:bg-[#252526] dark:hover:border-accent"
    >
      {recipe.image_local_path ? (
        <img
          src={buildImageUrl(recipe.image_local_path)}
          alt=""
          className="h-8 w-8 flex-shrink-0 rounded-lg object-cover"
        />
      ) : (
        <div className="h-8 w-8 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-[#3e3e42]" />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold text-gray-800 dark:text-gray-100">{recipe.title}</p>
        {recipe.source_domain && (
          <p className="truncate text-xs text-gray-400">{recipe.source_domain}</p>
        )}
      </div>
      <span className="select-none text-gray-300 dark:text-gray-600">&#x2807;</span>
    </li>
  );
}