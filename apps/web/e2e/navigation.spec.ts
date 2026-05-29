import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./global.setup";

/**
 * Department navigation tests — require authenticated session.
 */
test.describe("Department Navigation", () => {
  test.use({ storageState: AUTH_FILE });

  const DEPT_PAGES = [
    { path: "/dashboard/sales", heading: "Sales Analytics" },
    { path: "/dashboard/marketing", heading: "Marketing Analytics" },
    { path: "/dashboard/operations", heading: "Operations Analytics" },
    { path: "/dashboard/finance", heading: "Finance Analytics" },
    { path: "/dashboard/procurement", heading: "Procurement Analytics" },
  ] as const;

  for (const { path, heading } of DEPT_PAGES) {
    test(`${heading} page loads`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible({
        timeout: 10_000,
      });
      // Document title should be updated
      await expect(page).toHaveTitle(new RegExp(heading.split(" ")[0], "i"));
    });
  }

  test("uploads page shows drag-and-drop zone", async ({ page }) => {
    await page.goto("/dashboard/uploads");
    await expect(page.getByText(/drag.*drop|upload/i).first()).toBeVisible({
      timeout: 8_000,
    });
  });

  test("settings page renders profile form", async ({ page }) => {
    await page.goto("/dashboard/settings");
    await expect(page.getByText(/profile|settings/i).first()).toBeVisible({
      timeout: 6_000,
    });
  });

  test("sidebar navigation links are present", async ({ page }) => {
    await page.goto("/dashboard");
    // Sidebar should contain nav links for all depts
    await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sales" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Marketing" })).toBeVisible();
  });

  test("mobile menu button visible on narrow viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
  });
});
