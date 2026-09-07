import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { IAGrowthTipoOferta } from "./use-ia-growth-plano-recomendado";

export interface IAGrowthOportunidadeItem {
  usuario_id: string;
  usuario_label: string;
  persona?: string | null;
  plano_atual: string;
  plano_atual_label: string;
  plano_recomendado: string;
  plano_recomendado_label: string;
  score_fit: number;
  score_oportunidade: number;
  nivel: "BAIXO" | "MEDIO" | "ALTO";
  categoria: "ALTO_POTENCIAL" | "TRAVADO" | "RISCO" | "NEUTRO";
  contexto: string;
  cta_label: string;
  cta_url: string;
  acao_sugerida: string;
  impacto_estimado: number;
  impacto_estimado_label: string;
  churn_risk_level: "BAIXO" | "MEDIO" | "ALTO";
  uso_premium_score: number;
  frequencia_uso_score: number;
  assistente_score: number;
  cta_score: number;
  cta_clicks: number;
  cta_views: number;
  assistente_interacoes: number;
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
}

export interface IAGrowthOportunidadesResponse {
  periodo_dias: number;
  total_oportunidades: number;
  alto_potencial: number;
  travados: number;
  risco: number;
  neutros: number;
  impacto_total_estimado: number;
  contextos_disponiveis: string[];
  oportunidades: IAGrowthOportunidadeItem[];
}

interface OportunidadesFilters {
  periodoDias?: number;
  limite?: number;
  persona?: string | "todos";
  plano?: string | "todos";
  contexto?: string | "todos";
  categoria?: string | "todos";
}

export function useIAGrowthOportunidades(filters: OportunidadesFilters = {}) {
  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.periodoDias) params.set("periodo_dias", String(filters.periodoDias));
    if (filters.limite) params.set("limite", String(filters.limite));
    if (filters.persona && filters.persona !== "todos") params.set("persona", filters.persona);
    if (filters.plano && filters.plano !== "todos") params.set("plano", filters.plano);
    if (filters.contexto && filters.contexto !== "todos") params.set("contexto", filters.contexto);
    if (filters.categoria && filters.categoria !== "todos") params.set("categoria", filters.categoria);
    const query = params.toString();
    return query ? `?${query}` : "";
  }, [filters.categoria, filters.contexto, filters.limite, filters.persona, filters.periodoDias, filters.plano]);

  return useQuery<IAGrowthOportunidadesResponse>({
    queryKey: ["ia-growth-oportunidades", filters],
    queryFn: () => apiFetch(`/ia/growth/oportunidades${queryParams}`),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}
