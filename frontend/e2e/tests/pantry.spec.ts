import { test, expect } from "@playwright/test";
import {
  mockAuthenticatedUser,
  mockRecipeEndpoints,
  mockListEndpoints,
  mockPantryEndpoints,
} from "../helpers/mock-api";

test.describe("Pantry", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);
    await mockPantryEndpoints(page);
  });

  test("shows pantry title and subtitle", async ({ page }) => {
    await page.goto("/pantry");

    await expect(page.getByRole("heading", { name: "My Pantry" })).toBeVisible();
    await expect(
      page.getByText("Ingredients already at home")
    ).toBeVisible();
  });

  test("shows empty pantry message when no items", async ({ page }) => {
    await page.route("**/api/pantry", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
      } else {
        await route.continue();
      }
    });

    await page.goto("/pantry");

    await expect(page.getByText("Your pantry is empty.")).toBeVisible();
  });

  test("renders existing pantry items", async ({ page }) => {
    await page.goto("/pantry");

    await expect(page.getByText("olive oil")).toBeVisible();
    await expect(page.getByText("salt")).toBeVisible();
  });

  test("add item to pantry shows it in the list", async ({ page }) => {
    let addedName = "";
    await page.route("**/api/pantry", async (route) => {
      if (route.request().method() === "POST") {
        const body = await route.request().postDataJSON();
        addedName = body.name;
        await route.fulfill({
          json: {
            id: 99,
            name: body.name,
            name_fr: null,
            display_name: body.name,
            ingredient_id: null,
            category: "Other",
            added_at: "2026-05-22T12:00:00Z",
          },
          status: 201,
        });
      } else if (route.request().method() === "GET") {
        await route.fulfill({
          json: [
            {
              id: 1,
              name: "olive oil",
              name_fr: "huile d'olive",
              display_name: "olive oil",
              ingredient_id: 10,
              category: "Pantry",
              added_at: "2026-05-20T08:00:00Z",
            },
          ],
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/pantry");

    await page.getByPlaceholder("Ingredient name").fill("garlic");
    await page.getByRole("button", { name: "Add to pantry" }).click();

    expect(addedName).toBe("garlic");
    await expect(page.getByText("garlic")).toBeVisible();
  });

  test("remove item from pantry makes it disappear", async ({ page }) => {
    await page.goto("/pantry");

    await expect(page.getByText("olive oil")).toBeVisible();

    // Click the remove button for olive oil (first item)
    await page.getByRole("button", { name: "Remove" }).first().click();

    await expect(page.getByText("olive oil")).not.toBeVisible();
  });

  test("items are grouped by category", async ({ page }) => {
    await page.goto("/pantry");

    // Pantry and Spices categories from fixtures — match the <h2> category headings
    await expect(page.getByRole("heading", { name: "Pantry", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Spices", exact: true })).toBeVisible();
  });
});
