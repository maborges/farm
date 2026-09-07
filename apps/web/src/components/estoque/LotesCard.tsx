'use client';

import { useEstoqueLotes } from '@/hooks/use-estoque-lotes';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/ui/status-badge';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface LotesCardProps {
  safraId: string;
  depositoId?: string;
}

export function LotesCard({ safraId, depositoId }: LotesCardProps) {
  const { data, isLoading, isError } = useEstoqueLotes(safraId, depositoId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lotes Consumidos</CardTitle>
          <CardDescription>Batches de estoque consumidas em operações</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Erro ao carregar lotes. Verifique sua conexão.
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.lotes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lotes Consumidos</CardTitle>
          <CardDescription>Batches de estoque consumidas em operações</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Nenhum lote consumido ainda.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lotes Consumidos</CardTitle>
        <CardDescription>
          {data.total_lotes} lote{data.total_lotes !== 1 ? 's' : ''} consumido{data.total_lotes !== 1 ? 's' : ''}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.lotes.map((lote) => (
            <div key={lote.id} className="border rounded-lg p-4 space-y-3 hover:bg-muted/50 transition">
              {/* Header com numero_lote e status */}
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="font-mono text-sm font-semibold">{lote.numero_lote}</p>
                  <p className="text-xs text-muted-foreground">{lote.produto_nome}</p>
                </div>
                <StatusBadge
                  status={lote.status === 'ATIVO' ? 'ativo' : 'inativo'}
                  label={lote.status === 'ATIVO' ? 'Ativo' : 'Esgotado'}
                />
              </div>

              {/* Grid de informações */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Quantidade inicial</p>
                  <p className="font-semibold">{lote.quantidade_inicial.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Quantidade atual</p>
                  <p className="font-semibold">{lote.quantidade_atual.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Custo unitário</p>
                  <p className="font-semibold">R$ {lote.custo_unitario.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Depósito</p>
                  <p className="font-semibold text-xs">{lote.deposito_nome}</p>
                </div>
              </div>

              {/* Referência fiscal e datas */}
              <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
                {lote.nota_fiscal_ref && (
                  <p>
                    <span className="font-semibold">NFe:</span> {lote.nota_fiscal_ref}
                  </p>
                )}
                {lote.data_fabricacao && (
                  <p>
                    <span className="font-semibold">Fabricação:</span> {new Date(lote.data_fabricacao).toLocaleDateString('pt-BR')}
                  </p>
                )}
                {lote.data_validade && (
                  <p>
                    <span className="font-semibold">Validade:</span> {new Date(lote.data_validade).toLocaleDateString('pt-BR')}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
