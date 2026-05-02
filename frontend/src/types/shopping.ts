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
  is_excluded: boolean;
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
