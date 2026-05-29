import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for RetailFlux.
 *
 * Setup project handles authentication and stores browser state in
 * playwright/.auth/user.json so authenticated tests reuse the session.
 *
 * Run:  npx playwright test
 * UI:   npx playwright test --ui
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    // Global setup — log in once and save storage state
    {
      name: "setup",
      testMatch: "**/global.setup.ts",
    },
    // Main browser project — depends on setup
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },
  ],

  // Start the Vite dev server automatically when running locally
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
