import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";

export interface IAGrowthROIRankingItem {
  label: string;
  total: number;
  clicks: number;
  conversoes: number;
  taxa_conversao: number;
  impacto_estimado: number;
}

export interface IAGrowthROIResponse {
  periodo_dias: number;
  ctas_exibidos: number;
  cliques: number;
  conversoes: number;
  ctr: number;
  taxa_conversao: number;
  recomendacoes_plano: number;
  upgrades_influenciados: number;
  incentivos_oferecidos: number;
  incentivos_aceitos: number;
  taxa_aceite_incentivos: number;
  acoes_autopilot_executadas: number;
  usuarios_recuperados_churn: number;
  receita_potencial_influenciada: number;
  receita_estimada_convertida: number;
  funil: Array<{ etapa: string; valor: number }>;
  melhor_persona?: string | null;
  melhor_abordagem?: string | null;
  melhor_tipo_oferta?: string | null;
  melhor_incentivo?: string | null;
  ranking_personas: IAGrowthROIRankingItem[];
  ranking_abordagens: IAGrowthROIRankingItem[];
  ranking_tipos_oferta: IAGrowthROIRankingItem[];
  ranking_incentivos: IAGrowthROIRankingItem[];
  receita_estimativa: "estimada";
}

export function useIAGrowthROI(periodoDias = 30) {
  return useQuery<IAGrowthROIResponse>({
    queryKey: ["ia-growth-roi", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/roi?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}
