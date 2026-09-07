import { expect, test } from "@playwright/test";

import {
  getErpSyncErrorMessage,
  isErpConsoleBootstrapState,
  resolveErpOverviewReadiness,
} from "./erp-console";
import { buildSankhyaPeoplePreviewState } from "./erp/sankhya-people-preview";
import type { ErpStatusResponse } from "./erp/types";

function buildStatus(overrides: Partial<ErpStatusResponse> = {}): ErpStatusResponse {
  return {
    configurado: false,
    ativo: false,
    status_conexao: "NOT_CONFIGURED",
    status_origem: "UNCONFIGURED",
    health_origem: "UNCONFIGURED",
    consecutive_failures: 0,
    features_habilitadas: [],
    policies_resumidas: [],
    readiness: {
      status: "NOT_CONFIGURED",
      label: "Não configurado",
      variant: "secondary",
      summary: "Nenhum ERP configurado",
      pending: [],
      cta_url: "/dashboard/settings/integracoes/erp",
      provider_code: null,
    },
    ...overrides,
  };
}

test.describe("isErpConsoleBootstrapState", () => {
  test("abre seletor com status 200 não configurado e sem provider", () => {
    expect(isErpConsoleBootstrapState(buildStatus())).toBe(true);
  });

  test("mantém compatibilidade com 404 antigo", () => {
    expect(isErpConsoleBootstrapState({ ...buildStatus(), notFound: true })).toBe(true);
  });

  test("não abre seletor quando há provider legado resolvido", () => {
    expect(
      isErpConsoleBootstrapState(
        buildStatus({
          configurado: true,
          readiness: {
            status: "PENDENTE",
            label: "Pendente",
            variant: "secondary",
            summary: "Fallback legado",
            pending: [],
            cta_url: "/dashboard/settings/integracoes/erp",
            provider_code: "sankhya",
          },
        }),
      ),
    ).toBe(false);
  });

  test("não abre seletor quando o provider já está configurado", () => {
    expect(
      isErpConsoleBootstrapState(
        buildStatus({
          configurado: true,
          provider_definition: {
            provider_code: "sankhya",
            provider_name: "Sankhya",
            display_name: "Sankhya ERP",
          },
        }),
      ),
    ).toBe(false);
  });
});

test.describe("resolveErpOverviewReadiness", () => {
  test("reconhece o ERP selecionado mesmo antes da primeira configuração salva", () => {
    expect(
      resolveErpOverviewReadiness({
        readiness: buildStatus().readiness!,
        providerName: "Sankhya",
        hasSavedConfig: false,
      }),
    ).toEqual({
      label: "Configuração pendente",
      variant: "secondary",
      summary: "Sankhya selecionado. Preencha e salve a configuração para concluir a conexão.",
      pending: ["preencher e salvar a configuração inicial"],
    });
  });

  test("não informa ausência de ERP quando já existe configuração do provider", () => {
    expect(
      resolveErpOverviewReadiness({
        readiness: buildStatus().readiness!,
        providerName: "Sankhya",
        hasSavedConfig: true,
      }),
    ).toEqual({
      label: "Configuração salva",
      variant: "secondary",
      summary: "Sankhya está configurado. Valide a comunicação para confirmar que a integração está pronta.",
      pending: ["validar a comunicação com o ERP"],
    });
  });
});

test.describe("feedback e registros da sincronização", () => {
  test("preserva a mensagem retornada pela API", () => {
    expect(getErpSyncErrorMessage(new Error("Falha ao importar: connection is closed"))).toBe(
      "Falha ao importar: connection is closed",
    );
  });

  test("diferencia ausência de registros de carregamento", () => {
    expect(buildSankhyaPeoplePreviewState([], false, null)).toEqual({
      kind: "empty",
      message: "Nenhuma pessoa sincronizada até o momento.",
    });
    expect(buildSankhyaPeoplePreviewState([], true, null)).toEqual({ kind: "loading" });
  });
});
