import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { IAGrowthTipoOferta } from "./use-ia-growth-plano-recomendado";
import type { IAGrowthIncentivoItem } from "./use-ia-growth-incentivos";

export interface IAGrowthAssistenteContextoResponse {
  visao_completa: boolean;
  resumo_perfil: string;
  oportunidade_identificada: string;
  plano_atual: string;
  plano_atual_label: string;
  plano_sugerido: string;
  plano_sugerido_label: string;
  motivo_principal: string;
  proximos_passos_sugeridos: string[];
  perguntas_sugeridas: string[];
  score_fit: number;
  persona?: string | null;
  churn_risk_level: "BAIXO" | "MEDIO" | "ALTO";
  safra_status?: string | null;
  safra_ano?: string | null;
  estagio_safra?: string | null;
  modulos_usados: string[];
  features_bloqueadas: string[];
  cta_recente: Record<string, number>;
  sinais: Record<string, unknown>;
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
  incentivo?: IAGrowthIncentivoItem | null;
}

export interface IAGrowthAssistenteMensagemRequest {
  mensagem_usuario: string;
  contexto_atual?: IAGrowthAssistenteContextoResponse | null;
}

export interface IAGrowthAssistenteMensagemResponse {
  resposta_ia: string;
  cta_sugerido: string;
  cta_url: string;
  plano_recomendado: string;
  acao_sugerida: string;
  fonte: "LLM" | "HEURISTICO";
  tipo_oferta: IAGrowthTipoOferta;
  mensagem_oferta: string;
  beneficio_destacado: string;
  incentivo?: IAGrowthIncentivoItem | null;
  log_id?: string | null;
  contexto?: IAGrowthAssistenteContextoResponse | null;
}

export function useIAGrowthAssistenteComercialContexto() {
  return useQuery<IAGrowthAssistenteContextoResponse>({
    queryKey: ["ia-growth-assistente-comercial", "contexto"],
    queryFn: () => apiFetch("/ia/growth/assistente-comercial/contexto"),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

export function useIAGrowthAssistenteComercialMensagem() {
  return useMutation<IAGrowthAssistenteMensagemResponse, Error, IAGrowthAssistenteMensagemRequest>({
    mutationFn: (payload) =>
      apiFetch("/ia/growth/assistente-comercial/mensagem", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}
