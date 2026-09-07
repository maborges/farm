import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { IAGrowthTipoOferta } from "./use-ia-growth-plano-recomendado";
import type { IAGrowthIncentivoItem } from "./use-ia-growth-incentivos";

export interface IAGrowthAutopilotAcaoItem {
  id: string;
  usuario_id?: string | null;
  tipo_acao: string;
  contexto: string;
  motivo: string;
  score_oportunidade: number;
  churn_risk: number;
  impacto_estimado: number;
  executada_em: string;
  resultado?: Record<string, unknown> | null;
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
}

export interface IAGrowthAutopilotStatusResponse {
  ativo: boolean;
  autopilot_enabled: boolean;
  nivel_autonomia: "BAIXO" | "MEDIO" | "ALTO";
  modo: "CONSERVADOR" | "BALANCEADO" | "AGRESSIVO";
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
  incentivo?: IAGrowthIncentivoItem | null;
  acoes_executadas: number;
  impacto_estimado: number;
  recentes: IAGrowthAutopilotAcaoItem[];
}

export function useIAGrowthAutopilotStatus(periodoDias = 30) {
  return useQuery<IAGrowthAutopilotStatusResponse>({
    queryKey: ["ia-growth-autopilot-status", periodoDias],
    queryFn: () => apiFetch(`/ia/growth/autopilot/status?periodo_dias=${periodoDias}`),
    staleTime: 1000 * 60 * 2,
    retry: false,
  });
}
