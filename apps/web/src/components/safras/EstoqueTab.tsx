'use client';

import { useState, useMemo } from 'react';
import { UUID } from 'crypto';
import { useEstoque, MovimentacaoFilters } from '@/hooks/use-estoque';
import { SaldoGrid } from '@/components/estoque/SaldoGrid';
import { MovimentacaoFilters as FiltersComponent } from '@/components/estoque/MovimentacaoFilters';
import { MovimentacaoTimeline } from '@/components/estoque/MovimentacaoTimeline';
import { MovimentacaoTable } from '@/components/estoque/MovimentacaoTable';
import { LotesCard } from '@/components/estoque/LotesCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface EstoqueTabProps {
  safraId: string;
}

export function EstoqueTab({ safraId }: EstoqueTabProps) {
  const [movimentacaoFilters, setMovimentacaoFilters] = useState<MovimentacaoFilters>({
    limit: 100,
    offset: 0,
  });

  const { saldo, movimentacoes, isLoading, isError, error, refetch } = useEstoque(
    safraId,
    movimentacaoFilters
  );

  // Extract unique deposits for filter dropdown
  const depositosUnicos = useMemo(() => {
    if (!saldo.data?.depositos) return [];
    return saldo.data.depositos.map((d) => ({
      id: d.deposito_id,
      nome: d.deposito_nome,
    }));
  }, [saldo.data?.depositos]);

  const handleFilterChange = (filters: MovimentacaoFilters) => {
    setMovimentacaoFilters({
      ...filters,
      limit: 100,
      offset: 0, // Reset para primeira página
    });
  };

  const handlePageChange = (offset: number) => {
    setMovimentacaoFilters((prev) => ({
      ...prev,
      offset,
    }));
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Erro ao carregar dados de estoque. Verifique sua conexão e tente novamente.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* SEÇÃO 1: Saldo Atual */}
      <div className="space-y-3">
        <div>
          <h3 className="text-lg font-semibold">Saldo Atual</h3>
          <p className="text-sm text-muted-foreground">
            Quantidade disponível por depósito
          </p>
        </div>
        <SaldoGrid
          data={saldo.data}
          isLoading={saldo.isLoading}
          isError={saldo.isError}
        />
      </div>

      {/* SEÇÃO 1.5: Lotes Consumidos (P0 Rastreabilidade) */}
      <div className="space-y-3">
        <LotesCard safraId={safraId} />
      </div>

      {/* SEÇÃO 2: Histórico com Filtros e Timeline */}
      <div className="space-y-3">
        <div>
          <h3 className="text-lg font-semibold">Histórico</h3>
          <p className="text-sm text-muted-foreground">
            Movimentações e timeline de consumo
          </p>
        </div>

        {/* Filtros */}
        <FiltersComponent
          onFilterChange={handleFilterChange}
          depositos={depositosUnicos}
          isLoading={movimentacoes.isLoading}
        />

        {/* Timeline */}
        <MovimentacaoTimeline
          movimentacoes={movimentacoes.data?.movimentacoes}
          isLoading={movimentacoes.isLoading}
        />

        {/* Tabela */}
        <MovimentacaoTable
          data={movimentacoes.data}
          isLoading={movimentacoes.isLoading}
          onPageChange={handlePageChange}
          currentOffset={movimentacaoFilters.offset || 0}
        />
      </div>
    </div>
  );
}
