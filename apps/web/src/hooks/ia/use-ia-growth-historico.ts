import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthHistoricoItem {
  id: string;
  contexto: string;
  campo_alterado: string;
  valor_anterior: string | null;
  valor_novo: string;
  alterado_por_id: string | null;
  alterado_por_nome: string;
  criado_em: string;
}

export function useIAGrowthHistorico(contexto?: string, periodoDias = 30) {
  const params = new URLSearchParams({ periodo_dias: String(periodoDias) });
  if (contexto) params.set("contexto", contexto);

  return useQuery<IAGrowthHistoricoItem[]>({
    queryKey: ["ia-growth-historico", contexto, periodoDias],
    queryFn: () => apiFetch(`/ia/growth/config/historico?${params}`),
    staleTime: 1000 * 60 * 2,
    retry: false,
  });
}
