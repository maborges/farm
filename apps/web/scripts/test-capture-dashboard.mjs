import { chromium } from "playwright";
import fs from "fs";

const BASE_URL = "http://localhost:3000";

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: "pt-BR"
  });

  const page = await context.newPage();

  page.on("console", msg => {
    if (msg.type() === "error" || msg.text().includes("API Request")) {
      console.log(`[PAGE ${msg.type()}]`, msg.text());
    }
  });

  console.log("1. Realizando login...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(300);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(300);
  await page.click('button[type="submit"]');

  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 30000 });
  console.log("2. Autenticado! Aguardando carregamento dos dados do Dashboard...");

  // Wait for networkidle
  await page.waitForLoadState("networkidle");
  // Give extra time for React Query hooks and animations to settle
  await page.waitForTimeout(5000);

  // Check if there are any visible loading spinners / skeletons
  const skeletons = await page.$$('.animate-pulse, [role="status"]');
  console.log(`Skeletons/loading indicators encontrados: ${skeletons.length}`);

  // Capture standard 1440x900 viewport
  const targetPathStandard = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/00-navegacao/01-tela-inicial-dashboard.png";
  await page.screenshot({ path: targetPathStandard });
  console.log("✓ Screenshot padrão salvo em:", targetPathStandard, "Tamanho:", fs.statSync(targetPathStandard).size);

  // Also capture fullPage to check complete content
  const targetPathFull = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/00-navegacao/01-tela-inicial-dashboard-full.png";
  await page.screenshot({ path: targetPathFull, fullPage: true });
  console.log("✓ Screenshot fullPage salvo em:", targetPathFull, "Tamanho:", fs.statSync(targetPathFull).size);

  await browser.close();
}

run().catch(e => {
  console.error("Erro:", e);
  process.exit(1);
});
