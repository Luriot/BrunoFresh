import axios from "axios";
import type {
  CartInput,
  CartResponse,
  JobStatusResponse,
  RecipeCreate,
  RecipeDetail,
  RecipeListItem,
  ScrapeResponse,
  ShoppingList,
  ShoppingListCustomItemInput,
  ShoppingListItem,
  ShoppingListSummary,
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

export async function fetchRecipes() {
  const { data } = await api.get<RecipeListItem[]>("/recipes");
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
