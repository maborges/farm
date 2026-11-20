import { apiFetch } from "@/lib/api";
import type {
  JsonValue,
  MetadadosModeloFitossanitario,
} from "@/lib/agricola/clima-api";

export interface RegrasZoosanitarias {
  nivel_critico?: number;
  nivel_alto?: number;
  nivel_medio?: number;
  indice?: string;
  fonte_parametros?: string;
  fonte_url?: string;
  observacao?: string;
  metadados?: MetadadosModeloFitossanitario;
  [key: string]: JsonValue | MetadadosModeloFitossanitario | undefined;
}

export interface InteligenciaPecuariaResponse {
    especie: string;
    tipo_risco: string;
    risco_atual: 'BAIXO' | 'MEDIO' | 'ALTO' | 'CRITICO';
    data_analise: string;
    valor_referencia: number | null;
    detalhes: string[];
    historico: HistoricoIth[];
    alertas: string[];
    idade_dados_dias: number | null;
    dados_atualizados: boolean;
    previsao_ith: PrevisaoIth[];
    estresse_previsto: EstressePrevisto;
    chuva_prevista: ChuvaPrevista;
    janela_manejo: JanelaManejo;
}

export interface PrevisaoIth {
    data: string;
    horizonte_horas: number;
    ith_max: number | null;
    risco: 'BAIXO' | 'MEDIO' | 'ALTO' | 'CRITICO' | 'INDETERMINADO';
    temperatura_max_c: number | null;
    umidade_disponivel: boolean;
}

export interface EstressePrevisto {
    duracao_horas: number | null;
    intensidade: PrevisaoIth['risco'];
    horizonte_horas: number;
    dados_suficientes: boolean;
}

export interface ChuvaPrevista {
    volume_mm_72h: number | null;
    probabilidade_max_pct: number | null;
    dados_suficientes: boolean;
}

export interface JanelaManejo {
    horario: string | null;
    status: 'RECOMENDADA' | 'NAO_IDENTIFICADA';
    ith: number | null;
}

export interface HistoricoIth {
    data: string;
    ith: number | null;
    temperatura_c: number | null;
    umidade_pct: number | null;
}

export async function fetchInteligenciaPecuaria(
    unidadeProdutivaId: string,
    especie: string
): Promise<InteligenciaPecuariaResponse | null> {
    const params = new URLSearchParams({
        unidade_produtiva_id: unidadeProdutivaId,
        especie: especie,
    });
    return apiFetch(`/pecuaria/climatico/inteligencia/analise?${params.toString()}`);
}

// ---- Modelos Zoosanitários ----

export interface ModeloZoosanitario {
  id: string;
  tenant_id?: string | null;
  especie: string;
  tipo_risco: string;
  regras_risco: RegrasZoosanitarias;
  is_global: boolean;
  created_at?: string;
}

export type ModeloZoosanitarioCreate = Omit<ModeloZoosanitario, "id" | "created_at" | "is_global" | "tenant_id">;
export type ModeloZoosanitarioUpdate = Partial<ModeloZoosanitarioCreate>;

export async function fetchModelosZoosanitarios(): Promise<ModeloZoosanitario[]> {
  return apiFetch<ModeloZoosanitario[]>("/pecuaria/climatico/inteligencia/modelos");
}

export async function createModeloZoosanitario(data: ModeloZoosanitarioCreate): Promise<ModeloZoosanitario> {
  return apiFetch<ModeloZoosanitario>("/pecuaria/climatico/inteligencia/modelos", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateModeloZoosanitario(id: string, data: ModeloZoosanitarioUpdate): Promise<ModeloZoosanitario> {
  return apiFetch<ModeloZoosanitario>(`/pecuaria/climatico/inteligencia/modelos/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteModeloZoosanitario(id: string): Promise<void> {
  return apiFetch<void>(`/pecuaria/climatico/inteligencia/modelos/${id}`, {
    method: "DELETE",
  });
}

export async function copiarModeloZoosanitario(id: string): Promise<ModeloZoosanitario> {
  return apiFetch<ModeloZoosanitario>(`/pecuaria/climatico/inteligencia/modelos/${id}/copiar`, {
    method: "POST",
  });
}
