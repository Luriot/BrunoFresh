import axios from "axios";
import type {
  CartInput,
  CartResponse,
  IngredientDetail,
  JobStatusResponse,
  MealPlan,
  MealPlanEntry,
  MealPlanSummary,
  PantryItem,
  RecipeCreate,
  RecipeDetail,
  RecipeListItem,
  ScrapeResponse,
  ShoppingList,
  ShoppingListCustomItemInput,
  ShoppingListItem,
  ShoppingListSummary,
  StatsOut,
  Tag,
} from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "";

let unauthorizedHandler: (() => void) | null = null;

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const endpoint = String(error?.config?.url ?? "");
    if (status === 401 && !endpoint.includes("/auth/login")) {
      unauthorizedHandler?.();
    }
    return Promise.reject(error);
  }
);

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export function buildImageUrl(path: string): string {
  const normalized = path.replace(/^\/+/, "");
  const fileName = normalized.split("/").pop() || normalized;
  return `${API_BASE_URL}/api/images/${encodeURIComponent(fileName)}`;
}

export function buildJobStreamUrl(jobId: number): string {
  return `${API_BASE_URL}/api/jobs/${jobId}/stream`;
}

export async function loginWithPasscode(passcode: string): Promise<void> {
  await api.post("/auth/login", { passcode });
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function verifySession(): Promise<boolean> {
  const { data } = await api.get<{ authenticated: boolean }>("/auth/me");
  return Boolean(data.authenticated);
}

export async function fetchRecipes(params?: {
  q?: string;
  source?: string;
  is_favorite?: boolean;
  ingredients?: string;
  tags?: string;
  limit?: number;
  offset?: number;
}) {
  const { data } = await api.get<RecipeListItem[]>("/recipes", { params });
  return data;
}

export async function fetchRecipeDetail(id: number) {
  const { data } = await api.get<RecipeDetail>(`/recipes/${id}`);
  return data;
}

export async function createCustomRecipe(payload: RecipeCreate) {
  const { data } = await api.post<RecipeDetail>("/recipes", payload);
  return data;
}

export async function queueScrape(url: string) {
  const { data } = await api.post<ScrapeResponse>("/scrape", { url });
  return data;
}

export async function getJobStatus(jobId: number) {
  const { data } = await api.get<JobStatusResponse>(`/jobs/${jobId}`);
  return data;
}

export async function generateCart(items: CartInput[]) {
  const { data } = await api.post<CartResponse>("/cart/generate", { items });
  return data;
}

export async function createShoppingList(items: CartInput[], label?: string) {
  const { data } = await api.post<ShoppingList>("/lists", { items, label });
  return data;
}

export async function fetchShoppingLists() {
  const { data } = await api.get<ShoppingListSummary[]>("/lists");
  return data;
}

export async function fetchShoppingList(listId: number) {
  const { data } = await api.get<ShoppingList>(`/lists/${listId}`);
  return data;
}

export async function patchShoppingList(listId: number, label: string | null) {
  const { data } = await api.patch<ShoppingList>(`/lists/${listId}`, { label });
  return data;
}

export async function deleteShoppingList(listId: number) {
  await api.delete(`/lists/${listId}`);
}

export async function patchShoppingListItem(listId: number, itemId: number, isAlreadyOwned: boolean) {
  const { data } = await api.patch<ShoppingListItem>(`/lists/${listId}/items/${itemId}`, {
    is_already_owned: isAlreadyOwned,
  });
  return data;
}

export async function addShoppingListCustomItem(listId: number, payload: ShoppingListCustomItemInput) {
  const { data } = await api.post<ShoppingListItem>(`/lists/${listId}/items`, payload);
  return data;
}

export async function deleteShoppingListItem(listId: number, itemId: number) {
  await api.delete(`/lists/${listId}/items/${itemId}`);
}

// ── Recipes extras ────────────────────────────────────────────────────────

export async function patchRecipe(id: number, payload: { is_favorite?: boolean; instructions_text?: string }) {
  const { data } = await api.patch<RecipeDetail>(`/recipes/${id}`, payload);
  return data;
}

export async function setRecipeTags(recipeId: number, tagIds: number[]) {
  const { data } = await api.put<RecipeDetail>(`/recipes/${recipeId}/tags`, { tag_ids: tagIds });
  return data;
}

export async function fetchSimilarRecipes(recipeId: number, limit = 5) {
  const { data } = await api.get<RecipeListItem[]>(`/recipes/${recipeId}/similar`, { params: { limit } });
  return data;
}

export async function rescrapeRecipe(recipeId: number) {
  const { data } = await api.post<ScrapeResponse>(`/recipes/${recipeId}/rescrape`);
  return data;
}

export async function formatRecipeInstructions(recipeId: number) {
  const { data } = await api.post<RecipeDetail>(`/recipes/${recipeId}/format-instructions`);
  return data;
}

// ── Tags ──────────────────────────────────────────────────────────────────

export async function fetchTags() {
  const { data } = await api.get<Tag[]>("/tags");
  return data;
}

export async function createTag(name: string, color?: string) {
  const { data } = await api.post<Tag>("/tags", { name, color });
  return data;
}

export async function deleteTag(tagId: number) {
  await api.delete(`/tags/${tagId}`);
}

// ── Pantry ────────────────────────────────────────────────────────────────

export async function fetchPantry() {
  const { data } = await api.get<PantryItem[]>("/pantry");
  return data;
}

export async function addPantryItem(payload: { name: string; name_fr?: string; ingredient_id?: number; category?: string }) {
  const { data } = await api.post<PantryItem>("/pantry", payload);
  return data;
}

export async function removePantryItem(itemId: number) {
  await api.delete(`/pantry/${itemId}`);
}

// ── Stats ─────────────────────────────────────────────────────────────────

export async function fetchStats() {
  const { data } = await api.get<StatsOut>("/admin/stats");
  return data;
}

// ── Meal Plans ────────────────────────────────────────────────────────────

export async function fetchMealPlans() {
  const { data } = await api.get<MealPlanSummary[]>("/meal-plans");
  return data;
}

export async function createMealPlan(payload: { label?: string; week_start_date?: string }) {
  const { data } = await api.post<MealPlan>("/meal-plans", payload);
  return data;
}

export async function fetchMealPlan(planId: number) {
  const { data } = await api.get<MealPlan>(`/meal-plans/${planId}`);
  return data;
}

export async function deleteMealPlan(planId: number) {
  await api.delete(`/meal-plans/${planId}`);
}

export async function addMealPlanEntry(planId: number, payload: {
  recipe_id: number;
  day_of_week: number;
  meal_slot?: string;
  target_servings: number;
}) {
  const { data } = await api.post<MealPlanEntry>(`/meal-plans/${planId}/entries`, payload);
  return data;
}

export async function deleteMealPlanEntry(planId: number, entryId: number) {
  await api.delete(`/meal-plans/${planId}/entries/${entryId}`);
}

export async function generateListFromMealPlan(planId: number) {
  const { data } = await api.post<ShoppingList>(`/meal-plans/${planId}/generate-list`);
  return data;
}

// ── Admin: ingredients ────────────────────────────────────────────────────

export async function fetchIngredientsAdmin(params?: { q?: string; needs_review?: boolean; limit?: number; offset?: number }) {
  const { data } = await api.get<IngredientDetail[]>("/admin/ingredients", { params });
  return data;
}

export async function patchIngredient(id: number, payload: { name_en: string; name_fr?: string; category: string }) {
  const { data } = await api.patch<IngredientDetail>(`/ingredients/${id}`, payload);
  return data;
}

export async function mergeIngredients(sourceId: number, targetId: number) {
  const { data } = await api.post<IngredientDetail>("/admin/ingredients/merge", { source_id: sourceId, target_id: targetId });
  return data;
}
