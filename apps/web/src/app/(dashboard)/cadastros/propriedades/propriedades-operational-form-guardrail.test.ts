import fs from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const sourcePath = path.resolve(process.cwd(), "src/app/(dashboard)/cadastros/propriedades/propriedades-client.tsx");
const source = fs.readFileSync(sourcePath, "utf8");

test.describe("operational form guardrails", () => {
  test("não renderiza inputs editáveis fundiários no formulário operacional", () => {
    const forbiddenTokens = [
      'register("codigo_car")',
      'register("car_numero")',
      'register("nirf")',
      'register("ccir")',
      'register("ccir_numero")',
      'register("sigef_codigo")',
      'register("numero_matricula")',
      'register("cartorio_id")',
    ];

    for (const token of forbiddenTokens) {
      expect(source.includes(token), `token proibido encontrado: ${token}`).toBeFalsy();
    }
  });

  test("submit operacional não constrói bloco imovel_rural", () => {
    expect(source.includes("imovel_rural: {")).toBeFalsy();
    expect(source.includes("propriedade_imovel: {")).toBeFalsy();
    expect(source.includes("buildOperationalCadastroPayload({")).toBeTruthy();
  });

  test("modal usa linguagem de unidade produtiva", () => {
    expect(source.includes("Editar Unidade Produtiva")).toBeTruthy();
    expect(source.includes("Nova Unidade Produtiva")).toBeTruthy();
    expect(source.includes("Editar Propriedade")).toBeFalsy();
    expect(source.includes("Nova Propriedade")).toBeFalsy();
  });

  test("validação usa mensagens amigáveis em vez de texto genérico", () => {
    expect(source.includes("Invalid input")).toBeFalsy();
    expect(source.includes("Preencha os campos obrigatórios.")).toBeTruthy();
    expect(source.includes("Selecione o tipo")).toBeTruthy();
    expect(source.includes("Mínimo de 2 caracteres")).toBeTruthy();
  });
});
