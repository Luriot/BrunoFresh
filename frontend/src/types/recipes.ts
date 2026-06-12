import type { Tag } from "./tags";

export type Recommender = {
  username: string;
  avatar_url: string | null;
};

export type HFSearchResult = {
  id: string;
  name: string;
  image_url: string | null;
  tags: string[];
  total_time_minutes: number | null;
  hf_url: string;
  already_imported: boolean;
  kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
};

export type RecipeListItem = {
  id: number;
  title: string;
  url: string;
  source_domain: string;
  image_local_path: string | null;
  image_original_url: string | null;
  image_url: string | null;
  base_servings: number;
  prep_time_minutes: number | null;
  kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  is_favorite_by_me: boolean;
  recommenders: Recommender[];
  tags: Tag[];
};

export type RecipeIngredientOut = {
  raw_string: string | null;
  quantity: number | null;
  unit: string | null;
  needs_review: boolean;
  ingredient_name: string | null;
  ingredient_name_fr: string | null;
  display_name: string | null;
  quantity_display: string;
  category: string | null;
};

export type InstructionStep = {
  text: string;
  image_url?: string | null;
};

export type RecipeDetail = RecipeListItem & {
  instructions_text: string | null;
  prep_time_minutes: number | null;
  ingredients: RecipeIngredientOut[];
  instruction_steps: InstructionStep[];
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
