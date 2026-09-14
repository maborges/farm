"use client";

// Compatibilidade arquitetural: esta implementacao continua sendo a antiga "Integração Sankhya".

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Clock3,
  Database,
  Link2,
  Loader2,
  RefreshCw,
  Settings2,
  ShieldAlert,
  Trash2,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErpCapabilityCenter } from "@/components/integracoes/erp/capability-center";
import { AssociationCenter } from "@/components/integracoes/erp/association-center";
import { ErpConfigurationSection } from "@/components/integracoes/erp/configuration-section";
import { ErpSyncCenter } from "@/components/integracoes/erp/sync-center";
import { ErpPolicyManager } from "@/components/integracoes/erp/policy-manager";
import {
  buildInitialProviderFormData,
  getEditableProviderFields,
  getProviderFieldSelectOptions,
} from "@/components/integracoes/erp/provider-config-fields";
import { resolveProviderConsoleEndpoints } from "@/components/integracoes/erp/provider-console-endpoints";
import { buildErpSyncCenterViewModel } from "@/components/integracoes/erp/sync-center-view-model";
import { buildErpCapabilityDetailsViewModels } from "@/components/integracoes/erp/capability-details-view-model";
import { buildErpCapabilityViewModels } from "@/components/integracoes/erp/capability-view-model";
import { ERP_PROVIDER_CONSOLES } from "@/components/integracoes/erp/erp-provider-registry";
import { ErpProviderSelector } from "@/components/integracoes/erp/erp-provider-selector";
import type {
  ConsoleResourceState,
  ErpConsoleConfig,
  ErpDiagnosis,
  ErpHealthResponse,
  ErpJob,
  ErpReadinessSummary,
  ErpStatusResponse,
  ProviderFieldDefinition,
  ProviderSchemaResponse,
} from "@/components/integracoes/erp/types";
import { ErpTimeline, type ErpTimelineItem } from "@/components/integracoes/sankhya-timeline";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import { isApiError } from "@/lib/api-error";
import { buildProviderConfigPayload } from "./erp/provider-config-payload";
import {
  SankhyaPeoplePreview,
  type SankhyaPersonPreview,
} from "./erp/sankhya-people-preview";

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Não disponível";
  }
  return new Date(value).toLocaleString("pt-BR");
}

function getStatusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    sucesso: "default",
    processando: "secondary",
    erro: "destructive",
    pendente: "secondary",
    CONNECTED: "default",
    DEGRADED: "secondary",
    DISCONNECTED: "destructive",
    AUTH_ERROR: "destructive",
    CONFIG_ERROR: "destructive",
    PARTIAL_FAILURE: "secondary",
    RATE_LIMITED: "secondary",
    RUNNING: "secondary",
    SUCCESS: "default",
    FAILED: "destructive",
    ACTIVE: "default",
    PARTIAL: "secondary",
    DISABLED: "secondary",
    PENDING_CONFIGURATION: "secondary",
    DECLARED: "outline",
    NOT_AVAILABLE: "destructive",
  };

  return variants[status] || "secondary";
}

function formatLabel(value?: string | null) {
  if (!value) {
    return "Não disponível";
  }
  const translated: Record<string, string> = {
    CONNECTED: "Conectado",
    DISCONNECTED: "Sem comunicação",
    DEGRADED: "Com oscilações",
    AUTH_ERROR: "Falha de autenticação",
    CONFIG_ERROR: "Configuração incompleta",
    PARTIAL_FAILURE: "Falha parcial",
    RATE_LIMITED: "Limite de uso atingido",
    RUNNING: "Em andamento",
    SUCCESS: "Concluído",
    FAILED: "Falhou",
    PENDING: "Pendente",
    ACTIVE: "Ativo",
    PENDING_CONFIGURATION: "Configuração pendente",
    VALIDATING: "Em validação",
    VALID: "Válido",
    INVALID: "Inválido",
    SUSPENDED: "Suspenso",
    DISABLED: "Desativado",
    REMOVED: "Removido",
    REVOKED: "Revogado",
    MANUAL: "Manual",
    SCHEDULED: "Agendado",
    EVENT_DRIVEN: "Por evento",
    POLLING: "Consulta periódica",
    ON_DEMAND: "Sob demanda",
    WEBHOOK: "Webhook",
    SUPPORTED: "Disponível",
    PARTIAL: "Parcial",
    UNSUPPORTED: "Não disponível",
    UNKNOWN: "Em avaliação",
    DECLARED: "Declarado",
    NOT_AVAILABLE: "Indisponível",
    TESTED: "Validado",
    PILOT_READY: "Pronto para piloto",
    PRODUCTION_READY: "Pronto para produção",
    DEPRECATED: "Em descontinuação",
    ERP_TO_AGROSAAS: "ERP para DeepFarms",
    AGROSAAS_TO_ERP: "DeepFarms para ERP",
    BIDIRECTIONAL_CONTROLLED: "Fluxo controlado nos dois sentidos",
    EVIDENCE_RETURN: "Retorno de comprovantes",
    EVENT: "Por evento",
    OUTBOX: "Outbox",
    NOT_CONFIGURED: "Não configurado",
    NONE: "Sem atualização",
    UNAVAILABLE: "Indisponível",
    TENANT: "Produtor",
    ESTABELECIMENTO: "Estabelecimento",
  };
  if (translated[value]) {
    return translated[value];
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function idleResourceState<T>(): ConsoleResourceState<T> {
  return {
    status: "idle",
    data: null,
    message: null,
  };
}

function loadingResourceState<T>(): ConsoleResourceState<T> {
  return {
    status: "loading",
    data: null,
    message: null,
  };
}

function normalizeResourceErrorMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallbackMessage;
}

async function fetchConsoleResource<T>(
  path: string,
  options: {
    allowNotFound?: boolean;
    emptyMessage?: string;
    suppressErrorLog?: boolean;
  } = {},
): Promise<ConsoleResourceState<T>> {
  try {
    const data = await apiFetch<T>(path, { suppressErrorLog: options.suppressErrorLog ?? true });
    if (data === null) {
      return {
        status: "empty",
        data: null,
        message: options.emptyMessage || null,
      };
    }
    return {
      status: "success",
      data,
      message: null,
    };
  } catch (error) {
    if (isApiError(error)) {
      if (error.status === 404 && options.allowNotFound) {
        return {
          status: "not_found",
          data: null,
          message: null,
        };
      }
      if (error.status === 403) {
        return {
          status: "forbidden",
          data: null,
          message: normalizeResourceErrorMessage(
            error,
            "Você não possui permissão para acessar este recurso.",
          ),
        };
      }
      if (error.status === 404) {
        return {
          status: "not_found",
          data: null,
          message: normalizeResourceErrorMessage(error, "Recurso não encontrado."),
        };
      }
    }
    return {
      status: "error",
      data: null,
      message: normalizeResourceErrorMessage(error, "Não foi possível carregar este recurso."),
    };
  }
}

type ErpStatusQueryData = ErpStatusResponse & { notFound?: boolean };

function getActiveProviderSlug(
  statusData?: Pick<ErpStatusResponse, "provider_definition" | "readiness"> | null,
) {
  const activeProviderCode =
    statusData?.provider_definition?.provider_code || statusData?.readiness?.provider_code;
  return typeof activeProviderCode === "string" ? activeProviderCode.toLowerCase() : null;
}

export function isErpConsoleBootstrapState(statusData?: ErpStatusQueryData | null) {
  if (!statusData) {
    return false;
  }
  if (statusData.notFound) {
    return true;
  }
  return statusData.configurado === false && getActiveProviderSlug(statusData) === null;
}

export function resolveErpOverviewReadiness({
  readiness,
  providerName,
  hasSavedConfig,
}: {
  readiness: ErpReadinessSummary;
  providerName: string;
  hasSavedConfig: boolean;
}): Pick<ErpReadinessSummary, "label" | "variant" | "summary" | "pending"> {
  const providerIsMissingOnlyFromRuntime =
    readiness.status === "NOT_CONFIGURED" && !readiness.provider_code;

  if (!providerIsMissingOnlyFromRuntime) {
    return {
      label: readiness.label,
      variant: readiness.variant,
      summary: readiness.summary,
      pending: readiness.pending,
    };
  }

  if (hasSavedConfig) {
    return {
      label: "Configuração salva",
      variant: "secondary",
      summary: `${providerName} está configurado. Valide a comunicação para confirmar que a integração está pronta.`,
      pending: ["validar a comunicação com o ERP"],
    };
  }

  return {
    label: "Configuração pendente",
    variant: "secondary",
    summary: `${providerName} selecionado. Preencha e salve a configuração para concluir a conexão.`,
    pending: ["preencher e salvar a configuração inicial"],
  };
}

export function getErpSyncErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Não foi possível atualizar os dados do ERP.";
}

export interface DynamicErpConsoleProps {
  providerSlug?: string;
  endpoints?: {
    getConfig: string;
    saveConfig: string;
    testConnection: string;
    sync: (tipo: string) => string;
    getLogs: string;
    listPeople?: string;
  };
  operationalConfig?: {
    manualSyncCapabilities?: string[];
    fullSyncAction?: {
      code: string;
      label: string;
      variant?: "default" | "outline" | "secondary";
    };
    adapterLabel?: string;
  };
}

export function DynamicErpConsole({
  providerSlug = "sankhya",
  endpoints,
  operationalConfig,
}: DynamicErpConsoleProps) {
  const resolvedEndpoints = resolveProviderConsoleEndpoints(providerSlug, endpoints);
  const [schemaState, setSchemaState] = useState<ConsoleResourceState<ProviderSchemaResponse>>(
    loadingResourceState(),
  );
  const [configState, setConfigState] = useState<ConsoleResourceState<ErpConsoleConfig>>(
    loadingResourceState(),
  );
  const [statusState, setStatusState] = useState<ConsoleResourceState<ErpStatusResponse>>(
    loadingResourceState(),
  );
  const [healthState, setHealthState] = useState<ConsoleResourceState<ErpHealthResponse>>(
    loadingResourceState(),
  );
  const [jobsState, setJobsState] = useState<ConsoleResourceState<ErpJob[]>>(loadingResourceState());
  const [timelineState, setTimelineState] = useState<ConsoleResourceState<ErpTimelineItem[]>>(
    loadingResourceState(),
  );
  const [diagnosisState, setDiagnosisState] = useState<ConsoleResourceState<ErpDiagnosis>>(
    loadingResourceState(),
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<Record<string, boolean>>({});
  const [workspaceTab, setWorkspaceTab] = useState<"dados" | "atividade" | "associacoes" | "configuracao">("dados");
  const { toast } = useToast();
  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const configDataRef = useRef<ErpConsoleConfig | null>(null);
  const peopleEndpoint = endpoints?.listPeople;
  const peopleQuery = useQuery<SankhyaPersonPreview[]>({
    queryKey: ["erp", providerSlug, "pessoas-sincronizadas"],
    queryFn: () => apiFetch(peopleEndpoint!),
    enabled: Boolean(peopleEndpoint),
  });

  useEffect(() => {
    configDataRef.current = configState.data;
  }, [configState.data]);

  const loadConsole = useCallback(async () => {
    setLoading(true);
    setSchemaState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setConfigState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setStatusState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setHealthState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setJobsState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setTimelineState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    setDiagnosisState((current) =>
      current.status === "success" ? { ...current, status: "loading", message: null } : loadingResourceState(),
    );
    try {
      const [
        nextSchemaState,
        nextDiagnosisState,
        nextConfigState,
        nextStatusState,
        nextHealthState,
        nextJobsState,
        nextTimelineState,
      ] = await Promise.all([
        fetchConsoleResource<ProviderSchemaResponse>(
          `/integracoes/erp/providers/${providerSlug}/schema`,
          { emptyMessage: "Este provider não disponibilizou campos de configuração." },
        ),
        fetchConsoleResource<ErpDiagnosis>("/integracoes/erp/diagnostico"),
        fetchConsoleResource<ErpConsoleConfig>(
          resolvedEndpoints.getConfig,
          { allowNotFound: true },
        ),
        fetchConsoleResource<ErpStatusResponse>("/integracoes/erp/status"),
        fetchConsoleResource<ErpHealthResponse>("/integracoes/erp/health"),
        fetchConsoleResource<ErpJob[]>("/integracoes/erp/jobs?limit=5"),
        fetchConsoleResource<ErpTimelineItem[]>("/integracoes/erp/timeline?limit=12"),
      ]);

      const normalizedSchemaState =
        nextSchemaState.status === "success" && getEditableProviderFields(nextSchemaState.data).allFields.length === 0
          ? {
              ...nextSchemaState,
              status: "empty" as const,
              message: "Este provider não disponibilizou campos de configuração.",
            }
          : nextSchemaState;

      setSchemaState(normalizedSchemaState);
      setDiagnosisState(nextDiagnosisState);
      setConfigState((current) => {
        if (nextConfigState.status === "error" || nextConfigState.status === "forbidden") {
          return {
            ...nextConfigState,
            data: current.data,
          };
        }
        return nextConfigState;
      });
      setStatusState(nextStatusState);
      setHealthState(nextHealthState);
      setJobsState(nextJobsState);
      setTimelineState(nextTimelineState);

      const nextConfigData =
        nextConfigState.status === "success"
          ? nextConfigState.data
          : nextConfigState.status === "not_found"
            ? null
            : configDataRef.current;
      if (normalizedSchemaState.status === "success") {
        setFormData(
          buildInitialProviderFormData({
            schema: normalizedSchemaState.data,
            config: nextConfigData,
          }),
        );
      }

      const coreDataLoaded = [
        normalizedSchemaState,
        nextConfigState,
        nextStatusState,
        nextHealthState,
        nextDiagnosisState,
      ].some((resource) => ["success", "not_found", "empty"].includes(resource.status));
      setLoadError(
        coreDataLoaded
          ? null
          : "Não foi possível carregar a situação atual da integração com o ERP.",
      );
    } catch (error) {
      console.error("Erro ao carregar o console ERP:", error);
      setLoadError("Atualize a situação ou revise a configuração para tentar novamente.");
      toast({ title: "Erro", description: "Não foi possível carregar a situação atual da integração com o ERP.", variant: "destructive" });
      setSchemaState((current) => current.status === "idle" ? idleResourceState() : current);
    } finally {
      setLoading(false);
    }
  }, [providerSlug, resolvedEndpoints.getConfig, toast]);

  useEffect(() => {
    void loadConsole();
  }, [loadConsole]);

  const schema = schemaState.data;
  const config = configState.data;
  const status = statusState.data;
  const health = healthState.data;
  const jobs = jobsState.data || [];
  const timeline = timelineState.data || [];
  const diagnosis = diagnosisState.data;
  const {
    connectionFields,
    credentialFields,
    allFields: editableConfigFields,
  } = getEditableProviderFields(schema);
  const hasEditableConfigFields = editableConfigFields.length > 0;
  const hasSavedProviderConfig = configState.status === "success" && Boolean(config);
  const isConfigured = Boolean(status?.configurado || hasSavedProviderConfig);

  useEffect(() => {
    if (!loading && !isConfigured) {
      setWorkspaceTab("configuracao");
    }
  }, [isConfigured, loading]);

  async function handleSave() {
    if (!schema || editableConfigFields.length === 0) {
      toast({
        title: "Configuração indisponível",
        description: "Não há campos de configuração disponíveis para salvar neste momento.",
        variant: "destructive",
      });
      return;
    }
    setSaving(true);
    try {
      const initialValues: Record<string, unknown> = schema
        ? buildInitialProviderFormData({
            schema,
            config,
          })
        : {};

      const payload = buildProviderConfigPayload({
        schema,
        formData,
        initialValues,
      });

      await apiFetch(resolvedEndpoints.saveConfig, {
        method: "POST",
        body: payload,
      });

      await loadConsole();
      toast({ title: "Sucesso", description: "Dados da integração ERP salvos com sucesso." });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Não foi possível salvar os dados da integração.";
      toast({ title: "Erro", description: message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    if (!schema || editableConfigFields.length === 0) {
      toast({
        title: "Configuração indisponível",
        description: "Carregue os campos de configuração antes de testar a comunicação.",
        variant: "destructive",
      });
      return;
    }
    setTesting(true);
    try {
      const data = await apiFetch<{ sucesso: boolean; mensagem: string }>(resolvedEndpoints.testConnection, {
        method: "POST",
      });
      if (data.sucesso) {
        toast({ title: "Sucesso", description: data.mensagem });
      } else {
        toast({ title: "Erro", description: data.mensagem, variant: "destructive" });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Não foi possível testar a comunicação com o ERP.";
      toast({ title: "Erro", description: message, variant: "destructive" });
    } finally {
      setTesting(false);
    }
  }

  async function handleSync(tipo: string) {
    setSyncing((current) => ({ ...current, [tipo]: true }));
    try {
      const result = await apiFetch<{ sucesso: boolean; mensagem: string }>(resolvedEndpoints.sync(tipo), {
        method: "POST",
      });
      toast({ title: "Sucesso", description: result.mensagem });
      await Promise.all([loadConsole(), peopleEndpoint ? peopleQuery.refetch() : Promise.resolve()]);
    } catch (error) {
      toast({ title: "Erro", description: getErpSyncErrorMessage(error), variant: "destructive" });
    } finally {
      setSyncing((current) => ({ ...current, [tipo]: false }));
    }
  }



  if (loading && !status && !config && !schema) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  const providerDefinition = config?.provider_definition ?? status?.provider_definition ?? null;
  const readiness = status?.readiness ?? {
    status: "PENDENTE",
    label: "Pendente",
    variant: "secondary" as const,
    summary: "A avaliação consolidada da integração não está disponível no momento.",
    pending: ["avaliação da integração indisponível"],
    cta_url: "/dashboard/settings/integracoes/erp",
  };
  const currentErpLabel =
    providerDefinition?.display_name || config?.provider_display_name || "Sankhya";
  const overviewReadiness = resolveErpOverviewReadiness({
    readiness,
    providerName: currentErpLabel,
    hasSavedConfig: hasSavedProviderConfig,
  });
  const capabilityViewModels = buildErpCapabilityViewModels({
    providerSlug,
    providerSchema: schema,
    config,
    status,
    health,
    jobs,
    diagnosis,
    pendingAssociations: [],
    manualSyncCapabilities: operationalConfig?.manualSyncCapabilities,
    adapterLabel: operationalConfig?.adapterLabel,
    canConfigure: Boolean(resolvedEndpoints.saveConfig && hasEditableConfigFields),
  });
  const fullSyncAction = operationalConfig?.fullSyncAction;
  const capabilityDetails = buildErpCapabilityDetailsViewModels({
    capabilities: capabilityViewModels,
    jobs,
    timeline,
    pendingAssociations: [],
    health,
    status,
  });


  const manualActionsInput: Parameters<typeof buildErpSyncCenterViewModel>[4] = [];
  if (fullSyncAction) {
    manualActionsInput.push({
      label: fullSyncAction.label,
      description: "Executa sincronização completa do ERP.",
      execute: async () => { await handleSync(fullSyncAction.code); },
      enabled: true,
      requiresConfiguredIntegration: true,
    });
  }

  const syncCenterViewModel = buildErpSyncCenterViewModel(
    status,
    jobs,
    capabilityViewModels,
    currentErpLabel,
    manualActionsInput
  );


  function renderField(field: ProviderFieldDefinition) {
    const rawValue = formData[field.key];
    const value = rawValue ?? (field.type === "boolean" ? false : "");

    return (
      <div key={field.key} className="space-y-2">
        <Label htmlFor={field.key}>
          {field.label}
          {field.required && <span className="ml-1 text-destructive">*</span>}
        </Label>

        {field.type === "boolean" ? (
          <div className="flex h-8 items-center gap-2">
            <input
              type="checkbox"
              id={field.key}
              className="h-4 w-4 rounded border-gray-300"
              checked={Boolean(value)}
              onChange={(event) =>
                setFormData((current) => ({ ...current, [field.key]: event.target.checked }))
              }
            />
            <span className="text-sm text-muted-foreground">{field.help_text}</span>
          </div>
        ) : field.type === "select" ? (
          <select
            id={field.key}
            className="flex h-8 w-full items-center justify-between rounded-sm border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={String(value)}
            onChange={(event) =>
              setFormData((current) => ({ ...current, [field.key]: event.target.value }))
            }
          >
            <option value="" disabled>
              Selecione...
            </option>
            {getProviderFieldSelectOptions(field, value).map((option) => (
              <option key={String(option.value)} value={String(option.value)}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <Input
            id={field.key}
            type={field.secret || field.type === "secret" ? "password" : "text"}
            className="h-8 rounded-sm text-sm"
            placeholder={field.placeholder || ""}
            value={String(value)}
            onChange={(event) =>
              setFormData((current) => ({ ...current, [field.key]: event.target.value }))
            }
          />
        )}

        {field.help_text && field.type !== "boolean" ? (
          <p className="mt-1 text-xs text-muted-foreground">{field.help_text}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="rounded-sm border-border/70 bg-gradient-to-br from-background via-background to-primary/5">
        <CardHeader className="gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-1">
            <CardTitle>{currentErpLabel}</CardTitle>
            <CardDescription>{overviewReadiness.summary}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={status?.ativo ? "default" : "secondary"}>{status?.ativo ? "Ativo" : "Inativo"}</Badge>
            <Badge variant={overviewReadiness.variant}>{overviewReadiness.label}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-sm border bg-background/70 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Conexão</p>
              <p className="mt-1 font-medium">{formatLabel(health?.status || status?.status_conexao)}</p>
            </div>
            <div className="rounded-sm border bg-background/70 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Última atualização</p>
              <p className="mt-1 font-medium">{formatDateTime(status?.last_success_at || status?.ultimo_sync)}</p>
            </div>
            <div className="rounded-sm border bg-background/70 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Próxima atualização</p>
              <p className="mt-1 font-medium">{formatDateTime(status?.proximo_sync)}</p>
            </div>
            <div className="rounded-sm border bg-background/70 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Fluxos informados</p>
              <p className="mt-1 font-medium">{capabilityViewModels.length}</p>
            </div>
          </div>
          {overviewReadiness.pending.length > 0 ? (
            <Alert>
              <AlertDescription>
                <span className="font-medium">Próximo passo:</span> {overviewReadiness.pending[0]}
              </AlertDescription>
            </Alert>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" className="rounded-sm" onClick={() => void loadConsole()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Atualizar situação
            </Button>
            <Button type="button" size="sm" variant="outline" className="rounded-sm" onClick={() => setWorkspaceTab("configuracao")}>
              <Settings2 className="mr-2 h-4 w-4" />
              Abrir configuração
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs
        value={workspaceTab}
        onValueChange={(value) => setWorkspaceTab(value as typeof workspaceTab)}
        className="gap-4"
      >
        <TabsList className="grid h-auto w-full grid-cols-2 gap-1 lg:grid-cols-4">
          <TabsTrigger value="dados"><Database className="h-4 w-4" />Dados sincronizados</TabsTrigger>
          <TabsTrigger value="atividade"><Activity className="h-4 w-4" />Atividade</TabsTrigger>
          <TabsTrigger value="associacoes"><Link2 className="h-4 w-4" />Associações</TabsTrigger>
          <TabsTrigger value="configuracao"><Settings2 className="h-4 w-4" />Configuração</TabsTrigger>
        </TabsList>

        <TabsContent value="dados" className="space-y-4">
          <ErpCapabilityCenter
            capabilities={capabilityViewModels}
            capabilityDetails={capabilityDetails}
            loading={loading}
            error={loadError}
            configured={isConfigured}
            providerName={currentErpLabel}
            onRetry={() => void loadConsole()}
            onSyncManual={(capabilityCode) => void handleSync(capabilityCode)}
            syncing={syncing}
            onConfigure={() => setWorkspaceTab("configuracao")}
            onAssociations={() => setWorkspaceTab("associacoes")}
            configurationTargetId="erp-configuracao"
          />
          {peopleEndpoint ? (
            <SankhyaPeoplePreview
              people={peopleQuery.data ?? []}
              loading={peopleQuery.isLoading}
              error={peopleQuery.error ? getErpSyncErrorMessage(peopleQuery.error) : null}
            />
          ) : null}
        </TabsContent>

        <TabsContent value="atividade" className="space-y-6">
          <ErpPolicyManager onUpdated={() => void loadConsole()} />
          <ErpSyncCenter viewModel={syncCenterViewModel} syncing={syncing} />
          <Card id="erp-diagnostico" tabIndex={-1}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Clock3 className="h-4 w-4" />Diagnóstico operacional</CardTitle>
              <CardDescription>O que exige atenção na operação desta integração.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
              <div><p className="text-sm text-muted-foreground">Situação atual</p><Badge variant={getStatusBadge(diagnosis?.health_atual || "secondary")}>{formatLabel(diagnosis?.health_atual)}</Badge></div>
              <div><p className="text-sm text-muted-foreground">Degradação</p><p className="font-medium">{formatLabel(diagnosis?.status_degradacao)}</p></div>
              <div><p className="text-sm text-muted-foreground">Jobs pendentes</p><p className="font-medium">{diagnosis?.jobs_pendentes ?? 0}</p></div>
              <div><p className="text-sm text-muted-foreground">Jobs falhos</p><p className="font-medium">{diagnosis?.jobs_falhos ?? 0}</p></div>
              <div><p className="text-sm text-muted-foreground">Área com mais falhas</p><p className="font-medium">{diagnosis?.feature_mais_problematica || "Nenhuma"}</p></div>
              <div><p className="text-sm text-muted-foreground">Última falha</p><p className="font-medium">{formatDateTime(diagnosis?.ultima_falha_at)}</p></div>
              <div className="md:col-span-3 xl:col-span-6"><p className="text-sm text-muted-foreground">Recomendação operacional</p><p className="font-medium">{diagnosis?.recomendacao_operacional || "Sem recomendação disponível."}</p></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Linha do tempo operacional</CardTitle>
              <CardDescription>Histórico consolidado de execuções e mudanças de situação.</CardDescription>
            </CardHeader>
            <CardContent><ErpTimeline items={timeline} /></CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="associacoes" id="erp-associations">
          <AssociationCenter configured={isConfigured} />
        </TabsContent>

        <TabsContent value="configuracao">
          <ErpConfigurationSection
            sectionId="erp-configuracao"
            schemaState={schemaState}
            configState={configState}
            connectionFields={connectionFields}
            credentialFields={credentialFields}
            hasEditableFields={hasEditableConfigFields}
            saving={saving}
            testing={testing}
            onRetry={() => void loadConsole()}
            onSave={handleSave}
            onTestConnection={handleTestConnection}
            renderField={renderField}
            saveAllowed={Boolean(resolvedEndpoints.saveConfig)}
            testAllowed={Boolean(resolvedEndpoints.testConnection) && hasEditableConfigFields}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export function ErpConsole() {
  const [selectedProviderSlug, setSelectedProviderSlug] = useState<string | null>(null);
  const [isSelectingProvider, setIsSelectingProvider] = useState(false);
  const [deferredWithoutErp, setDeferredWithoutErp] = useState(false);
  const [removingErp, setRemovingErp] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: statusData, isLoading, error } = useQuery({
    queryKey: ["erp-status"],
    queryFn: async (): Promise<ErpStatusQueryData> => {
      try {
        return await apiFetch<ErpStatusQueryData>("/integracoes/erp/status", {
          suppressErrorLog: true,
        });
      } catch (error: unknown) {
        if (isApiError(error) && error.status === 404) {
          return { notFound: true } as ErpStatusQueryData;
        }
        throw error;
      }
    },
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-[200px] w-full rounded-xl" />
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <ShieldAlert className="h-4 w-4" />
        <AlertDescription>
          Erro ao carregar o status da integração. Verifique sua conexão e tente novamente.
        </AlertDescription>
      </Alert>
    );
  }

  // If there's no integration configured yet, and the user hasn't selected a provider in this session
  const bootstrapState = isErpConsoleBootstrapState(statusData);
  const activeProviderSlug = getActiveProviderSlug(statusData);
  const allowSkipErpSelection = !activeProviderSlug;
  const activeProviderEndpoints = activeProviderSlug
    ? resolveProviderConsoleEndpoints(activeProviderSlug)
    : null;

  async function handleRemoveErp() {
    if (!activeProviderEndpoints?.removeConfig) {
      return;
    }
    setRemovingErp(true);
    try {
      await apiFetch(activeProviderEndpoints.removeConfig, { method: "DELETE" });
      setSelectedProviderSlug(null);
      setIsSelectingProvider(false);
      setDeferredWithoutErp(true);
      await queryClient.refetchQueries({ queryKey: ["erp-status"] });
      toast({
        title: "ERP removido",
        description: "A plataforma voltou ao estado sem ERP configurado para este produtor.",
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Não foi possível remover a integração ERP.";
      toast({ title: "Erro", description: message, variant: "destructive" });
    } finally {
      setRemovingErp(false);
    }
  }

  if ((bootstrapState && !selectedProviderSlug && !deferredWithoutErp) || isSelectingProvider) {
    return (
      <div className="space-y-4">
        {(activeProviderSlug || selectedProviderSlug) && (
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => setIsSelectingProvider(false)}>
              Cancelar troca de ERP
            </Button>
          </div>
        )}
        <ErpProviderSelector
          onSelect={(slug) => {
            setSelectedProviderSlug(slug);
            setDeferredWithoutErp(false);
            setIsSelectingProvider(false);
          }}
          onSkip={() => {
            setSelectedProviderSlug(null);
            setDeferredWithoutErp(true);
            setIsSelectingProvider(false);
          }}
          showSkipOption={allowSkipErpSelection}
        />
      </div>
    );
  }

  if (!activeProviderSlug && deferredWithoutErp) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>ERP ainda não selecionado</CardTitle>
            <CardDescription>
              Você optou por continuar sem integrar um ERP neste momento. Quando quiser, volte ao catálogo para iniciar a configuração.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDeferredWithoutErp(false);
                setIsSelectingProvider(true);
              }}
            >
              Escolher ERP agora
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const slugToRender = selectedProviderSlug || activeProviderSlug;

  if (!slugToRender) {
    return (
      <ErpProviderSelector
        onSelect={(slug) => {
          setSelectedProviderSlug(slug);
          setDeferredWithoutErp(false);
          setIsSelectingProvider(false);
        }}
        onSkip={() => {
          setSelectedProviderSlug(null);
          setDeferredWithoutErp(true);
          setIsSelectingProvider(false);
        }}
        showSkipOption={allowSkipErpSelection}
      />
    );
  }

  const ProviderWrapper = ERP_PROVIDER_CONSOLES[slugToRender as keyof typeof ERP_PROVIDER_CONSOLES];

  if (!ProviderWrapper) {
    return (
      <div className="space-y-4">
        <div className="flex justify-end gap-2">
          {activeProviderSlug && selectedProviderSlug ? (
            <Button variant="outline" size="sm" onClick={() => setSelectedProviderSlug(null)}>
              Voltar ao ERP atual
            </Button>
          ) : null}
          {activeProviderSlug ? (
            <Button variant="outline" size="sm" className="rounded-sm text-destructive hover:text-destructive" onClick={() => void handleRemoveErp()} disabled={removingErp}>
              <Trash2 className="mr-2 h-4 w-4" />
              {removingErp ? "Removendo..." : "Não uso ERP"}
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={() => setIsSelectingProvider(true)}>
            Escolher outro ERP
          </Button>
        </div>
        <Alert variant="destructive">
          <ShieldAlert className="h-4 w-4" />
          <AlertDescription>
            A integração com o provedor <strong>{slugToRender}</strong> foi identificada, mas o console de administração ainda não suporta a configuração deste ERP visualmente nesta interface.
            A sincronização de retaguarda permanece inalterada e ativa. Para ajustes de configuração, contate o suporte.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        {bootstrapState && selectedProviderSlug && !activeProviderSlug ? (
          <>
            <Button variant="outline" size="sm" onClick={() => setSelectedProviderSlug(null)}>
              Voltar ao catálogo
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setSelectedProviderSlug(null);
                setDeferredWithoutErp(true);
              }}
            >
              Configurar depois
            </Button>
          </>
        ) : null}
        {activeProviderSlug ? (
          <Button variant="outline" size="sm" className="rounded-sm text-destructive hover:text-destructive" onClick={() => void handleRemoveErp()} disabled={removingErp}>
            <Trash2 className="mr-2 h-4 w-4" />
            {removingErp ? "Removendo..." : "Não uso ERP"}
          </Button>
        ) : null}
        <Button variant="outline" size="sm" onClick={() => setIsSelectingProvider(true)}>
          Trocar ERP
        </Button>
      </div>
      <ProviderWrapper />
    </div>
  );
}
