import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ShoppingListSummary } from "../types";

type Props = {
  lists: ShoppingListSummary[];
};

export function HistoryPage({ lists }: Props) {
  const { t } = useTranslation();

  return (
    <main className="mx-auto max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
      <section className="rounded-2xl border border-orange-200 bg-white p-4 sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-heading text-2xl font-semibold text-ink">{t("history.title")}</h2>
          <p className="text-sm text-gray-600">{t("history.count", { count: lists.length })}</p>
        </div>

        {lists.length === 0 ? (
          <p className="text-sm text-gray-600">{t("history.empty")}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {lists.map((entry) => (
              <Link
                key={entry.id}
                to={`/lists/${entry.id}`}
                className="rounded-xl border border-orange-200 bg-orange-50 p-4 transition hover:-translate-y-0.5 hover:shadow-sm"
              >
                <p className="text-xs uppercase tracking-wide text-gray-500">#{entry.id}</p>
                <p className="mt-1 text-lg font-semibold text-ink">{entry.label || t("history.defaultLabel")}</p>
                <p className="mt-2 text-sm text-gray-700">
                  {t("history.items", { count: entry.total_items })}
                </p>
                <p className="text-sm text-gray-700">
                  {t("history.owned", { count: entry.already_owned_items })}
                </p>
                <p className="mt-2 text-xs text-gray-500">
                  {new Date(entry.created_at).toLocaleString()}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
