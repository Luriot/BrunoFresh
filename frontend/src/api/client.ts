import type {
  CartInput,
  HFSearchResult,
  IngredientDetail,
  MealPlan,
  MealPlanEntry,
  MealPlanSummary,
  MergeSuggestionResponse,
  PantryItem,
  RecipeCreate,
  RecipeDetail,
  RecipeListItem,
  RecipeSimilarPairsResponse,
  ScrapeResponse,
  ShoppingList,
  ShoppingListCustomItemInput,
  ShoppingListItem,
  ShoppingListSummary,
  Tag,
  User,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export { API_BASE_URL };

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string | null,
  ) {
    super(detail ?? `HTTP ${status}`);
    this.name = "ApiError";
  }
}

type Options = {
  params?: Record<string, unknown>;
  body?: unknown;
  form?: FormData;
};

function queryString(params?: Record<string, unknown>): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) sp.set(key, String(value));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function callApi(method: string, path: string, opts: Options = {}): Promise<Response> {
  const res = await fetch(`${API_BASE_URL}/api${path}${queryString(opts.params)}`, {
    method,
    credentials: "include",
    headers: opts.form ? undefined : opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  });
  if (res.status === 401 && !path.includes("/auth/login") && !path.includes("/auth/me")) {
    unauthorizedHandler?.();
  }
  if (!res.ok) {
    const data: unknown = await res.json().catch(() => null);
    const detail =
      data && typeof data === "object" && typeof (data as { detail?: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : null;
    throw new ApiError(res.status, detail);
  }
  return res;
}

async function request<T>(method: string, path: string, opts: Options = {}): Promise<T> {
  const res = await callApi(method, path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function buildJobStreamUrl(jobId: number): string {
  return `${API_BASE_URL}/api/jobs/${jobId}/stream`;
}

// ── Auth / profile ──────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<User> {
  return request<User>("POST", "/auth/login", { body: { username, password } });
}

export async function logout(): Promise<void> {
  await request("POST", "/auth/logout");
}

export async function fetchMe(): Promise<User | null> {
  try {
    return await request<User>("GET", "/auth/me");
  } catch {
    return null;
  }
}

export async function patchLanguage(language: string): Promise<User> {
  return request<User>("PATCH", "/users/me/language", { body: { language } });
}

export async function patchMe(payload: {
  username?: string;
  current_password: string;
  new_password?: string;
}): Promise<User> {
  return request<User>("PATCH", "/users/me", { body: payload });
}

export async function uploadAvatar(file: File): Promise<User> {
  const form = new FormData();
  form.append("file", file);
  return request<User>("POST", "/users/me/avatar", { form });
}

// ── Recipes ─────────────────────────────────────────────────────────────────

export async function fetchRecipes(params?: {
  q?: string;
  source?: string;
  is_favorite?: boolean;
  ingredients?: string;
  tags?: string;
  limit?: number;
  offset?: number;
}) {
  return request<RecipeListItem[]>("GET", "/recipes", { params });
}

export async function fetchRecipeDetail(id: number) {
  return request<RecipeDetail>("GET", `/recipes/${id}`);
}

export async function createCustomRecipe(payload: RecipeCreate) {
  return request<RecipeDetail>("POST", "/recipes", { body: payload });
}

export async function uploadRecipeImage(recipeId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<RecipeDetail>("POST", `/recipes/${recipeId}/image`, { form });
}

export async function retryRecipeImage(recipeId: number) {
  return request<{ recipe_id: number; success: boolean; image_local_path: string | null; error: string | null }>(
    "POST",
    `/admin/recipes/${recipeId}/retry-image`,
  );
}

export async function retryAllMissingImages() {
  return request<{ retried: number; success: number; failed: { recipe_id: number; success: boolean; error: string | null }[] }>(
    "POST",
    "/admin/recipes/retry-images",
  );
}

export async function convertImagesToWebp() {
  return request<{ converted: number; skipped: number; failed: number }>(
    "POST",
    "/admin/recipes/convert-images-to-webp",
  );
}

export async function convertSingleImageToWebp(recipeId: number) {
  return request<{ converted: number; skipped: number; failed: number; image_local_path: string | null }>(
    "POST",
    `/admin/recipes/${recipeId}/convert-image-to-webp`,
  );
}

export async function queueScrape(url: string, force = false) {
  return request<ScrapeResponse>("POST", "/scrape", { body: { url, force } });
}

export async function searchHelloFresh(query: string): Promise<HFSearchResult[]> {
  return request<HFSearchResult[]>("GET", "/hellofresh/search", { params: { q: query } });
}

// ── Shopping lists ──────────────────────────────────────────────────────────

export async function createShoppingList(items: CartInput[], label?: string) {
  return request<ShoppingList>("POST", "/lists", { body: { items, label } });
}

export async function fetchShoppingLists() {
  return request<ShoppingListSummary[]>("GET", "/lists");
}

export async function fetchShoppingList(listId: number) {
  return request<ShoppingList>("GET", `/lists/${listId}`);
}

export async function patchShoppingList(listId: number, label: string | null) {
  return request<ShoppingList>("PATCH", `/lists/${listId}`, { body: { label } });
}

export async function deleteShoppingList(listId: number) {
  await request("DELETE", `/lists/${listId}`);
}

export async function patchShoppingListItem(
  listId: number,
  itemId: number,
  patch: { is_already_owned?: boolean; is_excluded?: boolean },
) {
  return request<ShoppingListItem>("PATCH", `/lists/${listId}/items/${itemId}`, { body: patch });
}

export async function addShoppingListCustomItem(listId: number, payload: ShoppingListCustomItemInput) {
  return request<ShoppingListItem>("POST", `/lists/${listId}/items`, { body: payload });
}

export async function deleteShoppingListItem(listId: number, itemId: number) {
  await request("DELETE", `/lists/${listId}/items/${itemId}`);
}

// ── Recipes extras ────────────────────────────────────────────────────────

export async function patchRecipe(id: number, payload: { instructions_text?: string; prep_time_minutes?: number }) {
  return request<RecipeDetail>("PATCH", `/recipes/${id}`, { body: payload });
}

export async function toggleFavorite(id: number): Promise<{ is_favorite_by_me: boolean }> {
  return request<{ is_favorite_by_me: boolean }>("POST", `/recipes/${id}/favorite`);
}

export async function deleteRecipe(id: number) {
  await request("DELETE", `/recipes/${id}`);
}

export async function setRecipeTags(recipeId: number, tagIds: number[]) {
  return request<RecipeDetail>("PUT", `/recipes/${recipeId}/tags`, { body: { tag_ids: tagIds } });
}

export async function fetchSimilarRecipes(recipeId: number, limit = 5) {
  return request<RecipeListItem[]>("GET", `/recipes/${recipeId}/similar`, { params: { limit } });
}

export async function rescrapeRecipe(recipeId: number) {
  return request<ScrapeResponse>("POST", `/recipes/${recipeId}/rescrape`);
}

export async function formatRecipeInstructions(recipeId: number) {
  return request<RecipeDetail>("POST", `/recipes/${recipeId}/format-instructions`);
}

// ── Tags ──────────────────────────────────────────────────────────────────

export async function fetchTags() {
  return request<Tag[]>("GET", "/tags");
}

export async function createTag(name: string, color?: string) {
  return request<Tag>("POST", "/tags", { body: { name, color } });
}

export async function deleteTag(tagId: number) {
  await request("DELETE", `/tags/${tagId}`);
}

// ── Pantry ────────────────────────────────────────────────────────────────

export async function fetchPantry() {
  return request<PantryItem[]>("GET", "/pantry");
}

export async function addPantryItem(payload: { name: string; lang: string; ingredient_id?: number; category?: string }) {
  return request<PantryItem>("POST", "/pantry", { body: payload });
}

export async function removePantryItem(itemId: number) {
  await request("DELETE", `/pantry/${itemId}`);
}

// ── Meal Plans ────────────────────────────────────────────────────────────

export async function fetchMealPlans() {
  return request<MealPlanSummary[]>("GET", "/meal-plans");
}

export async function createMealPlan(payload: { label?: string; week_start_date?: string }) {
  return request<MealPlan>("POST", "/meal-plans", { body: payload });
}

export async function generateQuickPlan(payload: {
  tag_id: number;
  label?: string;
  week_start_date?: string;
  meal_slot?: string;
  days?: number;
  target_servings?: number;
}) {
  return request<MealPlan>("POST", "/meal-plans/quick-generate", { body: payload });
}

export async function fetchMealPlan(planId: number) {
  return request<MealPlan>("GET", `/meal-plans/${planId}`);
}

export async function deleteMealPlan(planId: number) {
  await request("DELETE", `/meal-plans/${planId}`);
}

export async function addMealPlanEntry(planId: number, payload: {
  recipe_id: number;
  day_of_week: number;
  meal_slot?: string;
  target_servings: number;
}) {
  return request<MealPlanEntry>("POST", `/meal-plans/${planId}/entries`, { body: payload });
}

export async function deleteMealPlanEntry(planId: number, entryId: number) {
  await request("DELETE", `/meal-plans/${planId}/entries/${entryId}`);
}

export async function patchMealPlanEntry(planId: number, entryId: number, payload: { target_servings: number }) {
  return request<MealPlanEntry>("PATCH", `/meal-plans/${planId}/entries/${entryId}`, { body: payload });
}

export async function patchMealPlan(planId: number, payload: { label: string | null }) {
  return request<MealPlan>("PATCH", `/meal-plans/${planId}`, { body: payload });
}

export async function generateListFromMealPlan(planId: number) {
  return request<ShoppingList>("POST", `/meal-plans/${planId}/generate-list`);
}

// ── Admin: ingredients ────────────────────────────────────────────────────

export async function fetchIngredientsAdmin(params?: { q?: string; needs_review?: boolean; limit?: number; offset?: number; sort_by?: string; sort_order?: "asc" | "desc" }) {
  return request<IngredientDetail[]>("GET", "/admin/ingredients", { params });
}

export async function deleteIngredient(id: number) {
  await request("DELETE", `/admin/ingredients/${id}`);
}

export async function patchIngredient(id: number, payload: { name: string; lang: string; category: string }) {
  return request<IngredientDetail>("PATCH", `/ingredients/${id}`, { body: payload });
}

export async function mergeIngredients(sourceId: number, targetId: number) {
  return request<IngredientDetail>("POST", "/admin/ingredients/merge", { body: { source_id: sourceId, target_id: targetId } });
}

export async function findDuplicateRecipes() {
  return request<RecipeSimilarPairsResponse>("POST", "/admin/recipes/find-duplicates");
}

export async function suggestIngredientMerges() {
  return request<MergeSuggestionResponse>("POST", "/admin/ingredients/ai-suggest-merges");
}

// ── Admin: database ───────────────────────────────────────────────────────

export async function exportDb(): Promise<Blob> {
  const res = await callApi("GET", "/admin/db/export");
  return res.blob();
}

export async function backupDb(): Promise<{ filename: string }> {
  return request<{ filename: string }>("POST", "/admin/db/backup");
}

export async function importDb(file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await request("POST", "/admin/db/import", { form });
}
