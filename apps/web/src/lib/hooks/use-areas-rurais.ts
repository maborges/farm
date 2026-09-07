"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import type {
  AreaRuralTree,
  CreateAreaRuralInput,
  UpdateAreaRuralInput,
  PropriedadeResponse,
} from "@farm/zod-schemas";

/* ------------------------------------------------------------------ */
/* Hook: useAreasRurais                                                */
/* ------------------------------------------------------------------ */

export function useAreasRurais(propriedadeId: string, unidadeProdutivaId?: string) {
  const queryClient = useQueryClient();
  const hierarquiaKey = ["areas-rurais-hierarquia", propriedadeId];
  const areasKey = unidadeProdutivaId
    ? ["areas-rurais", propriedadeId, unidadeProdutivaId]
    : null;

  // Query hierarquia completa
  const { data: hierarquia, isLoading: loadingHierarquia } = useQuery({
    queryKey: hierarquiaKey,
    queryFn: () =>
      apiFetch<{
        propriedade: PropriedadeResponse;
        fazendas: Array<{
          unidade_produtiva_id: string;
          exploracao_id: string;
          natureza: string;
          data_inicio: string;
          data_fim: string | null;
          areas: AreaRuralTree[];
        }>;
      }>(`/cadastros/propriedades/${propriedadeId}/hierarquia`),
    enabled: !!propriedadeId,
  });

  // Query áreas de unidade produtiva específica (lista plana)
  const { data: areasPlana, isLoading: loadingAreas } = useQuery<AreaRuralTree[]>({
    queryKey: areasKey!,
    queryFn: () =>
      apiFetch(`/cadastros/propriedades/${propriedadeId}/fazendas/${unidadeProdutivaId}/areas`),
    enabled: !!propriedadeId && !!unidadeProdutivaId,
  });

  // Mutations
  const criarMutation = useMutation({
    mutationFn: ({ fazendaId, data }: { fazendaId: string; data: CreateAreaRuralInput }) =>
      apiFetch(
        `/cadastros/propriedades/${propriedadeId}/fazendas/${fazendaId}/areas`,
        { method: "POST", body: JSON.stringify(data) }
      ),
    onSuccess: () => {
      toast.success("Área rural criada com sucesso!");
      queryClient.invalidateQueries({ queryKey: hierarquiaKey });
      if (areasKey) queryClient.invalidateQueries({ queryKey: areasKey });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao criar área rural");
    },
  });

  const atualizarMutation = useMutation({
    mutationFn: ({ fazendaId, areaId, data }: { fazendaId: string; areaId: string; data: UpdateAreaRuralInput }) =>
      apiFetch(
        `/cadastros/unidades-produtivas/${fazendaId}/areas/${areaId}`,
        { method: "PATCH", body: JSON.stringify(data) }
      ),
    onSuccess: () => {
      toast.success("Área rural atualizada!");
      queryClient.invalidateQueries({ queryKey: hierarquiaKey });
      if (areasKey) queryClient.invalidateQueries({ queryKey: areasKey });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao atualizar área rural");
    },
  });

  const removerMutation = useMutation({
    mutationFn: ({ fazendaId, areaId }: { fazendaId: string; areaId: string }) =>
      apiFetch(
        `/cadastros/unidades-produtivas/${fazendaId}/areas/${areaId}`,
        { method: "DELETE" }
      ),
    onSuccess: () => {
      toast.success("Área rural removida!");
      queryClient.invalidateQueries({ queryKey: hierarquiaKey });
      if (areasKey) queryClient.invalidateQueries({ queryKey: areasKey });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Erro ao remover área rural");
    },
  });

  // Helper: extrair todas as áreas da hierarquia (lista plana)
  const flattenAreas = (areas: AreaRuralTree[]): AreaRuralTree[] => {
    const result: AreaRuralTree[] = [];
    for (const area of areas) {
      result.push(area);
      if (area.filhos?.length) {
        result.push(...flattenAreas(area.filhos));
      }
    }
    return result;
  };

  const todasAreas = hierarquia?.fazendas.flatMap((f) => flattenAreas(f.areas)) ?? [];

  return {
    hierarquia,
    todasAreas,
    areasPlana,
    loadingHierarquia,
    loadingAreas,
    criar: criarMutation,
    atualizar: atualizarMutation,
    remover: removerMutation,
    isPending:
      criarMutation.isPending ||
      atualizarMutation.isPending ||
      removerMutation.isPending,
    invalidate: () => {
      queryClient.invalidateQueries({ queryKey: hierarquiaKey });
      if (areasKey) queryClient.invalidateQueries({ queryKey: areasKey });
    },
  };
}
