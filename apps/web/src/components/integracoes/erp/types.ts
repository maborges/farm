export interface ProviderFieldSelectOption {
  value: string | number | boolean;
  label: string;
}

export interface ProviderFieldDefinition {
  key: string;
  label: string;
  type: "string" | "secret" | "select" | "boolean" | "integer" | "url";
  required: boolean;
  secret: boolean;
  placeholder?: string | null;
  help_text?: string | null;
  default?: unknown | null;
  order: number;
  options?: ProviderFieldSelectOption[] | null;
}

export interface ProviderSchemaDefinition {
  schema_version: number;
  required: string[];
  optional: string[];
  fields: ProviderFieldDefinition[];
}

export interface ProviderPublicIdentity {
  id: number;
  slug: string;
  nome: string;
  provider_type: string;
  ativa: boolean;
}

export interface ProviderSchemaResponse {
  provider: ProviderPublicIdentity;
  schema_version: number;
  connection_schema: ProviderSchemaDefinition | null;
  credential_schema: ProviderSchemaDefinition | null;
}

export type ConsoleResourceStatus =
  | "idle"
  | "loading"
  | "success"
  | "empty"
  | "not_found"
  | "forbidden"
  | "error";

export interface ConsoleResourceState<T> {
  status: ConsoleResourceStatus;
  data: T | null;
  message?: string | null;
}

export interface CapabilityMatrixItem {
  feature_code: string;
  display_name: string;
  description?: string | null;
  capability_code: string;
  status: string;
  maturity: string;
  direction: string;
  supported_scopes: string[];
  supported_sync_modes: string[];
  dependencies: string[];
  restrictions: string[];
  observability_requirements: string[];
  pilot_tier: string;
}

export interface ProviderDefinition {
  provider_code: string;
  provider_name: string;
  display_name: string;
  vendor?: string | null;
  supported_versions?: string[];
  authentication_models?: string[];
  supported_scopes?: string[];
  supported_capabilities?: string[];
  supported_sync_modes?: string[];
  support_level?: string | null;
  maturity?: string | null;
  provider_notes?: string[];
}

export interface ErpFeatureSchema {
  supported_features?: string[];
  capability_matrix?: CapabilityMatrixItem[];
}

export interface ErpConsoleConfig {
  [key: string]: unknown;
  id: number;
  tenant_id: string;
  provider_code?: string | null;
  provider_name?: string | null;
  provider_display_name?: string | null;
  sankhya_environment?: string | null;
  sankhya_api_base_url?: string | null;
  sankhya_auth_url?: string | null;
  sankhya_client_id?: string | null;
  sankhya_client_secret_configured?: boolean;
  sankhya_client_secret_mask?: string | null;
  sankhya_x_token_configured?: boolean;
  sankhya_x_token_mask?: string | null;
  sankhya_token_configured?: boolean;
  sankhya_token_mask?: string | null;
  sankhya_appkey_configured?: boolean;
  sankhya_appkey_mask?: string | null;
  connection_schema?: Record<string, unknown> | null;
  credential_schema?: Record<string, unknown> | null;
  provider_definition?: ProviderDefinition | null;
  feature_schema?: ErpFeatureSchema | null;
  sync_schema?: Record<string, unknown> | null;
  health_schema?: Record<string, unknown> | null;
  ws_url?: string | null;
  username?: string | null;
  ativo: boolean;
  ultimo_teste?: string | null;
  teste_status?: string | null;
  ultimo_sync?: string | null;
  sync_interval: number;
  auth_model?: string | null;
  legacy_configured?: boolean;
  password_configured: boolean;
  password_mask?: string | null;
}

export interface ErpPolicySummary {
  feature_code: string;
  mode: string;
  prioridade?: string | null;
  ativa: boolean;
  retry_ativo?: boolean | null;
  retry_limite: number;
  batch_size?: number | null;
  timeout_seconds?: number | null;
  trigger_expression?: string | null;
}

export interface ErpReadinessSummary {
  status: string;
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
  summary: string;
  pending: string[];
  block_reasons?: string[];
  cta_url: string;
  provider_code?: string | null;
  provider_display_name?: string | null;
  health_status?: string | null;
  capabilities_evaluated?: Array<Record<string, unknown>>;
  policies_evaluated?: Array<Record<string, unknown>>;
  pending_links?: number;
  conflict_links?: number;
}

export interface ErpStatusResponse {
  configurado: boolean;
  ativo: boolean;
  ultimo_sync?: string | null;
  proximo_sync?: string | null;
  status_conexao: string;
  status_legado?: string | null;
  status_canonico?: string | null;
  status_origem: string;
  health_origem: string;
  config_id_canonico?: number | null;
  lifecycle_state?: string | null;
  health_status?: string | null;
  health_summary?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  consecutive_failures: number;
  features_habilitadas: string[];
  policies_resumidas: ErpPolicySummary[];
  provider_definition?: ProviderDefinition | null;
  feature_schema?: ErpFeatureSchema | null;
  sync_schema?: Record<string, unknown> | null;
  health_schema?: Record<string, unknown> | null;
  readiness?: ErpReadinessSummary | null;
}

export interface ErpHealthResponse {
  configurado: boolean;
  origem: string;
  status: string;
  summary?: string | null;
  checked_at?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  consecutive_failures: number;
  details?: Record<string, unknown> | string | null;
}

export interface ErpJob {
  id: string;
  feature_code?: string | null;
  job_status: string;
  trigger_type: string;
  started_at?: string | null;
  finished_at?: string | null;
  processados: number;
  sucessos: number;
  erros: number;
  legacy_log_id?: number | null;
}

export interface ErpSyncLog {
  id: number;
  tipo: string;
  operacao: string;
  status: string;
  registros_processados: number;
  registros_sucesso: number;
  registros_erro: number;
  tempo_execucao_ms?: number | null;
  created_at: string;
  origem_dados?: string;
  integration_job_id?: string | null;
  feature_code?: string | null;
  job_status?: string | null;
  trigger_type?: string | null;
}

export interface ExternalAssociationHistoryItem {
  id: string;
  event_type: string;
  previous_external_record_id?: string | null;
  new_external_record_id?: string | null;
  previous_status?: string | null;
  new_status?: string | null;
  actor_usuario_id?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface ExternalAssociationPendingItem {
  id: string;
  provider_id: number;
  config_id: number;
  feature_id?: number | null;
  feature_code?: string | null;
  environment: string;
  local_entity_type: string;
  local_entity_id?: string | null;
  external_entity_type: string;
  external_id: string;
  external_key: string;
  external_payload?: Record<string, unknown> | null;
  motivo?: string | null;
  status: string;
  confidence: string;
  history: ExternalAssociationHistoryItem[];
}

export interface ErpDiagnosis {
  origem: string;
  health_atual: string;
  status_degradacao: string;
  ultimo_sucesso_at?: string | null;
  ultima_falha_at?: string | null;
  falhas_consecutivas: number;
  feature_mais_problematica?: string | null;
  jobs_pendentes: number;
  jobs_falhos: number;
  recomendacao_operacional: string;
}

export type ErpCapabilityOperationalStatus =
  | "ACTIVE"
  | "PARTIAL"
  | "DISABLED"
  | "PENDING_CONFIGURATION"
  | "DEGRADED"
  | "FAILED"
  | "DECLARED"
  | "NOT_AVAILABLE";

export type ErpSyncDirection =
  | "ERP_TO_AGROSAAS"
  | "AGROSAAS_TO_ERP"
  | "BIDIRECTIONAL_CONTROLLED"
  | "EVIDENCE_RETURN"
  | "NONE";

export type ErpSyncMode =
  | "MANUAL"
  | "SCHEDULED"
  | "EVENT"
  | "OUTBOX"
  | "DISABLED"
  | "NOT_CONFIGURED";

export type ErpCapabilityMaturity =
  | "TESTED"
  | "PARTIAL"
  | "DECLARED"
  | "P2"
  | "UNAVAILABLE";

export interface ErpCapabilityActionsViewModel {
  canViewDetails: boolean;
  canSyncManually: boolean;
  canConfigure: boolean;
  canReconcile: boolean;
  canReprocess: boolean;
}

export interface ErpCapabilityTechnicalViewModel {
  adapterLabel?: string | null;
  internalOperationLabels?: string[];
  externalSystemLabel?: string | null;
}

export interface ErpTimelineEntry {
  id: string;
  tipo_registro: string;
  origem_dado: string;
  feature_code?: string | null;
  status: string;
  event_type?: string | null;
  resumo: string;
  occurred_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  duracao_ms?: number | null;
  processados: number;
  sucessos: number;
  erros: number;
  correlation_id?: string | null;
}

export interface ErpCapabilityViewModel {
  code: string;
  name: string;
  description: string;
  providerSlug: string;
  providerName: string;
  status: ErpCapabilityOperationalStatus;
  enabled: boolean;
  maturity: ErpCapabilityMaturity;
  direction: ErpSyncDirection;
  masterSystem: string;
  syncMode: ErpSyncMode;
  healthStatus: string | null;
  lastSyncAt: string | null;
  lastJobAt: string | null;
  nextRunAt: string | null;
  pendingAssociations: number;
  conflictingAssociations: number;
  actions: ErpCapabilityActionsViewModel;
  pilotTier?: string | null;
  technical?: ErpCapabilityTechnicalViewModel;
}

export interface BuildErpCapabilityViewModelsInput {
  providerSlug: string;
  providerSchema?: ProviderSchemaResponse | null;
  config?: ErpConsoleConfig | null;
  status?: ErpStatusResponse | null;
  health?: ErpHealthResponse | null;
  jobs?: ErpJob[] | null;
  diagnosis?: ErpDiagnosis | null;
  pendingAssociations?: ExternalAssociationPendingItem[] | null;
  manualSyncCapabilities?: string[] | null;
  adapterLabel?: string | null;
  canConfigure?: boolean;
  canViewDetails?: boolean;
  canReconcile?: boolean;
}

export interface ErpCapabilityJobViewModel {
  id: string;
  relation: "RELATED" | "GENERAL";
  title: string;
  status: string;
  triggerLabel: string;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  processed: number;
  successes: number;
  errors: number;
}

export interface ErpCapabilityTimelineItemViewModel {
  id: string;
  relation: "RELATED" | "GENERAL";
  tipoRegistro: string;
  originLabel: string;
  featureCode: string | null;
  status: string;
  eventType: string | null;
  summary: string;
  occurredAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  processed: number;
  successes: number;
  errors: number;
  correlationId: string | null;
}

export interface ErpCapabilityAssociationItemViewModel {
  id: string;
  entityType: string;
  externalReference: string;
  status: string;
  reason: string | null;
  localEntityId: string | null;
}

export interface ErpCapabilityAssociationSummaryViewModel {
  pendingCount: number;
  conflictCount: number;
  relatedItems: ErpCapabilityAssociationItemViewModel[];
}

export interface ErpCapabilityDetailsViewModel {
  capability: ErpCapabilityViewModel;
  provider: {
    slug: string;
    name: string;
    executorLabel: string | null;
  };
  ownership: {
    masterSystem: string;
    directionLabel: string;
    operationalBoundary: string | null;
  };
  execution: {
    syncModeLabel: string;
    lastSyncAt: string | null;
    lastJobAt: string | null;
    nextRunAt: string | null;
    nextRunIsShared: boolean;
  };
  health: {
    status: string | null;
    label: string;
    summary: string | null;
    isGlobal: boolean;
  };
  jobs: {
    related: ErpCapabilityJobViewModel[];
    general: ErpCapabilityJobViewModel[];
  };
  timeline: {
    related: ErpCapabilityTimelineItemViewModel[];
    general: ErpCapabilityTimelineItemViewModel[];
  };
  associations: ErpCapabilityAssociationSummaryViewModel;
  technical: {
    internalOperationLabels: string[];
    externalSystemLabel: string | null;
  };
  actions: ErpCapabilityActionsViewModel;
}

export interface BuildErpCapabilityDetailsInput {
  capabilities: ErpCapabilityViewModel[];
  jobs?: ErpJob[] | null;
  timeline?: ErpTimelineEntry[] | null;
  pendingAssociations?: ExternalAssociationPendingItem[] | null;
  health?: ErpHealthResponse | null;
  status?: ErpStatusResponse | null;
}

export type ErpAssociationStatus =
  | "PENDING"
  | "ACTIVE"
  | "CONFLICT"
  | "SUPERSEDED"
  | "INACTIVE";

export interface ExternalAssociationSummaryResponse {
  PENDING: number;
  CONFLICT: number;
  ACTIVE: number;
  SUPERSEDED: number;
  INACTIVE: number;
  TOTAL: number;
}

export interface ErpAssociationViewModel {
  id: string;
  featureCode: string | null;
  environment: string;
  localEntityType: string;
  localEntityId: string | null;
  externalEntityType: string;
  externalId: string;
  status: ErpAssociationStatus;
  confidence: string;
  reason: string | null;
  createdAt: string;
  lastSyncAt: string | null;
  history: ExternalAssociationHistoryItem[];
  actions: {
    canViewDetails: boolean;
    canReconcile: boolean;
  };
}

export interface ErpAssociationSummaryViewModel {
  pendingCount: number;
  conflictCount: number;
  activeCount: number;
  totalCount: number;
}
