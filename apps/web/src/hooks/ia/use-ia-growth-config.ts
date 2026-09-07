import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface IAGrowthConfigItem {
  contexto: string;
  ativo: boolean;
  cooldown_horas: number;
  prioridade: number;
  updated_at: string | null;
}

export function useIAGrowthConfig() {
  return useQuery<IAGrowthConfigItem[]>({
    queryKey: ["ia-growth-config"],
    queryFn: () => apiFetch("/ia/growth/config"),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

export function useIAGrowthConfigUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contexto, dados }: { contexto: string; dados: Partial<IAGrowthConfigItem> }) =>
      apiFetch(`/ia/growth/config/${contexto}`, { method: "PATCH", body: JSON.stringify(dados) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ia-growth-config"] }),
  });
}

export function useIAGrowthConfigReverter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (contexto: string) =>
      apiFetch(`/ia/growth/config/${contexto}/reverter`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ia-growth-config"] }),
  });
}
