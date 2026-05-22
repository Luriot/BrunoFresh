import type { Page } from "@playwright/test";
import {
  mockUser,
  mockAdmin,
  mockRecipes,
  mockShoppingList,
  mockShoppingListSummaries,
  mockMealPlanSummaries,
  mockPantryItems,
  mockTags,
  mockAdminIngredients,
} from "../fixtures";

/** Mock GET /api/auth/me to return a regular user. */
export async function mockAuthenticatedUser(page: Page) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ json: mockUser })
  );
  await page.route("**/api/auth/logout", (route) =>
    route.fulfill({ json: {}, status: 200 })
  );
}

/** Mock GET /api/auth/me to return an admin user. */
export async function mockAuthenticatedAdmin(page: Page) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ json: mockAdmin })
  );
  await page.route("**/api/auth/logout", (route) =>
    route.fulfill({ json: {}, status: 200 })
  );
}

/** Mock GET /api/auth/me to return 401 (unauthenticated). */
export async function mockUnauthenticated(page: Page) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 401, json: { detail: "Not authenticated" } })
  );
}

/** Mock POST /api/auth/login to succeed. */
export async function mockLoginSuccess(page: Page) {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({ json: mockUser })
  );
}

/** Mock POST /api/auth/login to return 401 (invalid credentials). */
export async function mockLoginFailure(page: Page) {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({ status: 401, json: { detail: "Invalid credentials" } })
  );
}

/** Mock all recipe-related endpoints. */
export async function mockRecipeEndpoints(page: Page) {
  await page.route("**/api/recipes*", (route) =>
    route.fulfill({ json: mockRecipes })
  );
  await page.route("**/api/tags*", (route) =>
    route.fulfill({ json: mockTags })
  );
}

/** Mock all shopping list endpoints. */
export async function mockListEndpoints(page: Page) {
  await page.route("**/api/lists", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockShoppingListSummaries });
    } else if (route.request().method() === "POST") {
      await route.fulfill({ json: mockShoppingList, status: 201 });
    } else {
      await route.continue();
    }
  });
  await page.route(`**/api/lists/${mockShoppingList.id}`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockShoppingList });
    } else {
      await route.continue();
    }
  });
}

/** Mock meal plan endpoints. */
export async function mockMealPlanEndpoints(page: Page) {
  await page.route("**/api/meal-plans", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockMealPlanSummaries });
    } else if (route.request().method() === "POST") {
      const newPlan = {
        id: 99,
        label: null,
        week_start_date: null,
        created_at: "2026-05-22T12:00:00Z",
        entries: [],
      };
      await route.fulfill({ json: newPlan, status: 201 });
    } else {
      await route.continue();
    }
  });
  // Support DELETE /api/meal-plans/:id
  await page.route("**/api/meal-plans/*", async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204, body: "" });
    } else if (route.request().method() === "GET") {
      await route.fulfill({ json: mockMealPlanSummaries[0] });
    } else {
      await route.continue();
    }
  });
}

/** Mock pantry endpoints. */
export async function mockPantryEndpoints(page: Page) {
  await page.route("**/api/pantry", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockPantryItems });
    } else if (route.request().method() === "POST") {
      const newItem = {
        id: 99,
        name: "new item",
        name_fr: null,
        display_name: "new item",
        ingredient_id: null,
        category: "Other",
        added_at: "2026-05-22T12:00:00Z",
      };
      await route.fulfill({ json: newItem, status: 201 });
    } else {
      await route.continue();
    }
  });
  await page.route("**/api/pantry/*", async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204, body: "" });
    } else {
      await route.continue();
    }
  });
}

/** Mock admin endpoints. */
export async function mockAdminEndpoints(page: Page) {
  await page.route("**/api/admin/ingredients*", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockAdminIngredients });
    } else {
      await route.continue();
    }
  });
  await page.route("**/api/tags", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: mockTags });
    } else if (route.request().method() === "POST") {
      const newTag = { id: 99, name: "New Tag", color: "#9c27b0" };
      await route.fulfill({ json: newTag, status: 201 });
    } else {
      await route.continue();
    }
  });
  await page.route("**/api/tags/*", async (route) => {
    if (route.request().method() === "DELETE") {
      await route.fulfill({ status: 204, body: "" });
    } else {
      await route.continue();
    }
  });
  // Note: **/api/recipes* is already handled by mockRecipeEndpoints (called in beforeEach).
  // Do NOT re-register it here — the LIFO override would swallow non-GET method checks.
}
