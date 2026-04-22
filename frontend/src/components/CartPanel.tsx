import { useTranslation } from "react-i18next";
import type { CartEntry } from "../hooks/useCart";

type Props = {
  cart: CartEntry[];
  onUpdateServings: (recipeId: number, servings: number) => void;
  onGenerateList: () => Promise<void>;
  className?: string;
};

export function CartPanel({ cart, onUpdateServings, onGenerateList, className = "" }: Props) {
  const { t } = useTranslation();

  return (
    <section className={`rounded-2xl border border-orange-200 bg-white p-4 ${className}`.trim()}>
      <h2 className="font-heading text-xl font-semibold">{t("cart.title")}</h2>
      <div className="mt-3 space-y-3">
        {cart.length === 0 && <p className="text-sm text-gray-600">{t("cart.empty")}</p>}
        {cart.map((entry) => (
          <div key={entry.recipe.id} className="rounded-xl bg-orange-50 p-3">
            <p className="text-sm font-semibold">{entry.recipe.title}</p>
            <label className="mt-2 flex items-center gap-2 text-xs text-gray-700">
              {t("cart.servings")}
              <input
                className="w-20 rounded-lg border border-orange-200 px-2 py-1"
                type="number"
                min={1}
                value={entry.target_servings}
                onChange={(e) => onUpdateServings(entry.recipe.id, Number(e.target.value))}
              />
            </label>
          </div>
        ))}
      </div>
      <button
        className="mt-4 w-full rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        onClick={() => void onGenerateList()}
        disabled={cart.length === 0}
        type="button"
      >
        {t("cart.generate")}
      </button>
    </section>
  );
}
