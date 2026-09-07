"use client";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import type { OpenWeatherTenantConfigResponse } from "@/lib/integracoes/openweather-types";



export type OpenWeatherConfigUpsert = {
  api_key?: string;
  api_base_url: string;
  environment: string;
  location_query: string;
  units: "metric" | "imperial" | "standard";
  language: string;
  timeout_seconds: number;
  cache_ttl_seconds: number;
  daily_quota: number;
  sync_frequency_minutes: number;
};

export type OpenWeatherConfigResponse = {
  id: number;
  tenant_id: string;
  provider_id: number;
  provider_slug: string;
  status: string;
  ativo: boolean;
  lifecycle_state: string;
  connection_payload: Record<string, unknown>;
  configuracoes: Record<string, unknown>;
  api_key_configured: boolean;
  api_key_mask?: string | null;
  credential_ref_id?: number | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
  scope_type?: string;
  scope_id?: string | null;
};

export type OpenWeatherWeatherSnapshot = {
  location?: string | null;
  temperature?: number | null;
  humidity?: number | null;
  rainfall_mm?: number | null;
  wind_speed?: number | null;
  condition?: string | null;
  units?: string | null;
  observed_at?: string | null;
  source: string;
  job_id?: string | null;
};

export type OpenWeatherTestConnectionResponse = {
  sucesso: boolean;
  mensagem: string;
  weather?: OpenWeatherWeatherSnapshot | null;
};

export type OpenWeatherStatusResponse = {
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
  policies_resumidas: OpenWeatherPolicySummary[];
  latest_weather?: OpenWeatherWeatherSnapshot | null;
};

export type OpenWeatherPolicySummary = {
  feature_code?: string | null;
  mode?: string | null;
  ativa?: boolean;
  retry_limite?: number | null;
  trigger_expression?: string | null;
};

export type OpenWeatherHealthResponse = {
  configurado: boolean;
  origem: string;
  status: string;
  summary?: string | null;
  checked_at?: string | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  consecutive_failures: number;
  details?: Record<string, unknown> | string | null;
};

export type OpenWeatherJobResponse = {
  id: string;
  tenant_id: string;
  config_id?: number | null;
  feature_code?: string | null;
  job_status: string;
  trigger_type: string;
  started_at?: string | null;
  finished_at?: string | null;
  processados: number;
  sucessos: number;
  erros: number;
  correlation_id?: string | null;
  result_payload?: Record<string, unknown> | null;
  error_payload?: Record<string, unknown> | string | null;
};

export type OpenWeatherTimelineItem = {
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
  payload?: Record<string, unknown> | string | null;
};

export type OpenWeatherDiagnosis = {
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
};

export type OpenWeatherDashboard = {
  config: OpenWeatherConfigResponse | null;
  status: OpenWeatherStatusResponse | null;
  health: OpenWeatherHealthResponse | null;
  jobs: OpenWeatherJobResponse[];
  timeline: OpenWeatherTimelineItem[];
  diagnosis: OpenWeatherDiagnosis | null;
};

export type OpenWeatherOperationalDashboard = Pick<
  OpenWeatherDashboard,
  "jobs" | "timeline" | "diagnosis"
>;

export async function fetchOpenWeatherDashboard(unidadeProdutivaId?: string | null): Promise<OpenWeatherDashboard> {
  const configPath = unidadeProdutivaId
    ? `/integracoes/openweather/config/${unidadeProdutivaId}`
    : "/integracoes/openweather/config";
  const path = (resource: string) => unidadeProdutivaId
    ? `/integracoes/openweather/${resource}/${unidadeProdutivaId}`
    : `/integracoes/openweather/${resource}`;
  const [config, status, health] = await Promise.all([
    apiFetch<OpenWeatherConfigResponse | null>(configPath, { suppressErrorLog: true }).catch(() => null),
    apiFetch<OpenWeatherStatusResponse | null>(`${path("status")}`, { suppressErrorLog: true }).catch(() => null),
    apiFetch<OpenWeatherHealthResponse | null>(`${path("health")}`, { suppressErrorLog: true }).catch(() => null),
  ]);

  return { config, status, health, jobs: [], timeline: [], diagnosis: null };
}

export async function fetchOpenWeatherOperationalDashboard(
  unidadeProdutivaId?: string | null,
): Promise<OpenWeatherOperationalDashboard> {
  const path = (resource: string) => unidadeProdutivaId
    ? `/integracoes/openweather/${resource}/${unidadeProdutivaId}`
    : `/integracoes/openweather/${resource}`;
  const [jobs, timeline, diagnosis] = await Promise.all([
    apiFetch<OpenWeatherJobResponse[]>(`${path("jobs")}?limit=10`, { suppressErrorLog: true }).catch(() => []),
    apiFetch<OpenWeatherTimelineItem[]>(`${path("timeline")}?limit=12`, { suppressErrorLog: true }).catch(() => []),
    apiFetch<OpenWeatherDiagnosis | null>(`${path("diagnostico")}`, { suppressErrorLog: true }).catch(() => null),
  ]);
  return { jobs, timeline, diagnosis };
}

export async function saveOpenWeatherConfig(payload: OpenWeatherConfigUpsert): Promise<OpenWeatherConfigResponse> {
  const normalizedPayload: OpenWeatherConfigUpsert = {
    ...payload,
    api_key: payload.api_key?.trim() ? payload.api_key.trim() : undefined,
  };
  return apiFetch("/integracoes/openweather/config", {
    method: "POST",
    body: normalizedPayload,
  });
}

export async function saveOpenWeatherConfigForUnit(
  unidadeProdutivaId: string,
  payload: OpenWeatherConfigUpsert,
): Promise<OpenWeatherConfigResponse> {
  const normalizedPayload = {
    ...payload,
    api_key: payload.api_key?.trim() ? payload.api_key.trim() : undefined,
  };
  return apiFetch(`/integracoes/openweather/config/${unidadeProdutivaId}`, {
    method: "POST",
    body: normalizedPayload,
  });
}

export async function testOpenWeatherConnection(): Promise<OpenWeatherTestConnectionResponse> {
  const tenantId = useAppStore.getState().tenant?.id;
  const unitId = useAppStore.getState().activeFazendaId;
  const url = unitId
    ? `/integracoes/openweather/testar-conexao/unidade/${unitId}`
    : `/integracoes/openweather/testar-conexao`;
  return apiFetch(url, { method: "POST" });
}





export async function testOpenWeatherConnectionForUnit(
  unidadeProdutivaId: string,
): Promise<OpenWeatherTestConnectionResponse> {
  return apiFetch(`/integracoes/openweather/testar-conexao/unidade/${unidadeProdutivaId}`, {
    method: "POST",
  });
}

export async function syncOpenWeatherCurrentWeather(): Promise<OpenWeatherWeatherSnapshot> {
  return apiFetch("/integracoes/openweather/sync/current-weather", {
    method: "POST",
  });
}

export async function syncOpenWeatherCurrentWeatherForUnit(
  unidadeProdutivaId: string,
): Promise<OpenWeatherWeatherSnapshot> {
  return apiFetch(`/integracoes/openweather/sync/current-weather/${unidadeProdutivaId}`, {
    method: "POST",
  });
}
