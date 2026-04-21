import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ShoppingList as ShoppingListType } from "../types";

type Props = {
  data: ShoppingListType | null;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (name: string) => Promise<void>;
};

export function ShoppingList({ data, onToggleOwned, onAddCustomItem }: Props) {
  const { t } = useTranslation();
  const [customName, setCustomName] = useState("");

  if (!data) {
    return <p className="text-sm text-gray-600">{t("shopping.empty")}</p>;
  }

  const toBuy = data.items.filter((item) => !item.is_already_owned);
  const alreadyOwned = data.items.filter((item) => item.is_already_owned);

  async function onCustomSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = customName.trim();
    if (!trimmed) {
      return;
    }
    await onAddCustomItem(trimmed);
    setCustomName("");
  }

  function renderItems(items: ShoppingListType["items"], isOwnedTarget: boolean) {
    if (items.length === 0) {
      return <p className="text-sm text-gray-500">{t("shopping.none")}</p>;
    }

    return (
      <ul className="space-y-2 text-sm text-gray-700">
        {items.map((item) => (
          <li key={item.id}>
            <button
              className="flex w-full items-center justify-between rounded-lg border border-orange-200 px-3 py-2 text-left transition hover:bg-orange-50"
              onClick={() => onToggleOwned(item.id, isOwnedTarget)}
              type="button"
            >
              <span className="font-medium text-ink">{item.name}</span>
              <span className="text-xs text-gray-600">
                {item.quantity} {item.unit}
              </span>
            </button>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-orange-200 bg-white p-4">
        <h4 className="mb-2 font-heading text-lg font-semibold text-ink">{t("shopping.toBuy")}</h4>
        {renderItems(toBuy, true)}
      </section>

      <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <h4 className="mb-2 font-heading text-lg font-semibold text-emerald-900">
          {t("shopping.alreadyOwned")}
        </h4>
        {renderItems(alreadyOwned, false)}
      </section>

      <section className="rounded-2xl border border-orange-200 bg-white p-4">
        <h4 className="mb-2 font-heading text-lg font-semibold text-ink">{t("shopping.addManual")}</h4>
        <form className="flex gap-2" onSubmit={onCustomSubmit}>
          <input
            className="w-full rounded-lg border border-orange-200 px-3 py-2 text-sm outline-none focus:border-accent"
            onChange={(event) => setCustomName(event.target.value)}
            placeholder={t("shopping.manualPlaceholder")}
            value={customName}
          />
          <button className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-white" type="submit">
            +
          </button>
        </form>
      </section>

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
