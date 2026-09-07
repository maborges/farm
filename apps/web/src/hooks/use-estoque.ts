'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useState, useCallback } from 'react';

// Types
export interface SaldoDepositoItem {
  produto_id: string;
  produto_nome: string;
  deposito_id: string;
  deposito_nome: string;
  quantidade_atual: number;
  unidade: string | null;
  status_lotes: string | null;
  preco_unitario_medio: number | null;
}

export interface EstoqueResumoResponse {
  safra_id: string;
  total_produtos_ativos: number;
  total_depositos: number;
  depositos: {
    deposito_id: string;
    deposito_nome: string;
    produtos: SaldoDepositoItem[];
  }[];
}

export interface MovimentacaoSafra {
  id: string;
  produto_id: string;
  produto_nome: string;
  lote_id: string | null;
  numero_lote: string | null;
  deposito_id: string;
  deposito_nome: string;
  tipo: 'ENTRADA' | 'SAIDA' | 'SAIDA_REVERSA' | 'AJUSTE' | 'TRANSFERENCIA';
  quantidade: number;
  unidade: string | null;
  custo_unitario: number | null;
  custo_total: number | null;
  motivo: string | null;
  origem_id: string | null;
  origem_tipo: string | null;
  operacao_tipo: string | null;
  data_movimentacao: string;
}

export interface MovimentacaoResponse {
  safra_id: string;
  movimentacoes: MovimentacaoSafra[];
  total: number;
  limit: number;
  offset: number;
}

// Filter types
export interface MovimentacaoFilters {
  tipo?: string;
  deposito_id?: string;
  data_inicio?: string;
  data_fim?: string;
  numero_lote?: string;
  limit?: number;
  offset?: number;
}

function createEmptySaldoResponse(safraId: string): EstoqueResumoResponse {
  return {
    safra_id: safraId,
    total_produtos_ativos: 0,
    total_depositos: 0,
    depositos: [],
  };
}

function createEmptyMovimentacaoResponse(safraId: string): MovimentacaoResponse {
  return {
    safra_id: safraId,
    movimentacoes: [],
    total: 0,
    limit: 100,
    offset: 0,
  };
}

function isNotFoundError(error: unknown) {
  if (!(error instanceof Error)) return false;
  return error.message.includes('Not Found') || error.message.includes('404');
}

// Hook for saldo
export function useEstoqueSaldo(safraId: string) {
  return useQuery({
    queryKey: ['estoque-saldo', safraId],
    queryFn: async () => {
      try {
        const data = await apiFetch(
          `/agricola/safras/${safraId}/estoque/saldo`,
          { suppressErrorLog: true }
        );
        return data as EstoqueResumoResponse;
      } catch (error) {
        if (isNotFoundError(error)) {
          return createEmptySaldoResponse(safraId);
        }
        throw error;
      }
    },
    enabled: !!safraId,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for movimentacoes with filters
export function useEstoqueMovimentacoes(
  safraId: string,
  filters: MovimentacaoFilters = {}
) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['estoque-movimentacoes', safraId, filters],
    queryFn: async () => {
      const params = new URLSearchParams();

      if (filters.tipo) params.append('tipo', filters.tipo);
      if (filters.deposito_id) params.append('deposito_id', filters.deposito_id);
      if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
      if (filters.data_fim) params.append('data_fim', filters.data_fim);
      if (filters.numero_lote) params.append('numero_lote', filters.numero_lote);
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.offset) params.append('offset', filters.offset.toString());

      const queryString = params.toString();
      const url = queryString
        ? `/agricola/safras/${safraId}/estoque/movimentacoes?${queryString}`
        : `/agricola/safras/${safraId}/estoque/movimentacoes`;

      try {
        const data = await apiFetch(url, { suppressErrorLog: true });
        return data as MovimentacaoResponse;
      } catch (error) {
        if (isNotFoundError(error)) {
          return createEmptyMovimentacaoResponse(safraId);
        }
        throw error;
      }
    },
    enabled: !!safraId,
    retry: false,
    staleTime: 3 * 60 * 1000, // 3 minutes
  });

  const refetch = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ['estoque-movimentacoes', safraId],
    });
  }, [queryClient, safraId]);

  return { ...query, refetch };
}

// Combined hook for both queries
export function useEstoque(safraId: string, movimentacaoFilters: MovimentacaoFilters = {}) {
  const saldo = useEstoqueSaldo(safraId);
  const movimentacoes = useEstoqueMovimentacoes(safraId, movimentacaoFilters);

  const isLoading = saldo.isLoading || movimentacoes.isLoading;
  const isError = saldo.isError || movimentacoes.isError;
  const error = saldo.error || movimentacoes.error;

  return {
    saldo,
    movimentacoes,
    isLoading,
    isError,
    error,
    refetch: () => {
      saldo.refetch();
      movimentacoes.refetch();
    },
  };
}
