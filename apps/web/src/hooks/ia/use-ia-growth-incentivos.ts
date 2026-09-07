import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";

export type IAGrowthTipoIncentivo =
  | "TRIAL_PROFISSIONAL"
  | "TRIAL_ENTERPRISE"
  | "DEMO_ASSISTIDA"
  | "CONSULTORIA_RAPIDA"
  | "EXTENSAO_AVALIACAO";

export type IAGrowthOrigemIncentivo = "MANUAL" | "AUTOPILOT" | "ASSISTENTE";
export type IAGrowthStatusIncentivo =
  | "OFERECIDO"
  | "ACEITO"
  | "RECUSADO"
  | "EXPIRADO"
  | "CANCELADO"
  | "PENDENTE_APROVACAO"
  | "APROVADO"
  | "REPROVADO";

export interface IAGrowthIncentivoItem {
  id: string;
  usuario_id?: string | null;
  tipo_incentivo: IAGrowthTipoIncentivo;
  tipo_incentivo_label: string;
  plano_alvo: string;
  plano_alvo_label: string;
  origem: IAGrowthOrigemIncentivo;
  origem_label: string;
  status: IAGrowthStatusIncentivo;
  status_label: string;
  validade_inicio: string;
  validade_fim: string;
  motivo: string;
  aprovado_por?: string | null;
  aprovado_em?: string | null;
  motivo_reprovacao?: string | null;
  created_at: string;
  accepted_at?: string | null;
  ativo: boolean;
  dias_validade_restantes: number;
}

export interface IAGrowthIncentivosResponse {
  periodo_dias: number;
  oferecidos: number;
  aceitos: number;
  recusados: number;
  expirados: number;
  cancelados: number;
  taxa_aceite: number;
  conversao_pos_incentivo: number;
  incentivos: IAGrowthIncentivoItem[];
}

export interface IAGrowthIncentivoActionResponse {
  status: IAGrowthStatusIncentivo;
  incentivo: IAGrowthIncentivoItem;
}

export interface IAGrowthIncentivosAprovacaoResponse {
  periodo_dias: number;
  pendentes: number;
  aprovados: number;
  reprovados: number;
  incentivos: IAGrowthIncentivoItem[];
}

interface IncentivosFilters {
  periodoDias?: number;
  status?: string | "todos";
  limite?: number;
}

export function useIAGrowthIncentivos(filters: IncentivosFilters = {}) {
  const queryParams = new URLSearchParams();
  if (filters.periodoDias) queryParams.set("periodo_dias", String(filters.periodoDias));
  if (filters.status && filters.status !== "todos") queryParams.set("status", filters.status);
  if (filters.limite) queryParams.set("limite", String(filters.limite));
  const queryString = queryParams.toString();

  return useQuery<IAGrowthIncentivosResponse>({
    queryKey: ["ia-growth-incentivos", filters],
    queryFn: () => apiFetch(`/ia/growth/incentivos${queryString ? `?${queryString}` : ""}`),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });
}

function useIncentivoMutation(acao: "aceitar" | "recusar") {
  const queryClient = useQueryClient();
  return useMutation<IAGrowthIncentivoActionResponse, Error, string>({
    mutationFn: (id: string) =>
      apiFetch(`/ia/growth/incentivos/${id}/${acao}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos-pendentes"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-assistente-comercial", "contexto"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-autopilot-status"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-oportunidades"] });
    },
  });
}

export function useIAGrowthIncentivoAceitar() {
  return useIncentivoMutation("aceitar");
}

export function useIAGrowthIncentivoRecusar() {
  return useIncentivoMutation("recusar");
}

export function useIAGrowthIncentivosPendentes(periodoDias = 90, limite = 50) {
  return useQuery<IAGrowthIncentivosAprovacaoResponse>({
    queryKey: ["ia-growth-incentivos-pendentes", periodoDias, limite],
    queryFn: () =>
      apiFetch(`/ia/growth/incentivos/pendentes?periodo_dias=${periodoDias}&limite=${limite}`),
    staleTime: 1000 * 60 * 2,
    retry: false,
  });
}

export function useIAGrowthIncentivoAprovar() {
  const queryClient = useQueryClient();
  return useMutation<IAGrowthIncentivoActionResponse, Error, string>({
    mutationFn: (id: string) => apiFetch(`/ia/growth/incentivos/${id}/aprovar`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos-pendentes"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-autopilot-status"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-assistente-comercial", "contexto"] });
    },
  });
}

export function useIAGrowthIncentivoReprovar() {
  const queryClient = useQueryClient();
  return useMutation<IAGrowthIncentivoActionResponse, Error, { id: string; motivo_reprovacao?: string }>({
    mutationFn: ({ id, motivo_reprovacao }) =>
      apiFetch(`/ia/growth/incentivos/${id}/reprovar`, {
        method: "POST",
        body: JSON.stringify({ motivo_reprovacao: motivo_reprovacao ?? "Reprovado manualmente." }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos-pendentes"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-incentivos"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-autopilot-status"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-plano-recomendado"] });
      queryClient.invalidateQueries({ queryKey: ["ia-growth-assistente-comercial", "contexto"] });
    },
  });
}
