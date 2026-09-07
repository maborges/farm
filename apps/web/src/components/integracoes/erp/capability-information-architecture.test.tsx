import { expect, test } from "@playwright/test";
import { getErpCapabilitySectionCopy } from "./capability-center";
import { buildErpCapabilityViewModels } from "./capability-view-model";
import type { ErpCapabilityViewModel, ErpStatusResponse } from "./types";

const capability: ErpCapabilityViewModel = {
  code: "pessoas",
  name: "Pessoas",
  description: "Clientes, fornecedores e demais cadastros vindos do ERP.",
  providerSlug: "sankhya",
  providerName: "Sankhya",
  status: "ACTIVE",
  enabled: true,
  maturity: "TESTED",
  direction: "ERP_TO_AGROSAAS",
  masterSystem: "ERP",
  syncMode: "MANUAL",
  healthStatus: "CONNECTED",
  lastSyncAt: "2026-07-18T10:00:00Z",
  lastJobAt: "2026-07-18T10:00:00Z",
  nextRunAt: null,
  pendingAssociations: 0,
  conflictingAssociations: 0,
  actions: {
    canViewDetails: true,
    canSyncManually: true,
    canConfigure: true,
    canReconcile: false,
    canReprocess: false,
  },
};

test("não inventa dados sincronizados quando o provider não publica matriz", () => {
  const status = {
    configurado: true,
    ativo: true,
    status_conexao: "CONNECTED",
    status_origem: "canonical",
    health_origem: "canonical",
    consecutive_failures: 0,
    features_habilitadas: [],
    policies_resumidas: [],
    feature_schema: { supported_features: [], capability_matrix: [] },
  } satisfies ErpStatusResponse;

  expect(buildErpCapabilityViewModels({ providerSlug: "sankhya", status })).toEqual([]);
});

test("apresenta dados sincronizados em linguagem operacional", () => {
  expect(getErpCapabilitySectionCopy(capability.providerName)).toEqual({
    title: "Dados sincronizados",
    description: "O que o Sankhya troca com o AgroSaaS e a situação de cada fluxo.",
  });
});

test("aplica a política canônica usando feature_code e desativa a ação manual", () => {
  const status = {
    configurado: true,
    ativo: true,
    status_conexao: "CONNECTED",
    status_origem: "canonical",
    health_origem: "canonical",
    consecutive_failures: 0,
    features_habilitadas: ["produtos"],
    policies_resumidas: [
      {
        feature_code: "produtos",
        mode: "AGENDADO",
        ativa: false,
        retry_limite: 3,
      },
    ],
    feature_schema: {
      supported_features: ["produtos"],
      capability_matrix: [
        {
          feature_code: "produtos",
          capability_code: "erp.cadastros.produtos.importar",
          display_name: "Produtos",
          status: "SUPPORTED",
          maturity: "TESTED",
          direction: "ERP_TO_AGROSAAS",
          supported_scopes: ["TENANT"],
          supported_sync_modes: ["MANUAL", "SCHEDULED"],
          dependencies: [],
          restrictions: [],
          observability_requirements: [],
          pilot_tier: "P0",
        },
      ],
    },
  } satisfies ErpStatusResponse;

  const [produto] = buildErpCapabilityViewModels({
    providerSlug: "sankhya",
    status,
    manualSyncCapabilities: ["produtos"],
  });

  expect(produto.code).toBe("produtos");
  expect(produto.status).toBe("DISABLED");
  expect(produto.syncMode).toBe("DISABLED");
  expect(produto.actions.canSyncManually).toBe(false);
});
