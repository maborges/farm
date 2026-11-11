'use client';

import { EstoqueResumoResponse, SaldoDepositoItem } from '@/hooks/use-estoque';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

interface SaldoGridProps {
  data?: EstoqueResumoResponse;
  isLoading?: boolean;
  isError?: boolean;
}

export function SaldoGrid({ data, isLoading, isError }: SaldoGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card className="border-destructive/30 bg-destructive/5">
        <CardHeader>
          <CardTitle className="text-destructive">Erro ao carregar saldos</CardTitle>
          <CardDescription>
            Verifique sua conexão e tente novamente
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (data.depositos.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sem estoque</CardTitle>
          <CardDescription>
            Nenhum lote ativo com saldo disponível
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {data.depositos.map((deposito) => (
        <Card key={deposito.deposito_id} className="overflow-hidden">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">{deposito.deposito_nome}</CardTitle>
            <CardDescription>
              {deposito.produtos.length} produto{deposito.produtos.length !== 1 ? 's' : ''}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {deposito.produtos.map((produto) => (
              <div key={produto.produto_id} className="space-y-1 border-b pb-2 last:border-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium leading-tight">
                      {produto.produto_nome}
                    </p>
                    {produto.status_lotes && (
                      <p className="text-xs text-muted-foreground">{produto.status_lotes}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-lg font-semibold">
                    {produto.quantidade_atual.toFixed(2)}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    {produto.unidade || 'un'}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
