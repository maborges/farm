import { defineConfig, devices } from "@playwright/test";

const port = 3005;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${port}`;
const apiOrigin = process.env.AGRO_API_INTERNAL_ORIGIN ?? "http://127.0.0.1:8001";

if (baseURL !== `http://127.0.0.1:${port}` || apiOrigin !== "http://127.0.0.1:8001") {
  throw new Error("A configuração Playwright do laboratório aceita somente PWA 3005 e API 8001 em loopback.");
}

const providerSecretNames = [
  "OPENWEATHER_API_KEY",
  "WEATHERAPI_API_KEY",
  "TOMORROWIO_API_KEY",
  "STRIPE_SECRET_KEY",
  "ASAAS_API_KEY",
  "SANKHYA_CLIENT_SECRET",
  "SANKHYA_X_TOKEN",
  "TARA_CLIENT_SECRET",
  "BALANCA_WEBHOOK_SECRET",
];

const webServerEnv: Record<string, string> = {
  ENVIRONMENT: "staging",
  APP_ENV: "staging",
  PORT: String(port),
  AGRO_API_INTERNAL_ORIGIN: apiOrigin,
  NEXT_PUBLIC_AGRO_API_ORIGIN: "",
  DATABASE_URL: "",
  REDIS_URL: "",
  STORAGE_LOCAL_PATH: "",
  S3_BUCKET: "",
  S3_BUCKET_NAME: "",
  S3_ENDPOINT_URL: "",
  AWS_ACCESS_KEY_ID: "",
  AWS_SECRET_ACCESS_KEY: "",
  AWS_SESSION_TOKEN: "",
};
for (const name of Object.keys(process.env)) {
  if (/(API_KEY|ACCESS_KEY|CLIENT_SECRET|WEBHOOK_SECRET|TOKEN$|SECRET|SMTP_PASS|MAIL_PASS)/i.test(name)) {
    webServerEnv[name] = "";
  }
}
for (const name of providerSecretNames) webServerEnv[name] = "";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  reporter: "line",
  timeout: 30000,
  use: {
    baseURL,
    headless: true,
    launchOptions: {
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        // Browser E2E is confined to loopback; public provider calls must be mocked.
        "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost, EXCLUDE ::1",
      ],
    },
    trace: "on-first-retry",
  },
  webServer: {
    command: `npx next dev -p ${port} --webpack`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 30000,
    env: webServerEnv,
  },
  projects: [{ name: "chromium-lab", use: { ...devices["Desktop Chrome"] } }],
});
