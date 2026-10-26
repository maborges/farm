import { expect, test } from "@playwright/test";

test.describe("B5B — Expansão Controlada do Catálogo Público de Commodities", () => {
  test("renderiza catálogo de 22 commodities, filtra por categoria e valida segregação de links DERAL", async ({
    page,
  }) => {
    await page.goto("/mercado");

    // 1. Verifica presença dos 7 preços B4 homologados
    await expect(page.locator('[data-commodity-id="soja"]')).toContainText("R$ 134,98");
    await expect(page.locator('[data-commodity-id="milho"]')).toContainText("R$ 51,77");
    await expect(page.locator('[data-commodity-id="cafe-arabica"]')).toContainText("R$ 1.380,51");
    await expect(page.locator('[data-commodity-id="boi-gordo"]')).toContainText("R$ 371,21");
    await expect(page.locator('[data-commodity-id="trigo"]')).toContainText("R$ 78,93");
    await expect(page.locator('[data-commodity-id="arroz"]')).toContainText("R$ 107,00");
    await expect(page.locator('[data-commodity-id="feijao"]')).toContainText("R$ 302,68");

    // 2. Verifica presença de novos produtos P1 expandidos
    await expect(page.locator('[data-commodity-id="leite"]')).toContainText("R$ 2,81");
    await expect(page.locator('[data-commodity-id="frango-vivo"]')).toContainText("R$ 4,95");
    await expect(page.locator('[data-commodity-id="cana-de-acucar"]')).toContainText("R$ 100,21");
    await expect(page.locator('[data-commodity-id="amendoim"]')).toContainText("R$ 75,00");

    // 3. Verifica item cadastral com link homologado (Algodão)
    const cardAlgodao = page.locator('[data-commodity-id="algodao"]');
    await expect(cardAlgodao).toContainText("Preço indisponível");
    await expect(cardAlgodao).not.toContainText(/R\$\s*[\d.,]+/);
    await expect(cardAlgodao).toContainText("CONAB/MAPA");

    // 4. Verifica proveniência audite de célula (Rav!X...) no card
    const cardSoja = page.locator('[data-commodity-id="soja"]');
    await expect(cardSoja).toContainText("Rav!X12");

    // 5. Valida segregação estrita de links (prevenção do bug de download inesperado)
    // Botão institucional principal DEVE apontar para a página HTML do DERAL
    const botaoConsultaDeral = cardSoja.getByRole("link", { name: /Consultar no DERAL/i });
    await expect(botaoConsultaDeral).toHaveAttribute(
      "href",
      "https://www.agricultura.pr.gov.br/deral/precos"
    );
    await expect(botaoConsultaDeral).toHaveAttribute("target", "_blank");

    // Link secundário de download DEVE apontar para o .xls com indicação de download
    const linkDownloadXls = cardSoja.getByRole("link", { name: /Baixar planilha oficial/i });
    await expect(linkDownloadXls).toHaveAttribute(
      "href",
      "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls"
    );
    await expect(linkDownloadXls).toHaveAttribute("download", "");

    // 6. Testa navegação por categoria (filtro pills)
    await page.getByRole("tab", { name: /Pecuária/i }).click();
    await expect(page.locator('[data-commodity-id="boi-gordo"]')).toBeVisible();
    await expect(page.locator('[data-commodity-id="leite"]')).toBeVisible();
    await expect(page.locator('[data-commodity-id="soja"]')).toHaveCount(0);

    // Volta para todas as categorias
    await page.getByRole("tab", { name: /Todos/i }).click();
    await expect(page.locator('[data-commodity-id="soja"]')).toBeVisible();
  });
});
