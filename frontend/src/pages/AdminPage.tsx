import { useState } from "react";
import { useTranslation } from "react-i18next";
import { IngredientsTab } from "./admin/IngredientsTab";
import { TagsTab } from "./admin/TagsTab";
import { DatabaseTab } from "./admin/DatabaseTab";
import { RecipesTab } from "./admin/RecipesTab";

type AdminTab = "ingredients" | "tags" | "database" | "recipes";

export function AdminPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<AdminTab>("ingredients");

  const TABS: { key: AdminTab; label: string }[] = [
    { key: "ingredients", label: t("admin.tabs.ingredients") },
    { key: "tags", label: t("admin.tabs.tags") },
    { key: "database", label: t("admin.tabs.database") },
    { key: "recipes", label: t("admin.tabs.recipes") },
  ];

  return (
    <main className="mx-auto max-w-5xl px-4 pb-10 pt-4 sm:px-6 lg:px-8">
      <div className="mb-6 flex justify-center">
        <div className="grid grid-cols-2 gap-1 rounded-2xl border border-gray-200 bg-gray-50 p-1 dark:border-[#3e3e42] dark:bg-[#252526] sm:flex sm:flex-nowrap">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold transition ${
                activeTab === tab.key
                  ? "bg-accent text-white shadow"
                  : "text-gray-600 hover:text-ink dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "ingredients" && <IngredientsTab />}
      {activeTab === "tags" && <TagsTab />}
      {activeTab === "database" && <DatabaseTab />}
      {activeTab === "recipes" && <RecipesTab />}
    </main>
  );
}