export type DuplicateWarningInfo = {
  id: number;
  title: string;
  url: string;
  image_local_path: string | null;
  title_score: number;
  ingredient_score: number;
};

export type ScrapeResponse = {
  message: string;
  url: string;
  job_id?: number;
  status: "pending" | "running" | "completed" | "failed" | "duplicate_warning";
  similar_recipe?: DuplicateWarningInfo | null;
};

export type JobStatusResponse = {
  job_id: number;
  status: "pending" | "running" | "completed" | "failed" | "duplicate_warning";
  error_message?: string | null;
};

export type RecipeSimilarPair = {
  recipe_a_id: number;
  recipe_a_title: string;
  recipe_a_url: string;
  recipe_a_image: string | null;
  recipe_b_id: number;
  recipe_b_title: string;
  recipe_b_url: string;
  recipe_b_image: string | null;
  title_score: number;
  ingredient_score: number;
};

export type RecipeSimilarPairsResponse = {
  pairs: RecipeSimilarPair[];
};
