import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { IAGrowthTipoOferta } from "./use-ia-growth-plano-recomendado";

export interface IAGrowthOfertaPerformanceItem {
  tipo_oferta: IAGrowthTipoOferta;
  total_recomendacoes: number;
  total_clicks: number;
  total_conversoes: number;
  taxa_conversao: number;
  participacao: number;
  impacto_estimado: number;
  impacto_estimado_label: string;
}

export interface IAGrowthOfertasPerformanceResponse {
  periodo_dias: number;
  total_recomendacoes: number;
  total_conversoes: number;
  impacto_total_estimado: number;
  performance: IAGrowthOfertaPerformanceItem[];
}

export function useIAGrowthOfertasPerformance(periodoDias = 30) {
  return useQuery<IAGrowthOfertasPerformanceResponse>({
    queryKey: ["ia-growth-ofertas-performance", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/ofertas/performance?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}
