import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3004";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  reporter: "line",
  timeout: 30000,
  use: {
    baseURL,
    headless: true,
    launchOptions: {
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    },
    trace: "on-first-retry",
  },
  webServer: {
    command: "npx next start -p 3004",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
    env: {
      AGRO_API_INTERNAL_ORIGIN: process.env.AGRO_API_INTERNAL_ORIGIN ?? "http://127.0.0.1:8000",
    },
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});
