import { expect, test } from "@playwright/test";

async function openHome(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect.poll(() => page.evaluate(() =>
    (window as Window & { __installListenersReady?: boolean }).__installListenersReady === true
  )).toBe(true);
}

test.describe("Convite de instalação do DeepFarms Agro", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const originalAddEventListener = window.addEventListener.bind(window);
      window.addEventListener = ((
        type: string,
        listener: Parameters<typeof window.addEventListener>[1],
        options?: Parameters<typeof window.addEventListener>[2]
      ) => {
        if (type === "beforeinstallprompt" || type === "appinstalled") {
          (window as Window & { __installListenersReady?: boolean }).__installListenersReady = true;
        }
        return originalAddEventListener(type, listener, options);
      }) as typeof window.addEventListener;
    });
  });

  test("mostra o convite e oferece instruções manuais sem prompt nativo", async ({ page }) => {
    await openHome(page);
    const invite = page.getByTestId("install-invite");

    await expect(invite).toBeVisible();
    await expect(invite).toContainText("Leve o DeepFarms Agro para o campo!");
    await expect(invite).toContainText("Gratuito. Sem cadastro.");
    await page.getByRole("button", { name: "Como instalar" }).click();
    await expect(page.getByTestId("install-instructions")).toContainText(
      "No menu do navegador"
    );
  });

  test("invoca o prompt simulado e não declara instalação apenas pela escolha", async ({ page }) => {
    await page.addInitScript(() => {
      (window as Window & { installPromptCalls?: number }).installPromptCalls = 0;
    });
    await openHome(page);
    await expect(page.getByTestId("install-invite")).toBeVisible();

    await page.evaluate(() => {
      class SimulatedBeforeInstallPrompt extends Event {
        prompt = async () => {
          (window as Window & { installPromptCalls?: number }).installPromptCalls! += 1;
        };
        userChoice = Promise.resolve({ outcome: "accepted" as const, platform: "web" });
      }
      window.dispatchEvent(new SimulatedBeforeInstallPrompt("beforeinstallprompt"));
    });

    await page.getByRole("button", { name: "Instalar aplicativo" }).click();
    await expect.poll(() => page.evaluate(() =>
      (window as Window & { installPromptCalls?: number }).installPromptCalls
    )).toBe(1);
    await expect(page.getByTestId("install-invite")).toBeVisible();
    await expect(page.getByTestId("install-invite")).not.toContainText("Aplicativo instalado");
  });

  test("mostra instruções de Tela de Início no iPhone e no iPadOS", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "userAgent", {
        configurable: true,
        value: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
      });
    });
    await openHome(page);
    await page.getByRole("button", { name: "Como instalar" }).click();
    await expect(page.getByTestId("install-instructions")).toContainText(
      "No Safari, toque em"
    );
    await expect(page.getByTestId("install-instructions")).toContainText(
      "Adicionar à Tela de Início"
    );
  });

  test("reconhece iPadOS com user agent de desktop", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "userAgent", {
        configurable: true,
        value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
      });
      Object.defineProperty(navigator, "platform", { configurable: true, value: "MacIntel" });
      Object.defineProperty(navigator, "maxTouchPoints", { configurable: true, value: 5 });
    });
    await openHome(page);
    await page.getByRole("button", { name: "Como instalar" }).click();
    await expect(page.getByTestId("install-instructions")).toContainText(
      "No Safari, toque em"
    );
  });

  test("oculta o convite em modo standalone", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "standalone", { configurable: true, value: true });
    });
    await openHome(page);
    await expect(page.getByTestId("install-invite")).toHaveCount(0);
  });

  test("considera appinstalled sem depender do resultado do prompt", async ({ page }) => {
    await openHome(page);
    await expect(page.getByTestId("install-invite")).toBeVisible();
    await page.evaluate(() => window.dispatchEvent(new Event("appinstalled")));
    await expect(page.getByTestId("install-invite")).toHaveCount(0);
  });

  test("persiste localmente a dispensa do convite", async ({ page }) => {
    await openHome(page);
    await page.getByRole("button", { name: "Dispensar convite de instalação" }).click();
    await expect(page.getByTestId("install-invite")).toHaveCount(0);
    await page.reload();
    await expect(page.getByTestId("install-invite")).toHaveCount(0);
  });
});
