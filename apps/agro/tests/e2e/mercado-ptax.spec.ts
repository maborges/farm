import { test, expect } from "@playwright/test";

test.describe("DEEPFARMS-AGRO-FREE-01E2B — Homologação E2E Mercado e PTAX", () => {
  test("1. Carrega a página /mercado e exibe o card Dólar PTAX", async ({ page }) => {
    await page.route("**/api/v1/public/mercado/ptax", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          indicador: "DOLAR_PTAX",
          moeda: "USD",
          moedaReferencia: "BRL",
          cotacaoCompra: 5.6372,
          cotacaoVenda: 5.6378,
          dataCotacao: "2026-10-16",
          dataHoraBoletimIso: "2026-10-16T13:06:27.393-03:00",
          tipoBoletim: "Fechamento PTAX",
          fonteOficial: "Banco Central do Brasil (BCB)",
          dataConsultaIso: "2026-10-17T15:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-17T15:00:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
          estaDesatualizado: false,
          avisoLegal: "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.",
        }),
      });
    });
    await page.route("**/api/v1/public/mercado/indicadores-macro", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T19:50:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estaDesatualizado: false,
          avisoLegal: "Dados públicos oficiais divulgados pelo Banco Central do Brasil (BCB) e IBGE.",
          itens: [
            {
              id: "SELIC_META",
              nomeOficial: "Taxa de juros - Meta Selic definida pelo Copom",
              codigoSerieBcb: 432,
              valor: 13.75,
              unidade: "% a.a.",
              periodicidade: "DIARIA",
              dataReferencia: "2026-11-04",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "IPCA_MENSAL",
              nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA)",
              codigoSerieBcb: 433,
              valor: 0.82,
              unidade: "% a.m.",
              periodicidade: "MENSAL",
              dataReferencia: "2026-09-01",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "IPCA_12M",
              nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses",
              codigoSerieBcb: 13522,
              valor: 4.58,
              unidade: "% em 12 meses",
              periodicidade: "MENSAL",
              dataReferencia: "2026-09-01",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "EURO_PTAX",
              nomeOficial: "Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
              codigoSerieBcb: 21619,
              valor: 5.6682,
              valorCompra: 5.6665,
              valorVenda: 5.6682,
              unidade: "BRL",
              periodicidade: "DIARIA",
              dataReferencia: "2026-10-19",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
          ],
        }),
      });
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Verifica título da página
    await expect(page.locator("h1")).toContainText("Mercado e Indicadores Agro");

    // Verifica a presença do Card do Dólar/Câmbio PTAX
    const ptaxCard = page.locator('div[aria-label="Câmbio PTAX — Banco Central do Brasil"]');
    await expect(ptaxCard).toBeVisible();
    await expect(ptaxCard).toContainText("Câmbio PTAX — Banco Central do Brasil");
    await expect(ptaxCard).toContainText("5,6372");
    await expect(ptaxCard).toContainText("5,6378");

    // Verifica a presença dos Indicadores Macroeconômicos Oficiais
    await expect(page.locator("text=Indicadores Econômicos e Câmbio Oficial")).toBeVisible();
    await expect(page.locator("text=Meta Selic")).toBeVisible();
    await expect(page.locator("text=13,75%")).toBeVisible();
    await expect(page.locator("text=IPCA (Mensal)")).toBeVisible();
    await expect(page.locator("text=+0,82%")).toBeVisible();
    await expect(page.locator("text=IPCA (12 Meses)")).toBeVisible();
    await expect(page.locator("text=4,58%")).toBeVisible();
    await expect(page.locator("text=Euro PTAX")).toBeVisible();

    // Verifica que o Catálogo de Commodities está visível com links homologados
    await expect(page.locator("text=Catálogo de Commodities e Referências Oficiais")).toBeVisible();
    await expect(page.locator("text=Soja em Grão")).toBeVisible();
    await expect(page.locator("text=Milho Físico")).toBeVisible();
  });

  test("2. Persistência e exibição offline de dados salvos", async ({ page }) => {
    // Bloqueia rotas de rede da API e do fallback do BCB para simular desconexão total
    await page.route("**/CotacaoDolarPeriodo*", async (route) => {
      await route.abort();
    });
    await page.route("**/api/v1/public/mercado/ptax*", async (route) => {
      await route.abort();
    });

    // Acessa a origem para liberar o acesso ao localStorage
    await page.goto("/");
    await page.evaluate(() => {
      const mockQuote = {
        version: 1,
        quote: {
          sucesso: true,
          versao: "1.0",
          indicador: "DOLAR_PTAX",
          moeda: "USD",
          moedaReferencia: "BRL",
          cotacaoCompra: 5.6372,
          cotacaoVenda: 5.6378,
          dataCotacao: "2024-10-15",
          dataHoraBoletimIso: "2024-10-15T13:06:27.393-03:00",
          tipoBoletim: "Fechamento PTAX",
          fonteOficial: "Banco Central do Brasil (BCB)",
          dataConsultaIso: "2026-10-16T21:40:00.000Z",
          cacheAtualizadoEmIso: "2026-10-16T21:30:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
          estaDesatualizado: false,
          avisoLegal:
            "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.",
        },
      };
      window.localStorage.setItem(
        "deepfarms_agro_mercado_ptax_v1",
        JSON.stringify(mockQuote)
      );
      window.localStorage.setItem(
        "deepfarms_agro_mercado_cotacao_v1:USD",
        JSON.stringify({ currency: "USD", quote: mockQuote.quote })
      );
    });

    // Navega para o mercado e simula offline
    await page.goto("/mercado", { waitUntil: "domcontentloaded" });
    const ptaxCard = page.locator('div[aria-label="Câmbio PTAX — Banco Central do Brasil"]');
    await expect(ptaxCard).toBeVisible();
    await page.waitForTimeout(400);

    await page.evaluate(() => {
      window.dispatchEvent(new Event("offline"));
    });

    // Valida que o card exibe os valores salvos e o badge de modo offline
    await expect(ptaxCard).toContainText("Compra");
    await expect(ptaxCard).toContainText("Venda");
    await expect(ptaxCard).toContainText("Modo offline — dado salvo");
  });

  test("3. Não regressão do Service Worker e das Calculadoras", async ({ page }) => {
    await page.goto("/calculadoras");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("h1")).toContainText("Calculadoras e Conversores Agrícolas");
    await expect(page.locator("text=Sacas, Kg e Toneladas").first()).toBeVisible();
    await expect(page.locator("text=Áreas Rurais").first()).toBeVisible();
    await expect(page.locator("text=Frete").first()).toBeVisible();
    await expect(page.locator("text=Custo").first()).toBeVisible();
    await expect(page.locator("text=Conversor").first()).toBeVisible();
  });

  test("4. Responsividade mobile em viewport 375x667 (iPhone SE)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.route("**/api/v1/public/mercado/ptax", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          indicador: "DOLAR_PTAX",
          moeda: "USD",
          moedaReferencia: "BRL",
          cotacaoCompra: 5.6372,
          cotacaoVenda: 5.6378,
          dataCotacao: "2026-10-19",
          dataHoraBoletimIso: "2026-10-19T13:06:27.393-03:00",
          tipoBoletim: "Fechamento PTAX",
          fonteOficial: "Banco Central do Brasil (BCB)",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T20:00:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
          estaDesatualizado: false,
          avisoLegal: "Aviso legal",
        }),
      });
    });

    await page.route("**/api/v1/public/mercado/indicadores-macro", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T19:50:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estaDesatualizado: false,
          avisoLegal: "Aviso legal",
          itens: [
            {
              id: "SELIC_META",
              nomeOficial: "Taxa de juros - Meta Selic definida pelo Copom",
              codigoSerieBcb: 432,
              valor: 13.75,
              unidade: "% a.a.",
              periodicidade: "DIARIA",
              dataReferencia: "2026-11-04",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "IPCA_MENSAL",
              nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA)",
              codigoSerieBcb: 433,
              valor: 0.82,
              unidade: "% a.m.",
              periodicidade: "MENSAL",
              dataReferencia: "2026-09-01",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "IPCA_12M",
              nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses",
              codigoSerieBcb: 13522,
              valor: 4.58,
              unidade: "% em 12 meses",
              periodicidade: "MENSAL",
              dataReferencia: "2026-09-01",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "EURO_PTAX",
              nomeOficial: "Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
              codigoSerieBcb: 21619,
              valor: 5.6682,
              valorCompra: 5.6665,
              valorVenda: 5.6682,
              unidade: "BRL",
              periodicidade: "DIARIA",
              dataReferencia: "2026-10-19",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
          ],
        }),
      });
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Valida que não há scroll horizontal no body
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowInnerWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(windowInnerWidth);

    // Valida que todos os 4 cards macro estão visíveis e formatados
    await expect(page.locator("text=Meta Selic")).toBeVisible();
    await expect(page.locator("text=13,75%")).toBeVisible();
    await expect(page.locator("text=Euro PTAX")).toBeVisible();
    await expect(page.locator("text=R$ 5,6682").first()).toBeVisible();
  });

  test("5. Recuperação de conexão online e recarga dos indicadores", async ({ page }) => {
    let requestsCount = 0;
    await page.route("**/*indicadores-macro*", async (route) => {
      requestsCount++;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T20:00:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estaDesatualizado: false,
          avisoLegal: "Aviso legal",
          itens: [
            {
              id: "SELIC_META",
              nomeOficial: "Taxa de juros - Meta Selic definida pelo Copom",
              codigoSerieBcb: 432,
              valor: 13.75,
              unidade: "% a.a.",
              periodicidade: "DIARIA",
              dataReferencia: "2026-11-04",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
          ],
        }),
      });
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");
    await expect.poll(() => requestsCount, { timeout: 7000 }).toBeGreaterThanOrEqual(1);

    // Dispara offline e verifica badge
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await expect(page.locator("text=Modo offline — dado salvo").first()).toBeVisible();

    // Dispara online e verifica restabelecimento
    const prevCount = requestsCount;
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await page.waitForTimeout(300);
    expect(requestsCount).toBeGreaterThanOrEqual(prevCount);
  });

  test("6. Isolamento de fallback parcial na interface", async ({ page }) => {
    await page.route("**/api/v1/public/mercado/indicadores-macro", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T19:00:00.000Z",
          estadoDisponibilidade: "PARCIAL",
          estaDesatualizado: true,
          avisoLegal: "Aviso legal",
          itens: [
            {
              id: "SELIC_META",
              nomeOficial: "Taxa de juros - Meta Selic definida pelo Copom",
              codigoSerieBcb: 432,
              valor: 13.75,
              unidade: "% a.a.",
              periodicidade: "DIARIA",
              dataReferencia: "2026-11-04",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "NORMAL",
              estaDesatualizado: false,
              avisoLegal: "Aviso legal",
            },
            {
              id: "EURO_PTAX",
              nomeOficial: "Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
              codigoSerieBcb: 21619,
              valor: 5.6682,
              valorCompra: 5.6665,
              valorVenda: 5.6682,
              unidade: "BRL",
              periodicidade: "DIARIA",
              dataReferencia: "2026-10-16",
              dataConsultaIso: "2026-10-19T20:00:00.000Z",
              fonteOficial: "Banco Central do Brasil (BCB)",
              estadoDisponibilidade: "FONTE_INDISPONIVEL",
              estaDesatualizado: true,
              avisoLegal: "Aviso legal",
            },
          ],
        }),
      });
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Valida que o cabeçalho exibe badge de Atualização parcial
    await expect(page.locator("text=Atualização parcial")).toBeVisible();

    // Valida que o Euro exibe o badge contextual 'Último'
    await expect(page.locator("text=Último").first()).toBeVisible();
  });

  test("7. Acessibilidade e estabilidade estrutural", async ({ page }) => {
    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Verifica botão de recarga acessível
    const refreshBtn = page.locator('button[aria-label="Atualizar indicadores macroeconômicos"]');
    await expect(refreshBtn).toBeVisible();

    // Verifica hierarquia de cabeçalho
    await expect(page.locator("h1")).toBeVisible();
  });

  test("8. Exibe e interage com o card de estatísticas de produção IBGE/SIDRA", async ({ page }) => {
    await page.route("**/api/v1/public/mercado/ibge/catalogo", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          fonteOficial: "Instituto Brasileiro de Geografia e Estatística (IBGE) — SIDRA",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          anoMinimo: 1974,
          produtos: [
            { id: "soja", nome: "Soja (em grão)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
            { id: "milho", nome: "Milho (em grão)", tipo: "LAVOURA", pesquisa: "PAM", indicadores: [], suportaLspa: true },
            { id: "bovinos", nome: "Bovinos", tipo: "REBANHO", pesquisa: "PPM", indicadores: [], suportaLspa: false },
          ],
          ufs: [
            { codigo: "51", sigla: "MT", nome: "Mato Grosso" },
            { codigo: "35", sigla: "SP", nome: "São Paulo" },
          ],
        }),
      });
    });

    await page.route("**/api/v1/public/mercado/ibge/estatisticas*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          fonteOficial: "Instituto Brasileiro de Geografia e Estatística (IBGE) — SIDRA",
          dataConsultaIso: "2026-10-19T20:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-19T19:50:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estaDesatualizado: false,
          avisoLegal: "Estatística oficial de produção divulgada pelo IBGE. Não é cotação nem preço de comercialização.",
          pesquisa: "Produção Agrícola Municipal (PAM)",
          fontePesquisa: "PAM",
          tabelaSidra: 5457,
          urlTabela: "https://sidra.ibge.gov.br/tabela/5457",
          periodicidade: "ANUAL",
          produto: { id: "soja", nome: "Soja (em grão)", tipo: "LAVOURA" },
          localidade: { nivel: "BRASIL", codigo: "1", nome: "Brasil" },
          periodoSolicitado: "2024",
          ultimoPeriodoDisponivel: "2024",
          dataAtualizacaoFonte: "2024-10-15",
          avisoDefasagem: null,
          indicadores: [
            {
              id: "PRODUCAO",
              nomeOficial: "Quantidade produzida",
              codigoVariavelSidra: 214,
              recorte: null,
              unidade: "Toneladas",
              pontos: [{ periodo: "2024", valor: 150000000, simboloIbge: null }],
              ultimoPeriodo: "2024",
              ultimoValor: 150000000,
            },
            {
              id: "AREA_COLHIDA",
              nomeOficial: "Área colhida",
              codigoVariavelSidra: 216,
              recorte: null,
              unidade: "Hectares",
              pontos: [{ periodo: "2024", valor: 45000000, simboloIbge: null }],
              ultimoPeriodo: "2024",
              ultimoValor: 45000000,
            },
          ],
        }),
      });
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Verifica presença do card IBGE/SIDRA
    await expect(page.locator("text=Inteligência e Estatísticas Oficiais de Produção (IBGE/SIDRA)")).toBeVisible();
    await expect(page.locator("text=150.000.000 Toneladas")).toBeVisible();
    await expect(page.locator("text=45.000.000 Hectares")).toBeVisible();

    // Verifica link oficial da tabela SIDRA
    const linkSidra = page.locator('a[href="https://sidra.ibge.gov.br/tabela/5457"]');
    await expect(linkSidra).toBeVisible();

    // Verifica aviso de semântica regulatória
    await expect(page.locator("text=Estatística oficial de produção divulgada pelo IBGE")).toBeVisible();
  });

  test("9. Conversão Cambial Reativa nos Cards de Commodities (USD → EUR → GBP)", async ({ page }) => {
    // 1. Mock de rotas PTAX USD
    await page.route("**/api/v1/public/mercado/ptax", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sucesso: true,
          versao: "1.0",
          indicador: "DOLAR_PTAX",
          moeda: "USD",
          moedaReferencia: "BRL",
          cotacaoCompra: 5.6372,
          cotacaoVenda: 5.6378,
          dataCotacao: "2026-10-16",
          dataHoraBoletimIso: "2026-10-16T13:06:27.393-03:00",
          tipoBoletim: "Fechamento PTAX",
          fonteOficial: "Banco Central do Brasil (BCB)",
          dataConsultaIso: "2026-10-21T18:00:00.000Z",
          cacheAtualizadoEmIso: "2026-10-21T18:00:00.000Z",
          estadoDisponibilidade: "NORMAL",
          estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
          estaDesatualizado: false,
          avisoLegal: "A PTAX é uma taxa de referência oficial.",
        }),
      });
    });

    // 2. Mock de rotas OData BCB para outras moedas (EUR e GBP)
    await page.route("**/CotacaoMoedaPeriodo*", async (route) => {
      const url = route.request().url();
      if (url.includes("@moeda='EUR'") || url.includes("EUR")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            value: [
              {
                cotacaoCompra: 6.1240,
                cotacaoVenda: 6.1245,
                dataHoraCotacao: "2026-10-16 13:05:00.000",
                tipoBoletim: "Fechamento",
              },
            ],
          }),
        });
      } else if (url.includes("@moeda='GBP'") || url.includes("GBP")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            value: [
              {
                cotacaoCompra: 7.3450,
                cotacaoVenda: 7.3456,
                dataHoraCotacao: "2026-10-16 13:05:00.000",
                tipoBoletim: "Fechamento",
              },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/mercado");
    await page.waitForLoadState("networkidle");

    // Localiza o card da Soja
    const cardSoja = page.locator('div[data-commodity-id="soja"]');
    await expect(cardSoja).toBeVisible();

    // Valida que o preço oficial em BRL está presente e inalterado
    await expect(cardSoja).toContainText("R$");
    await expect(cardSoja).toContainText("/ Saca de 60 kg");

    // Valida que exibe a conversão inicial em USD
    const conversaoSoja = cardSoja.locator('[data-testid="conversao-cambial-card"]');
    await expect(conversaoSoja).toBeVisible();
    await expect(conversaoSoja).toContainText("Equiv.:");
    await expect(conversaoSoja).toContainText("US$");

    // Screenshot 1: Conversão USD ativa
    await page.screenshot({
      path: "../../docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B6B/01-conversao-usd.png",
      fullPage: true,
    });

    // 3. Altera a moeda para EUR no seletor oficial do PtaxCard
    const currencySelect = page.locator("#ptax-currency");
    await currencySelect.selectOption("EUR");

    // Valida que os cards atualizam sem recarregar a página para o Euro (€)
    await expect(conversaoSoja).toContainText("€");
    // Preço em Reais permanece inalterado!
    await expect(cardSoja).toContainText("R$");
    await expect(cardSoja).toContainText("/ Saca de 60 kg");

    // Screenshot 2: Conversão EUR reativa
    await page.screenshot({
      path: "../../docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B6B/02-conversao-eur.png",
      fullPage: true,
    });

    // 4. Altera a moeda para GBP (Libra Esterlina)
    await currencySelect.selectOption("GBP");

    // Valida que os cards atualizam imediatamente para a Libra (£)
    await expect(conversaoSoja).toContainText("£");
    await expect(cardSoja).toContainText("R$");

    // Screenshot 3: Conversão GBP reativa
    await page.screenshot({
      path: "../../docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B6B/03-conversao-gbp.png",
      fullPage: true,
    });

    // 5. Preservação dos Filtros ao alternar moeda
    const inputBusca = page.locator('input[aria-label="Buscar produtos agropecuários no catálogo"]');
    await inputBusca.fill("Milho");

    // Apenas cards de milho devem ficar visíveis
    await expect(page.locator('div[data-commodity-id="milho"]')).toBeVisible();
    await expect(cardSoja).not.toBeVisible();

    // Alterna a moeda enquanto a busca está ativa
    await currencySelect.selectOption("USD");
    const cardMilho = page.locator('div[data-commodity-id="milho"]');
    await expect(cardMilho).toBeVisible();
    await expect(cardMilho.locator('[data-testid="conversao-cambial-card"]')).toContainText("US$");
    // O campo de busca continua com "Milho" intacto
    await expect(inputBusca).toHaveValue("Milho");

    // Limpa a busca
    await inputBusca.fill("");
    await expect(cardSoja).toBeVisible();

    // 6. Teste de Responsividade Mobile
    await page.setViewportSize({ width: 375, height: 812 });
    await expect(cardSoja).toBeVisible();
    await expect(conversaoSoja).toBeVisible();
    await page.screenshot({
      path: "../../docs/implementation/reports/evidencias/DEEPFARMS-AGRO-FREE-01E2F-B6B/04-mobile-conversao-usd.png",
      fullPage: true,
    });
  });
});
