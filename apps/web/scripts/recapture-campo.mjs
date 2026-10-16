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
  console.log("2. Autenticado! Navegando para /dashboard/operacional/campo/tarefas...");

  await page.goto(`${BASE_URL}/dashboard/operacional/campo/tarefas`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector('text=Tarefas de Campo', { timeout: 30000 });

  // Wait specifically for "Carregando dados..." to disappear from the table!
  console.log("Aguardando carregamento da tabela de tarefas...");
  await page.waitForFunction(() => {
    return !document.body.innerText.includes("Carregando dados...");
  }, { timeout: 30000 }).catch(() => {
    console.log("Aviso: Timeout aguardando Carregando dados... sumir.");
  });

  await page.waitForTimeout(2000);

  const targetPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/14-campo-pwa/01-tela-campo-pwa.png";
  await page.screenshot({ path: targetPath });
  console.log("✓ Screenshot salvo:", targetPath, "Tamanho:", fs.statSync(targetPath).size);

  await browser.close();
}

run().catch(e => {
  console.error("Erro:", e);
  process.exit(1);
});
