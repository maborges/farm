import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  reporter: "line",
  use: {
    baseURL,
    headless: true,
    launchOptions: {
      env: {
        HOME: "/tmp",
        XDG_CONFIG_HOME: "/tmp",
        XDG_RUNTIME_DIR: "/tmp",
      },
    },
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        browserName: "chromium",
        launchOptions: {
          args: ["--no-sandbox"],
        },
      },
    },
    {
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
        browserName: "firefox",
      },
    },
  ],
});
