import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthChurnNivelItem {
  nivel: "BAIXO" | "MEDIO" | "ALTO";
  usuarios: number;
  percentual: number;
}

export interface IAGrowthChurnConversaoItem {
  nivel: "BAIXO" | "MEDIO" | "ALTO";
  exibicoes: number;
  cliques: number;
  conversao: number;
}

export interface IAGrowthChurnDashboardResponse {
  periodo_dias: number;
  total_usuarios_avaliados: number;
  distribuicao_niveis: IAGrowthChurnNivelItem[];
  conversao_por_nivel: IAGrowthChurnConversaoItem[];
  recuperacao_alto_risco: {
    usuarios_alto_risco: number;
    usuarios_recuperados: number;
    taxa_recuperacao: number;
  };
  impacto_cta_preventivo: {
    exibicoes: number;
    cliques: number;
    dismisses: number;
    conversao: number;
  };
}

export function useIAGrowthChurnPerformance(periodoDias = 30) {
  return useQuery<IAGrowthChurnDashboardResponse>({
    queryKey: ["ia-growth-churn-performance", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/churn/performance?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}
