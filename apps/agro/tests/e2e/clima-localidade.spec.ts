import { expect, test } from "@playwright/test";

test.describe("CLIMA-01C1 — Validação E2E com Serviços Reais (Next.js + FastAPI)", () => {
  test.beforeEach(async ({ page }) => {
    // Garante que o localStorage esteja limpo antes de cada teste
    await page.goto("/clima");
    await page.evaluate(() => {
      localStorage.removeItem("deepfarms_agro_clima_localidade_v1");
    });
    await page.reload();
  });

  test("pesquisa Santos, Campinas, São Paulo (com e sem acento) e Cascavel (PR e CE) contra API real", async ({
    page,
  }) => {
    await page.goto("/clima");

    // Abre o modal de seleção
    const btnAbrir = page.locator("#btn-abrir-seletor-localidade");
    await expect(btnAbrir).toBeVisible();
    await btnAbrir.click();

    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();
    const inputBusca = page.locator("#input-busca-municipio");

    // 1. Pesquisa 'Santos' -> Santos/SP deve estar presente
    await inputBusca.fill("Santos");
    const optionSantosSp = page.getByRole("option", { name: /Santos.*SP/i });
    await expect(optionSantosSp).toBeVisible({ timeout: 5000 });

    // 2. Pesquisa 'Campinas' -> Campinas/SP deve estar presente
    await inputBusca.fill("");
    await inputBusca.fill("Campinas");
    const optionCampinasSp = page.getByRole("option", { name: /Campinas.*SP/i });
    await expect(optionCampinasSp).toBeVisible({ timeout: 5000 });

    // 3. Pesquisa 'São Paulo' (com acento) e 'Sao Paulo' (sem acento)
    await inputBusca.fill("");
    await inputBusca.fill("São Paulo");
    const optionSpAcento = page.getByRole("option", { name: /São Paulo.*SP/i });
    await expect(optionSpAcento).toBeVisible({ timeout: 5000 });

    await inputBusca.fill("");
    await inputBusca.fill("Sao Paulo");
    const optionSpSemAcento = page.getByRole("option", { name: /São Paulo.*SP/i });
    await expect(optionSpSemAcento).toBeVisible({ timeout: 5000 });

    // 4. Pesquisa 'Cascavel' -> Distingue PR e CE
    await inputBusca.fill("");
    await inputBusca.fill("Cascavel");
    const optionCascavelPr = page.getByRole("option", { name: /Cascavel.*PR/i });
    const optionCascavelCe = page.getByRole("option", { name: /Cascavel.*CE/i });
    await expect(optionCascavelPr).toBeVisible({ timeout: 5000 });
    await expect(optionCascavelCe).toBeVisible({ timeout: 5000 });
  });

  test("seleção de município, atualização na tela, persistência pós-reload e troca", async ({
    page,
  }) => {
    await page.goto("/clima");

    // Abre modal e busca Santos
    await page.locator("#btn-abrir-seletor-localidade").click();
    await page.locator("#input-busca-municipio").fill("Santos");

    const optionSantos = page.getByRole("option", { name: /Santos.*SP/i });
    await expect(optionSantos).toBeVisible({ timeout: 5000 });
    await optionSantos.click();

    // Modal fecha e card atualiza
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText("Santos — SP")).toBeVisible();
    await expect(page.getByText("Centroide Municipal Oficial (IBGE)")).toBeVisible();
    await expect(page.getByText("IBGE: 3548500")).toBeVisible();

    // Persistência: recarrega a página e valida que Santos permanece
    await page.reload();
    await expect(page.getByText("Santos — SP")).toBeVisible();
    await expect(page.getByText("Centroide Municipal Oficial (IBGE)")).toBeVisible();

    // Troca de município para Campinas
    await page.locator("#btn-abrir-seletor-localidade").click();
    await expect(page.getByRole("dialog")).toBeVisible();

    await page.locator("#input-busca-municipio").fill("Campinas");
    const optionCampinas = page.getByRole("option", { name: /Campinas.*SP/i });
    await expect(optionCampinas).toBeVisible({ timeout: 5000 });
    await optionCampinas.click();

    // Card agora reflete Campinas
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.getByText("Campinas — SP")).toBeVisible();
    await expect(page.getByText("IBGE: 3509502")).toBeVisible();

    // Limpa a seleção
    const btnLimpar = page.locator("#btn-limpar-localidade");
    await expect(btnLimpar).toBeVisible();
    await btnLimpar.click();
    await expect(page.getByText("Nenhum município selecionado")).toBeVisible();
  });

  test("busca inexistente exibe estado vazio específico e honesto", async ({ page }) => {
    await page.goto("/clima");
    await page.locator("#btn-abrir-seletor-localidade").click();

    await page.locator("#input-busca-municipio").fill("MunicipioInexistenteXYZ123");

    // Aguarda estado vazio
    const estadoVazio = page.locator("#estado-vazio");
    await expect(estadoVazio).toBeVisible({ timeout: 5000 });
    await expect(estadoVazio.getByText("Nenhum município encontrado", { exact: true })).toBeVisible();
    // Confirma que NÃO exibiu mensagem de erro falso
    await expect(page.locator("#estado-erro-comunicacao")).not.toBeVisible();
  });

  test("falha de API exibe erro visual e não mascara como lista vazia", async ({ page }) => {
    // Intercepta propositalmente para simular falha HTTP 500 do servidor
    await page.route("**/api/v1/public/clima/municipios*", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal Server Error Simulado" }),
      });
    });

    await page.goto("/clima");
    await page.locator("#btn-abrir-seletor-localidade").click();

    await page.locator("#input-busca-municipio").fill("Londrina");

    // Valida que exibe o card de erro de comunicação
    const erroComunicacao = page.locator("#estado-erro-comunicacao");
    await expect(erroComunicacao).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Falha na comunicação com a API")).toBeVisible();
    await expect(page.getByText(/HTTP 500/)).toBeVisible();

    // Garante que NÃO mascarou como lista vazia
    await expect(page.locator("#estado-vazio")).not.toBeVisible();
  });

  test("fluxo de GPS consentido com permissão concedida", async ({ page, context }) => {
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation({ latitude: -23.3045, longitude: -51.1696 });

    await page.goto("/clima");
    await page.locator("#btn-abrir-seletor-localidade").click();
    await expect(page.getByRole("dialog")).toBeVisible();

    const btnGps = page.locator("#btn-usar-gps");
    await expect(btnGps).toBeVisible();
    await btnGps.click();

    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Localização Atual (GPS)" })
    ).toBeVisible();
    await expect(page.getByText("Localização GPS (Consentida)")).toBeVisible();
    await expect(page.getByText("-23.3045°")).toBeVisible();
  });

  test("fluxo de GPS com permissão negada exibe aviso amigável", async ({ page, context }) => {
    await context.clearPermissions();

    await page.goto("/clima");
    await page.locator("#btn-abrir-seletor-localidade").click();

    await page.evaluate(() => {
      navigator.geolocation.getCurrentPosition = (
        _success: PositionCallback,
        error?: PositionErrorCallback | null
      ) => {
        if (error) {
          const geoError = {
            code: 1, // PERMISSION_DENIED
            message: "User denied Geolocation",
            PERMISSION_DENIED: 1,
            POSITION_UNAVAILABLE: 2,
            TIMEOUT: 3,
          } as GeolocationPositionError;
          error(geoError);
        }
      };
    });

    await page.locator("#btn-usar-gps").click();
    await expect(page.getByText("Permissão de localização negada")).toBeVisible();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("navegação e usabilidade em viewport móvel (375x667)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/clima");

    const btnAbrir = page.locator("#btn-abrir-seletor-localidade");
    await expect(btnAbrir).toBeVisible();
    await btnAbrir.click();

    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();
    await expect(page.locator("#btn-usar-gps")).toBeVisible();

    const inputBusca = page.locator("#input-busca-municipio");
    await inputBusca.fill("Santos");
    const optionSantos = page.getByRole("option", { name: /Santos.*SP/i });
    await expect(optionSantos).toBeVisible({ timeout: 5000 });
    await optionSantos.click();

    await expect(modal).not.toBeVisible();
    await expect(page.getByText("Santos — SP")).toBeVisible();
  });
});
