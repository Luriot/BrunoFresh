import axios from "axios";
import type { CartInput, CartResponse, RecipeListItem } from "../types";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

export async function fetchRecipes() {
  const { data } = await api.get<RecipeListItem[]>("/recipes");
  return data;
}

export async function queueScrape(url: string) {
  const { data } = await api.post<{ message: string; url: string }>("/scrape", { url });
  return data;
}

export async function generateCart(items: CartInput[]) {
  const { data } = await api.post<CartResponse>("/cart/generate", { items });
  return data;
}
