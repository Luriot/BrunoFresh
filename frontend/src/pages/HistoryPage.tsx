import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ShoppingListSummary } from "../types";

type Props = {
  lists: ShoppingListSummary[];
  onDeleteList: (listId: number) => Promise<void>;
};

export function HistoryPage({ lists, onDeleteList }: Readonly<Props>) {
  const { t } = useTranslation();
  const [deletingId, setDeletingId] = useState<number | null>(null);

  async function handleDelete(listId: number) {
    if (deletingId !== null) {
      return;
    }

    setDeletingId(listId);
    try {
      await onDeleteList(listId);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-6 dark:border-[#3e3e42] dark:bg-[#1e1e1e]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-heading text-2xl font-semibold text-ink dark:text-gray-100">{t("history.title")}</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">{t("history.count", { count: lists.length })}</p>
        </div>

        {lists.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">{t("history.empty")}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {lists.map((entry) => (
              <article
                key={entry.id}
                className="relative rounded-xl border border-gray-200 bg-green-50 p-4 transition hover:-translate-y-0.5 hover:shadow-sm dark:border-[#3e3e42] dark:bg-[#252526]"
              >
                {/* Full-card link — covers the entire card */}
                <Link
                  to={`/lists/${entry.id}`}
                  className="absolute inset-0 rounded-xl"
                  aria-label={entry.label || t("history.defaultLabel")}
                />
                <div className="pointer-events-none relative flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">#{entry.id}</p>
                    <p className="mt-1 truncate text-lg font-semibold text-ink dark:text-gray-200">
                      {entry.label || t("history.defaultLabel")}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="pointer-events-auto relative z-10 inline-flex h-8 w-8 items-center justify-center rounded-lg border border-red-200 bg-red-50 text-red-500 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400 dark:hover:bg-red-500/20"
                    onClick={() => handleDelete(entry.id)}
                    disabled={deletingId === entry.id}
                    aria-label={t("history.delete")}
                    title={t("history.delete")}
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M3 6h18" />
                      <path d="M8 6V4h8v2" />
                      <path d="M19 6l-1 14H6L5 6" />
                    </svg>
                  </button>
                </div>
                <p className="pointer-events-none mt-2 text-sm text-gray-700 dark:text-gray-300">
                  {t("history.items", { count: entry.total_items })}
                </p>
                <p className="pointer-events-none text-sm text-gray-700 dark:text-gray-300">
                  {t("history.owned", { count: entry.already_owned_items })}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
