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

  page.on("console", msg => console.log("PAGE LOG:", msg.type(), msg.text()));
  page.on("pageerror", err => console.log("PAGE ERROR:", err.message));

  console.log("Logging in...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(300);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(300);
  await page.click('button[type="submit"]');

  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 30000 });
  await page.waitForTimeout(2000);
  console.log("Logged in, navigating to /cadastros/propriedades/talhoes...");

  await page.goto(`${BASE_URL}/cadastros/propriedades/talhoes`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(6000);

  const title = await page.title();
  console.log("Page title:", title);
  console.log("Current URL:", page.url());

  const screenshotPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/01-cadastros/03-mapa-talhoes.png";
  await page.screenshot({ path: screenshotPath });
  console.log("Screenshot saved at:", screenshotPath, "Size:", fs.statSync(screenshotPath).size);

  // Click on the first talhão card to open the Sheet
  console.log("Clicking on Talhão F1-A1...");
  const cardTalhao = await page.$('text=Talhão F1-A1');
  if (cardTalhao) {
    await cardTalhao.click();
    await page.waitForTimeout(1500);
    const sheetPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/01-cadastros/04-drawer-talhao.png";
    await page.screenshot({ path: sheetPath });
    console.log("Sheet screenshot saved at:", sheetPath, "Size:", fs.statSync(sheetPath).size);

    console.log("Clicking Editar Dados do Talhão...");
    const btnEditar = await page.$('button:has-text("Editar Dados do Talhão")');
    if (btnEditar) {
      await btnEditar.click();
      await page.waitForTimeout(1500);
      const dialogPath = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/01-cadastros/05-dialog-talhao.png";
      await page.screenshot({ path: dialogPath });
      console.log("Talhao dialog screenshot saved at:", dialogPath, "Size:", fs.statSync(dialogPath).size);
    }
  }

  await browser.close();
}

run().catch(e => {
  console.error(e);
  process.exit(1);
});
