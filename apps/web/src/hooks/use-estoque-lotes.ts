'use client';

import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

export interface LoteItem {
  id: string;
  numero_lote: string;
  produto_id: string;
  produto_nome: string;
  deposito_id: string;
  deposito_nome: string;
  quantidade_inicial: number;
  quantidade_atual: number;
  custo_unitario: number;
  status: 'ATIVO' | 'ESGOTADO';
  data_fabricacao: string | null;
  data_validade: string | null;
  nota_fiscal_ref: string | null;
  created_at: string;
}

export interface EstoqueLotesResponse {
  safra_id: string;
  total_lotes: number;
  lotes: LoteItem[];
}

function createEmptyResponse(safraId: string): EstoqueLotesResponse {
  return {
    safra_id: safraId,
    total_lotes: 0,
    lotes: [],
  };
}

function isNotFoundError(error: unknown) {
  if (!(error instanceof Error)) return false;
  return error.message.includes('Not Found') || error.message.includes('404');
}

export function useEstoqueLotes(safraId: string, depositoId?: string) {
  return useQuery({
    queryKey: ['estoque-lotes', safraId, depositoId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (depositoId) params.append('deposito_id', depositoId);

      const queryString = params.toString();
      const url = queryString
        ? `/agricola/safras/${safraId}/estoque/lotes?${queryString}`
        : `/agricola/safras/${safraId}/estoque/lotes`;

      try {
        const data = await apiFetch(url, { suppressErrorLog: true });
        return data as EstoqueLotesResponse;
      } catch (error) {
        if (isNotFoundError(error)) {
          return createEmptyResponse(safraId);
        }
        throw error;
      }
    },
    enabled: !!safraId,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
