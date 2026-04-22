import { useTranslation } from "react-i18next";
import type { CartEntry } from "../hooks/useCart";

type Props = {
  cart: CartEntry[];
  onUpdateServings: (recipeId: number, servings: number) => void;
  onClearCart: () => void;
  onGenerateList: () => Promise<void>;
  className?: string;
};

export function CartPanel({
  cart,
  onUpdateServings,
  onClearCart,
  onGenerateList,
  className = "",
}: Props) {
  const { t } = useTranslation();

  return (
    <section className={`rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-[#3e3e42] dark:bg-[#252526] ${className}`.trim()}>
      <h2 className="font-heading text-xl font-semibold dark:text-gray-100">{t("cart.title")}</h2>
      <div className="mt-3 space-y-3">
        {cart.length === 0 && <p className="text-sm text-gray-600 dark:text-gray-400">{t("cart.empty")}</p>}
        {cart.map((entry) => (
          <div key={entry.recipe.id} className="rounded-xl bg-green-50 p-3 dark:bg-accent/10">
            <p className="text-sm font-semibold dark:text-gray-200">{entry.recipe.title}</p>
            <div className="mt-2 flex items-center justify-between text-xs text-gray-700 dark:text-gray-300">
              <span>{t("cart.servings")}</span>
              <div className="flex items-center rounded-lg border border-gray-200 bg-white dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
                <button
                  className="inline-flex h-8 w-8 items-center justify-center text-base font-bold text-gray-700 hover:bg-green-50 disabled:cursor-not-allowed disabled:opacity-40 dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  type="button"
                  disabled={entry.target_servings <= 1}
                  onClick={() => onUpdateServings(entry.recipe.id, entry.target_servings - 1)}
                  aria-label={t("cart.decreaseServings")}
                  title={t("cart.decreaseServings")}
                >
                  -
                </button>
                <span className="inline-flex min-w-[2.5rem] items-center justify-center px-2 text-sm font-semibold text-ink dark:text-gray-200">
                  {entry.target_servings}
                </span>
                <button
                  className="inline-flex h-8 w-8 items-center justify-center text-base font-bold text-gray-700 hover:bg-green-50 dark:text-gray-300 dark:hover:bg-[#2d2d30]"
                  type="button"
                  onClick={() => onUpdateServings(entry.recipe.id, entry.target_servings + 1)}
                  aria-label={t("cart.increaseServings")}
                  title={t("cart.increaseServings")}
                >
                  +
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <button
          className="inline-flex h-10 w-full whitespace-nowrap items-center justify-center gap-2 rounded-xl border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200"
          onClick={onClearCart}
          disabled={cart.length === 0}
          type="button"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M3 6h18" />
            <path d="M8 6V4h8v2" />
            <path d="M19 6l-1 14H6L5 6" />
          </svg>
          {t("cart.clear")}
        </button>
        <button
          className="inline-flex h-10 w-full whitespace-nowrap items-center justify-center gap-2 rounded-xl bg-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 dark:bg-accent dark:hover:bg-accent/80"
          onClick={() => void onGenerateList()}
          disabled={cart.length === 0}
          type="button"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M3 12h18" />
            <path d="M12 3v18" />
          </svg>
          {t("cart.generate")}
        </button>
      </div>
    </section>
  );
}
