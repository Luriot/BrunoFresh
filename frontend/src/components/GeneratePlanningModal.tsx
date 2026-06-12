import { FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Tag, Wand2, X } from "lucide-react";
import { fetchTags, generateQuickPlan } from "../api/client";
import type { Tag as TagType } from "../types";
import { extractApiDetail } from "../utils/error";

type Props = {
  onClose: () => void;
  onSuccess: (planId: number) => void;
};

export function GeneratePlanningModal({ onClose, onSuccess }: Readonly<Props>) {
  const { t } = useTranslation();

  const [tags, setTags] = useState<TagType[]>([]);
  const [loadingTags, setLoadingTags] = useState(true);

  const [selectedTagId, setSelectedTagId] = useState<number | "">("");
  const [planName, setPlanName] = useState("");
  const [dishes, setDishes] = useState(7);
  const [servings, setServings] = useState(2);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchTags()
      .then((data) => {
        if (!cancelled) setTags(data);
      })
      .catch(() => {
        /* empty */
      })
      .finally(() => {
        if (!cancelled) setLoadingTags(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleTagChange(tagId: number | "") {
    setSelectedTagId(tagId);
    if (tagId !== "") {
      const tag = tags.find((t) => t.id === tagId);
      if (tag && !planName) {
        setPlanName(tag.name);
      } else if (tag) {
        // Keep current custom name, but auto-fill if user hasn't typed anything yet
        const currentTag = tags.find((t) => t.id === Number(selectedTagId));
        if (!currentTag || planName === currentTag.name) {
          setPlanName(tag.name);
        }
      }
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (selectedTagId === "") {
      setError(t("mealPlanner.quickGenerateNoTag"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const plan = await generateQuickPlan({
        tag_id: Number(selectedTagId),
        label: planName.trim() || undefined,
        target_servings: servings,
        days: dishes,
      });
      onSuccess(plan.id);
    } catch (err) {
      setError(extractApiDetail(err) ?? t("mealPlanner.quickGenerateError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog
      open
      tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />

      <div className="relative z-10 flex max-h-[90vh] w-full max-w-md flex-col rounded-2xl bg-white shadow-xl dark:bg-[#252526] dark:text-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between border-b p-4 dark:border-[#3e3e42]">
          <div className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-accent" aria-hidden="true" />
            <h2 className="text-lg font-bold">{t("mealPlanner.quickGenerateTitle")}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("app.close")}
            className="rounded-xl p-2 hover:bg-gray-100 dark:hover:bg-[#3e3e42]"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <form id="quick-generate-form" onSubmit={(e) => void handleSubmit(e)} className="overflow-y-auto p-4">
          {error && (
            <div className="mb-4 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </div>
          )}

          {/* Tag selector */}
          <div className="mb-4">
            <label className="mb-1 flex items-center gap-1 text-sm font-medium">
              <Tag className="h-4 w-4 opacity-60" aria-hidden="true" />
              {t("mealPlanner.quickGenerateTagLabel")}
              <span className="text-red-500">*</span>
            </label>
            {loadingTags ? (
              <p className="text-sm text-gray-400">{t("app.loading")}</p>
            ) : (
              <select
                value={selectedTagId}
                onChange={(e) => handleTagChange(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-100"
                required
              >
                <option value="">{t("mealPlanner.quickGenerateTagPlaceholder")}</option>
                {tags.map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Plan name */}
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium">
              {t("mealPlanner.quickGenerateNameLabel")}
            </label>
            <input
              type="text"
              value={planName}
              onChange={(e) => setPlanName(e.target.value)}
              maxLength={160}
              placeholder={t("mealPlanner.labelPlaceholder")}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-100"
            />
          </div>

          {/* Dishes + Servings (side by side) */}
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">
                {t("mealPlanner.quickGenerateDishesLabel")}
              </label>
              <input
                type="number"
                value={dishes}
                min={1}
                max={14}
                placeholder="1 – 14"
                onChange={(e) => setDishes(Math.min(14, Math.max(1, Number(e.target.value))))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                {t("mealPlanner.quickGenerateServingsLabel")}
              </label>
              <input
                type="number"
                value={servings}
                min={1}
                max={20}
                onChange={(e) => setServings(Math.min(20, Math.max(1, Number(e.target.value))))}
                className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-100"
              />
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t p-4 dark:border-[#3e3e42]">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-xl px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-60 dark:text-gray-300 dark:hover:bg-[#3e3e42]"
          >
            {t("mealPlanner.discard")}
          </button>
          <button
            type="submit"
            form="quick-generate-form"
            disabled={submitting || selectedTagId === ""}
            className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-60"
          >
            <Wand2 className="h-4 w-4" aria-hidden="true" />
            {submitting ? t("mealPlanner.quickGenerating") : t("mealPlanner.quickGenerateBtn")}
          </button>
        </div>
      </div>
    </dialog>
  );
}
