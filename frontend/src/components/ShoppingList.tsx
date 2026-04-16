import type { CartResponse } from "../types";
import { useTranslation } from "react-i18next";

type Props = {
  data: CartResponse | null;
};

export function ShoppingList({ data }: Props) {
  const { t } = useTranslation();

  if (!data) {
    return <p className="text-sm text-gray-600">{t("shopping.empty")}</p>;
  }

  return (
    <div className="space-y-4">
      {Object.entries(data.grouped).map(([category, items]) => (
        <section key={category} className="rounded-2xl border border-orange-200 bg-white p-4">
          <h4 className="mb-2 font-heading text-lg font-semibold text-ink">
            {t(`category.${category}`, { defaultValue: category })}
          </h4>
          <ul className="space-y-1 text-sm text-gray-700">
            {items.map((item) => (
              <li key={`${category}-${item.name}-${item.unit}`}>
                {item.name}: {item.quantity} {item.unit}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {data.needs_review.length > 0 && (
        <section className="rounded-2xl border border-amber-300 bg-amber-50 p-4">
          <h4 className="mb-2 font-heading text-lg font-semibold text-amber-900">
            {t("shopping.needsReview")}
          </h4>
          <ul className="space-y-1 text-sm text-amber-800">
            {data.needs_review.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
