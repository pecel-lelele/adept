import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e", outputDir: "tmp/playwright-results", fullyParallel: false,
  workers: 1, retries: 0, timeout: 90000,
  use: { baseURL: "http://127.0.0.1:13091", trace: "retain-on-failure", actionTimeout: 15000 },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: { command: "node tests/e2e/serve.mjs", url: "http://127.0.0.1:13091", reuseExistingServer: false, timeout: 60000 },
});
