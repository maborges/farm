import type {
  ErpStatusResponse,
  ErpJob,
  ErpCapabilityViewModel,
  ErpPolicySummary,
} from "./types";

export type ErpSyncExecutionMode =
  | "MANUAL"
  | "SCHEDULED"
  | "EVENT"
  | "OUTBOX"
  | "DISABLED"
  | "NOT_CONFIGURED"
  | "DECLARED";

export type ErpSyncImplementationStatus =
  | "IMPLEMENTED_ACTIVE"
  | "IMPLEMENTED_INACTIVE"
  | "CONFIGURED"
  | "DECLARED"
  | "NOT_AVAILABLE"
  | "P2_FORBIDDEN";

export interface ErpSyncPolicyViewModel {
  id: string;
  featureCode: string | null;
  capabilityName: string;
  mode: ErpSyncExecutionMode;
  implementationStatus: ErpSyncImplementationStatus;
  enabled: boolean;
  triggerLabel: string;
  scheduleLabel: string | null;
  lastRunAt: string | null;
  nextRunAt: string | null;
  providerName: string;
  scopeLabel: string;
}

export interface ErpSyncJobViewModel {
  id: string;
  featureCode: string | null;
  capabilityName: string;
  status: string;
  triggerLabel: string;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  processed: number | null;
  successes: number | null;
  failures: number | null;
  message: string | null;
}

export interface ErpManualSyncActionViewModel {
  id: string;
  capabilityCode?: string;
  label: string;
  description?: string;
  execute: () => Promise<void>;
  enabled: boolean;
  requiresConfiguredIntegration: boolean;
}

export interface ErpPlannedSyncViewModel {
  id: string;
  capabilityName: string;
  description: string;
  status: string;
}

export interface ErpSyncCenterViewModel {
  summary: {
    activePolicies: number;
    runningJobs: number;
    recentFailures: number;
    lastSuccessAt: string | null;
    nextRunAt: string | null;
  };
  policies: ErpSyncPolicyViewModel[];
  jobs: ErpSyncJobViewModel[];
  manualActions: ErpManualSyncActionViewModel[];
  plannedCapabilities: ErpPlannedSyncViewModel[];
}

export function buildErpSyncCenterViewModel(
  status: ErpStatusResponse | null,
  jobs: ErpJob[],
  capabilities: ErpCapabilityViewModel[],
  providerName: string,
  manualActionsInput: Array<Omit<ErpManualSyncActionViewModel, "id">>,
): ErpSyncCenterViewModel {
  const isConfigured = Boolean(status?.configurado);
  const nextRunAt = status?.proximo_sync || null;
  const lastSuccessAt = status?.last_success_at || null;

  const policyViewModels: ErpSyncPolicyViewModel[] = [];
  const plannedCapabilities: ErpPlannedSyncViewModel[] = [];

  const policiesByFeature = new Map<string, ErpPolicySummary>();
  if (status?.policies_resumidas) {
    status.policies_resumidas.forEach((p) => policiesByFeature.set(p.feature_code, p));
  }

  // Iterate over capabilities to build policies and planned items
  capabilities.forEach((cap) => {
    const policy = policiesByFeature.get(cap.code);

    // Identify P2 capabilities properly using view-model properties
    if (cap.maturity === "P2" || cap.pilotTier === "P2" || cap.status === "NOT_AVAILABLE") {
      let description = "Planejado para fases futuras da integração.";
      if (cap.code === "estoque") {
        description = "A sincronização do estoque administrativo do ERP está planejada para uma fase posterior. O estoque operacional continua sendo controlado pelo AgroSaaS.";
      } else if (cap.code === "pedidos") {
        description = "A sincronização de pedidos de venda está planejada para ser implementada em breve.";
      }
      
      plannedCapabilities.push({
        id: `planned-${cap.code}`,
        capabilityName: cap.name,
        description,
        status: cap.status === "NOT_AVAILABLE" ? "Não disponível" : "Planejado",
      });
      return;
    }

    let mode: ErpSyncExecutionMode = "NOT_CONFIGURED";
    let implStatus: ErpSyncImplementationStatus = "NOT_AVAILABLE";
    let enabled = false;
    let scheduleLabel: string | null = null;
    let triggerLabel = "Não configurado";

    if (!isConfigured) {
      mode = "NOT_CONFIGURED";
    } else if (policy) {
      enabled = policy.ativa;
      if (policy.mode === "AGENDADO" || policy.mode === "SCHEDULED") {
        mode = "SCHEDULED";
        implStatus = enabled ? "IMPLEMENTED_ACTIVE" : "IMPLEMENTED_INACTIVE";
        triggerLabel = "Automática";
        scheduleLabel = policy.trigger_expression || "Intervalo pré-definido";
      } else if (policy.mode === "EVENTO" || policy.mode === "EVENT") {
        // According to audit: verify true event. Currently sankhya has no true events running.
        // But if policy is EVENT, we mark as EVENT, but change label.
        mode = "EVENT";
        implStatus = enabled ? "IMPLEMENTED_ACTIVE" : "IMPLEMENTED_INACTIVE";
        triggerLabel = "Por evento";
        scheduleLabel = "Assíncrono";
      } else if (policy.mode === "OUTBOX") {
        mode = "OUTBOX";
        implStatus = enabled ? "IMPLEMENTED_ACTIVE" : "IMPLEMENTED_INACTIVE";
        triggerLabel = "Pela fila de eventos";
        scheduleLabel = "Assíncrono via Outbox";
      } else {
        mode = "DISABLED";
        implStatus = "CONFIGURED";
        triggerLabel = "Desabilitada";
      }
    } else if (cap.syncMode === "MANUAL") {
      mode = "MANUAL";
      implStatus = "IMPLEMENTED_ACTIVE";
      triggerLabel = "Manual";
      enabled = true;
    } else {
      mode = "DECLARED";
      implStatus = "DECLARED";
      triggerLabel = "Declarada";
    }

    if (mode !== "NOT_CONFIGURED" && mode !== "DECLARED") {
      policyViewModels.push({
        id: `policy-${cap.code}`,
        featureCode: cap.code,
        capabilityName: cap.name,
        mode,
        implementationStatus: implStatus,
        enabled,
        triggerLabel,
        scheduleLabel,
        lastRunAt: lastSuccessAt, // using global for now unless we have per-policy
        nextRunAt: enabled && mode === "SCHEDULED" ? nextRunAt : null,
        providerName,
        scopeLabel: "Geral",
      });
    }
  });

  const jobViewModels: ErpSyncJobViewModel[] = jobs.map((job) => {
    let durationMs: number | null = null;
    if (job.started_at && job.finished_at) {
      durationMs = new Date(job.finished_at).getTime() - new Date(job.started_at).getTime();
    }
    const cap = capabilities.find((c) => c.code === job.feature_code);

    let message = null;
    if (job.job_status === "FAILED" || job.erros > 0) {
      message = "Ocorreram erros durante a sincronização";
    }

    return {
      id: job.id,
      featureCode: job.feature_code || null,
      capabilityName: cap?.name || job.feature_code || "Processo global",
      status: job.job_status,
      triggerLabel: job.trigger_type === "MANUAL" ? "Manual" : job.trigger_type === "SCHEDULED" ? "Automática" : "Sistema",
      startedAt: job.started_at || null,
      finishedAt: job.finished_at || null,
      durationMs,
      processed: job.processados,
      successes: job.sucessos,
      failures: job.erros,
      message,
    };
  });

  const runningJobsCount = jobs.filter((j) => j.job_status === "RUNNING" || j.job_status === "PENDING").length;
  // Recent failures: in the loaded job set, how many failed
  const recentFailures = jobs.filter((j) => j.job_status === "FAILED" || j.erros > 0).length;
  const activePoliciesCount = policyViewModels.filter((p) => p.enabled).length;

  return {
    summary: {
      activePolicies: activePoliciesCount,
      runningJobs: runningJobsCount,
      recentFailures,
      lastSuccessAt,
      nextRunAt,
    },
    policies: policyViewModels,
    jobs: jobViewModels,
    manualActions: manualActionsInput.map((action, idx) => ({
      ...action,
      enabled:
        action.enabled &&
        (!action.requiresConfiguredIntegration || isConfigured),
      id: `manual-action-${idx}`,
    })),
    plannedCapabilities,
  };
}
