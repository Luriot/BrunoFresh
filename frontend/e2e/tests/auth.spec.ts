import { test, expect } from "@playwright/test";
import {
  mockUnauthenticated,
  mockAuthenticatedUser,
  mockLoginSuccess,
  mockLoginFailure,
  mockRecipeEndpoints,
  mockListEndpoints,
} from "../helpers/mock-api";

test.describe("Authentication", () => {
  test("shows login form when unauthenticated", async ({ page }) => {
    await mockUnauthenticated(page);
    await page.goto("/");
    await expect(page.getByText("Sign in to access your recipes.")).toBeVisible();
    await expect(page.getByPlaceholder("Username")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  test("login success redirects to dashboard", async ({ page }) => {
    await mockUnauthenticated(page);
    await mockLoginSuccess(page);
    // Also mock recipes and lists so dashboard loads after login
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);

    await page.goto("/");
    await page.getByPlaceholder("Username").fill("testuser");
    await page.getByPlaceholder("Password").fill("password123");
    await page.getByRole("button", { name: "Sign in" }).click();

    // Dashboard navbar should appear (app sets user directly from login response)
    await expect(page.getByText("Dashboard")).toBeVisible({ timeout: 5000 });
  });

  test("login failure shows error message", async ({ page }) => {
    await mockUnauthenticated(page);
    await mockLoginFailure(page);

    await page.goto("/");
    await page.getByPlaceholder("Username").fill("wronguser");
    await page.getByPlaceholder("Password").fill("wrongpass");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText("Invalid username or password.")).toBeVisible();
  });

  test("logout brings back the login form", async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);

    await page.goto("/");

    // Wait until the app is fully loaded (dashboard visible)
    await expect(page.getByText("Dashboard")).toBeVisible();

    // After logout, /auth/me should return null
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "Not authenticated" } })
    );

    await page.getByRole("button", { name: "Logout" }).click();

    await expect(page.getByText("Sign in to access your recipes.")).toBeVisible();
  });

  test("admin page access denied for regular user", async ({ page }) => {
    await mockAuthenticatedUser(page);
    await mockRecipeEndpoints(page);
    await mockListEndpoints(page);

    await page.goto("/admin");

    await expect(page.getByText("Access denied. Admin only.")).toBeVisible();
  });
});
