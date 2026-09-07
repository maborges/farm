import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthSugestaoDesempenho {
  sugestao_id: string;
  contexto: string;
  tipo: string;
  impacto: string;
  applied_at: string | null;
  taxa_antes: number;
  taxa_depois: number;
  variacao: number;
  ganho: boolean;
}

export interface IAGrowthSugestoesDesempenhoResponse {
  periodo_dias: number;
  total_geradas: number;
  total_aplicadas: number;
  total_ignoradas: number;
  total_pendentes: number;
  taxa_aplicacao: number;
  conversao_media_antes: number;
  conversao_media_depois: number;
  variacao_media: number;
  com_ganho: IAGrowthSugestaoDesempenho[];
  sem_ganho: IAGrowthSugestaoDesempenho[];
}

export function useIAGrowthSugestoesDesempenho(periodoDias = 30) {
  return useQuery<IAGrowthSugestoesDesempenhoResponse>({
    queryKey: ["ia-growth-desempenho", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/sugestoes/desempenho?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}
