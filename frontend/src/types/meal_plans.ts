export type MealPlanEntry = {
  id: number;
  recipe_id: number;
  recipe_title: string;
  recipe_image_local_path: string | null;
  day_of_week: number;
  meal_slot: string | null;
  target_servings: number;
};

export type MealPlan = {
  id: number;
  label: string | null;
  week_start_date: string | null;
  created_at: string;
  entries: MealPlanEntry[];
};

export type MealPlanSummary = {
  id: number;
  label: string | null;
  week_start_date: string | null;
  created_at: string;
  entry_count: number;
  preview_images: (string | null)[];
};
