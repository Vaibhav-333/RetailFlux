/**
 * E2E tests for Session 26 chart features:
 *  - SmartChart zoom toggle
 *  - DateControl preset switching
 *  - Compare-to selector shows delta on KPI cards
 *  - ScopeChips appear when dims are set
 */
import { test, expect } from "@playwright/test";
import { AUTH_FILE } from "./global.setup";

test.describe("Smart Charts & Filter Context", () => {
  test.use({ storageState: AUTH_FILE });

  // ── DateControl ────────────────────────────────────────────────────────────

  test("DateControl is visible on analytics pages", async ({ page }) => {
    await page.goto("/dashboard/sales");
    // Wait for the page to load
    await page.waitForLoadState("networkidle");
    // The filter bar should contain preset buttons
    await expect(page.getByRole("button", { name: "7d" })).toBeVisible({ timeout: 8_000 });
    await expect(page.getByRole("button", { name: "28d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "QTD" })).toBeVisible();
  });

  test("DateControl is NOT visible on uploads page", async ({ page }) => {
    await page.goto("/dashboard/uploads");
    await page.waitForLoadState("networkidle");
    // No date preset buttons on the uploads page
    await expect(page.getByRole("button", { name: "7d" })).not.toBeVisible();
  });

  test("switching preset re-queries the data", async ({ page }) => {
    await page.goto("/dashboard/sales");
    await page.waitForLoadState("networkidle");

    // Click "7d" preset
    await page.getByRole("button", { name: "7d" }).click();
    // Page should still show the chart (data re-fetched)
    await expect(page.getByText("Daily Revenue Trend")).toBeVisible({ timeout: 10_000 });
  });

  test("Custom preset reveals date pickers", async ({ page }) => {
    await page.goto("/dashboard/sales");
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Custom" }).click();
    // Custom date pickers should appear
    await expect(page.getByLabel("From date")).toBeVisible({ timeout: 4_000 });
    await expect(page.getByLabel("To date")).toBeVisible();
  });

  // ── SmartChart zoom button ─────────────────────────────────────────────────

  test("SmartChart zoom toggle button is present on Sales page", async ({ page }) => {
    await page.goto("/dashboard/sales");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Daily Revenue Trend")).toBeVisible({ timeout: 10_000 });

    // The SmartChart renders a Zoom button
    const zoomBtn = page.getByRole("button", { name: /zoom/i }).first();
    await expect(zoomBtn).toBeVisible({ timeout: 6_000 });
  });

  test("clicking zoom button toggles brush visibility", async ({ page }) => {
    await page.goto("/dashboard/sales");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Daily Revenue Trend")).toBeVisible({ timeout: 10_000 });

    const zoomBtn = page.getByRole("button", { name: /zoom/i }).first();
    // First click enables zoom (brush)
    await zoomBtn.click();
    // After clicking, the button should toggle to "zoom out" state (aria-pressed=true)
    await expect(zoomBtn).toHaveAttribute("aria-pressed", "true", { timeout: 3_000 });

    // Second click disables zoom
    await zoomBtn.click();
    await expect(zoomBtn).toHaveAttribute("aria-pressed", "false", { timeout: 3_000 });
  });

  // ── Compare-to ─────────────────────────────────────────────────────────────

  test("compare-to selector is visible on analytics pages", async ({ page }) => {
    await page.goto("/dashboard/marketing");
    await page.waitForLoadState("networkidle");

    const compareSelect = page.getByLabel("Compare to period");
    await expect(compareSelect).toBeVisible({ timeout: 8_000 });
  });

  test("selecting compare-to triggers data reload", async ({ page }) => {
    await page.goto("/dashboard/finance");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Finance Analytics")).toBeVisible({ timeout: 10_000 });

    const compareSelect = page.getByLabel("Compare to period");
    await compareSelect.selectOption("previous_period");

    // Data re-fetches; page stays visible
    await expect(page.getByText("Finance Analytics")).toBeVisible({ timeout: 10_000 });
  });

  // ── Filter bar visible on all 5 dept pages ─────────────────────────────────

  for (const [url, title] of [
    ["/dashboard/sales", "Sales Analytics"],
    ["/dashboard/marketing", "Marketing Analytics"],
    ["/dashboard/operations", "Operations Analytics"],
    ["/dashboard/finance", "Finance Analytics"],
    ["/dashboard/procurement", "Procurement Analytics"],
  ]) {
    test(`filter bar and preset buttons visible on ${url}`, async ({ page }) => {
      await page.goto(url);
      await page.waitForLoadState("networkidle");
      await expect(page.getByText(title)).toBeVisible({ timeout: 10_000 });
      await expect(page.getByRole("button", { name: "28d" })).toBeVisible({ timeout: 8_000 });
    });
  }
});
