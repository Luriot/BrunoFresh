import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import type { RecipeDetail } from "../types";

type Props = {
  recipe: RecipeDetail;
  onClose: () => void;
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

export function CookModeModal({ recipe, onClose }: Readonly<Props>) {
  const { t } = useTranslation();
  // Use structured steps when scraped, otherwise fall back to parsing text
  const hasStructuredSteps = recipe.instruction_steps && recipe.instruction_steps.length > 0;
  const steps = hasStructuredSteps
    ? recipe.instruction_steps.map((s) => s.text)
    : parseSteps(recipe.instructions_text ?? "");
  const stepImages = hasStructuredSteps
    ? recipe.instruction_steps.map((s) => s.image_url ?? null)
    : steps.map(() => null);
  const [currentStep, setCurrentStep] = useState(0);

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

  return (
    <dialog
      open
      className="fixed inset-0 z-[60] flex flex-col bg-white text-gray-900 dark:bg-[#1e1e1e] dark:text-gray-100"
      aria-label={t("cookMode.title")}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-[#3e3e42]">
        <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
          {recipe.title}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 transition hover:bg-gray-100 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          {t("app.close")}
        </button>
      </div>

      {/* Step content — flex-1 fills remaining height */}
      {totalSteps === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-xl text-gray-400">{t("recipe.noInstructions")}</p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          {/* Step counter */}
          <p className="mb-6 text-lg font-semibold text-accent dark:text-accent/80">
            {t("cookMode.step", { current: currentStep + 1, total: totalSteps })}
          </p>

          <div className="w-full max-w-2xl">
            {/* Step image (when available from structured scrape) */}
            {stepImages[currentStep] && (
              <img
                src={stepImages[currentStep]}
                alt={`Step ${currentStep + 1}`}
                className="mb-6 w-full rounded-2xl object-cover shadow-lg"
                style={{ maxHeight: "320px" }}
              />
            )}

            {/* Step text */}
            <p className="whitespace-pre-line text-left text-xl font-medium leading-relaxed text-gray-800 dark:text-gray-100 sm:text-2xl">
              {steps[currentStep]}
            </p>
          </div>

          {/* Progress dots */}
          <div className="mt-10 flex flex-wrap justify-center gap-2">
            {steps.map((step, i) => (
              <button
                key={step.slice(0, 40)}
                type="button"
                aria-label={t("cookMode.stepDot", { step: i + 1 })}
                onClick={() => setCurrentStep(i)}
                className={`h-2 w-2 rounded-full transition ${
                  i === currentStep ? "w-6 bg-accent" : "bg-gray-300 hover:bg-gray-400 dark:bg-[#3e3e42] dark:hover:bg-gray-500"
                }`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Bottom navigation */}
      <div className="flex items-center justify-between border-t border-gray-200 px-6 pt-4 dark:border-[#3e3e42]" style={{ paddingBottom: "max(1.5rem, calc(0.75rem + env(safe-area-inset-bottom, 0px)))" }}>
        <button
          type="button"
          onClick={goPrev}
          disabled={currentStep === 0}
          className="rounded-xl border border-gray-300 px-6 py-3 text-lg font-semibold transition hover:bg-gray-100 dark:border-[#3e3e42] dark:hover:bg-[#2d2d30] disabled:opacity-30"
        >
          ← {t("cookMode.prev")}
        </button>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {currentStep + 1} / {totalSteps}
        </span>
        <button
          type="button"
          onClick={goNext}
          disabled={currentStep === totalSteps - 1}
          className="rounded-xl bg-accent px-6 py-3 text-lg font-semibold text-white transition hover:bg-accent/90 disabled:opacity-30"
        >
          {t("cookMode.next")} →
        </button>
      </div>
    </dialog>
  );
}
