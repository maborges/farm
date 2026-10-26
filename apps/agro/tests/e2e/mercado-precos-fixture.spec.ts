import { expect, test } from "@playwright/test";

const fixtureResponse = {
  sucesso: true,
  versao: "1.0",
  dataConsultaIso: "2026-10-16T12:00:00Z",
  cacheAtualizadoEmIso: "2026-10-16T12:00:00Z",
  estadoDisponibilidade: "NORMAL",
  avisoLegal: "Fixture sintética exclusiva de testes; não representa cotação oficial.",
  totalItens: 4,
  itens: [
    ["soja", "Soja", 134.98, "Saca de 60 kg", "Rav!X1"],
    ["milho", "Milho", 51.77, "Saca de 60 kg", "Rav!X2"],
    ["cafe-arabica", "Café Beneficiado (Produtor)", 1380.51, "Saca de 60 kg", "Rav!X3"],
    ["boi-gordo", "Boi Gordo", 371.21, "Arroba", "Rav!X4"],
  ].map(([id, commodityNome, valor, unidade, registroOriginal]) => ({
    id,
    commodityNome,
    classificacao: "Fixture de homologação",
    valor,
    moeda: "BRL",
    unidade,
    pracaReferencia: "Praça sintética de teste",
    fonteOficial: "Fixture DeepFarms",
    siglaFonte: "FIXTURE",
    linkOficial: "https://example.invalid/fixture",
    urlConsultaInstitucional: "https://example.invalid/fixture",
    urlDocumentoDownload: null,
    tipoPreco: "REFERENCIA_OFICIAL_GOVERNAMENTAL",
    periodicidade: "SEMANAL",
    dataReferencia: "2026-10-16",
    dataConsultaIso: "2026-10-16T12:00:00Z",
    defasagemDiasAproximada: 0,
    indicacaoTemporal: "Fixture sintética — homologação",
    avisoLegal: "Dado sintético; não usar como preço de mercado.",
    documentoOficial: "https://example.invalid/fixture.pdf",
    documentoHashSha256: "0".repeat(64),
    dataPublicacao: "2026-10-16",
    registroOriginal,
    valorOriginal: valor,
    unidadeOriginal: unidade,
    transformacaoAplicada: "Fixture sem conversão",
  })),
};

test.describe("Catálogo de preços públicos com fixture sintética", () => {
  test("carrega preços via mesma origem em desktop, recarrega e recupera após offline", async ({ page, context }) => {
    const urls: string[] = [];
    let fixtureRequests = 0;
    await page.route("**/api/v1/public/mercado/precos", async (route) => {
      fixtureRequests += 1;
      if (fixtureRequests <= 2) {
        await route.fulfill({ json: fixtureResponse });
      } else {
        await route.abort("failed");
      }
    });
    page.on("request", (request) => {
      if (request.url().includes("/api/v1/public/mercado/precos")) urls.push(request.url());
    });

    await page.goto("/mercado");
    await expect(page.locator('[data-commodity-id="soja"]')).toContainText("R$ 134,98");
    await expect(page.locator('[data-commodity-id="milho"]')).toContainText("R$ 51,77");
    const cafe = page.locator('[data-commodity-id="cafe-arabica"]');
    await expect(cafe).toContainText("Café Beneficiado (Produtor)");
    await expect(cafe).toContainText("R$ 1.380,51");
    await expect(cafe).toContainText("Fixture sintética");
    await expect(page.locator('[data-commodity-id="boi-gordo"]')).toContainText("R$ 371,21");
    const origin = new URL(page.url()).origin;
    expect(urls.some((url) => url.startsWith(`${origin}/api/v1/`))).toBe(true);
    expect(urls.every((url) => new URL(url).origin === new URL(origin).origin)).toBe(true);

    await page.reload();
    await expect(page.locator('[data-commodity-id="soja"]')).toContainText("R$ 134,98");

    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Exibindo dado salvo/)).toBeVisible();
    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect(page.locator('[data-testid="estado-precos"]')).toHaveCount(0);
  });

  test("exibe fonte, data e unidade no viewport móvel", async ({ page }) => {
    await page.route("**/api/v1/public/mercado/precos", async (route) => {
      await route.fulfill({ json: fixtureResponse });
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/mercado");
    const card = page.locator('[data-commodity-id="soja"]');
    await expect(card).toContainText("R$ 134,98");
    await expect(card).toContainText("Saca de 60 kg");
    await expect(card).toContainText("FIXTURE");
    await expect(card).toContainText("16/10/2026");
  });
});
