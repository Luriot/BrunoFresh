import { type ReactNode, FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ShoppingList } from "../components/ShoppingList";
import type { ShoppingList as ShoppingListType } from "../types";

type Props = {
  list: ShoppingListType | null;
  onOpenShoppingList: (listId: number) => Promise<void>;
  onRenameList: (listId: number, label: string) => Promise<void>;
  onToggleOwned: (itemId: number, isAlreadyOwned: boolean) => void;
  onAddCustomItem: (payload: { name: string; quantity: number; unit: string }) => Promise<void>;
  onDeleteItem?: (itemId: number) => void;
};

export function ShoppingListViewPage({
  list,
  onOpenShoppingList,
  onRenameList,
  onToggleOwned,
  onAddCustomItem,
  onDeleteItem,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const params = useParams();
  const listId = Number(params.listId);
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [labelDraft, setLabelDraft] = useState("");

  useEffect(() => {
    if (Number.isFinite(listId) && listId > 0) {
      void onOpenShoppingList(listId);
    }
  }, [listId, onOpenShoppingList]);

  useEffect(() => {
    if (list?.id === listId) {
      setLabelDraft(list.label ?? "");
      setIsEditingLabel(false);
    }
  }, [list, listId]);

  async function onLabelSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (list?.id !== listId) {
      return;
    }
    await onRenameList(list.id, labelDraft.trim());
    setIsEditingLabel(false);
  }

  const isCurrentList = list?.id === listId;

  const editForm = (
    <form className="flex items-center gap-2" onSubmit={(event) => void onLabelSubmit(event)}>
      <input
        className="w-56 rounded-lg border border-gray-200 bg-white px-3 py-1 text-sm text-gray-900 outline-none focus:border-accent dark:border-[#3e3e42] dark:bg-[#1e1e1e] dark:text-gray-200 dark:placeholder-gray-500"
        maxLength={160}
        value={labelDraft}
        onChange={(event) => setLabelDraft(event.target.value)}
        placeholder={t("shopping.renamePlaceholder")}
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
      />
      <button
        type="submit"
        className="rounded-lg bg-accent px-2 py-1 text-xs font-semibold text-white"
      >
        {t("shopping.save")}
      </button>
      <button
        type="button"
        className="rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-700 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
        onClick={() => {
          setLabelDraft(list?.label ?? "");
          setIsEditingLabel(false);
        }}
      >
        {t("shopping.cancel")}
      </button>
    </form>
  );

  const labelView = (
    <div className="flex items-center gap-2">
      <h2 className="font-heading text-2xl font-semibold text-ink dark:text-gray-100">
        {list?.label || t("history.defaultLabel")}
      </h2>
      <button
        type="button"
        className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-gray-200 text-gray-700 hover:bg-green-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
        onClick={() => setIsEditingLabel(true)}
        aria-label={t("shopping.rename")}
        title={t("shopping.rename")}
      >
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4z" />
        </svg>
      </button>
    </div>
  );

  let headerContent: ReactNode;
  if (!isCurrentList) {
    headerContent = (
      <h2 className="font-heading text-2xl font-semibold text-ink dark:text-gray-100">
        {t("shopping.loading")}
      </h2>
    );
  } else if (isEditingLabel) {
    headerContent = editForm;
  } else {
    headerContent = labelView;
  }

  return (
    <main className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-gray-200 bg-white p-4 sm:p-6 dark:border-[#3e3e42] dark:bg-[#252526]">
        <div className="mb-4 flex items-center justify-between">
          <div>
            {headerContent}
          </div>
          <Link
            to="/history"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-700 hover:bg-green-50 dark:border-[#3e3e42] dark:text-gray-300 dark:hover:bg-[#2d2d30]"
            aria-label={t("history.back")}
            title={t("history.back")}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </Link>
        </div>

        {isCurrentList ? (
          <ShoppingList data={list} onAddCustomItem={onAddCustomItem} onToggleOwned={onToggleOwned} onDeleteItem={onDeleteItem} />
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-400">{t("shopping.loading")}</p>
        )}
      </section>
    </main>
  );
}
