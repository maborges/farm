'use client';

import { useState, useMemo } from 'react';
import { MovimentacaoSafra } from '@/hooks/use-estoque';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface MovimentacaoTimelineProps {
  movimentacoes?: MovimentacaoSafra[];
  isLoading?: boolean;
}

type ViewMode = 'daily' | 'cumulative';

interface TimelineData {
  data: string;
  saida_total: number;
  entrada_total: number;
  saldo_acumulado?: number;
  dia: string;
}

export function MovimentacaoTimeline({
  movimentacoes = [],
  isLoading = false,
}: MovimentacaoTimelineProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('daily');

  const chartData = useMemo(() => {
    if (movimentacoes.length === 0) return [];

    // Agrupa por data
    const byDate: { [date: string]: { entrada: number; saida: number } } = {};

    movimentacoes.forEach((mov) => {
      const date = new Date(mov.data_movimentacao).toLocaleDateString('pt-BR');

      if (!byDate[date]) {
        byDate[date] = { entrada: 0, saida: 0 };
      }

      if (mov.tipo === 'ENTRADA') {
        byDate[date].entrada += mov.quantidade;
      } else if (mov.tipo === 'SAIDA') {
        byDate[date].saida += mov.quantidade;
      }
    });

    // Converte para array e ordena
    const data = Object.entries(byDate)
      .map(([date, values]) => ({
        data: date,
        entrada_total: parseFloat(values.entrada.toFixed(2)),
        saida_total: parseFloat(values.saida.toFixed(2)),
        dia: date.split('/')[0], // Dia para XAxis
      }))
      .sort((a, b) => new Date(a.data).getTime() - new Date(b.data).getTime());

    // Se cumulative, adiciona saldo acumulado
    if (viewMode === 'cumulative') {
      let saldoAcumulado = 0;
      return data.map((item) => {
        saldoAcumulado += item.entrada_total - item.saida_total;
        return {
          ...item,
          saldo_acumulado: parseFloat(saldoAcumulado.toFixed(2)),
        };
      });
    }

    return data;
  }, [movimentacoes, viewMode]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <CardTitle className="text-amber-900">Sem dados para visualizar</CardTitle>
          <CardDescription className="text-amber-700">
            Nenhuma movimentação encontrada com os filtros aplicados
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>Timeline de Movimentações</CardTitle>
          <CardDescription>
            Visualização diária de entradas e saídas de estoque
          </CardDescription>
        </div>
        <ToggleGroup type="single" value={viewMode} onValueChange={(v) => v && setViewMode(v as ViewMode)}>
          <ToggleGroupItem value="daily" aria-label="Diário">
            Diário
          </ToggleGroupItem>
          <ToggleGroupItem value="cumulative" aria-label="Acumulado">
            Acumulado
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          {viewMode === 'daily' ? (
            <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="dia"
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                formatter={(value: any) => parseFloat(value).toFixed(2)}
              />
              <Legend />
              <Bar dataKey="entrada_total" name="Entradas" fill="#10b981" />
              <Bar dataKey="saida_total" name="Saídas" fill="#ef4444" />
            </BarChart>
          ) : (
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="dia"
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                formatter={(value: any) => parseFloat(value).toFixed(2)}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="saldo_acumulado"
                name="Saldo Acumulado"
                stroke="#3b82f6"
                strokeWidth={2}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
