export type IngredientDetail = {
  id: number;
  name_en: string;
  name_fr: string | null;
  category: string | null;
  is_normalized: boolean;
  needs_review: boolean;
  usage_count: number;
  translations: Record<string, string>;
};

export type MergeSuggestion = {
  source_id: number;
  source_name: string;
  target_id: number;
  target_name: string;
  reason: string;
};

export type MergeSuggestionResponse = {
  suggestions: MergeSuggestion[];
};
