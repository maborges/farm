import { apiFetch } from "@/lib/api";

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export interface CondicaoFitossanitario {
  variavel?: string;
  operador?: ">=" | "<=" | ">" | "<" | "between";
  peso?: number;
  valor?: number;
  min?: number;
  max?: number;
}

export interface RegrasFitossanitarias {
  condicoes?: CondicaoFitossanitario[];
  nivel_critico_pct?: number;
  nivel_alto_pct?: number;
  nivel_medio_pct?: number;
}

export interface ClimaResponse {
  id: string;
  unidade_produtiva_id: string;
  data_registro: string;
  precipitacao_mm: number | null;
  temp_max_c: number | null;
  temp_min_c: number | null;
  temp_media_c: number | null;
  umidade_rel_pct: number | null;
  evapotranspiracao_mm: number | null;
  gdu_calculado: number | null;
  vento_kmh: number | null;
  fonte: string;
  created_at: string;
}

export async function fetchHistoricoClima(
  unidadeProdutivaId: string,
  dias: number = 30
): Promise<ClimaResponse[]> {
  return apiFetch<ClimaResponse[]>(`/climatico/historico/${unidadeProdutivaId}?dias=${dias}`);
}

export interface SerieTemporalClima {
  data: string;
  temp_min: number | null;
  temp_max: number | null;
  temp_media: number | null;
  precipitacao: number | null;
}

export interface RiscoClimatico {
  tipo: string;
  nivel: string;
  mensagem: string;
  data_alerta: string | null;
}

export interface JanelaPulverizacao {
  hora: string;
  status: "verde" | "amarelo" | "vermelho";
  motivo: string | null;
  temp_c: number;
  umidade_pct: number;
  vento_kmh: number;
}

export interface BalancoHidrico {
  data: string;
  etc_mm: number | null;
  chuva_efetiva_mm: number;
  saldo_mm: number | null;
  status: "saturado" | "conforto" | "alerta" | "deficit" | "sem_dados";
}

export interface Cultura {
  id: string;
  nome: string;
  tenant_id?: string;
}

export const fetchCulturas = async (isBackoffice = false): Promise<Cultura[]> => {
  try {
    const endpoint = isBackoffice ? "/backoffice/tabelas/culturas" : "/cadastros/culturas";
    return await apiFetch<Cultura[]>(endpoint);
  } catch (error) {
    console.error("Failed to fetch culturas", error);
    return [];
  }
};

export interface RiscoDoenca {
  doenca: string;
  cultura: string;
  nivel_favorabilidade: "baixa" | "moderada" | "alta" | "muito_alta";
  favorabilidade_pct: number;
  /** @deprecated Alias temporário de compatibilidade; não é probabilidade. */
  nivel: "baixo" | "medio" | "alto" | "critico";
  /** @deprecated Alias temporário de compatibilidade; não é probabilidade. */
  probabilidade_pct: number;
  auto_copied?: boolean;
}

export type RiscoFitossanitarioStatus =
  | "SEM_CULTURA_ATIVA"
  | "SEM_MODELO_APLICAVEL"
  | "DADOS_CLIMATICOS_INSUFICIENTES"
  | "DADOS_CLIMATICOS_INVALIDOS"
  | "CONFIGURACAO_INVALIDA"
  | "PARCIAL"
  | "CALCULADO";

export interface AgriculturaInteligencia {
  janela_pulverizacao: JanelaPulverizacao[];
  balanco_hidrico: BalancoHidrico[];
  risco_doencas: RiscoDoenca[];
}

export interface ClimaInteligenciaResponse {
  gdu_acumulado: number;
  gdu_progresso_pct: number | null;
  riscos: RiscoClimatico[];
  historico: SerieTemporalClima[];
  agricultura?: AgriculturaInteligencia; // Opcional até o backend implementar
  risco_fitossanitario_status?: RiscoFitossanitarioStatus;
}

export async function fetchInteligenciaClimatica(
  unidadeProdutivaId: string,
  dias_historico: number = 30
): Promise<ClimaInteligenciaResponse> {
  return apiFetch<ClimaInteligenciaResponse>(
    `/climatico/inteligencia/${unidadeProdutivaId}?dias_historico=${dias_historico}`
  );
}

// ---- Modelos Fitossanitarios ----

export interface ModeloFitossanitario {
  id: string;
  cultura: string;
  doenca: string;
  regras_risco: RegrasFitossanitarias;
  is_global: boolean;
  created_at: string;
}

export type ModeloFitossanitarioCreate = Omit<ModeloFitossanitario, "id" | "created_at" | "is_global">;
export type ModeloFitossanitarioUpdate = Partial<ModeloFitossanitarioCreate>;

export async function fetchModelosFitossanitarios(): Promise<ModeloFitossanitario[]> {
  return apiFetch<ModeloFitossanitario[]>("/climatico/modelos-fitossanitarios");
}

export async function createModeloFitossanitario(data: ModeloFitossanitarioCreate): Promise<ModeloFitossanitario> {
  return apiFetch<ModeloFitossanitario>("/climatico/modelos-fitossanitarios", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateModeloFitossanitario(id: string, data: ModeloFitossanitarioUpdate): Promise<ModeloFitossanitario> {
  return apiFetch<ModeloFitossanitario>(`/climatico/modelos-fitossanitarios/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteModeloFitossanitario(id: string): Promise<void> {
  return apiFetch<void>(`/climatico/modelos-fitossanitarios/${id}`, {
    method: "DELETE",
  });
}

export async function copiarModeloFitossanitario(id: string): Promise<ModeloFitossanitario> {
  return apiFetch<ModeloFitossanitario>(`/climatico/modelos-fitossanitarios/${id}/copiar`, {
    method: "POST",
  });
}

// ---- Backoffice Modelos ----

export async function fetchBackofficeModelos(): Promise<ModeloFitossanitario[]> {
  return apiFetch<ModeloFitossanitario[]>("/climatico/backoffice/modelos-fitossanitarios");
}

export async function createBackofficeModelo(data: ModeloFitossanitarioCreate): Promise<ModeloFitossanitario> {
  return apiFetch<ModeloFitossanitario>("/climatico/backoffice/modelos-fitossanitarios", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateBackofficeModelo(id: string, data: ModeloFitossanitarioUpdate): Promise<ModeloFitossanitario> {
  return apiFetch<ModeloFitossanitario>(`/climatico/backoffice/modelos-fitossanitarios/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteBackofficeModelo(id: string): Promise<void> {
  return apiFetch<void>(`/climatico/backoffice/modelos-fitossanitarios/${id}`, {
    method: "DELETE",
  });
}
