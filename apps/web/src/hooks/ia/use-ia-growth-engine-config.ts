import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";

export interface IAGrowthEngineFeatureItem {
  chave: string;
  label: string;
  disponivel: boolean;
  bloqueado: boolean;
  motivo?: string | null;
}

export interface IAGrowthEngineConfigResponse {
  tenant_id: string;
  plano_atual: string;
  plano_atual_label: string;
  growth_engine_enabled: boolean;
  growth_autopilot_enabled: boolean;
  growth_llm_copy_enabled: boolean;
  growth_incentivos_enabled: boolean;
  growth_learning_enabled: boolean;
  growth_max_acoes_dia: number;
  growth_max_incentivos_mes: number;
  growth_modo: "CONSERVADOR" | "BALANCEADO" | "AGRESSIVO";
  atualizado_em: string | null;
  recursos_disponiveis: IAGrowthEngineFeatureItem[];
  recursos_bloqueados: IAGrowthEngineFeatureItem[];
  limites_plano: Record<string, unknown>;
  cta_upgrade_label: string;
  cta_upgrade_url: string;
}

export interface IAGrowthEngineConfigUpdatePayload {
  ativo?: boolean;
  autopilot_enabled?: boolean;
  growth_engine_enabled?: boolean;
  growth_llm_copy_enabled?: boolean;
  growth_incentivos_enabled?: boolean;
  growth_learning_enabled?: boolean;
  growth_max_acoes_dia?: number;
  growth_max_incentivos_mes?: number;
  growth_modo?: "CONSERVADOR" | "BALANCEADO" | "AGRESSIVO";
  nivel_autonomia?: "BAIXO" | "MEDIO" | "ALTO";
  tipos_permitidos?: string[];
  limite_impacto_percentual?: number;
}

export function useIAGrowthEngineConfig() {
  return useQuery<IAGrowthEngineConfigResponse>({
    queryKey: ["ia-growth-engine-config"],
    queryFn: () => apiFetch("/ia/growth/engine/config"),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

export function useIAGrowthEngineConfigUpdate() {
  const qc = useQueryClient();
  return useMutation<IAGrowthEngineConfigResponse, Error, IAGrowthEngineConfigUpdatePayload>({
    mutationFn: (payload) =>
      apiFetch("/ia/growth/engine/config", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ia-growth-engine-config"] });
      qc.invalidateQueries({ queryKey: ["ia-growth-autopilot-status"] });
      qc.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado"] });
      qc.invalidateQueries({ queryKey: ["ia-growth-learning-weights"] });
    },
  });
}
