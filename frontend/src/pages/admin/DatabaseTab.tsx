import { ChangeEvent, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { exportDb, importDb } from "../../api/client";
import { Database } from "lucide-react";

type StatusMsg = { text: string; isError: boolean } | null;

export function DatabaseTab() {
  const { t } = useTranslation();
  const [dbExporting, setDbExporting] = useState(false);
  const [dbImporting, setDbImporting] = useState(false);
  const [dbStatus, setDbStatus] = useState<StatusMsg>(null);
  const importFileRef = useRef<HTMLInputElement>(null);

  async function handleExportDb() {
    setDbExporting(true);
    setDbStatus(null);
    try {
      const blob = await exportDb();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "brunofresh_backup.db";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDbStatus({ text: t("admin.db.importError"), isError: true });
    } finally {
      setDbExporting(false);
    }
  }

  async function handleImportDb(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!confirm(t("admin.db.importDesc"))) {
      if (importFileRef.current) importFileRef.current.value = "";
      return;
    }
    setDbImporting(true);
    setDbStatus(null);
    try {
      await importDb(file);
      setDbStatus({ text: t("admin.db.importSuccess"), isError: false });
    } catch {
      setDbStatus({ text: t("admin.db.importError"), isError: true });
    } finally {
      setDbImporting(false);
      if (importFileRef.current) importFileRef.current.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="flex items-center gap-1.5 font-heading text-base font-bold text-ink dark:text-gray-100">
        <Database className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
        {t("admin.db.title")}
      </h2>

      {dbStatus && (
        <p className={`text-sm font-medium ${dbStatus.isError ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
          {dbStatus.text}
        </p>
      )}

      {/* Export */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-[#3e3e42] dark:bg-[#252526]">
        <h3 className="mb-1 text-sm font-semibold text-ink dark:text-gray-200">{t("admin.db.exportBtn")}</h3>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">{t("admin.db.exportDesc")}</p>
        <button
          type="button"
          disabled={dbExporting}
          onClick={() => void handleExportDb()}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 disabled:opacity-50"
        >
          {dbExporting ? t("app.loading") : `⬇ ${t("admin.db.exportBtn")}`}
        </button>
      </div>

      {/* Import */}
      <div className="rounded-2xl border border-red-200 bg-red-50 p-5 dark:border-red-700/30 dark:bg-red-900/10">
        <h3 className="mb-1 text-sm font-semibold text-red-800 dark:text-red-300">{t("admin.db.importBtn")}</h3>
        <p className="mb-3 text-xs text-red-600 dark:text-red-400">{t("admin.db.importDesc")}</p>
        <label className="flex cursor-pointer items-center gap-3">
          <span className="rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 dark:border-red-700/40 dark:bg-[#252526] dark:text-red-400 dark:hover:bg-[#2d2d30]">
            {dbImporting ? t("app.loading") : `⬆ ${t("admin.db.importBtn")}`}
          </span>
          <input
            ref={importFileRef}
            type="file"
            accept=".db"
            disabled={dbImporting}
            onChange={(e) => void handleImportDb(e)}
            className="sr-only"
            aria-label={t("admin.db.importFileLabel")}
          />
        </label>
      </div>
    </div>
  );
}
