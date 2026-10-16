import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE_URL = "http://localhost:3000";
const OUTPUT_DIR = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens/01-cadastros";

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  console.log("=== CAPTURANDO FLUXO COMPLETO DO MÓDULO 01 (CADASTROS & PROPRIEDADES) ===");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: "pt-BR"
  });

  const page = await context.newPage();

  // 1. Login
  console.log("Realizando login...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(400);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(400);
  await page.click('button[type="submit"]');

  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 30000 });
  await page.waitForTimeout(2000);
  console.log("✓ Login com sucesso!");

  // 2. Etapa 1: Tela Principal (/cadastros/propriedades)
  console.log("Capturando Etapa 1: Listagem de Unidades Produtivas...");
  await page.goto(`${BASE_URL}/cadastros/propriedades`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);
  const p1 = path.join(OUTPUT_DIR, "01-tela-propriedades.png");
  await page.screenshot({ path: p1 });
  console.log("✓ Etapa 1 salva:", p1);

  // 3. Etapa 2: Dialog de Nova Unidade Produtiva
  console.log("Abrindo Dialog de Nova Unidade Produtiva...");
  const btnNovaUnidade = await page.$('button:has-text("Nova Unidade Produtiva")');
  if (btnNovaUnidade) {
    await btnNovaUnidade.click();
    await page.waitForTimeout(1500); // Aguarda abertura e animação do modal
    const p2 = path.join(OUTPUT_DIR, "02-dialog-nova-unidade.png");
    await page.screenshot({ path: p2 });
    console.log("✓ Etapa 2 (Dialog) salva:", p2);

    // Fecha o modal para prosseguir limpo
    const btnCancelar = await page.$('button:has-text("Cancelar"), [aria-label="Close"]');
    if (btnCancelar) {
      await btnCancelar.click();
      await page.waitForTimeout(500);
    }
  } else {
    console.warn("⚠️ Botão Nova Unidade Produtiva não encontrado!");
  }

  // 4. Etapa 3: Gestão de Talhões (/cadastros/propriedades/talhoes)
  console.log("Capturando Etapa 3: Gestão de Talhões & Georreferenciamento...");
  await page.goto(`${BASE_URL}/cadastros/propriedades/talhoes`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("text=Georreferenciamento", { timeout: 30000 });
  await page.waitForTimeout(4000); // Aguarda renderização completa do mapa
  const p3 = path.join(OUTPUT_DIR, "03-tela-talhoes.png");
  await page.screenshot({ path: p3 });
  console.log("✓ Etapa 3 (Talhões) salva:", p3);

  await browser.close();
  console.log("=== FLUXO DO MÓDULO 01 CAPTURADO COM SUCESSO! ===");
}

main().catch(err => {
  console.error("Erro fatal:", err);
  process.exit(1);
});
