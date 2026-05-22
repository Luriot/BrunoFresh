// Mock data fixtures for E2E tests — typed to match backend API responses.

export const mockUser = {
  id: 1,
  username: "testuser",
  role: "user" as const,
  avatar_url: null,
  language: "en",
};

export const mockAdmin = {
  id: 2,
  username: "adminuser",
  role: "admin" as const,
  avatar_url: null,
  language: "en",
};

export const mockTags = [
  { id: 1, name: "Vegetarian", color: "#4caf50" },
  { id: 2, name: "Quick", color: "#ff9800" },
  { id: 3, name: "Pasta", color: "#e91e63" },
];

export const mockRecipes = [
  {
    id: 1,
    title: "Spaghetti Bolognese",
    url: "https://example.com/spaghetti",
    source_domain: "example.com",
    image_local_path: null,
    image_original_url: null,
    image_url: null,
    base_servings: 4,
    prep_time_minutes: 30,
    is_favorite_by_me: false,
    recommenders: [],
    tags: [mockTags[2]],
  },
  {
    id: 2,
    title: "Tomato Soup",
    url: "https://example.com/soup",
    source_domain: "example.com",
    image_local_path: null,
    image_original_url: null,
    image_url: null,
    base_servings: 2,
    prep_time_minutes: 20,
    is_favorite_by_me: true,
    recommenders: [],
    tags: [mockTags[0], mockTags[1]],
  },
  {
    id: 3,
    title: "Caesar Salad",
    url: "https://example.com/salad",
    source_domain: "example.com",
    image_local_path: null,
    image_original_url: null,
    image_url: null,
    base_servings: 2,
    prep_time_minutes: 10,
    is_favorite_by_me: false,
    recommenders: [],
    tags: [],
  },
];

export const mockShoppingListItems = [
  {
    id: 1,
    name: "spaghetti",
    name_fr: "spaghetti",
    display_name: "spaghetti",
    quantity: 400,
    quantity_display: "400",
    unit: "g",
    category: "Pantry",
    is_custom: false,
    is_already_owned: false,
    is_excluded: false,
  },
  {
    id: 2,
    name: "ground beef",
    name_fr: "boeuf haché",
    display_name: "ground beef",
    quantity: 500,
    quantity_display: "500",
    unit: "g",
    category: "Meat",
    is_custom: false,
    is_already_owned: false,
    is_excluded: false,
  },
  {
    id: 3,
    name: "olive oil",
    name_fr: "huile d'olive",
    display_name: "olive oil",
    quantity: 2,
    quantity_display: "2",
    unit: "tbsp",
    category: "Pantry",
    is_custom: false,
    is_already_owned: true,
    is_excluded: false,
  },
  {
    id: 4,
    name: "bay leaf",
    name_fr: "feuille de laurier",
    display_name: "bay leaf",
    quantity: 1,
    quantity_display: "1",
    unit: "",
    category: "Spices",
    is_custom: false,
    is_already_owned: false,
    is_excluded: true,
  },
];

export const mockShoppingList = {
  id: 1,
  label: "My Weekly List",
  created_at: "2026-05-22T10:00:00Z",
  updated_at: "2026-05-22T10:00:00Z",
  items: mockShoppingListItems,
  recipes: [
    {
      recipe_id: 1,
      title: "Spaghetti Bolognese",
      url: "https://example.com/spaghetti",
      source_domain: "example.com",
      image_local_path: null,
      image_url: null,
      target_servings: 4,
    },
  ],
  needs_review: [],
};

export const mockShoppingListSummaries = [
  {
    id: 1,
    label: "My Weekly List",
    created_at: "2026-05-22T10:00:00Z",
    total_items: 4,
    already_owned_items: 1,
  },
];

export const mockMealPlanSummaries = [
  {
    id: 1,
    label: "Week of May 22",
    week_start_date: "2026-05-22",
    created_at: "2026-05-22T09:00:00Z",
    entry_count: 3,
    preview_images: [null, null, null],
  },
  {
    id: 2,
    label: "Vacation meals",
    week_start_date: null,
    created_at: "2026-05-20T09:00:00Z",
    entry_count: 2,
    preview_images: [null, null],
  },
];

export const mockPantryItems = [
  {
    id: 1,
    name: "olive oil",
    name_fr: "huile d'olive",
    display_name: "olive oil",
    ingredient_id: 10,
    category: "Pantry",
    added_at: "2026-05-20T08:00:00Z",
  },
  {
    id: 2,
    name: "salt",
    name_fr: "sel",
    display_name: "salt",
    ingredient_id: 11,
    category: "Spices",
    added_at: "2026-05-20T08:01:00Z",
  },
];

export const mockAdminIngredients = [
  {
    id: 10,
    name_en: "olive oil",
    name_fr: "huile d'olive",
    category: "Pantry",
    is_normalized: true,
    needs_review: false,
    usage_count: 5,
    translations: { en: "olive oil", fr: "huile d'olive" },
  },
  {
    id: 11,
    name_en: "salt",
    name_fr: "sel",
    category: "Spices",
    is_normalized: true,
    needs_review: true,
    usage_count: 12,
    translations: { en: "salt", fr: "sel" },
  },
];
