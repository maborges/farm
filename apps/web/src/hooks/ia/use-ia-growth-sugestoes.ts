import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthSugestao {
  id: string;
  contexto: string;
  tipo: "DESATIVAR" | "REDUZIR_COOLDOWN" | "AUMENTAR_PRIORIDADE" | "ESTABILIZAR";
  justificativa: string;
  impacto: "BAIXO" | "MÉDIO" | "ALTO";
  confianca: number;
  aplicavel: boolean;
  acao_payload: Record<string, unknown>;
}

export interface IAGrowthSugestoesResponse {
  periodo_dias: number;
  total: number;
  sugestoes: IAGrowthSugestao[];
}

const INVALIDATE_KEYS = [
  ["ia-growth-sugestoes"],
  ["ia-growth-config"],
  ["ia-growth-historico"],
  ["ia-growth-metricas"],
];

export function useIAGrowthSugestoes(periodoDias = 30) {
  return useQuery<IAGrowthSugestoesResponse>({
    queryKey: ["ia-growth-sugestoes", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/sugestoes?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

export function useIAGrowthSugestaoAplicar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sugestaoId: string) =>
      apiFetch(`/ia/growth/sugestoes/${sugestaoId}/aplicar`, { method: "POST" }),
    onSuccess: () => INVALIDATE_KEYS.forEach(k => qc.invalidateQueries({ queryKey: k })),
  });
}

export function useIAGrowthSugestaoIgnorar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sugestaoId: string) =>
      apiFetch(`/ia/growth/sugestoes/${sugestaoId}/ignorar`, { method: "POST" }),
    onSuccess: () => INVALIDATE_KEYS.forEach(k => qc.invalidateQueries({ queryKey: k })),
  });
}
