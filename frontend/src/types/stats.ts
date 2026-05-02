export type RecipeSourceStat = { source_domain: string; count: number };
export type TopRecipeStat = { recipe_id: number; title: string; appearance_count: number };
export type TopIngredientStat = { name: string; count: number };

export type StatsOut = {
  total_recipes: number;
  total_lists: number;
  recipes_by_source: RecipeSourceStat[];
  top_recipes_in_lists: TopRecipeStat[];
  top_ingredients: TopIngredientStat[];
};
