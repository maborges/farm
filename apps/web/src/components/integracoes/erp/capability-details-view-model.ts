import {
  getErpCapabilityCatalogEntry,
  getErpOperationalBoundaryLabel,
  getErpSyncDirectionLabel,
  getErpSyncModeLabel,
  getIntegrationHealthOperationalLabel,
} from "./capability-labels";
import type {
  BuildErpCapabilityDetailsInput,
  ErpCapabilityAssociationItemViewModel,
  ErpCapabilityDetailsViewModel,
  ErpCapabilityJobViewModel,
  ErpCapabilityTimelineItemViewModel,
  ErpCapabilityViewModel,
  ErpJob,
  ErpTimelineEntry,
  ExternalAssociationPendingItem,
} from "./types";

function normalizeCode(value?: string | null): string {
  return (value || "").trim().toLowerCase();
}

function toArray<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

function sanitizeExternalReference(value?: string | null): string {
  if (!value) {
    return "Não informado";
  }
  if (value.length <= 8) {
    return value;
  }
  return `${value.slice(0, 4)}...${value.slice(-4)}`;
}

function buildJobTitle(job: ErpJob): string {
  return job.feature_code ? `Execução de ${job.feature_code}` : "Execução geral da integração";
}

function buildJobViewModel(job: ErpJob, relation: "RELATED" | "GENERAL"): ErpCapabilityJobViewModel {
  const durationMs =
    job.started_at && job.finished_at
      ? Math.max(0, new Date(job.finished_at).getTime() - new Date(job.started_at).getTime())
      : null;

  return {
    id: job.id,
    relation,
    title: buildJobTitle(job),
    status: job.job_status,
    triggerLabel: job.trigger_type,
    startedAt: job.started_at || null,
    finishedAt: job.finished_at || null,
    durationMs,
    processed: job.processados,
    successes: job.sucessos,
    errors: job.erros,
  };
}

function buildTimelineViewModel(
  item: ErpTimelineEntry,
  relation: "RELATED" | "GENERAL",
): ErpCapabilityTimelineItemViewModel {
  return {
    id: item.id,
    relation,
    tipoRegistro: item.tipo_registro,
    originLabel: item.origem_dado,
    featureCode: item.feature_code || null,
    status: item.status,
    eventType: item.event_type || null,
    summary: item.resumo,
    occurredAt: item.occurred_at,
    startedAt: item.started_at || null,
    finishedAt: item.finished_at || null,
    durationMs: item.duracao_ms ?? null,
    processed: item.processados,
    successes: item.sucessos,
    errors: item.erros,
    correlationId: item.correlation_id || null,
  };
}

function buildAssociationItem(item: ExternalAssociationPendingItem): ErpCapabilityAssociationItemViewModel {
  return {
    id: item.id,
    entityType: item.external_entity_type || item.local_entity_type,
    externalReference: sanitizeExternalReference(item.external_id || item.external_key),
    status: item.status,
    reason: item.motivo || null,
    localEntityId: item.local_entity_id || null,
  };
}

function buildCapabilityDetails(
  capability: ErpCapabilityViewModel,
  input: BuildErpCapabilityDetailsInput,
): ErpCapabilityDetailsViewModel {
  const capabilityCode = normalizeCode(capability.code);
  const relatedJobs = toArray(input.jobs)
    .filter((job) => normalizeCode(job.feature_code) === capabilityCode)
    .map((job) => buildJobViewModel(job, "RELATED"));
  const generalJobs = toArray(input.jobs)
    .filter((job) => !job.feature_code)
    .map((job) => buildJobViewModel(job, "GENERAL"));

  const relatedTimeline = toArray(input.timeline)
    .filter((item) => normalizeCode(item.feature_code) === capabilityCode)
    .map((item) => buildTimelineViewModel(item, "RELATED"));
  const generalTimeline = toArray(input.timeline)
    .filter((item) => !item.feature_code)
    .map((item) => buildTimelineViewModel(item, "GENERAL"));

  const relatedAssociations = toArray(input.pendingAssociations)
    .filter((item) => normalizeCode(item.feature_code) === capabilityCode)
    .map(buildAssociationItem);
  const conflictCount = toArray(input.pendingAssociations).filter(
    (item) => normalizeCode(item.feature_code) === capabilityCode && normalizeCode(item.status) === "conflict",
  ).length;

  const catalogEntry = getErpCapabilityCatalogEntry(capabilityCode);

  return {
    capability,
    provider: {
      slug: capability.providerSlug,
      name: capability.providerName,
      executorLabel: capability.technical?.adapterLabel || null,
    },
    ownership: {
      masterSystem: capability.masterSystem,
      directionLabel: getErpSyncDirectionLabel(capability.direction),
      operationalBoundary: getErpOperationalBoundaryLabel(capabilityCode),
    },
    execution: {
      syncModeLabel: getErpSyncModeLabel(capability.syncMode),
      lastSyncAt: capability.lastSyncAt,
      lastJobAt: capability.lastJobAt,
      nextRunAt: capability.nextRunAt,
      nextRunIsShared: Boolean(capability.nextRunAt),
    },
    health: {
      status: capability.healthStatus,
      label: getIntegrationHealthOperationalLabel(capability.healthStatus),
      summary: input.health?.summary || input.status?.health_summary || null,
      isGlobal: true,
    },
    jobs: {
      related: relatedJobs,
      general: relatedJobs.length === 0 ? generalJobs : generalJobs.slice(0, 3),
    },
    timeline: {
      related: relatedTimeline,
      general: relatedTimeline.length === 0 ? generalTimeline : generalTimeline.slice(0, 4),
    },
    associations: {
      pendingCount: capability.pendingAssociations,
      conflictCount,
      relatedItems: relatedAssociations.slice(0, 5),
    },
    technical: {
      internalOperationLabels: capability.technical?.internalOperationLabels || catalogEntry?.technicalOperations || [],
      externalSystemLabel: capability.technical?.externalSystemLabel || capability.providerName,
    },
    actions: capability.actions,
  };
}

export function buildErpCapabilityDetailsViewModels(
  input: BuildErpCapabilityDetailsInput,
): Record<string, ErpCapabilityDetailsViewModel> {
  return input.capabilities.reduce<Record<string, ErpCapabilityDetailsViewModel>>((accumulator, capability) => {
    accumulator[capability.code] = buildCapabilityDetails(capability, input);
    return accumulator;
  }, {});
}
