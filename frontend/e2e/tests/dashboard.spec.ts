import { test, expect } from "@playwright/test";
import {
  mockAuthenticatedUser,
  mockRecipeEndpoints,
  mockListEndpoints,
} from "../helpers/mock-api";
import { mockRecipes } from "../fixtures";

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);
  });

  test("renders recipe cards with titles", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Spaghetti Bolognese")).toBeVisible();
    await expect(page.getByText("Tomato Soup")).toBeVisible();
    await expect(page.getByText("Caesar Salad")).toBeVisible();
  });

  test("search filter sends query to API", async ({ page }) => {
    let lastSearchQuery = "";

    await page.route("**/api/recipes*", async (route) => {
      const url = new URL(route.request().url());
      const q = url.searchParams.get("q") ?? "";
      if (q) {
        lastSearchQuery = q;
        await route.fulfill({ json: [mockRecipes[0]] });
      } else {
        await route.fulfill({ json: mockRecipes });
      }
    });

    await page.goto("/");
    await expect(page.getByText("Spaghetti Bolognese")).toBeVisible();

    await page.getByPlaceholder("Search recipes...").fill("pasta");
    // Wait for the debounced API call to resolve instead of using an arbitrary sleep
    await page.waitForResponse("**/api/recipes*");

    expect(lastSearchQuery).toBe("pasta");
    // Only the Bolognese should remain visible
    await expect(page.getByText("Spaghetti Bolognese")).toBeVisible();
    await expect(page.getByText("Caesar Salad")).not.toBeVisible();
  });

  test("favorites filter shows only favorite recipes", async ({ page }) => {
    await page.route("**/api/recipes*", async (route) => {
      const url = new URL(route.request().url());
      const isFav = url.searchParams.get("is_favorite");
      if (isFav === "true") {
        await route.fulfill({ json: [mockRecipes[1]] }); // Tomato Soup is favorite
      } else {
        await route.fulfill({ json: mockRecipes });
      }
    });

    await page.goto("/");
    await expect(page.getByText("Spaghetti Bolognese")).toBeVisible();

    await page.getByRole("button", { name: "Favorites", exact: true }).click();

    await expect(page.getByText("Tomato Soup")).toBeVisible();
    await expect(page.getByText("Spaghetti Bolognese")).not.toBeVisible();
  });

  test("add recipe to cart shows it in CartPanel", async ({ page }) => {
    await page.goto("/");

    // Click the first "Add to cart" button (Spaghetti Bolognese card)
    await page.getByRole("button", { name: "Add to cart" }).first().click();

    // Cart panel should show the recipe title
    await expect(page.getByRole("complementary").getByText("Spaghetti Bolognese")).toBeVisible();
    // "Generate list" button should be enabled
    await expect(page.getByRole("button", { name: "Generate list" })).toBeEnabled();
  });

  test("clear cart empties the CartPanel", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Add to cart" }).first().click();
    await expect(page.getByRole("button", { name: "Generate list" })).toBeEnabled();

    await page.getByRole("button", { name: "Clear cart" }).click();

    // Cart should show empty state
    await expect(page.getByText("No recipes selected yet.")).toBeVisible();
  });

  test("tag badge is displayed on recipe card", async ({ page }) => {
    await page.goto("/");

    // "Pasta" tag is on Spaghetti Bolognese
    await expect(page.getByText("Pasta").first()).toBeVisible();
  });

  test("HelloFresh Discovery tab is accessible", async ({ page }) => {
    await page.route("**/api/hellofresh/search*", (route) =>
      route.fulfill({ json: [] })
    );

    await page.goto("/");
    await page.getByText("HF Discovery").click();

    // The HF search input should appear
    await expect(page.getByPlaceholder("Search a HelloFresh recipe...")).toBeVisible();
  });
});
