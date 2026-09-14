import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";

interface CulturaCanonica {
  id: string;
  nome: string;
}

interface CulturaLegada {
  id: string;
  nome: string;
}

export interface CultivoResumo {
  id: string;
  cultura: string;
  safra_nome: string;
  data_plantio_real?: string;
  status: string;
}

export interface TalhaoContexto {
  id: string;
  nome: string;
  tipo: string;
  parent_id?: string;
  area_hectares?: number;
  tipo_solo_nome?: string;
  irrigado: boolean;
  tipo_irrigacao_nome?: string;
  cultivo_atual?: CultivoResumo;
}

interface SafraAtiva {
  id: string;
  ano_safra: string;
  cultura?: string | null;
  nome?: string | null;
  status: string;
  ativa?: boolean;
}

export interface RecomendacaoSoloItem {
  necessaria?: boolean;
  quantidade?: number;
  dose_t_ha?: number;
  rec_p2o5_kg_ha?: number;
  rec_k2o_kg_ha?: number;
  rec_n_kg_ha?: number;
  observacao?: string;
  custo_estimado?: number;
}

export interface RecomendacoesSolo {
  area_ha?: number;
  investimento_estimado_total?: number;
  calagem?: RecomendacaoSoloItem;
  fosforo?: RecomendacaoSoloItem;
  potassio?: RecomendacaoSoloItem;
  nitrogenio?: RecomendacaoSoloItem;
}

export function useTalhoesContexto(unidadeProdutivaId?: string) {
  return useQuery<TalhaoContexto[]>({
    queryKey: ["talhoes-contexto", unidadeProdutivaId],
    queryFn: async () => {
      return apiFetch("/talhoes/contexto", {
        params: { unidade_produtiva_id: unidadeProdutivaId },
      });
    },
    enabled: !!unidadeProdutivaId,
  });
}

export function useCulturas() {
  return useQuery<CulturaCanonica[]>({
    queryKey: ["culturas"],
    queryFn: async () => {
      try {
        return await apiFetch<CulturaCanonica[]>("/cadastros/culturas", {
          params: { ativa: true },
        });
      } catch {
        const legado = await apiFetch<CulturaLegada[]>("/agricola/cadastros/culturas");
        return legado.map((item) => ({
          id: item.id,
          nome: item.nome,
        }));
      }
    },
  });
}

export function useSafrasAtivas(unidadeProdutivaId?: string) {
  return useQuery<SafraAtiva[]>({
    queryKey: ["safras-ativas", unidadeProdutivaId],
    queryFn: async () => {
      const data = await apiFetch<SafraAtiva[]>(
        `/safras/${unidadeProdutivaId ? `?unidade_produtiva_id=${unidadeProdutivaId}` : ""}`
      );
      return data.filter((s) => {
        if (typeof s.ativa === "boolean") {
          return s.ativa;
        }

        return !["ENCERRADA", "CANCELADA"].includes(s.status);
      });
    },
  });
}

export function useAnalisesSolo(talhaoId?: string) {
  return useQuery<Record<string, unknown>[]>({
    queryKey: ["analises-solo", talhaoId],
    queryFn: async () => {
      return apiFetch("/agricola/analises-solo", {
        params: { talhao_id: talhaoId },
      });
    },
  });
}

export function useRecomendacoes(analiseId?: string) {
  const hasProfessionalTier = useHasTier("PROFISSIONAL");

  return useQuery<RecomendacoesSolo>({
    queryKey: ["recomendacoes-solo", analiseId],
    queryFn: async () => {
      return apiFetch(`/agricola/analises-solo/${analiseId}/recomendacoes`);
    },
    enabled: !!analiseId && hasProfessionalTier,
  });
}

export interface AnaliseSoloDetalhe {
  id: string;
  ph_agua?: number | null;
  argila_pct?: number | null;
  v_pct?: number | null;
  area_ha?: number | null;
  [key: string]: unknown;
}

export function useAnaliseSolo(analiseId?: string) {
  return useQuery<AnaliseSoloDetalhe>({
    queryKey: ["analise-solo", analiseId],
    queryFn: async () => {
      return apiFetch(`/agricola/analises-solo/${analiseId}`);
    },
    enabled: !!analiseId,
  });
}
