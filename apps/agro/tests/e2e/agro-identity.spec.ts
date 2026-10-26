import { test, expect } from "@playwright/test";

test.describe("DEEPFARMS-AGRO-FREE-01E2F-C2 — Identidade Individual Segregada E2E", () => {
  test.beforeEach(async ({ page }) => {
    page.on("pageerror", (exception) => {
      console.log(`[Browser PageError]: ${exception.message}`);
    });
  });

  test("1. Usuário anônimo acessa funcionalidades públicas sem qualquer bloqueio", async ({ page }) => {
    // 1.1 Início
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("h1")).toBeVisible();

    // 1.2 Mercado (PTAX + Indicadores BCB + IBGE/SIDRA)
    await page.goto("/mercado");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.getByText("Mercado e Indicadores Agro")).toBeVisible();

    // 1.3 Calculadoras Rurais
    await page.goto("/calculadoras");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.getByText("Calculadoras e Conversores Agrícolas")).toBeVisible();


  });

  test("2. Acesso à área de Conta Individual via Header (Desktop)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const contaButton = page.locator("header").getByRole("link", { name: /Minha Conta|Conta/i });
    await expect(contaButton).toBeVisible();
    await contaButton.click();

    await page.waitForURL("**/conta");
    await expect(page.getByText("Minha Conta DeepFarms Agro")).toBeVisible();
    await expect(page.getByText("Conta Individual DeepFarms Agro")).toBeVisible();
    await expect(page.getByText("Acesso Público 100% Gratuito e Anônimo")).toBeVisible();
  });

  test("3. Acesso à área de Conta Individual via Bottom Nav (Mobile)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const bottomContaLink = page.locator("nav[aria-label='Navegação móvel']").getByRole("link", { name: "Conta" });
    await expect(bottomContaLink).toBeVisible();
    await bottomContaLink.click();

    await page.waitForURL("**/conta");
    await expect(page.getByText("Minha Conta DeepFarms Agro")).toBeVisible();
  });

  test("4. Alternância entre abas de Login, Cadastro e Recuperação de Senha", async ({ page }) => {
    await page.goto("/conta");
    await page.waitForLoadState("domcontentloaded");

    // Aba Inicial: Entrar
    await expect(page.getByRole("button", { name: "Entrar na Conta Individual" })).toBeVisible();

    // Alternar para Cadastrar
    const btnCadastrarTab = page.locator("button", { hasText: "Cadastrar" });
    await btnCadastrarTab.click();
    await expect(page.getByRole("button", { name: "Criar Conta Individual Gratuita" })).toBeVisible();
    await expect(page.getByLabel("Nome Completo")).toBeVisible();

    // Voltar para Entrar
    const btnEntrarTab = page.locator("button", { hasText: "Entrar" });
    await btnEntrarTab.click();
    await expect(page.getByRole("button", { name: "Entrar na Conta Individual" })).toBeVisible();

    // Clicar em Esqueceu a senha?
    await page.getByRole("button", { name: "Esqueceu a senha?" }).click();
    await expect(page.getByLabel("E-mail cadastrado")).toBeVisible();
    await expect(page.getByRole("button", { name: "Solicitar Código" })).toBeVisible();
  });

  test("5. Apresentação das garantias de segurança: HttpOnly, Zero localStorage e Isolamento", async ({ page }) => {
    await page.goto("/conta");
    await page.waitForLoadState("domcontentloaded");

    // Verifica garantia declarada na interface
    await expect(page.getByText(/Sessões HttpOnly SameSite protegidas/i)).toBeVisible();

    // Garante que nenhum token sensível está exposto em localStorage
    const localStorageKeys = await page.evaluate(() => Object.keys(localStorage));
    const sensitiveKeys = localStorageKeys.filter((k) =>
      k.toLowerCase().includes("token") || k.toLowerCase().includes("jwt") || k.toLowerCase().includes("bearer")
    );
    expect(sensitiveKeys).toEqual([]);
  });

  test("6. Fluxo completo E2E: Cadastro, Confirmação de E-mail, Sessão Persistente e Logout", async ({ page }) => {
    let mockUser: {
      id: string;
      email: string;
      nome: string;
      ativo: boolean;
      emailVerificado: boolean;
      createdAt: string;
    } = {
      id: "usr-e2e-1234-uuid",
      email: "produtor_e2e@agro.com.br",
      nome: "Produtor E2E Homologado",
      ativo: true,
      emailVerificado: false,
      createdAt: "2026-10-20T10:00:00Z",
    };
    let isLoggedIn = false;

    // Roteamento mock do backend no navegador
    await page.route("**/api/v1/auth/me", async (route) => {
      if (!isLoggedIn) {
        await route.fulfill({ status: 401, json: { detail: "Não autenticado" } });
      } else {
        await route.fulfill({ status: 200, json: mockUser });
      }
    });

    await page.route("**/api/v1/auth/register-free", async (route) => {
      isLoggedIn = true;
      await route.fulfill({
        status: 201,
        headers: {
          "set-cookie": "deepfarms_agro_session=mock_cookie_jwt_e2e; HttpOnly; SameSite=Lax; Path=/",
        },
        json: {
          sucesso: true,
          mensagem: "Conta individual criada com sucesso.",
          token: "mock_jwt_token",
          usuario: mockUser,
        },
      });
    });

    await page.route("**/api/v1/auth/verify-email", async (route) => {
      const body = route.request().postDataJSON();
      if (body.codigo === "482910") {
        mockUser.emailVerificado = true;
        await route.fulfill({ status: 200, json: { sucesso: true, mensagem: "E-mail verificado com sucesso." } });
      } else {
        await route.fulfill({ status: 400, json: { detail: "Código incorreto." } });
      }
    });

    await page.route("**/api/v1/auth/logout", async (route) => {
      isLoggedIn = false;
      await route.fulfill({ status: 200, json: { sucesso: true, mensagem: "Sessão encerrada com sucesso." } });
    });

    // 6.1 Navega para a tela de conta
    await page.goto("/conta");
    await page.waitForLoadState("domcontentloaded");

    // 6.2 Alterna para a aba de cadastro
    await page.locator("button", { hasText: "Cadastrar" }).click();
    await page.getByLabel("Nome Completo").fill("Produtor E2E Homologado");
    await page.locator("#reg-email").fill("produtor_e2e@agro.com.br");
    await page.locator("#reg-senha").fill("SenhaSegura123!@");
    await page.getByRole("button", { name: "Criar Conta Individual Gratuita" }).click();

    // 6.3 Verifica se entrou na área autenticada com e-mail pendente
    await expect(page.getByText("Produtor E2E Homologado")).toBeVisible();
    await expect(page.getByText("Confirmação de E-mail Pendente")).toBeVisible();
    await expect(page.getByText("Pendente de confirmação")).toBeVisible();

    // 6.4 Preenche o código de 6 dígitos no formulário e confirma
    const inputCodigo = page.locator("#input-codigo-verificacao");
    await expect(inputCodigo).toBeVisible();
    await inputCodigo.fill("482910");
    await page.getByRole("button", { name: "Confirmar Código" }).click();

    // 6.5 Comprova transição para estado verificado
    await expect(page.getByText(/E-mail verificado com sucesso/i)).toBeVisible();
    await expect(page.getByText("Verificado", { exact: true })).toBeVisible();

    // 6.6 Comprova persistência de sessão após reload da página
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await expect(page.getByText("Produtor E2E Homologado")).toBeVisible();
    await expect(page.getByText("Verificado", { exact: true })).toBeVisible();

    // 6.7 Executa logout seguro
    await page.getByRole("button", { name: "Sair da conta" }).click();
    await expect(page.getByText("Sessão encerrada com sucesso.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Entrar na Conta Individual" })).toBeVisible();
  });

  test("7. Fluxo completo E2E: Recuperação de Senha e Autenticação (Login)", async ({ page }) => {
    let mockUser = {
      id: "usr-e2e-reset-uuid",
      email: "recuperacao@agro.com.br",
      nome: "Produtor Redefinido",
      ativo: true,
      emailVerificado: true,
      createdAt: "2026-10-20T10:00:00Z",
    };
    let currentPassword = "SenhaAntiga123!";
    let isLoggedIn = false;

    await page.route("**/api/v1/auth/me", async (route) => {
      if (!isLoggedIn) {
        await route.fulfill({ status: 401, json: { detail: "Não autenticado" } });
      } else {
        await route.fulfill({ status: 200, json: mockUser });
      }
    });

    await page.route("**/api/v1/auth/forgot-password", async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          sucesso: true,
          mensagem: "Instruções enviadas com sucesso.",
          tokenSimulado: "tok-e2e-simulado-reset",
        },
      });
    });

    await page.route("**/api/v1/auth/reset-password", async (route) => {
      const body = route.request().postDataJSON();
      if (body.token === "tok-e2e-simulado-reset") {
        currentPassword = body.novaSenha;
        await route.fulfill({ status: 200, json: { sucesso: true, mensagem: "Senha redefinida com sucesso." } });
      } else {
        await route.fulfill({ status: 400, json: { detail: "Token inválido." } });
      }
    });

    await page.route("**/api/v1/auth/login", async (route) => {
      const body = route.request().postDataJSON();
      if (body.senha === currentPassword) {
        isLoggedIn = true;
        await route.fulfill({
          status: 200,
          headers: {
            "set-cookie": "deepfarms_agro_session=mock_cookie_jwt_e2e_new; HttpOnly; SameSite=Lax; Path=/",
          },
          json: {
            sucesso: true,
            mensagem: "Autenticado com sucesso.",
            token: "mock_jwt_token_new",
            usuario: mockUser,
          },
        });
      } else {
        await route.fulfill({ status: 401, json: { detail: "E-mail ou senha incorretos." } });
      }
    });

    // 7.1 Navega para /conta
    await page.goto("/conta");
    await page.waitForLoadState("domcontentloaded");

    // 7.2 Clica em 'Esqueceu a senha?'
    await page.getByRole("button", { name: "Esqueceu a senha?" }).click();
    await page.locator("#forgot-email").fill("recuperacao@agro.com.br");
    await page.getByRole("button", { name: "Solicitar Código" }).click();

    // 7.3 Formulário transita para a etapa de confirmação de senha
    await expect(page.locator("#reset-token")).toBeVisible();
    await page.locator("#reset-nova-senha").fill("NovaSenhaSegura456!@");
    await page.getByRole("button", { name: "Salvar Nova Senha" }).click();

    // 7.4 Retorna para tela de login com mensagem de sucesso
    await expect(page.getByText("Senha redefinida com sucesso.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Entrar na Conta Individual" })).toBeVisible();

    // 7.5 Autentica com a nova senha
    await page.locator("#login-email").fill("recuperacao@agro.com.br");
    await page.locator("#login-senha").fill("NovaSenhaSegura456!@");
    await page.getByRole("button", { name: "Entrar na Conta Individual" }).click();

    // 7.6 Verifica entrada no perfil
    await expect(page.getByRole("heading", { name: "Produtor Redefinido" })).toBeVisible();
    await expect(page.getByText("Sessão HttpOnly Segregada")).toBeVisible();
  });
});
