import { test, expect } from "@playwright/test";

/**
 * Authentication flow tests — run without stored auth state.
 */
test.describe("Authentication", () => {
  test("redirects to /login when unauthenticated", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login page renders form fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByPlaceholder("you@company.com")).toBeVisible();
    await expect(page.getByPlaceholder("••••••••")).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("shows error toast on invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("you@company.com").fill("nobody@nowhere.com");
    await page.getByPlaceholder("••••••••").fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Sonner toast or inline error should appear
    await expect(
      page.getByText(/invalid|incorrect|credentials|unauthorized/i),
    ).toBeVisible({ timeout: 6_000 });
  });

  test("register page is accessible from login", async ({ page }) => {
    await page.goto("/login");
    const registerLink = page.getByRole("link", { name: /register|sign up|create account/i });
    await expect(registerLink).toBeVisible();
    await registerLink.click();
    await expect(page).toHaveURL(/\/register/);
  });
});
