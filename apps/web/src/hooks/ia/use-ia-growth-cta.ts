import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { IAGrowthIncentivoItem } from "./use-ia-growth-incentivos";

export interface IAGrowthCTAResponse {
  deve_exibir: boolean;
  tipo: string;
  mensagem: string;
  cta_label: string;
  cta_url: string;
  contexto: string;
  cooldown_ativo: boolean;
  roi_valor: number;
  experimento_id?: string;
  variante_id?: string;
  titulo_alternativo?: string; // Growth-10
  tipo_abordagem?: string; // Growth-10
  moment_score?: number; // IA-Growth-14
  timing_decision?: "FULL" | "SOFT" | "HIDDEN"; // IA-Growth-14
  churn_risk_score?: number; // IA-Growth-15
  churn_risk_level?: "BAIXO" | "MEDIO" | "ALTO"; // IA-Growth-15
  incentivo?: IAGrowthIncentivoItem | null;
}

export function useIAGrowthCTA(contexto: "progresso" | "acao" | "resumo" = "progresso") {
  return useQuery<IAGrowthCTAResponse>({
    queryKey: ["ia-growth-cta", contexto],
    queryFn: () => apiFetch(`/ia/growth/recomendacao-upgrade?contexto=${contexto}`),
    staleTime: 1000 * 60 * 10, // 10 minutos — cooldown é gerenciado no backend
    retry: false,
  });
}

export function useIAGrowthTrack() {
  return useMutation({
    mutationFn: (payload: {
      evento: string;
      tipo_cta: string;
      contexto: string;
      churn_risk_score?: number;
      churn_risk_level?: "BAIXO" | "MEDIO" | "ALTO";
      metadados?: Record<string, unknown>;
    }) =>
      apiFetch("/ia/growth/track", { method: "POST", body: JSON.stringify(payload) }),
  });
}

export function useIAGrowthTrackClick() {
  return useMutation({
    mutationFn: (payload: {
      experimento_id: string;
      variante_id: string;
      contexto: string;
      churn_risk_score?: number;
      churn_risk_level?: "BAIXO" | "MEDIO" | "ALTO";
    }) =>
      apiFetch("/ia/growth/experimentos/track-click", { method: "POST", body: JSON.stringify(payload) }),
  });
}
