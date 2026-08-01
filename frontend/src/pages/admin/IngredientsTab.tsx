import { useState } from "react";
import { useTranslation } from "react-i18next";
import { IngredientsCatalogPanel } from "./IngredientsCatalogPanel";
import { MergeRulesPanel } from "./MergeRulesPanel";

type SubTab = "catalog" | "rules";

export function IngredientsTab() {
  const { t } = useTranslation();
  const [subTab, setSubTab] = useState<SubTab>("catalog");

  const SUB_TABS: { key: SubTab; label: string }[] = [
    { key: "catalog", label: t("ingredients.subTabs.catalog") },
    { key: "rules", label: t("ingredients.subTabs.rules") },
  ];

  return (
    <>
      <div className="mb-5 flex justify-center">
        <div className="inline-flex gap-1 rounded-2xl border border-gray-200 bg-gray-50 p-1 dark:border-[#3e3e42] dark:bg-[#252526]">
          {SUB_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setSubTab(tab.key)}
              className={`whitespace-nowrap rounded-xl px-4 py-1.5 text-sm font-semibold transition ${
                subTab === tab.key
                  ? "bg-accent text-white shadow"
                  : "text-gray-600 hover:text-ink dark:text-gray-400 dark:hover:text-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {subTab === "catalog" && <IngredientsCatalogPanel />}
      {subTab === "rules" && <MergeRulesPanel />}
    </>
  );
}