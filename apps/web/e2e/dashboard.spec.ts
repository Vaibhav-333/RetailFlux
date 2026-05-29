import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./global.setup";

/**
 * Master dashboard tests — require authenticated session.
 */
test.describe("Master Dashboard", () => {
  test.use({ storageState: AUTH_FILE });

  test("renders page title and subtitle", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Master Dashboard")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("Company-wide overview")).toBeVisible();
  });

  test("document title is set correctly", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveTitle(/Master Dashboard.*RetailFlux/i, { timeout: 8_000 });
  });

  test("renders 5 department KPI cards", async ({ page }) => {
    await page.goto("/dashboard");
    // Wait for data to load (KPI cards appear after API response)
    await expect(page.getByText("Total Revenue")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("ROAS")).toBeVisible();
    await expect(page.getByText("SKUs Below Reorder")).toBeVisible();
    await expect(page.getByText("Gross Margin")).toBeVisible();
    await expect(page.getByText("Procurement Spend")).toBeVisible();
  });

  test("revenue sparkline chart renders", async ({ page }) => {
    await page.goto("/dashboard");
    await page.waitForSelector(".recharts-responsive-container", { timeout: 12_000 });
    const charts = page.locator(".recharts-responsive-container");
    await expect(charts.first()).toBeVisible();
  });

  test("command palette opens with Ctrl+K", async ({ page }) => {
    await page.goto("/dashboard");
    await page.keyboard.press("Control+k");
    await expect(page.getByPlaceholder(/search/i)).toBeVisible({ timeout: 3_000 });
    await page.keyboard.press("Escape");
  });
});
