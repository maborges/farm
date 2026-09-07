"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface PrecoHistoricoItem {
  fornecedor_nome: string;
  valor_unitario: number;
  data: string;
  origem: string;
}

interface Props {
  data: PrecoHistoricoItem[];
  precoMedio?: number;
}

export function TendenciaPrecosChart({ data, precoMedio }: Props) {
  if (!data || data.length < 2) {
    return (
      <div className="flex h-40 w-full items-center justify-center rounded-sm border border-dashed border-muted-foreground/20 bg-muted/5">
        <p className="text-sm text-muted-foreground italic">
          Histórico insuficiente para análise de tendência
        </p>
      </div>
    );
  }

  // Pegar os últimos 12 registros (já vem ordenado ASC do backend agora)
  const chartData = data.slice(-12).map((item) => ({
    ...item,
    data_formatada: format(new Date(item.data), "dd/MM", { locale: ptBR }),
  }));

  // Calcular se subiu ou desceu
  const primeiro = chartData[0].valor_unitario;
  const ultimo = chartData[chartData.length - 1].valor_unitario;
  const isCrescente = ultimo > primeiro;
  const lineColor = isCrescente ? "#ef4444" : "#10b981"; // Vermelho se subiu, verde se desceu

  return (
    <div className="h-64 w-full pt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted-foreground))" opacity={0.1} />
          <XAxis
            dataKey="data_formatada"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            dy={10}
          />
          <YAxis
            hide
            domain={["auto", "auto"]}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="rounded-sm border bg-background p-2 shadow-sm">
                    <p className="text-[10px] font-bold text-muted-foreground uppercase">
                      {format(new Date(item.data), "PPP", { locale: ptBR })}
                    </p>
                    <p className="text-sm font-semibold">
                      R$ {item.valor_unitario.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-[10px] text-muted-foreground truncate max-w-[150px]">
                      {item.fornecedor_nome}
                    </p>
                  </div>
                );
              }
              return null;
            }}
          />
          {precoMedio && (
            <ReferenceLine
              y={precoMedio}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="3 3"
              label={{
                value: "Média",
                position: "insideLeft",
                fill: "hsl(var(--muted-foreground))",
                fontSize: 10,
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="valor_unitario"
            stroke={lineColor}
            strokeWidth={2}
            dot={{ r: 3, fill: lineColor, strokeWidth: 0 }}
            activeDot={{ r: 5, strokeWidth: 0 }}
            animationDuration={1000}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
