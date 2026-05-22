import { test, expect } from "@playwright/test";
import {
  mockAuthenticatedUser,
  mockAuthenticatedAdmin,
  mockRecipeEndpoints,
  mockListEndpoints,
  mockAdminEndpoints,
} from "../helpers/mock-api";

test.describe("Admin page — access control", () => {
  test("regular user sees Access denied message", async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);

    await page.goto("/admin");

    await expect(page.getByText("Access denied. Admin only.")).toBeVisible();
  });
});

test.describe("Admin page — admin user", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticatedAdmin(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);
    await mockAdminEndpoints(page);
  });

  test("shows all four admin tabs", async ({ page }) => {
    await page.goto("/admin");

    await expect(page.getByRole("button", { name: "Ingredients" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Tags" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Database" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Recipes" })).toBeVisible();
  });

  test("Tags tab — existing tags are listed", async ({ page }) => {
    await page.goto("/admin");
    await page.getByRole("button", { name: "Tags" }).click();

    await expect(page.getByText("Vegetarian")).toBeVisible();
    await expect(page.getByText("Quick")).toBeVisible();
    await expect(page.getByText("Pasta")).toBeVisible();
  });

  test("Tags tab — create a new tag adds it to the list", async ({ page }) => {
    // Accept confirm dialog for any prompt
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto("/admin");
    await page.getByRole("button", { name: "Tags" }).click();

    await page.getByPlaceholder("Tag name").fill("New Tag");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByText("New Tag")).toBeVisible();
  });

  test("Tags tab — delete a tag removes it from the list", async ({ page }) => {
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto("/admin");
    await page.getByRole("button", { name: "Tags" }).click();

    // All three tags visible initially
    await expect(page.getByText("Vegetarian")).toBeVisible();

    // Click the first Delete button (Vegetarian tag)
    await page.getByRole("button", { name: "Delete" }).first().click();

    await expect(page.getByText("Vegetarian")).not.toBeVisible();
    // The other tags must be unaffected by a single delete
    await expect(page.getByText("Quick")).toBeVisible();
    await expect(page.getByText("Pasta")).toBeVisible();
  });

  test("Database tab — Export and Backup buttons are present", async ({ page }) => {
    await page.goto("/admin");
    await page.getByRole("button", { name: "Database" }).click();

    await expect(page.getByRole("button", { name: "Export Database" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Backup to Server" })).toBeVisible();
  });
});
