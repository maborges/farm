import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthMetricaContexto {
  contexto: string;
  total_exibicoes: number;
  total_cliques: number;
  taxa_conversao: number;
  classificacao: "ALTA" | "MÉDIA" | "BAIXA";
}

export interface IAGrowthMetricasResponse {
  periodo_dias: number;
  total_exibicoes: number;
  total_cliques: number;
  taxa_conversao_geral: number;
  por_contexto: IAGrowthMetricaContexto[];
  recomendacoes: string[];
}

export function useIAGrowthMetricas(periodoDias = 30) {
  return useQuery<IAGrowthMetricasResponse>({
    queryKey: ["ia-growth-metricas", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/metricas?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 15,
    retry: false,
  });
}
