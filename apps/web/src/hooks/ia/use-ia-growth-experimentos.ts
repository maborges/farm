import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthExperimentoVariante {
  id: string;
  nome: string;
  config_override: Record<string, unknown>;
  peso: number;
  ativo: boolean;
}

export interface IAGrowthExperimento {
  id: string;
  contexto: string;
  nome: string;
  status: "ATIVO" | "FINALIZADO";
  created_at: string;
  started_at?: string;
  ended_at?: string;
  variantes: IAGrowthExperimentoVariante[];
}

export interface IAGrowthExperimentoResultado {
  experimento_id: string;
  nome: string;
  status: string;
  total_exibicoes: number;
  total_cliques: number;
  variantes: {
    variante_id: string;
    nome: string;
    exibicoes: number;
    cliques: number;
    conversao: number;
  }[];
  vencedora?: string;
  significancia_atingida: boolean;
}

export function useIAGrowthExperimentos(contexto?: string, status?: string) {
  const queryParams = new URLSearchParams();
  if (contexto) queryParams.append("contexto", contexto);
  if (status) queryParams.append("status", status);

  return useQuery<IAGrowthExperimento[]>({
    queryKey: ["ia-growth-experimentos", contexto, status],
    queryFn: () => apiFetch(`/ia/growth/experimentos?${queryParams.toString()}`),
  });
}

export function useIAGrowthExperimentoResultado(experimentoId: string) {
  return useQuery<IAGrowthExperimentoResultado>({
    queryKey: ["ia-growth-experimento-resultado", experimentoId],
    queryFn: () => apiFetch(`/ia/growth/experimentos/${experimentoId}/resultado`),
    enabled: !!experimentoId,
  });
}

export function useIAGrowthCriarExperimento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { contexto: string; nome: string; variantes: any[] }) =>
      apiFetch("/ia/growth/experimentos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-experimentos"] });
    },
  });
}

export function useIAGrowthFinalizarExperimento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (experimentoId: string) =>
      apiFetch(`/ia/growth/experimentos/${experimentoId}/finalizar`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-experimentos"] });
    },
  });
}
