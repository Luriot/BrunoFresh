import { useTranslation } from "react-i18next";

type NutritionBadgesProps = {
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  variant?: "sm" | "md";
};

export function NutritionBadges({ kcal, protein_g, carbs_g, fat_g, variant = "sm" }: Readonly<NutritionBadgesProps>) {
  const { t } = useTranslation();
  if (kcal == null && protein_g == null) return null;

  const px = variant === "sm" ? "px-1.5" : "px-2.5";
  const py = variant === "sm" ? "py-0.5" : "py-1.5";

  return (
    <div className="flex flex-wrap gap-1.5">
      {kcal != null && (
        <span className={`rounded-full bg-amber-50 ${px} ${py} text-[10px] font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300`}>
          {kcal} {t("recipe.kcal")}
        </span>
      )}
      {protein_g != null && (
        <span className={`rounded-full bg-red-50 ${px} ${py} text-[10px] font-semibold text-red-700 dark:bg-red-900/30 dark:text-red-300`}>
          {protein_g}g {t("recipe.protein")}
        </span>
      )}
      {carbs_g != null && (
        <span className={`rounded-full bg-sky-50 ${px} ${py} text-[10px] font-semibold text-sky-700 dark:bg-sky-900/30 dark:text-sky-300`}>
          {carbs_g}g {t("recipe.carbs")}
        </span>
      )}
      {fat_g != null && (
        <span className={`rounded-full bg-yellow-50 ${px} ${py} text-[10px] font-semibold text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300`}>
          {fat_g}g {t("recipe.fat")}
        </span>
      )}
    </div>
  );
}