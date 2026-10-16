import { chromium } from "playwright";
import fs from "fs";

const BASE_URL = "http://localhost:3000";

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 950 },
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
  console.log("2. Autenticado! Navegando para /cadastros/propriedades...");

  await page.goto(`${BASE_URL}/cadastros/propriedades`, { waitUntil: "domcontentloaded", timeout: 60000 });

  // Wait for the button "Nova Unidade Produtiva" to appear
  await page.waitForSelector('button:has-text("Nova Unidade Produtiva")', { timeout: 30000 });
  console.log("Botão Nova Unidade Produtiva presente!");

  // Wait for loading skeletons to disappear
  await page.waitForFunction(() => {
    const skeletons = document.querySelectorAll('.animate-pulse');
    return skeletons.length === 0;
  }, { timeout: 30000 }).catch(() => {
    console.log("Aviso: Timeout aguardando skeletons sumirem, prosseguindo com espera.");
  });

  await page.waitForTimeout(3000);

  const targetPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/01-cadastros/01-tela-propriedades.png";
  await page.screenshot({ path: targetPath });
  console.log("✓ Screenshot salvo:", targetPath, "Tamanho:", fs.statSync(targetPath).size);

  await browser.close();
}

run().catch(e => {
  console.error("Erro:", e);
  process.exit(1);
});
