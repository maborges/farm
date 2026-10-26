import { expect, test } from "@playwright/test";

// Fixture sintética representativa para testes visuais de interface
const FIXTURE_SINTETICA_COMPLETA = {
  latitude: -23.55,
  longitude: -46.63,
  latitudeGrid: -23.55,
  longitudeGrid: -46.65,
  fusoHorario: "America/Sao_Paulo",
  provedor: "TEST_METEO_FIXTURE",
  licencaFonte: "Ambiente Controlado E2E",
  tipoDado: "PREVISTO",
  dadosSinteticos: true,
  temperaturaAtualC: 24.8,
  sensacaoTermicaC: 25.2,
  umidadeRelativaPct: 68,
  ventoVelocidadeKmH: 15.5,
  ventoDirecaoGraus: 135,
  ventoRajadasKmH: 26.0,
  precipitacaoMm: 0.0,
  probabilidadeChuvaPct: 15,
  condicaoDescricao: "Parcialmente nublado",
  condicaoIcone: "cloudsun",
  previsaoHoraria: Array.from({ length: 24 }, (_, i) => ({
    horaIso: new Date(Date.now() + i * 3600000).toISOString(),
    temperaturaC: 20 + (i % 6),
    sensacaoTermicaC: 20 + (i % 6),
    umidadePct: 60 + (i % 25),
    ventoKmH: 12 + (i % 8),
    ventoDirecaoGraus: (i * 25) % 360,
    ventoRajadasKmH: 18 + (i % 10),
    precipitacaoMm: i % 4 === 0 ? 1.5 : 0.0,
    probabilidadeChuvaPct: i % 4 === 0 ? 60 : 10,
    condicaoDescricao: i % 4 === 0 ? "Pancadas de chuva" : "Parcialmente nublado",
    condicaoIcone: i % 4 === 0 ? "cloudrain" : "cloudsun",
  })),
  previsaoDiaria: [
    {
      dataIso: "2026-10-22",
      diaSemana: "qui",
      tempMinC: 18.0,
      tempMaxC: 28.5,
      precipitacaoMm: 0.0,
      probabilidadeChuvaPct: 10,
      ventoMaxKmH: 25.0,
      condicaoDescricao: "Sol com algumas nuvens",
      condicaoIcone: "cloudsun",
    },
    {
      dataIso: "2026-10-23",
      diaSemana: "sex",
      tempMinC: 19.5,
      tempMaxC: 30.0,
      precipitacaoMm: 4.2,
      probabilidadeChuvaPct: 65,
      ventoMaxKmH: 28.0,
      condicaoDescricao: "Pancadas isoladas",
      condicaoIcone: "cloudrain",
    },
    {
      dataIso: "2026-10-24",
      diaSemana: "sáb",
      tempMinC: 17.0,
      tempMaxC: 24.0,
      precipitacaoMm: 12.0,
      probabilidadeChuvaPct: 80,
      ventoMaxKmH: 35.0,
      condicaoDescricao: "Chuva moderada",
      condicaoIcone: "cloudrain",
    },
    {
      dataIso: "2026-10-25",
      diaSemana: "dom",
      tempMinC: 16.5,
      tempMaxC: 23.0,
      precipitacaoMm: 2.0,
      probabilidadeChuvaPct: 40,
      ventoMaxKmH: 20.0,
      condicaoDescricao: "Nublado",
      condicaoIcone: "cloud",
    },
    {
      dataIso: "2026-10-26",
      diaSemana: "seg",
      tempMinC: 18.0,
      tempMaxC: 27.0,
      precipitacaoMm: 0.0,
      probabilidadeChuvaPct: 15,
      ventoMaxKmH: 18.0,
      condicaoDescricao: "Tempo firme",
      condicaoIcone: "sun",
    },
    {
      dataIso: "2026-10-27",
      diaSemana: "ter",
      tempMinC: 19.0,
      tempMaxC: 29.0,
      precipitacaoMm: 0.0,
      probabilidadeChuvaPct: 20,
      ventoMaxKmH: 22.0,
      condicaoDescricao: "Sol",
      condicaoIcone: "sun",
    },
    {
      dataIso: "2026-10-28",
      diaSemana: "qua",
      tempMinC: 20.0,
      tempMaxC: 31.0,
      precipitacaoMm: 1.0,
      probabilidadeChuvaPct: 35,
      ventoMaxKmH: 24.0,
      condicaoDescricao: "Sol com nuvens",
      condicaoIcone: "cloudsun",
    },
  ],
  horarioReferenciaIso: new Date().toISOString(),
  obtidoEmIso: new Date().toISOString(),
  validoAteIso: new Date(Date.now() + 1800000).toISOString(),
  emCache: false,
  desatualizado: false,
  statusOperacional: "NORMAL",
  avisoLegal: "Dados sintéticos gerados para validação de layout E2E.",
};

test.describe("CLIMA-01D — Dashboard Meteorológico e Previsão do Tempo", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/clima");
    await page.evaluate(() => {
      localStorage.clear();
    });
    await page.reload();
  });

  // -------------------------------------------------------------------------
  // 1. Integração Real com FastAPI (sem mock): Provedor Não Licenciado (HTTP 503)
  // -------------------------------------------------------------------------
  test("integração real Next.js + FastAPI: localidade selecionada recebe HTTP 503 com governança de licença", async ({
    page,
  }) => {
    await page.goto("/clima");

    // Seleciona Santos/SP através do catálogo oficial real
    await page.locator("#btn-abrir-seletor-localidade").click();
    await page.locator("#input-busca-municipio").fill("Santos");
    const optSantos = page.getByRole("option", { name: /Santos.*SP/i });
    await expect(optSantos).toBeVisible({ timeout: 5000 });
    await optSantos.click();

    // Valida que o card da localidade foi preenchido
    await expect(page.locator("#card-localidade-ativa")).toBeVisible();
    await expect(page.getByText("Santos — SP")).toBeVisible();

    // A consulta real a GET /api/v1/public/clima/previsao?lat=...&lon=... retorna HTTP 503
    // pois OPEN_METEO_LICENSED=False por conformidade estrita de governança
    const estadoNaoLicenciado = page.locator("#estado-provedor-nao-licenciado");
    await expect(estadoNaoLicenciado).toBeVisible({ timeout: 10000 });
    await expect(
      estadoNaoLicenciado.getByRole("paragraph").first()
    ).toContainText("Serviço Meteorológico em Atualização");
    await expect(
      estadoNaoLicenciado.getByText("Em Atualização", { exact: true })
    ).toBeVisible();
    await expect(
      estadoNaoLicenciado.getByRole("link", { name: "Continuar usando a aplicação" })
    ).toHaveAttribute("href", "/");
  });

  test("HTTP 503 mantém a previsão salva visível e informa a contingência", async ({ page }) => {
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Serviço meteorológico temporariamente indisponível.",
        }),
      });
    });

    await page.evaluate((dadosPrevisao) => {
      const lat = -23.55;
      const lon = -46.63;
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "São Paulo",
            uf: "SP",
            codigoIbge: 3550308,
            latitude: lat,
            longitude: lon,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
      localStorage.setItem(
        `deepfarms_agro_clima_previsao_v1:${lat.toFixed(2)}_${(-46.65).toFixed(2)}`,
        JSON.stringify({
          version: 1,
          localidadeNome: "São Paulo",
          salvoEmIso: new Date(Date.now() - 300000).toISOString(),
          validoAteIso: new Date(Date.now() + 1800000).toISOString(),
          dados: dadosPrevisao,
        })
      );
    }, FIXTURE_SINTETICA_COMPLETA);

    await page.reload();

    await expect(page.locator("#estado-servico-indisponivel-com-cache")).toBeVisible();
    await expect(page.locator("#dashboard-meteorologico-ativo")).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 2. Dashboard Completo Desktop (com Fixture Sintética Homologada)
  // -------------------------------------------------------------------------
  test("renderização completa do dashboard desktop: condições atuais, 24h, 7 dias e aviso agronômico", async ({
    page,
  }) => {
    // Intercepta a rota para retornar dados sintéticos claramente rotulados
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(FIXTURE_SINTETICA_COMPLETA),
      });
    });

    // Pré-configura localidade no localStorage para abrir diretamente
    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Ribeirão Preto",
            uf: "SP",
            codigoIbge: 3543402,
            latitude: -21.1767,
            longitude: -47.8208,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();

    // Valida o dashboard ativo
    await expect(page.locator("#dashboard-meteorologico-ativo")).toBeVisible();

    // 1. Badge explícito de dados sintéticos de teste
    await expect(page.locator("#badge-dados-sinteticos")).toBeVisible();
    await expect(page.locator("#badge-dados-sinteticos")).toContainText("Dados Sintéticos");

    // 2. Card de Condições Atuais
    const cardAtuais = page.locator("#card-condicoes-atuais");
    await expect(cardAtuais).toBeVisible();
    await expect(cardAtuais.locator("#temp-atual-valor")).toContainText("25°");
    await expect(cardAtuais.getByText("Sensação térmica de")).toBeVisible();
    await expect(cardAtuais.getByText("68%")).toBeVisible(); // Umidade
    await expect(cardAtuais.getByText("16 km/h", { exact: false })).toBeVisible(); // Vento arredondado
    await expect(cardAtuais.getByText("Rajadas até 26 km/h")).toBeVisible(); // Rajadas

    // 3. Previsão Horária (24h)
    const horaria = page.locator("#previsao-horaria");
    await expect(horaria).toBeVisible();
    await expect(horaria.getByText("Próximas 24 Horas")).toBeVisible();
    const itensHorarios = horaria.locator("[data-horario-item]");
    await expect(itensHorarios).toHaveCount(24);

    // 4. Previsão Diária (7 dias)
    const diaria = page.locator("#previsao-diaria");
    await expect(diaria).toBeVisible();
    await expect(diaria.getByText("Previsão dos Próximos 7 Dias")).toBeVisible();
    const itensDiarios = diaria.locator("[data-diaria-item]");
    await expect(itensDiarios).toHaveCount(7);

    // 5. Card de Aviso Agronômico
    const avisoAgronomico = page.locator("#card-aviso-agronomico");
    await expect(avisoAgronomico).toBeVisible();
    await expect(avisoAgronomico).toContainText("Diretrizes Agrometeorológicas e Responsabilidade Técnica");
  });

  // -------------------------------------------------------------------------
  // 3. Responsividade em Viewport Mobile (375x667)
  // -------------------------------------------------------------------------
  test("navegação e usabilidade em viewport mobile (375x667) com scroll horizontal", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(FIXTURE_SINTETICA_COMPLETA),
      });
    });

    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Londrina",
            uf: "PR",
            codigoIbge: 4113700,
            latitude: -23.3045,
            longitude: -51.1696,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();

    // Aguarda o dashboard carregar completamente
    await expect(page.locator("#dashboard-meteorologico-ativo")).toBeVisible();
    const scrollContainer = page.locator("#scroll-previsao-horaria");
    await expect(scrollContainer).toBeVisible();
    await expect(scrollContainer.locator("[data-horario-item]").first()).toBeVisible();

    // Valida que o container permite rolagem horizontal (conteúdo maior que viewport)
    const { scrollWidth, clientWidth } = await scrollContainer.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(scrollWidth).toBeGreaterThan(clientWidth);

    // Rola para a direita para testar scroll horizontal no mobile
    await scrollContainer.evaluate((el) => {
      el.scrollTo({ left: 200, behavior: "instant" });
    });

    const scrollPos = await scrollContainer.evaluate((el) => el.scrollLeft);
    expect(scrollPos).toBeGreaterThanOrEqual(100);
  });

  // -------------------------------------------------------------------------
  // 4. Tolerância a Campos Meteorológicos Nulos
  // -------------------------------------------------------------------------
  test("trata campos nulos com placeholders '—' sem crash e sem gerar NaN", async ({
    page,
  }) => {
    const fixtureNulos = {
      ...FIXTURE_SINTETICA_COMPLETA,
      temperaturaAtualC: null,
      sensacaoTermicaC: null,
      umidadeRelativaPct: null,
      ventoVelocidadeKmH: null,
      ventoRajadasKmH: null,
      probabilidadeChuvaPct: null,
      condicaoDescricao: null,
      previsaoHoraria: [
        {
          horaIso: new Date().toISOString(),
          temperaturaC: null,
          umidadePct: null,
          ventoKmH: null,
        },
      ],
      previsaoDiaria: [
        {
          dataIso: "2026-10-22",
          diaSemana: "qui",
          tempMinC: null,
          tempMaxC: null,
        },
      ],
    };

    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(fixtureNulos),
      });
    });

    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Sorriso",
            uf: "MT",
            codigoIbge: 5107925,
            latitude: -12.5431,
            longitude: -55.7214,
            fusoHorario: "America/Cuiaba",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();

    const cardAtuais = page.locator("#card-condicoes-atuais");
    await expect(cardAtuais).toBeVisible();
    // Confirma que não há "NaN" no texto renderizado
    const texto = await cardAtuais.innerText();
    expect(texto).not.toContain("NaN");
    expect(texto).toContain("—");
  });

  // -------------------------------------------------------------------------
  // 5. Erros HTTP: 429 Limite Excedido e 500 Erro de Servidor
  // -------------------------------------------------------------------------
  test("trata HTTP 429 (limite de requisições) com alerta específico", async ({ page }) => {
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({ status: 429, body: "Too Many Requests" });
    });

    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Campinas",
            uf: "SP",
            codigoIbge: 3509502,
            latitude: -22.9056,
            longitude: -47.0608,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();
    await expect(page.locator("#estado-limite-excedido")).toBeVisible();
    await expect(page.locator("#estado-limite-excedido")).toContainText("Limite de consultas de clima atingido");
  });

  test("trata HTTP 500 (erro no servidor) com estado de erro temporário", async ({ page }) => {
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.fulfill({ status: 500, body: "Internal Server Error" });
    });

    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Campinas",
            uf: "SP",
            codigoIbge: 3509502,
            latitude: -22.9056,
            longitude: -47.0608,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();
    await expect(page.locator("#estado-erro-servidor")).toBeVisible();
    await expect(page.locator("#estado-erro-servidor")).toContainText("Serviço meteorológico temporariamente indisponível");
  });

  // -------------------------------------------------------------------------
  // 6. Cache Offline: Sem Conexão com Cache vs Sem Conexão sem Cache
  // -------------------------------------------------------------------------
  test("offline com cache local: exibe dados previamente armazenados e banner informativo", async ({
    page,
  }) => {
    // Interrompe conexões à rota de previsão para simular offline
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.abort("failed");
    });

    // Popula o localStorage com localidade e cache de previsão correspondente
    await page.evaluate((dadosPrevisao) => {
      const lat = -23.55;
      const lon = -46.63;
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "São Paulo",
            uf: "SP",
            codigoIbge: 3550308,
            latitude: lat,
            longitude: lon,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );

      // Chave quantizada
      const cacheKey = `deepfarms_agro_clima_previsao_v1:${lat.toFixed(2)}_${(-46.65).toFixed(2)}`;
      localStorage.setItem(
        cacheKey,
        JSON.stringify({
          version: 1,
          localidadeNome: "São Paulo",
          salvoEmIso: new Date(Date.now() - 300000).toISOString(),
          validoAteIso: new Date(Date.now() + 1800000).toISOString(),
          dados: dadosPrevisao,
        })
      );
    }, FIXTURE_SINTETICA_COMPLETA);

    await page.reload();

    // Deve exibir o estado de aviso offline COM cache
    await expect(page.locator("#estado-offline-com-cache")).toBeVisible();
    // E os dados devem estar visíveis
    await expect(page.locator("#dashboard-meteorologico-ativo")).toBeVisible();
    await expect(page.locator("#card-condicoes-atuais")).toBeVisible();
  });

  test("offline sem cache: exibe aviso de ausência de rede e nenhum dado falso", async ({
    page,
  }) => {
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.abort("failed");
    });

    await page.evaluate(() => {
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "Belo Horizonte",
            uf: "MG",
            codigoIbge: 3106200,
            latitude: -19.9208,
            longitude: -43.9378,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );
    });

    await page.reload();
    await expect(page.locator("#estado-offline-sem-cache")).toBeVisible();
    await expect(page.locator("#dashboard-meteorologico-ativo")).not.toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 7. Dados Desatualizados (Cache Expirado)
  // -------------------------------------------------------------------------
  test("cache com validade expirada exibe banner de dados desatualizados", async ({
    page,
  }) => {
    // Interrompe chamada para manter no cache
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      await route.abort("failed");
    });

    await page.evaluate((dadosPrevisao) => {
      const lat = -23.55;
      const lon = -46.63;
      localStorage.setItem(
        "deepfarms_agro_clima_localidade_v1",
        JSON.stringify({
          version: 1,
          localidade: {
            tipoOrigem: "CENTROIDE_IBGE",
            nome: "São Paulo",
            uf: "SP",
            codigoIbge: 3550308,
            latitude: lat,
            longitude: lon,
            fusoHorario: "America/Sao_Paulo",
          },
          salvoEm: new Date().toISOString(),
        })
      );

      const cacheKey = `deepfarms_agro_clima_previsao_v1:${lat.toFixed(2)}_${(-46.65).toFixed(2)}`;
      localStorage.setItem(
        cacheKey,
        JSON.stringify({
          version: 1,
          localidadeNome: "São Paulo",
          salvoEmIso: new Date(Date.now() - 7200000).toISOString(),
          // Validade expirou há 1 hora
          validoAteIso: new Date(Date.now() - 3600000).toISOString(),
          dados: {
            ...dadosPrevisao,
            desatualizado: true,
            validoAteIso: new Date(Date.now() - 3600000).toISOString(),
          },
        })
      );
    }, FIXTURE_SINTETICA_COMPLETA);

    await page.reload();

    // Deve exibir o banner de dados desatualizados
    await expect(page.locator("#banner-dados-desatualizados")).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // 8. Proteção contra Race Conditions / Respostas Fora de Ordem
  // -------------------------------------------------------------------------
  test("descarte de respostas atrasadas evita sobrescrever nova localidade", async ({
    page,
  }) => {
    // A rota para Cascavel (-24.9558, -53.4552) atrasa 800ms
    // A rota para Maringá (-23.4205, -51.9333) responde imediatamente
    await page.route("**/api/v1/public/clima/previsao*", async (route) => {
      const url = route.request().url();
      if (url.includes("-24.95")) {
        await new Promise((r) => setTimeout(r, 800));
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...FIXTURE_SINTETICA_COMPLETA,
            latitude: -24.9558,
            longitude: -53.4552,
            temperaturaAtualC: 15.0, // Temperatura Cascavel
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...FIXTURE_SINTETICA_COMPLETA,
            latitude: -23.4205,
            longitude: -51.9333,
            temperaturaAtualC: 32.0, // Temperatura Maringá
          }),
        });
      }
    });

    // Inicia selecionando Cascavel
    await page.goto("/clima");
    await page.locator("#btn-abrir-seletor-localidade").click();
    await page.locator("#input-busca-municipio").fill("Cascavel");
    const optCascavel = page.getByRole("option", { name: /Cascavel.*PR/i });
    await expect(optCascavel).toBeVisible({ timeout: 5000 });
    await optCascavel.click();

    // Imediatamente abre o seletor e troca para Maringá antes dos 800ms
    await page.locator("#btn-trocar-localidade-card").click();
    await page.locator("#input-busca-municipio").fill("Maringa");
    const optMaringa = page.getByRole("option", { name: /Maringá.*PR/i });
    await expect(optMaringa).toBeVisible({ timeout: 5000 });
    await optMaringa.click();

    // Valida que Maringá é a localidade ativa e a temperatura reflete 32°C (não 15°C)
    await expect(page.getByText("Maringá — PR")).toBeVisible();
    await expect(page.locator("#card-condicoes-atuais")).toContainText("32°C");

    // Aguarda mais de 1000ms para confirmar que a resposta atrasada de Cascavel não sobrescreveu Maringá
    await page.waitForTimeout(1100);
    await expect(page.locator("#card-localidade-ativa").getByText("Maringá — PR")).toBeVisible();
    await expect(page.locator("#card-condicoes-atuais")).toContainText("32°C");
  });
});
