import { expect, test } from "@playwright/test";

import { buildErpSyncCenterViewModel } from "./sync-center-view-model";
import type { ErpCapabilityViewModel, ErpStatusResponse } from "./types";

const capability: ErpCapabilityViewModel = {
  code: "pessoas",
  name: "Pessoas",
  description: "Cadastro de pessoas",
  providerSlug: "sankhya",
  providerName: "Sankhya ERP",
  direction: "ERP_TO_AGROSAAS",
  syncMode: "MANUAL",
  masterSystem: "ERP",
  status: "PENDING_CONFIGURATION",
  maturity: "TESTED",
  pilotTier: "P0",
  enabled: false,
  lastSyncAt: null,
  lastJobAt: null,
  nextRunAt: null,
  pendingAssociations: 0,
  conflictingAssociations: 0,
  healthStatus: "NOT_CONFIGURED",
  actions: {
    canViewDetails: true,
    canSyncManually: false,
    canConfigure: true,
    canReconcile: false,
    canReprocess: false,
  },
};

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
    },
    ...overrides,
  };
}

test.describe("buildErpSyncCenterViewModel", () => {
  test("desabilita ações manuais quando a integração ainda não está configurada", () => {
    const viewModel = buildErpSyncCenterViewModel(
      buildStatus(),
      [],
      [capability],
      "Sankhya ERP",
      [
        {
          label: "Sincronizar tudo",
          execute: async () => undefined,
          enabled: true,
          requiresConfiguredIntegration: true,
        },
      ],
    );

    expect(viewModel.manualActions).toHaveLength(1);
    expect(viewModel.manualActions[0].enabled).toBe(false);
  });

  test("mantém ações manuais habilitadas quando a integração já está configurada", () => {
    const viewModel = buildErpSyncCenterViewModel(
      buildStatus({ configurado: true }),
      [],
      [capability],
      "Sankhya ERP",
      [
        {
          label: "Sincronizar tudo",
          execute: async () => undefined,
          enabled: true,
          requiresConfiguredIntegration: true,
        },
      ],
    );

    expect(viewModel.manualActions[0].enabled).toBe(true);
  });
});
