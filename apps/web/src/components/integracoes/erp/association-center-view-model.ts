import {
  ErpAssociationStatus,
  ErpAssociationSummaryViewModel,
  ErpAssociationViewModel,
  ExternalAssociationPendingItem,
  ExternalAssociationSummaryResponse,
} from "./types";

export function buildErpAssociationViewModel(
  item: ExternalAssociationPendingItem
): ErpAssociationViewModel {
  const canReconcile = item.status === "PENDING";
  const canViewDetails = true; // Permissão básica, pode ser restrita se necessário

  return {
    id: item.id,
    featureCode: item.feature_code || null,
    environment: item.environment,
    localEntityType: item.local_entity_type,
    localEntityId: item.local_entity_id || null,
    externalEntityType: item.external_entity_type,
    externalId: item.external_id,
    status: item.status as ErpAssociationStatus,
    confidence: item.confidence,
    reason: item.motivo || null,
    createdAt: item.history.length > 0 ? item.history[item.history.length - 1].created_at : "",
    lastSyncAt: null, // Puxar do backend quando disponível
    history: item.history,
    actions: {
      canViewDetails,
      canReconcile,
    },
  };
}

export function buildErpAssociationSummaryViewModel(
  summary: ExternalAssociationSummaryResponse
): ErpAssociationSummaryViewModel {
  return {
    pendingCount: summary.PENDING || 0,
    conflictCount: summary.CONFLICT || 0,
    activeCount: summary.ACTIVE || 0,
    totalCount: summary.TOTAL || 0,
  };
}
