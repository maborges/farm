import { expect, test } from "@playwright/test";

import { isErpConsoleBootstrapState } from "./erp-console";
import type { ErpStatusResponse } from "./erp/types";

function buildStatus(overrides: Partial<ErpStatusResponse> = {}): ErpStatusResponse {
  return {
    configurado: true,
    ativo: true,
    status_conexao: "CONNECTED",
    status_origem: "canonical",
    health_origem: "canonical",
    consecutive_failures: 0,
    features_habilitadas: [],
    policies_resumidas: [],
    provider_definition: {
      provider_code: "sankhya",
      provider_name: "Sankhya",
      display_name: "Sankhya ERP",
    },
    readiness: {
      status: "ATENDIDO",
      label: "Apto",
      variant: "default",
      summary: "Configuração válida",
      pending: [],
      cta_url: "/dashboard/settings/integracoes/erp",
      provider_code: "sankhya",
    },
    ...overrides,
  };
}

test.describe("ErpConsole switching guards", () => {
  test("não trata provider ativo como bootstrap", () => {
    expect(isErpConsoleBootstrapState(buildStatus())).toBe(false);
  });
});
