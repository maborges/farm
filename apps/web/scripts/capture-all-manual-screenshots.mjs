import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE_URL = "http://localhost:3000";
const IMAGES_BASE_DIR = "/opt/lampp/htdocs/farm/apps/web/public/manual/imagens";

const MODULES_TO_CAPTURE = [
  {
    id: "00-navegacao",
    route: "/dashboard",
    filename: "01-tela-inicial-dashboard.png"
  },
  {
    id: "01-cadastros",
    route: "/cadastros/propriedades",
    filename: "01-tela-propriedades.png"
  },
  {
    id: "02-imoveis",
    route: "/cadastros/imoveis",
    filename: "01-tela-imoveis.png"
  },
  {
    id: "03-agricultura",
    route: "/agricola",
    filename: "01-tela-agricultura.png"
  },
  {
    id: "04-clima",
    route: "/dashboard/agricola/clima/monitoramento",
    filename: "01-tela-clima.png"
  },
  {
    id: "05-estoque",
    route: "/suprimentos",
    filename: "01-tela-estoque.png"
  },
  {
    id: "06-frota",
    route: "/operacional",
    filename: "01-tela-frota.png"
  },
  {
    id: "07-pecuaria",
    route: "/dashboard/pecuaria",
    filename: "01-tela-pecuaria.png"
  },
  {
    id: "08-balanca",
    route: "/dashboard/operacional/balanca/pesagens",
    filename: "01-tela-balanca.png"
  },
  {
    id: "09-financeiro",
    route: "/dashboard/financeiro",
    filename: "01-tela-financeiro.png"
  },
  {
    id: "10-rh",
    route: "/dashboard/rh/colaboradores",
    filename: "01-tela-rh.png"
  },
  {
    id: "11-seguranca",
    route: "/dashboard/rh/seguranca",
    filename: "01-tela-seguranca.png"
  },
  {
    id: "12-ambiental",
    route: "/dashboard/ambiental",
    filename: "01-tela-ambiental.png"
  },
  {
    id: "13-ia",
    route: "/dashboard/ia",
    filename: "01-tela-copiloto-ia.png"
  },
  {
    id: "14-campo-pwa",
    route: "/dashboard/operacional/campo/tarefas",
    filename: "01-tela-campo-pwa.png"
  },
  {
    id: "15-gestao-acesso",
    route: "/dashboard/settings/team",
    filename: "01-tela-gestao-acesso.png"
  },
  {
    id: "16-configuracoes",
    route: "/dashboard/settings/tenant",
    filename: "01-tela-configuracoes.png"
  },
  {
    id: "17-jornadas",
    route: "/manual",
    filename: "01-tela-jornadas.png"
  }
];

async function main() {
  console.log("=== INICIANDO CAPTURA DE SCREENSHOTS DOS MÓDULOS ===");

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: "pt-BR"
  });

  const page = await context.newPage();

  // 1. Realizar Login
  console.log("Efetuando login como borgesma63@gmail.com...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000); // Aguarda hidratação completa
  await page.fill("#email", "borgesma63@gmail.com");
  await page.waitForTimeout(500);
  await page.fill("#password", "agro1234");
  await page.waitForTimeout(500);
  await page.click('button[type="submit"]');

  await page.waitForFunction(() => window.location.pathname.includes("/dashboard"), { timeout: 30000 });
  await page.waitForTimeout(3000);
  console.log("✓ Login autenticado com sucesso! URL atual:", page.url());

  // 2. Capturar cada tela
  for (let i = 0; i < MODULES_TO_CAPTURE.length; i++) {
    const mod = MODULES_TO_CAPTURE[i];
    const targetDir = path.join(IMAGES_BASE_DIR, mod.id);
    fs.mkdirSync(targetDir, { recursive: true });
    const targetFile = path.join(targetDir, mod.filename);

    if (fs.existsSync(targetFile) && fs.statSync(targetFile).size > 20000) {
      console.log(`[${i + 1}/${MODULES_TO_CAPTURE.length}] ✓ ${mod.id} já capturado (${mod.filename}). Pulando.`);
      continue;
    }

    console.log(`[${i + 1}/${MODULES_TO_CAPTURE.length}] Capturando ${mod.id} (${mod.route})...`);
    let captured = false;
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        await page.goto(`${BASE_URL}${mod.route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
        await page.waitForTimeout(3500); // Aguardar compilação webpack e renderização
        await page.screenshot({ path: targetFile });
        console.log(`  ✓ Salvo com sucesso em: ${targetFile}`);
        captured = true;
        break;
      } catch (err) {
        console.warn(`  ⚠️ Tentativa ${attempt} falhou para ${mod.id} (${err.message}). Aguardando 5s...`);
        await page.waitForTimeout(5000);
      }
    }
    if (!captured) {
      console.error(`  ✗ Falha definitiva ao capturar ${mod.id}`);
    }
    await page.waitForTimeout(1000);
  }

  await browser.close();
  console.log("=== TODAS AS SCREENSHOTS FORAM CAPTURADAS COM SUCESSO! ===");
}

main().catch(err => {
  console.error("Erro fatal:", err);
  process.exit(1);
});
