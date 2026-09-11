import type {
  ErpCapabilityMaturity,
  ErpCapabilityOperationalStatus,
  ErpSyncDirection,
  ErpSyncMode,
} from "./types";

interface ErpCapabilityCatalogEntry {
  code: string;
  name: string;
  description: string;
  masterSystem: string;
  technicalOperations: string[];
  preferredSyncMode?: ErpSyncMode;
  planningNote?: string;
  operationalBoundary?: string;
}

export const ERP_CAPABILITY_ORDER = [
  "pessoas",
  "produtos",
  "financeiro",
  "nfe",
  "pedidos",
  "estoque",
] as const;

const ERP_CAPABILITY_CATALOG: Record<string, ErpCapabilityCatalogEntry> = {
  pessoas: {
    code: "pessoas",
    name: "Pessoas",
    description: "Importação de clientes, fornecedores e demais cadastros de pessoas do ERP.",
    masterSystem: "ERP",
    technicalOperations: ["Importação de pessoas"],
    preferredSyncMode: "MANUAL",
    operationalBoundary:
      "O ERP é responsável pelos cadastros administrativos utilizados nesta integração. O DeepFarms mantém seus vínculos e contextos operacionais.",
  },
  produtos: {
    code: "produtos",
    name: "Produtos",
    description: "Importação de produtos e cadastros administrativos controlados pelo ERP.",
    masterSystem: "ERP",
    technicalOperations: ["Importação de produtos"],
    preferredSyncMode: "MANUAL",
    operationalBoundary:
      "O ERP fornece os produtos e insumos administrativos. O uso operacional no DeepFarms continua sujeito aos seus próprios cadastros e regras.",
  },
  financeiro: {
    code: "financeiro",
    name: "Financeiro",
    description: "Integrações financeiras administrativas do ERP sem transferir o domínio operacional do DeepFarms.",
    masterSystem: "ERP administrativo",
    technicalOperations: [
      "Importação financeira",
      "Exportação de contas a pagar",
      "Exportação de contas a receber",
    ],
    operationalBoundary:
      "O ERP governa títulos, pagamentos, recebimentos e liquidações administrativas. O financeiro operacional do DeepFarms permanece separado.",
  },
  nfe: {
    code: "nfe",
    name: "NFe",
    description: "Fluxos fiscais com retorno de evidências e consulta de documentos fiscais quando suportado.",
    masterSystem: "ERP fiscal",
    technicalOperations: [
      "Consulta de documentos fiscais",
      "Importação de entradas fiscais",
      "Retorno de evidências fiscais",
    ],
    operationalBoundary:
      "O ERP é o sistema fiscal responsável pelos documentos e retornos fiscais desta integração.",
  },
  pedidos: {
    code: "pedidos",
    name: "Pedidos",
    description: "Capability declarada para fases futuras. Não operacionalizar nesta etapa.",
    masterSystem: "ERP",
    technicalOperations: ["Sincronização planejada de pedidos"],
    preferredSyncMode: "NOT_CONFIGURED",
    planningNote: "Integração planejada. Ainda não está operacional para o piloto atual.",
    operationalBoundary:
      "Capability planejada para uma fase posterior. Ainda não existe operação ativa no piloto.",
  },
  estoque: {
    code: "estoque",
    name: "Estoque",
    description: "Capability P2 planejada para estoque administrativo. O estoque operacional permanece no DeepFarms.",
    masterSystem: "ERP administrativo",
    technicalOperations: ["Sincronização planejada de estoque administrativo"],
    preferredSyncMode: "NOT_CONFIGURED",
    planningNote:
      "Integração administrativa planejada. O estoque operacional continua sendo controlado pelo DeepFarms.",
    operationalBoundary:
      "Esta capability se refere ao estoque administrativo do ERP. O estoque operacional continua sendo controlado pelo DeepFarms.",
  },
};

const OPERATIONAL_STATUS_LABELS: Record<ErpCapabilityOperationalStatus, string> = {
  ACTIVE: "Ativa",
  PARTIAL: "Parcialmente disponível",
  DISABLED: "Desativada",
  PENDING_CONFIGURATION: "Aguardando configuração",
  DEGRADED: "Requer atenção",
  FAILED: "Com falha",
  DECLARED: "Planejada",
  NOT_AVAILABLE: "Indisponível",
};

const SYNC_DIRECTION_LABELS: Record<ErpSyncDirection, string> = {
  ERP_TO_AGROSAAS: "ERP para DeepFarms",
  AGROSAAS_TO_ERP: "DeepFarms para ERP",
  BIDIRECTIONAL_CONTROLLED: "Atualização controlada nos dois sentidos",
  EVIDENCE_RETURN: "Envio com retorno de confirmação",
  NONE: "Sem atualização ativa",
};

const SYNC_MODE_LABELS: Record<ErpSyncMode, string> = {
  MANUAL: "Manual",
  SCHEDULED: "Automática",
  EVENT: "Por evento",
  OUTBOX: "Por fila de eventos",
  DISABLED: "Desabilitada",
  NOT_CONFIGURED: "Não configurada",
};

const MATURITY_LABELS: Record<ErpCapabilityMaturity, string> = {
  TESTED: "Validada",
  PARTIAL: "Parcial",
  DECLARED: "Declarada",
  P2: "Planejada para P2",
  UNAVAILABLE: "Indisponível",
};

const INTEGRATION_HEALTH_LABELS: Record<string, string> = {
  CONNECTED: "Conector saudável",
  DEGRADED: "Integração requer atenção",
  DISCONNECTED: "Integração sem comunicação",
  AUTH_ERROR: "Falha de autenticação do conector",
  CONFIG_ERROR: "Configuração incompleta da integração",
  PARTIAL_FAILURE: "Integração com falhas parciais",
  RATE_LIMITED: "Integração com limite de uso atingido",
  FAILED: "Integração com falha",
};

export function getErpCapabilityCatalogEntry(code: string): ErpCapabilityCatalogEntry | null {
  return ERP_CAPABILITY_CATALOG[code] ?? null;
}

export function getErpOperationalBoundaryLabel(code: string): string | null {
  return ERP_CAPABILITY_CATALOG[code]?.operationalBoundary ?? null;
}

export function getErpOperationalStatusLabel(status: ErpCapabilityOperationalStatus): string {
  return OPERATIONAL_STATUS_LABELS[status];
}

export function getErpSyncDirectionLabel(direction: ErpSyncDirection): string {
  return SYNC_DIRECTION_LABELS[direction];
}

export function getErpSyncModeLabel(mode: ErpSyncMode): string {
  return SYNC_MODE_LABELS[mode];
}

export function getErpCapabilityMaturityLabel(maturity: ErpCapabilityMaturity): string {
  return MATURITY_LABELS[maturity];
}

export function getIntegrationHealthOperationalLabel(status?: string | null): string {
  if (!status) {
    return "Situação geral não informada";
  }
  return INTEGRATION_HEALTH_LABELS[status] ?? status;
}
