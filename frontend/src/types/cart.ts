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
