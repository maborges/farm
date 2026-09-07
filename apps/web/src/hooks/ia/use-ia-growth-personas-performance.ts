import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthPersonaPerformance {
  persona: string;
  usuarios: number;
  exibicoes: number;
  cliques: number;
  conversao: number;
  melhor_abordagem: string | null;
  melhor_origem: string | null;
  melhor_contexto: string | null;
}

export interface IAGrowthTimingPerformance {
  timing_decision: string;
  exibicoes: number;
  cliques: number;
  skipped: number;
  conversao: number;
}

export interface IAGrowthPersonasPerformanceResponse {
  periodo_dias: number;
  total_usuarios_classificados: number;
  distribuicao_persona: Record<string, number>;
  performance_por_persona: IAGrowthPersonaPerformance[];
  timing_performance: IAGrowthTimingPerformance[]; // IA-Growth-14
  melhor_persona_conversao: string | null;
  melhor_abordagem_geral: string | null;
  melhor_origem_geral: string | null;
}

export function useIAGrowthPersonasPerformance(periodoDias = 30) {
  return useQuery<IAGrowthPersonasPerformanceResponse>({
    queryKey: ["ia-growth-personas-performance", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/personas/performance?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}
