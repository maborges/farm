import { apiFetch } from "@/lib/api";

export type ModoGestaoLote = "POR_LOTE" | "INDIVIDUAL";

export interface LoteBovino {
  id: string;
  tenant_id: string;
  unidade_produtiva_id: string;
  piquete_id?: string | null;
  identificacao: string;
  modo_gestao: ModoGestaoLote | string;
  categoria?: string | null;
  raca?: string | null;
  quantidade_cabecas: number;
  peso_medio_kg: number;
  peso_inicial_medio_kg?: number | null;
  rendimento_carcaca_pct: number;
  valor_aquisicao_total?: number | null;
  cotacao_arroba_override?: number | null;
  data_formacao: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoteBovinoCreate {
  unidade_produtiva_id: string;
  piquete_id?: string | null;
  identificacao: string;
  modo_gestao: ModoGestaoLote;
  categoria: string;
  raca: string;
  quantidade_cabecas: number;
  peso_medio_kg: number;
  peso_inicial_medio_kg?: number | null;
  rendimento_carcaca_pct?: number;
  valor_aquisicao_total?: number | null;
  cotacao_arroba_override?: number | null;
  data_formacao?: string;
}

export interface LoteBovinoUpdate {
  piquete_id?: string | null;
  identificacao?: string;
  modo_gestao?: ModoGestaoLote;
  categoria?: string;
  raca?: string;
  quantidade_cabecas?: number;
  peso_medio_kg?: number;
  peso_inicial_medio_kg?: number | null;
  rendimento_carcaca_pct?: number;
  valor_aquisicao_total?: number | null;
  cotacao_arroba_override?: number | null;
  ativo?: boolean;
}

export interface LoteIndicadores {
  lote_id: string;
  nome_lote: string;
  modo_gestao: string;
  rendimento_carcaca_pct: number;
  quantidade_animais: number;
  peso_total_kg: number;
  peso_medio_kg: number;
  arrobas_totais: number;
  arrobas_produzidas: number;
  gmd_medio_kg_dia: number | null;
  ultima_pesagem: string | null;
  custo_sanitario_total: number;
  custo_sanitario_por_cabeca: number;
  custo_sanitario_por_kg: number;
  custo_sanitario_por_arroba: number;
  custo_aquisicao_total: number;
  area_piquete_ha: number;
  lotacao_ua_ha: number;
  arrobas_por_hectare: number;
  custo_nutricao_total: number;
  custo_outros_total: number;
  custo_total_operacional: number;
  custo_total_por_arroba: number;
  custo_por_arroba_produzida: number;
  custo_break_even_por_arroba: number;
  cotacao_arroba_referencia: number | null;
  fonte_cotacao: string | null;
  valor_mercado_estimado: number | null;
  margem_bruta_estimada: number | null;
  margem_estimada_por_cabeca: number | null;
}

export interface PecuariaDashboardResumoExecutivo {
  animais_ativos: number;
  lotes_ativos: number;
  piquetes_ativos: number;
  peso_total_kg: number;
  peso_medio_kg: number;
  ua_total: number;
  manejos_pendentes: number;
  vacinacoes_pendentes: number;
  custo_sanitario_acumulado: number;
  custo_aquisicao_acumulado: number;
  custo_nutricao_acumulado: number;
  custo_outros_acumulado: number;
  custo_operacional_acumulado: number;
  area_pastagem_ha: number;
  lotacao_ua_ha: number;
  arrobas_totais: number;
  arrobas_por_hectare: number;
  custo_total_por_arroba: number;
  custo_break_even_por_arroba: number;
  cotacao_arroba_referencia: number | null;
  fonte_cotacao: string | null;
  valor_mercado_estimado: number | null;
  margem_bruta_estimada: number | null;
}

export interface PiqueteOption {
  id: string;
  nome: string;
  tipo: string;
  area_hectares: number | null;
  area_hectares_manual?: number | null;
  ativo: boolean;
  dados_extras?: {
    capacidade_suporte_ua?: number | null;
  } | null;
}

export async function fetchLotes(unidadeProdutivaId?: string | null): Promise<LoteBovino[]> {
  const qs = unidadeProdutivaId
    ? `?unidade_produtiva_id=${encodeURIComponent(unidadeProdutivaId)}`
    : "";
  return apiFetch<LoteBovino[]>(`/pecuaria/lotes${qs}`);
}

export async function createLote(payload: LoteBovinoCreate): Promise<LoteBovino> {
  return apiFetch<LoteBovino>("/pecuaria/lotes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateLote(loteId: string, payload: LoteBovinoUpdate): Promise<LoteBovino> {
  return apiFetch<LoteBovino>(`/pecuaria/lotes/${loteId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchLoteIndicadores(loteId: string): Promise<LoteIndicadores> {
  return apiFetch<LoteIndicadores>(`/pecuaria/lotes/${loteId}/indicadores`);
}

export async function fetchPecuariaResumoExecutivo(
  unidadeProdutivaId?: string | null
): Promise<PecuariaDashboardResumoExecutivo> {
  const qs = unidadeProdutivaId
    ? `?unidade_produtiva_id=${encodeURIComponent(unidadeProdutivaId)}`
    : "";
  return apiFetch<PecuariaDashboardResumoExecutivo>(`/pecuaria/dashboard/resumo-executivo${qs}`);
}

export async function fetchPiquetesAtivos(unidadeProdutivaId: string): Promise<PiqueteOption[]> {
  const lista = await apiFetch<PiqueteOption[]>(
    `/cadastros/areas-rurais?tipo=PIQUETE&unidade_produtiva_id=${encodeURIComponent(unidadeProdutivaId)}`
  );
  return lista.filter((p) => p.ativo);
}
