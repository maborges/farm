import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { IAGrowthIncentivoItem } from "./use-ia-growth-incentivos";

export type IAGrowthTipoOferta = "SEM_INCENTIVO" | "INCENTIVO_LEVE" | "INCENTIVO_FORTE" | "EDUCATIVO" | "CONSULTIVO";

// IA-Growth-16 — Recomendação consultiva de plano

export interface IAGrowthPlanoFitItem {
  plano: string;
  plano_label: string;
  score_fit: number;
  motivos: string[];
  funcionalidades_relevantes: string[];
}

export interface IAGrowthPlanoRecomendadoResponse {
  plano_atual: string;
  plano_atual_label: string;
  plano_recomendado: string;
  plano_recomendado_label: string;
  score_fit: number;
  motivos: string[];
  beneficios: string[];
  funcionalidades_mais_relevantes: string[];
  cta_label: string;
  cta_url: string;
  cta_secundaria_label?: string | null;
  cta_secundaria_url?: string | null;
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
  incentivo?: IAGrowthIncentivoItem | null;
  nivel_urgencia: "ALTA" | "MEDIA" | "BAIXA" | string;
  churn_risk_level: "BAIXO" | "MEDIO" | "ALTO" | string;
  persona?: string | null;
  fit_por_plano: IAGrowthPlanoFitItem[];
  log_id?: string | null;
}

export interface IAGrowthPlanoMetricasItem {
  plano: string;
  plano_label: string;
  total_recomendacoes: number;
  total_clicks: number;
  taxa_clique: number;
  total_conversoes: number;
  taxa_conversao: number;
}

export interface IAGrowthPlanoMetricasResponse {
  periodo_dias: number;
  total_recomendacoes: number;
  distribuicao: IAGrowthPlanoMetricasItem[];
}

export function useIAGrowthPlanoRecomendado() {
  return useQuery<IAGrowthPlanoRecomendadoResponse>({
    queryKey: ["ia-growth-plano-recomendado"],
    queryFn: () => apiFetch("/ia/growth/plano-recomendado"),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}

export function useIAGrowthPlanoRecomendadoMetricas(periodoDias = 30) {
  return useQuery<IAGrowthPlanoMetricasResponse>({
    queryKey: ["ia-growth-plano-recomendado-metricas", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/plano-recomendado/metricas?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}

export function useIAGrowthPlanoRecomendadoClique() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (logId: string) =>
      apiFetch(`/ia/growth/plano-recomendado/${logId}/clique`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado-metricas"] });
    },
  });
}

export function useIAGrowthPlanoRecomendadoConversao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (logId: string) =>
      apiFetch(`/ia/growth/plano-recomendado/${logId}/conversao`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado-metricas"] });
    },
  });
}
