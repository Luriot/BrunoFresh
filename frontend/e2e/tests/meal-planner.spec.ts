import { test, expect } from "@playwright/test";
import {
  mockAuthenticatedUser,
  mockRecipeEndpoints,
  mockListEndpoints,
  mockMealPlanEndpoints,
} from "../helpers/mock-api";
import { mockMealPlanSummaries } from "../fixtures";

test.describe("Meal Planner", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);
    await mockMealPlanEndpoints(page);
  });

  test("shows empty state when no meal plans exist", async ({ page }) => {
    // Override the meal plans endpoint to return empty list
    await page.route("**/api/meal-plans", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
      } else {
        await route.continue();
      }
    });

    await page.goto("/planner");

    await expect(page.getByText("No meal plans yet...")).toBeVisible();
    // The "+ New plan" button should still be shown in the empty state
    await expect(page.getByRole("button", { name: /New plan/ }).first()).toBeVisible();
  });

  test("lists existing meal plans with title and meal count", async ({ page }) => {
    await page.goto("/planner");

    await expect(page.getByText("Week of May 22")).toBeVisible();
    await expect(page.getByText("Vacation meals")).toBeVisible();
    await expect(page.getByText("(3 meals)")).toBeVisible();
    await expect(page.getByText("(2 meals)")).toBeVisible();
  });

  test("create new plan navigates to plan detail page", async ({ page }) => {
    // Mock the detail page endpoint that MealPlanDetailPage will load
    await page.route("**/api/meal-plans/99", (route) =>
      route.fulfill({
        json: {
          id: 99,
          label: null,
          week_start_date: null,
          created_at: "2026-05-22T12:00:00Z",
          entries: [],
        },
      })
    );

    await page.goto("/planner");

    // Click the header "+ New plan" button (not the empty-state one)
    await page.getByRole("button", { name: /New plan/ }).first().click();

    // Should navigate to /planner/99
    await expect(page).toHaveURL(/\/planner\/99/, { timeout: 5000 });
  });

  test("delete plan removes it from the list", async ({ page }) => {
    // Accept the confirm() dialog
    page.on("dialog", (dialog) => dialog.accept());

    // Override the plans endpoint: React StrictMode fires 2 GET requests on
    // initial mount, so the first 2 GET requests return both plans; subsequent
    // requests (after delete + page.goto re-mount) return only plan 2.
    let requestCount = 0;
    await page.route("**/api/meal-plans", async (route) => {
      if (route.request().method() === "GET") {
        requestCount++;
        if (requestCount <= 2) {
          await route.fulfill({ json: mockMealPlanSummaries });
        } else {
          await route.fulfill({ json: [mockMealPlanSummaries[1]] });
        }
      } else {
        await route.continue();
      }
    });

    await page.goto("/planner");
    await expect(page.getByText("Week of May 22")).toBeVisible();

    // Force-click the delete button (bypasses opacity-0 visibility check)
    await page.getByRole("button", { name: "delete" }).first().click({ force: true });

    // Navigate back in case the app navigated to a plan detail page
    await page.goto("/planner");

    // Plan 1 should be gone; Plan 2 should remain
    await expect(page.getByText("Week of May 22")).not.toBeVisible();
    await expect(page.getByText("Vacation meals")).toBeVisible();
  });

  test("Meal Planner title and page heading are visible", async ({ page }) => {
    await page.goto("/planner");

    await expect(page.getByRole("heading", { name: "Meal Planner" })).toBeVisible();
    // "Create a planning" quick-generate button
    await expect(page.getByRole("button", { name: "Create a planning" })).toBeVisible();
  });
});
