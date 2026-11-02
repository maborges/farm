import { expect, test } from "@playwright/test";

test.describe("UI/UX Adaptativa do Módulo PWA Agro (Mobile, Tablet e Desktop)", () => {
  test("1. Identifica execução em Celular (Mobile 375x667) e ativa Bottom Dock + App Bar + Bottom Sheet", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    const shell = page.locator("#agro-adaptive-shell");
    await expect(shell).toHaveAttribute("data-device-category", "mobile");
    await expect(shell).toHaveAttribute("data-navigation-pattern", "bottom-dock");

    // Na home mobile, exibe os tiles rápidos estilo App Launcher e a Bottom Dock de 5 itens
    await expect(page.getByTestId("mobile-launcher-tiles")).toBeVisible();
    const bottomDock = page.getByTestId("mobile-bottom-dock");
    await expect(bottomDock).toBeVisible();
    await expect(bottomDock.getByRole("link")).toHaveCount(5);

    // Sidebar lateral permanece oculta no celular
    await expect(page.getByTestId("adaptive-sidebar")).not.toBeVisible();

    // Navega para /clima e valida que o modal de localidade adapta para Bottom Sheet no celular
    await bottomDock.getByRole("link", { name: "Clima" }).click();
    await page.waitForURL("**/clima");

    // No mobile em subpágina, o header exibe botão nativo de voltar e título contextual
    await expect(page.getByRole("link", { name: "Voltar para início" })).toBeVisible();
    await expect(page.getByTestId("agro-app-header")).toContainText("Clima & Pulverização");

    await page.locator("#btn-abrir-seletor-localidade").click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("data-presentation", "bottom-sheet");
  });

  test("2. Identifica execução em Tablet (768x1024) e ativa Navigation Rail retrátil sem Bottom Dock", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/clima");

    const shell = page.locator("#agro-adaptive-shell");
    await expect(shell).toHaveAttribute("data-device-category", "tablet");
    await expect(shell).toHaveAttribute("data-navigation-pattern", "navigation-rail");

    // No tablet, a sidebar funciona como Navigation Rail (inicia retraída para preservar área útil)
    const sidebar = page.getByTestId("adaptive-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toHaveAttribute("data-collapsed", "true");
    await expect(page.getByTestId("mobile-bottom-dock")).not.toBeVisible();

    // Permite expandir e retrair a barra lateral no tablet
    await sidebar.getByRole("button", { name: "Expandir menu lateral" }).click();
    await expect(sidebar).toHaveAttribute("data-collapsed", "false");
    await expect(sidebar).toContainText("Modo Tablet");

    // No tablet, o seletor de localidade abre como diálogo centralizado
    await page.locator("#btn-abrir-seletor-localidade").click();
    await expect(page.getByRole("dialog")).toHaveAttribute("data-presentation", "centered-dialog");
  });

  test("3. Identifica execução em Desktop (1280x800) com Sidebar expandida e modo Standalone PWA", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "standalone", { configurable: true, value: true });
    });

    await page.goto("/");

    const shell = page.locator("#agro-adaptive-shell");
    await expect(shell).toHaveAttribute("data-device-category", "desktop");
    await expect(shell).toHaveAttribute("data-execution-mode", "standalone");
    await expect(shell).toHaveAttribute("data-navigation-pattern", "sidebar-and-topbar");

    const sidebar = page.getByTestId("adaptive-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toContainText("PWA Instalado");
  });
});

