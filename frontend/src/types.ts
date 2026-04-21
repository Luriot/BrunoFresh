export type RecipeListItem = {
  id: number;
  title: string;
  url: string;
  source_domain: string;
  image_local_path: string | null;
  base_servings: number;
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
  quantity: number;
  unit: string;
  category: string;
};

export type ShoppingListItem = {
  id: number;
  name: string;
  quantity: number;
  unit: string;
  category: string;
  is_custom: boolean;
  is_already_owned: boolean;
};

export type ShoppingList = {
  id: number;
  label: string | null;
  created_at: string;
  updated_at: string;
  items: ShoppingListItem[];
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
