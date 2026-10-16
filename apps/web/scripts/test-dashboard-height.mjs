import { chromium } from "playwright";
import fs from "fs";

const BASE_URL = "http://localhost:3000";

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  // Let's test with viewport height 1200
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1350 },
    locale: "pt-BR"
  });

  const page = await context.newPage();

  console.log("Logging in...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(300);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(300);
  await page.click('button[type="submit"]');

  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 30000 });
  console.log("Logged in!");

  // Wait for networkidle and all dashboard data
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(4000);

  // Capture standard viewport
  const targetPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/00-navegacao/01-tela-inicial-dashboard.png";
  await page.screenshot({ path: targetPath });
  console.log("Saved 01-tela-inicial-dashboard.png, size:", fs.statSync(targetPath).size);

  await browser.close();
}

run().catch(console.error);
