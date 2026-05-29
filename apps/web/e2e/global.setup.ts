import { test as setup, expect } from "@playwright/test";
import path from "path";

/** Path where the authenticated browser state is saved. */
export const AUTH_FILE = path.join(__dirname, "../playwright/.auth/user.json");

/**
 * Global setup: log in with demo CEO credentials and persist the browser
 * storage state so subsequent test projects reuse the session without
 * re-authenticating on every spec file.
 *
 * Prerequisites:
 *   1. API running on http://localhost:8000
 *   2. Frontend running on http://localhost:3000
 *   3. Demo data seeded: `python scripts/seed_demo.py`
 */
setup("authenticate as CEO", async ({ page }) => {
  await page.goto("/login");

  await page.getByPlaceholder("you@company.com").fill("ceo@demo.com");
  await page.getByPlaceholder("••••••••").fill("Demo1234!");
  await page.getByRole("button", { name: /sign in/i }).click();

  // Wait until the dashboard loads — confirms auth worked
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  await expect(page.getByText("Master Dashboard")).toBeVisible({ timeout: 10_000 });

  // Persist the authenticated session
  await page.context().storageState({ path: AUTH_FILE });
});
