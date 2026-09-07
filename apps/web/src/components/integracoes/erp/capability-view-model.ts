import { ERP_CAPABILITY_ORDER, getErpCapabilityCatalogEntry } from "./capability-labels";
import type {
  BuildErpCapabilityViewModelsInput,
  CapabilityMatrixItem,
  ErpCapabilityMaturity,
  ErpCapabilityOperationalStatus,
  ErpCapabilityViewModel,
  ErpJob,
  ErpPolicySummary,
  ErpSyncDirection,
  ErpSyncMode,
  ExternalAssociationPendingItem,
} from "./types";

const CRITICAL_HEALTH = new Set(["DISCONNECTED", "AUTH_ERROR", "CONFIG_ERROR", "FAILED"]);
const WARNING_HEALTH = new Set(["DEGRADED", "PARTIAL_FAILURE", "RATE_LIMITED"]);
const SUCCESS_JOB = new Set(["SUCCESS", "SUCESSO", "COMPLETED"]);
const PENDING_ASSOCIATION = new Set(["PENDING", "PENDENTE"]);
const CONFLICT_ASSOCIATION = new Set(["CONFLICT", "CONFLITO", "DUPLICATE"]);

function toArray<T>(value: T[] | null | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

function normalizeCode(value?: string | null): string {
  return (value || "").trim().toLowerCase();
}

function getFeatureCode(item: CapabilityMatrixItem): string {
  return normalizeCode(item.feature_code || item.capability_code);
}

function sortByMostRecentJob(jobs: ErpJob[]): ErpJob[] {
  return [...jobs].sort((left, right) => {
    const leftDate = new Date(left.finished_at || left.started_at || 0).getTime();
    const rightDate = new Date(right.finished_at || right.started_at || 0).getTime();
    return rightDate - leftDate;
  });
}

function isDeclaredOnly(item: CapabilityMatrixItem): boolean {
  return item.maturity === "DECLARED" || item.pilot_tier === "P2";
}

function isP2Capability(item: CapabilityMatrixItem): boolean {
  return item.pilot_tier === "P2" || getFeatureCode(item) === "estoque";
}

function deriveMaturity(item: CapabilityMatrixItem): ErpCapabilityMaturity {
  if (isP2Capability(item)) {
    return "P2";
  }
  if (item.status === "UNSUPPORTED") {
    return "UNAVAILABLE";
  }
  if (item.maturity === "DECLARED") {
    return "DECLARED";
  }
  if (item.status === "PARTIAL" || item.maturity === "PARTIAL") {
    return "PARTIAL";
  }
  if (item.maturity === "TESTED") {
    return "TESTED";
  }
  return "UNAVAILABLE";
}

function deriveDirection(direction?: string | null): ErpSyncDirection {
  switch (direction) {
    case "ERP_TO_AGROSAAS":
    case "AGROSAAS_TO_ERP":
    case "BIDIRECTIONAL_CONTROLLED":
    case "EVIDENCE_RETURN":
      return direction;
    default:
      return "NONE";
  }
}

function deriveSyncMode(
  item: CapabilityMatrixItem,
  policy: ErpPolicySummary | undefined,
  enabled: boolean,
): ErpSyncMode {
  if (isP2Capability(item)) {
    return "NOT_CONFIGURED";
  }
  if (!enabled) {
    return "DISABLED";
  }
  if (policy && !policy.ativa) {
    return "DISABLED";
  }

  const mode = policy?.mode ?? toArray(item.supported_sync_modes)[0];
  switch (mode) {
    case "MANUAL":
    case "ON_DEMAND":
      return "MANUAL";
    case "SCHEDULED":
    case "AGENDADO":
    case "POLLING":
      return "SCHEDULED";
    case "EVENT":
    case "EVENT_DRIVEN":
    case "WEBHOOK":
      return "EVENT";
    case "OUTBOX":
      return "OUTBOX";
    default: {
      const catalogEntry = getErpCapabilityCatalogEntry(getFeatureCode(item));
      return catalogEntry?.preferredSyncMode ?? "NOT_CONFIGURED";
    }
  }
}

function deriveStatus(params: {
  item: CapabilityMatrixItem;
  enabled: boolean;
  configured: boolean;
  policyActive?: boolean;
  healthStatus?: string | null;
}): ErpCapabilityOperationalStatus {
  const { item, enabled, configured, policyActive, healthStatus } = params;

  if (isP2Capability(item) || isDeclaredOnly(item)) {
    return "DECLARED";
  }
  if (item.status === "UNSUPPORTED") {
    return "NOT_AVAILABLE";
  }
  if (!enabled) {
    return "DISABLED";
  }
  if (policyActive === false) {
    return "DISABLED";
  }
  if (!configured) {
    return "PENDING_CONFIGURATION";
  }
  if (healthStatus && CRITICAL_HEALTH.has(healthStatus)) {
    return "FAILED";
  }
  if (healthStatus && WARNING_HEALTH.has(healthStatus)) {
    return "DEGRADED";
  }
  if (item.status === "PARTIAL") {
    return "PARTIAL";
  }
  return "ACTIVE";
}

function deriveMasterSystem(item: CapabilityMatrixItem): string {
  return (
    getErpCapabilityCatalogEntry(getFeatureCode(item))?.masterSystem ||
    (deriveDirection(item.direction) === "AGROSAAS_TO_ERP" ? "AgroSaaS" : "ERP")
  );
}

function countAssociations(items: ExternalAssociationPendingItem[], capabilityCode: string) {
  return items.reduce(
    (accumulator, item) => {
      if (normalizeCode(item.feature_code) !== capabilityCode) {
        return accumulator;
      }

      const normalizedStatus = normalizeCode(item.status).toUpperCase();
      if (CONFLICT_ASSOCIATION.has(normalizedStatus)) {
        accumulator.conflictingAssociations += 1;
      }
      if (
        PENDING_ASSOCIATION.has(normalizedStatus) ||
        (!CONFLICT_ASSOCIATION.has(normalizedStatus) && normalizedStatus !== "RECONCILED")
      ) {
        accumulator.pendingAssociations += 1;
      }
      return accumulator;
    },
    { pendingAssociations: 0, conflictingAssociations: 0 },
  );
}

function getLatestJob(jobs: ErpJob[], capabilityCode: string): ErpJob | undefined {
  return sortByMostRecentJob(
    jobs.filter((job) => normalizeCode(job.feature_code) === capabilityCode),
  )[0];
}

function getLatestSuccessfulJob(jobs: ErpJob[], capabilityCode: string): ErpJob | undefined {
  return sortByMostRecentJob(
    jobs.filter(
      (job) =>
        normalizeCode(job.feature_code) === capabilityCode &&
        SUCCESS_JOB.has(normalizeCode(job.job_status).toUpperCase()),
    ),
  )[0];
}

function getProviderName(input: BuildErpCapabilityViewModelsInput): string {
  return (
    input.status?.provider_definition?.display_name ||
    input.config?.provider_display_name ||
    input.providerSchema?.provider?.nome ||
    input.providerSlug
  );
}

export function buildErpCapabilityViewModels(
  input: BuildErpCapabilityViewModelsInput,
): ErpCapabilityViewModel[] {
  const providerName = getProviderName(input);
  const capabilityMatrix = toArray(
    input.config?.feature_schema?.capability_matrix ?? input.status?.feature_schema?.capability_matrix,
  );
  const normalizedCapabilityMatrix = capabilityMatrix;
  const enabledFeatures = new Set(
    toArray(input.status?.features_habilitadas).map((item) => normalizeCode(item)),
  );
  const jobs = toArray(input.jobs);
  const pendingAssociations = toArray(input.pendingAssociations);
  const healthStatus = input.health?.status ?? input.status?.health_status ?? null;
  const configured = Boolean(input.status?.configurado || input.config);
  const canConfigure =
    input.canConfigure ??
    Boolean(
      input.providerSchema?.connection_schema?.fields?.length ||
        input.providerSchema?.credential_schema?.fields?.length,
    );

  const models = normalizedCapabilityMatrix.map((item) => {
    const capabilityCode = getFeatureCode(item);
    const policy = toArray(input.status?.policies_resumidas).find(
      (entry) => normalizeCode(entry.feature_code) === capabilityCode,
    );
    const associationSummary = countAssociations(pendingAssociations, capabilityCode);
    const latestJob = getLatestJob(jobs, capabilityCode);
    const latestSuccessfulJob = getLatestSuccessfulJob(jobs, capabilityCode);
    const catalogEntry = getErpCapabilityCatalogEntry(capabilityCode);
    const p2 = isP2Capability(item);
    const enabled = p2 ? false : enabledFeatures.has(capabilityCode);
    const maturity = deriveMaturity(item);
    const status = deriveStatus({
      item,
      enabled,
      configured,
      policyActive: policy?.ativa,
      healthStatus,
    });
    const syncMode = deriveSyncMode(item, policy, enabled);

    return {
      code: capabilityCode,
      name: catalogEntry?.name || item.display_name || capabilityCode,
      description: catalogEntry?.description || item.description || "Sem descrição operacional cadastrada.",
      providerSlug: input.providerSlug,
      providerName,
      status,
      enabled,
      maturity,
      direction: deriveDirection(item.direction),
      masterSystem: deriveMasterSystem(item),
      syncMode,
      healthStatus,
      lastSyncAt:
        latestSuccessfulJob?.finished_at ||
        latestSuccessfulJob?.started_at ||
        input.status?.last_success_at ||
        input.status?.ultimo_sync ||
        null,
      lastJobAt: latestJob?.finished_at || latestJob?.started_at || null,
      nextRunAt: policy?.ativa ? input.status?.proximo_sync || null : null,
      pendingAssociations: associationSummary.pendingAssociations,
      conflictingAssociations: associationSummary.conflictingAssociations,
      actions: {
        canViewDetails: input.canViewDetails ?? true,
        canSyncManually:
          !p2 &&
          enabled &&
          policy?.ativa !== false &&
          (input.manualSyncCapabilities ?? []).map(normalizeCode).includes(capabilityCode),
        canConfigure: canConfigure && !p2,
        canReconcile:
          (input.canReconcile ?? true) &&
          !p2 &&
          associationSummary.pendingAssociations + associationSummary.conflictingAssociations > 0,
        canReprocess: false,
      },
      pilotTier: item.pilot_tier || null,
      technical: {
        adapterLabel: input.adapterLabel || `Conector ${providerName}`,
        internalOperationLabels: catalogEntry?.technicalOperations || [],
        externalSystemLabel: providerName,
      },
    } satisfies ErpCapabilityViewModel;
  });

  return models.sort((left, right) => {
    const leftIndex = ERP_CAPABILITY_ORDER.indexOf(left.code as (typeof ERP_CAPABILITY_ORDER)[number]);
    const rightIndex = ERP_CAPABILITY_ORDER.indexOf(right.code as (typeof ERP_CAPABILITY_ORDER)[number]);
    const safeLeft = leftIndex === -1 ? ERP_CAPABILITY_ORDER.length : leftIndex;
    const safeRight = rightIndex === -1 ? ERP_CAPABILITY_ORDER.length : rightIndex;
    return safeLeft - safeRight || left.name.localeCompare(right.name);
  });
}
