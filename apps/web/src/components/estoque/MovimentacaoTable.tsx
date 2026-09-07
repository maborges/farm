'use client';

import { MovimentacaoResponse, MovimentacaoSafra } from '@/hooks/use-estoque';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface MovimentacaoTableProps {
  data?: MovimentacaoResponse;
  isLoading?: boolean;
  onPageChange?: (offset: number) => void;
  currentOffset?: number;
}

const TIPO_CORES = {
  ENTRADA: 'bg-green-100 text-green-800',
  SAIDA: 'bg-red-100 text-red-800',
  SAIDA_REVERSA: 'bg-purple-100 text-purple-800',
  AJUSTE: 'bg-yellow-100 text-yellow-800',
  TRANSFERENCIA: 'bg-blue-100 text-blue-800',
};

const TIPO_LABELS = {
  ENTRADA: 'Entrada',
  SAIDA: 'Saída',
  SAIDA_REVERSA: 'Devolução (Reversa)',
  AJUSTE: 'Ajuste',
  TRANSFERENCIA: 'Transferência',
};

export function MovimentacaoTable({
  data,
  isLoading = false,
  onPageChange,
  currentOffset = 0,
}: MovimentacaoTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.movimentacoes.length === 0) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-amber-900">Sem registros</CardTitle>
          <CardDescription className="text-amber-700">
            Nenhuma movimentação encontrada com os filtros aplicados
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const hasNextPage = currentOffset + (data.limit || 100) < data.total;
  const hasPrevPage = currentOffset > 0;

  const handleNextPage = () => {
    if (onPageChange && hasNextPage) {
      onPageChange(currentOffset + (data.limit || 100));
    }
  };

  const handlePrevPage = () => {
    if (onPageChange && hasPrevPage) {
      onPageChange(Math.max(0, currentOffset - (data.limit || 100)));
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Histórico de Movimentações</CardTitle>
            <CardDescription>
              {data.total} registro{data.total !== 1 ? 's' : ''} encontrado{data.total !== 1 ? 's' : ''}
            </CardDescription>
          </div>
          {data.total > (data.limit || 100) && (
            <div className="text-xs text-muted-foreground">
              {currentOffset + 1}-{Math.min(currentOffset + (data.limit || 100), data.total)} de {data.total}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table className="text-sm">
            <TableHeader>
              <TableRow>
                <TableHead>Data</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Produto</TableHead>
                <TableHead>Lote</TableHead>
                <TableHead>Depósito</TableHead>
                <TableHead className="text-right">Qtd</TableHead>
                <TableHead className="text-right">Custo Total</TableHead>
                <TableHead>Operação</TableHead>
                <TableHead>Motivo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.movimentacoes.map((mov) => (
                <TableRow key={mov.id}>
                  <TableCell className="whitespace-nowrap">
                    {new Date(mov.data_movimentacao).toLocaleDateString('pt-BR')}
                  </TableCell>
                  <TableCell>
                    <Badge
                      className={TIPO_CORES[mov.tipo as keyof typeof TIPO_CORES]}
                      variant="outline"
                    >
                      {TIPO_LABELS[mov.tipo as keyof typeof TIPO_LABELS]}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-xs truncate">{mov.produto_nome}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {mov.numero_lote ? (
                      <span title={mov.numero_lote}>{mov.numero_lote.substring(0, 10)}</span>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="text-xs">{mov.deposito_nome}</TableCell>
                  <TableCell className="text-right">
                    {mov.quantidade.toFixed(2)} {mov.unidade}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {mov.custo_total ? (
                      `R$ ${parseFloat(mov.custo_total.toString()).toFixed(2)}`
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="text-xs">
                    {mov.operacao_tipo ? (
                      <Badge variant="secondary">{mov.operacao_tipo}</Badge>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                    {mov.motivo || '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {data.total > (data.limit || 100) && (
          <div className="mt-4 flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevPage}
              disabled={!hasPrevPage}
            >
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!hasNextPage}
            >
              Próxima
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
