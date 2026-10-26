import { test, expect } from "@playwright/test";

test.describe("DEEPFARMS-AGRO-FREE-01E1A — Calculadoras Agrícolas e Homologação PWA", () => {
  test.beforeEach(async ({ page }) => {
    // Escuta erros de console não capturados
    page.on("pageerror", (exception) => {
      console.log(`[Browser PageError]: ${exception.message}`);
    });
  });

  test("1. Registra e ativa o Service Worker no navegador", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Aguarda registro do Service Worker
    const swRegistered = await page.evaluate(async () => {
      if (!("serviceWorker" in navigator)) return false;
      const registration = await navigator.serviceWorker.getRegistration();
      return !!registration;
    });

    expect(swRegistered).toBe(true);

    // Valida que o Service Worker está ativo ou controlando a página
    const swAtivo = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.ready;
      return reg && reg.active !== null;
    });

    expect(swAtivo).toBe(true);
  });

  test("2. Verifica pré-cache do App Shell no CacheStorage", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Aguarda o Service Worker completar o install & activate
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      // Pequena pausa para garantir pre-cache concluído
      await new Promise((resolve) => setTimeout(resolve, 800));
    });

    const chavesCache = await page.evaluate(async () => {
      const keys = await caches.keys();
      const agroCacheKey = keys.find((k) => k.startsWith("deepfarms-agro-")) || "deepfarms-agro-v2";
      const cache = await caches.open(agroCacheKey);
      const requests = await cache.keys();
      return requests.map((req) => new URL(req.url).pathname);
    });

    expect(chavesCache).toContain("/");
    expect(chavesCache).toContain("/calculadoras");
    expect(chavesCache).toContain("/clima");
    expect(chavesCache).toContain("/offline");
  });

  test("3. Interface e cálculos interativos das 5 ferramentas com correções 01E1A", async ({ page }) => {
    await page.goto("/calculadoras");
    await page.waitForLoadState("networkidle");

    // Verifica título principal
    await expect(page.locator("h1")).toContainText("Calculadoras e Conversores Agrícolas");

    // ── FERRAMENTA 1: Sacas, Kg e Toneladas ──
    const inputMassa = page.locator("#valor-massa");
    await inputMassa.fill("200");
    await expect(page.getByText("Equivalentes")).toBeVisible();
    await expect(page.getByText("12.000")).toBeVisible(); // 200 sacas * 60kg = 12.000 kg

    // Testa aviso de ambiguidade pt-BR (ex: "1.234")
    await inputMassa.fill("1.234");
    await expect(page.getByText(/Notação pt-BR: '1.234' foi interpretado como 1234 unidades/i)).toBeVisible();
    await inputMassa.fill("200");

    // Testa botão 50kg (alterar padrão de saca)
    await page.getByRole("button", { name: "50kg" }).click();
    await expect(page.getByText("10.000")).toBeVisible(); // 200 * 50kg = 10.000 kg

    // ── FERRAMENTA 2: Áreas Rurais ──
    await page.getByRole("button", { name: /Áreas Rurais/i }).click();
    await expect(page.getByRole("heading", { name: "Conversão de Áreas Rurais" })).toBeVisible();

    const inputArea = page.locator("#valor-area");
    await inputArea.fill("10"); // 10 hectares
    await expect(page.getByText("100.000")).toBeVisible(); // 10 ha * 10.000 m²
    await expect(page.getByText("Alqueire Paulista", { exact: true })).toBeVisible();
    await expect(page.getByText("Alqueire Mineiro / Goiano", { exact: true })).toBeVisible();
    await expect(page.getByText("Alqueire do Norte", { exact: true })).toBeVisible();
    await expect(page.getByText("Alqueire Baiano / Pequeno", { exact: true })).toBeVisible();

    // ── FERRAMENTA 3: Frete Agrícola ──
    await page.getByRole("button", { name: /Frete/i }).click();
    await expect(page.getByRole("heading", { name: "Estimativa de Frete Agrícola" })).toBeVisible();

    const inputQtdFrete = page.locator("#quantidade-frete");
    await inputQtdFrete.fill("30");
    const inputTarifa = page.locator("#valor-tarifa");
    await inputTarifa.fill("150"); // 30t * 150 = R$ 4.500
    await expect(page.getByText("R$ 4.500,00", { exact: true })).toBeVisible();

    // ── FERRAMENTA 4: Custo por Hectare e Ponto de Equilíbrio (Correções 01E1A) ──
    await page.getByRole("button", { name: /Custo/i }).click();
    await expect(page.getByRole("heading", { name: "Custo por Hectare e Ponto de Equilíbrio" })).toBeVisible();

    const inputAreaHa = page.locator("#area-ha");
    await inputAreaHa.fill("100");
    const inputCusto = page.locator("#custo-total");
    await inputCusto.fill("300000"); // R$ 3.000/ha
    await expect(page.getByText("R$ 3.000,00 / ha", { exact: true })).toBeVisible();

    // Valida terminologia financeira corrigida
    await expect(page.getByText("Resultado estimado (receita menos custos informados)")).toBeVisible();

    // Valida Correção 01: quando produtividade é zero, custo unitário e preço de equilíbrio são 'Não calculável com os valores informados.'
    const inputProd = page.locator("#prod-esperada");
    await inputProd.fill("0");
    await expect(page.getByText("Não calculável com os valores informados.").first()).toBeVisible();

    // Restaura produtividade
    await inputProd.fill("60");

    // ── FERRAMENTA 5: Conversor Geral ──
    await page.getByRole("button", { name: /Conversor Geral/i }).click();
    await expect(page.getByRole("heading", { name: "Conversor Geral de Unidades" })).toBeVisible();

    const inputConversao = page.locator("#valor-conversao");
    await inputConversao.fill("5000");
    // Massa: 5000 kg para tonelada = 5 t
    await expect(page.getByText("5 t", { exact: true })).toBeVisible();
  });

  test("4. Funcionamento 100% Offline: navegação e cálculos sem conexão", async ({
    page,
    context,
  }) => {
    // 1. Visita inicial para garantir cache
    await page.goto("/calculadoras");
    await page.waitForLoadState("networkidle");

    // Aguarda o Service Worker controlar a página
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      await new Promise((resolve) => setTimeout(resolve, 800));
    });

    // 2. Simula perda total de internet (modo avião / offline)
    await context.setOffline(true);

    // 3. Recarrega a página offline
    await page.reload({ waitUntil: "domcontentloaded" });

    // Valida que a página carregou do cache offline com sucesso
    await expect(page.locator("h1")).toContainText("Calculadoras e Conversores Agrícolas");

    // 4. Executa cálculo em modo offline
    const inputMassa = page.locator("#valor-massa");
    await inputMassa.fill("350");

    // 350 * 60 = 21.000 kg
    await expect(page.getByText("21.000")).toBeVisible();

    // 5. Navega entre abas offline
    await page.getByRole("button", { name: /Áreas Rurais/i }).click();
    await expect(page.getByRole("heading", { name: "Conversão de Áreas Rurais" })).toBeVisible();

    // 6. Restaura conexão
    await context.setOffline(false);
  });

  test("5. Segurança: Service Worker não intercepta nem cacheia /api/", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Testa chamada para rota /api/
    await page.evaluate(async () => {
      try {
        const res = await fetch("/api/status-teste", { method: "GET" });
        return { status: res.status, ok: res.ok };
      } catch (e) {
        return { erro: String(e) };
      }
    });

    // A rota /api/ deve ir para a rede sem cache do SW
    const cacheApi = await page.evaluate(async () => {
      const cache = await caches.open("deepfarms-agro-v1");
      const match = await cache.match("/api/status-teste");
      return match !== undefined;
    });

    expect(cacheApi).toBe(false);
  });
});
