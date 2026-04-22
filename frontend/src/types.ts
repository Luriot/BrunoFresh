export type RecipeListItem = {
  id: number;
  title: string;
  url: string;
  source_domain: string;
  image_local_path: string | null;
  base_servings: number;
};

export type RecipeIngredientOut = {
  raw_string: string | null;
  quantity: number | null;
  unit: string | null;
  needs_review: boolean;
  ingredient_name: string | null;
  ingredient_name_fr: string | null;
  category: string | null;
};

export type RecipeDetail = RecipeListItem & {
  image_original_url: string | null;
  instructions_text: string | null;
  prep_time_minutes: number | null;
  ingredients: RecipeIngredientOut[];
};

export type CartInput = {
  recipe_id: number;
  target_servings: number;
};

export type CartGroupItem = {
  name: string;
  quantity: number;
  unit: string;
};

export type CartResponse = {
  grouped: Record<string, CartGroupItem[]>;
  needs_review: string[];
};

export type ShoppingListCustomItemInput = {
  name: string;
  name_fr?: string | null;
  quantity: number;
  unit: string;
  category: string;
};

export type ShoppingListItem = {
  id: number;
  name: string;
  name_fr: string | null;
  quantity: number;
  unit: string;
  category: string;
  is_custom: boolean;
  is_already_owned: boolean;
};

export type ShoppingListRecipe = {
  recipe_id: number;
  title: string;
  url: string;
  source_domain: string;
  image_local_path: string | null;
  target_servings: number;
};

export type ShoppingList = {
  id: number;
  label: string | null;
  created_at: string;
  updated_at: string;
  items: ShoppingListItem[];
  recipes: ShoppingListRecipe[];
  needs_review: string[];
};

export type ShoppingListSummary = {
  id: number;
  label: string | null;
  created_at: string;
  total_items: number;
  already_owned_items: number;
};

export type ScrapeResponse = {
  message: string;
  url: string;
  job_id?: number;
  status: "pending" | "running" | "completed" | "failed";
};

export type JobStatusResponse = {
  job_id: number;
  status: "pending" | "running" | "completed" | "failed";
  error_message?: string | null;
};

export type RecipeIngredientCreate = {
  raw_string: string;
  quantity: number;
  unit: string;
  ingredient_name: string;
  ingredient_name_fr?: string | null;
  category?: string;
};

export type RecipeCreate = {
  title: string;
  instructions_text?: string;
  base_servings?: number;
  prep_time_minutes?: number | null;
  ingredients?: RecipeIngredientCreate[];
};
