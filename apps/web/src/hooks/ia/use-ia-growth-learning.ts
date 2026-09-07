import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";

export interface IAGrowthLearningWeightItem {
  id: string;
  dimensao: "TIMING" | "PERSONA" | "ABORDAGEM" | "OFERTA" | "AUTOPILOT";
  chave: string;
  peso_atual: number;
  amostras: number;
  conversoes: number;
  updated_at: string;
}

export interface IAGrowthLearningWeightsResponse {
  periodo_dias: number;
  total: number;
  pesos: IAGrowthLearningWeightItem[];
  ultima_atualizacao?: string | null;
}

export interface IAGrowthLearningRecalcularResponse {
  periodo_dias: number;
  total_atualizados: number;
  total_criados: number;
  mensagem: string;
}

export function useIAGrowthLearningWeights(periodoDias = 30) {
  return useQuery<IAGrowthLearningWeightsResponse>({
    queryKey: ["ia-growth-learning-weights", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/learning/weights?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

export function useIAGrowthLearningRecalcular() {
  const queryClient = useQueryClient();
  return useMutation<IAGrowthLearningRecalcularResponse, Error, number>({
    mutationFn: (periodoDias: number) =>
      apiFetch(`/ia/growth/learning/recalcular?periodo_dias=${periodoDias}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-learning-weights"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-roi"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-performance"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-oportunidades"] });
    },
  });
}
