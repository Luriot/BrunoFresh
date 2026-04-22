import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ShoppingList } from "../components/ShoppingList";
import type { ShoppingList as ShoppingListType } from "../types";

type Props = {
  list: ShoppingListType | null;
  onOpenShoppingList: (listId: number) => Promise<void>;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (name: string) => Promise<void>;
};

export function ShoppingListViewPage({
  list,
  onOpenShoppingList,
  onToggleOwned,
  onAddCustomItem,
}: Props) {
  const { t } = useTranslation();
  const params = useParams();
  const listId = Number(params.listId);

  useEffect(() => {
    if (Number.isFinite(listId) && listId > 0) {
      void onOpenShoppingList(listId);
    }
  }, [listId, onOpenShoppingList]);

  return (
    <main className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-orange-200 bg-white p-4 sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="font-heading text-2xl font-semibold text-ink">
              {t("shopping.listDetail", { id: Number.isFinite(listId) ? listId : "-" })}
            </h2>
            {list && (
              <p className="mt-1 text-sm text-gray-600">{new Date(list.created_at).toLocaleString()}</p>
            )}
          </div>
          <Link to="/history" className="rounded-lg border border-orange-200 px-3 py-1 text-sm text-gray-700">
            {t("history.back")}
          </Link>
        </div>

        {list && list.id === listId ? (
          <ShoppingList data={list} onAddCustomItem={onAddCustomItem} onToggleOwned={onToggleOwned} />
        ) : (
          <p className="text-sm text-gray-600">{t("shopping.loading")}</p>
        )}
      </section>
    </main>
  );
}
