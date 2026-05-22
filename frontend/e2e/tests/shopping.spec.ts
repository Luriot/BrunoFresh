import { test, expect } from "@playwright/test";
import {
  mockAuthenticatedUser,
  mockRecipeEndpoints,
  mockListEndpoints,
} from "../helpers/mock-api";
import { mockShoppingList } from "../fixtures";

test.describe("Shopping List", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);
    // Mock item patch (used by toggle-owned / exclude)
    await page.route("**/api/lists/1/items/*", (route) =>
      route.fulfill({ json: {}, status: 200 })
    );
    // Mock history refetch after toggles
    await page.route("**/api/lists", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          json: [
            {
              id: 1,
              label: "My Weekly List",
              created_at: "2026-05-22T10:00:00Z",
              total_items: 4,
              already_owned_items: 1,
            },
          ],
        });
      } else {
        await route.continue();
      }
    });
  });

  test("displays items grouped into To Buy, Already Owned and Excluded", async ({ page }) => {
    await page.goto("/lists/1");

    await expect(page.getByText("To Buy")).toBeVisible();
    await expect(page.getByText("Already Owned")).toBeVisible();
    await expect(page.getByText("Excluded")).toBeVisible();

    // Items from fixtures
    await expect(page.getByText("spaghetti", { exact: true })).toBeVisible();       // toBuy
    await expect(page.getByText("ground beef")).toBeVisible();     // toBuy
    await expect(page.getByText("olive oil")).toBeVisible();       // alreadyOwned
    await expect(page.getByText("bay leaf")).toBeVisible();        // excluded
  });

  test("generate list from dashboard cart and navigate to list page", async ({ page }) => {
    // Override the POST /api/lists to return our mock list
    await page.route("**/api/lists", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ json: mockShoppingList, status: 201 });
      } else if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
      } else {
        await route.continue();
      }
    });

    await page.goto("/");
    // Add first recipe to cart
    await page.getByRole("button", { name: "Add to cart" }).first().click();
    await expect(page.getByRole("button", { name: "Generate list" })).toBeEnabled();

    await page.getByRole("button", { name: "Generate list" }).click();

    // Should navigate to the shopping list page
    await expect(page).toHaveURL(/\/lists\/1/);
    await expect(page.getByText("spaghetti", { exact: true })).toBeVisible();
  });

  test("mark item as owned moves it to Already Owned section", async ({ page }) => {
    await page.goto("/lists/1");
    // spaghetti and ground beef are both in To Buy — each has a "Mark as owned" button
    await expect(page.getByRole("button", { name: "Mark as owned" })).toHaveCount(2);

    // Click "Mark as owned" on first item (spaghetti)
    await page.getByRole("button", { name: "Mark as owned" }).first().click();

    // spaghetti moved to Already Owned — only ground beef's button remains
    await expect(page.getByRole("button", { name: "Mark as owned" })).toHaveCount(1);
  });

  test("exclude item moves it to Excluded section", async ({ page }) => {
    await page.goto("/lists/1");
    // spaghetti and ground beef are both in To Buy — each has an "Exclude item" button
    await expect(page.getByRole("button", { name: "Exclude item" })).toHaveCount(2);

    // Click "Exclude item" on first item (spaghetti)
    await page.getByRole("button", { name: "Exclude item" }).first().click();

    // spaghetti moved to Excluded — only ground beef's button remains
    await expect(page.getByRole("button", { name: "Exclude item" })).toHaveCount(1);
  });

  test("restore excluded item moves it back", async ({ page }) => {
    await page.goto("/lists/1");
    // bay leaf is the only excluded item — one "Restore item" button
    await expect(page.getByRole("button", { name: "Restore item" })).toHaveCount(1);

    await page.getByRole("button", { name: "Restore item" }).click();

    // bay leaf moved back to To Buy — no "Restore item" buttons remain
    await expect(page.getByRole("button", { name: "Restore item" })).toHaveCount(0);
  });

  test("copy list button changes to Copied!", async ({ page }) => {
    // Mock clipboard API so navigator.clipboard.writeText() doesn't throw in headless
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: async () => {} },
        writable: true,
      });
    });

    await page.goto("/lists/1");
    await expect(page.getByRole("button", { name: "Copy list" })).toBeVisible();

    await page.getByRole("button", { name: "Copy list" }).click();

    // The SVG icon's aria-label changes to "Copied!" — button accessible name changes
    await expect(page.getByRole("button", { name: "Copied!" })).toBeVisible();
  });
});
