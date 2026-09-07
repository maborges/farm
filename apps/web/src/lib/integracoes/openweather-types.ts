// src/lib/integracoes/openweather-types.ts

/**
 * Tipo de resposta da configuração do OpenWeather ao nível de tenant.
 * Sem o campo `unidadeProdutivaId`, pois a configuração é compartilhada.
 */
export type OpenWeatherTenantConfigResponse = {
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
