import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { formatRecipeInstructions } from "../api/client";
import type { RecipeDetail } from "../types";

type Props = {
  recipe: RecipeDetail;
  onClose: () => void;
  onRecipeUpdated: (updated: RecipeDetail) => void;
};

function parseSteps(text: string): string[] {
  if (!text.trim()) return [];

  // Try numbered steps: "1. ...", "1) ...", "Step 1:", "Étape 1:"
  const numbered = text.split(/\n/).filter((l) => /^\s*(\d+[.):]|\bstep\b|\bétape\b)/i.test(l));
  if (numbered.length >= 2) {
    return numbered.map((l) => l.replace(/^\s*\d+[.):\s]+/, "").trim()).filter(Boolean);
  }

  // Fall back to double-newline paragraphs, then single newlines
  const byParagraph = text.split(/\n{2,}/).map((s) => s.replace(/\n/g, " ").trim()).filter(Boolean);
  if (byParagraph.length >= 2) return byParagraph;

  return text.split(/\n/).map((s) => s.trim()).filter(Boolean);
}

export function CookModeModal({ recipe, onClose, onRecipeUpdated }: Readonly<Props>) {
  const { t } = useTranslation();
  const steps = parseSteps(recipe.instructions_text ?? "");
  const [currentStep, setCurrentStep] = useState(0);
  const [formatting, setFormatting] = useState(false);
  const [formatError, setFormatError] = useState<string | null>(null);

  const totalSteps = steps.length;

  const goNext = useCallback(() => setCurrentStep((s) => Math.min(s + 1, totalSteps - 1)), [totalSteps]);
  const goPrev = useCallback(() => setCurrentStep((s) => Math.max(s - 1, 0)), []);

  // Keyboard navigation
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") goNext();
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") goPrev();
      else if (e.key === "Escape") onClose();
    }
    globalThis.addEventListener("keydown", onKey);
    return () => globalThis.removeEventListener("keydown", onKey);
  }, [goNext, goPrev, onClose]);

  async function handleFormat() {
    setFormatting(true);
    setFormatError(null);
    try {
      const updated = await formatRecipeInstructions(recipe.id);
      onRecipeUpdated(updated);
      setCurrentStep(0);
    } catch {
      setFormatError(t("cookMode.formatError"));
    } finally {
      setFormatting(false);
    }
  }

  return (
    <dialog
      open
      className="fixed inset-0 z-[60] flex flex-col bg-gray-900 text-white"
      aria-label={t("cookMode.title")}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="text-sm font-medium text-gray-400">
          {recipe.title}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void handleFormat()}
            disabled={formatting}
            className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 transition hover:bg-gray-700 disabled:opacity-50"
          >
            {formatting ? t("cookMode.formatting") : t("cookMode.formatWithAI")}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 transition hover:bg-gray-700"
          >
            ✕ {t("app.close")}
          </button>
        </div>
      </div>

      {formatError && (
        <p className="px-6 text-sm text-red-400">{formatError}</p>
      )}

      {/* Step content — flex-1 fills remaining height */}
      {totalSteps === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-xl text-gray-400">{t("recipe.noInstructions")}</p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          {/* Step counter */}
          <p className="mb-6 text-lg font-semibold text-green-400">
            {t("cookMode.step", { current: currentStep + 1, total: totalSteps })}
          </p>

          {/* Step text */}
          <p className="max-w-2xl text-3xl font-medium leading-snug sm:text-4xl">
            {steps[currentStep]}
          </p>

          {/* Progress dots */}
          <div className="mt-10 flex gap-2">
            {steps.map((step, i) => (
              <button
                key={step.slice(0, 40)}
                type="button"
                aria-label={t("cookMode.stepDot", { step: i + 1 })}
                onClick={() => setCurrentStep(i)}
                className={`h-2 w-2 rounded-full transition ${
                  i === currentStep ? "w-6 bg-green-400" : "bg-gray-600 hover:bg-gray-500"
                }`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Bottom navigation */}
      <div className="flex items-center justify-between px-6 py-6">
        <button
          type="button"
          onClick={goPrev}
          disabled={currentStep === 0}
          className="rounded-xl bg-gray-700 px-6 py-3 text-lg font-semibold transition hover:bg-gray-600 disabled:opacity-30"
        >
          ← {t("cookMode.prev")}
        </button>
        <span className="text-sm text-gray-500">
          {currentStep + 1} / {totalSteps}
        </span>
        <button
          type="button"
          onClick={goNext}
          disabled={currentStep === totalSteps - 1}
          className="rounded-xl bg-green-600 px-6 py-3 text-lg font-semibold transition hover:bg-green-500 disabled:opacity-30"
        >
          {t("cookMode.next")} →
        </button>
      </div>
    </dialog>
  );
}
