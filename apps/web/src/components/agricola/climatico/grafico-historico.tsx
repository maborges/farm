"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Legend,
} from "recharts";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import type { SerieTemporalClima } from "@/lib/agricola/clima-api";

interface GraficoHistoricoProps {
  dados: SerieTemporalClima[];
}

export function GraficoHistorico({ dados }: GraficoHistoricoProps) {
  const chartData = useMemo(() => {
    return [...dados].map((item) => ({
      ...item,
      labelData: format(parseISO(item.data), "dd/MM", { locale: ptBR }),
    }));
  }, [dados]);

  if (!dados || dados.length === 0) {
    return (
      <Card className="rounded-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Série Histórica e Inteligência</CardTitle>
          <CardDescription>Visualização de temperaturas e precipitação</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground text-sm">
          Sem dados históricos suficientes para gerar o gráfico.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-sm flex flex-col">
      <CardHeader>
        <CardTitle className="text-base font-medium">Comportamento Climático (30 dias)</CardTitle>
        <CardDescription>
          Relação entre precipitação (mm) e temperaturas (Mínima, Média e Máxima)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            
            <XAxis 
              dataKey="labelData" 
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} 
              axisLine={false} 
              tickLine={false} 
              dy={10} 
            />
            
            <YAxis 
              yAxisId="temp" 
              orientation="left" 
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} 
              axisLine={false} 
              tickLine={false} 
              dx={-10}
              domain={['auto', 'auto']}
            />
            <YAxis 
              yAxisId="precip" 
              orientation="right" 
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} 
              axisLine={false} 
              tickLine={false} 
              dx={10}
              domain={[0, 'auto']}
            />
            
            <Tooltip
              contentStyle={{ 
                borderRadius: "4px", 
                border: "1px solid hsl(var(--border))",
                backgroundColor: "hsl(var(--background))",
                fontSize: "12px"
              }}
              labelStyle={{ fontWeight: "bold", color: "hsl(var(--foreground))", marginBottom: "4px" }}
            />
            
            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }} />

            <Bar 
              yAxisId="precip" 
              dataKey="precipitacao" 
              name="Precipitação (mm)" 
              fill="#3b82f6" 
              radius={[2, 2, 0, 0]} 
              barSize={20}
              opacity={0.7}
            />

            <Line 
              yAxisId="temp" 
              type="monotone" 
              dataKey="temp_max" 
              name="Temp. Máx (°C)" 
              stroke="#ef4444" 
              strokeWidth={2} 
              dot={{ r: 3, fill: "#ef4444", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
            
            <Line 
              yAxisId="temp" 
              type="monotone" 
              dataKey="temp_media" 
              name="Temp. Média (°C)" 
              stroke="#10b981" 
              strokeWidth={2} 
              strokeDasharray="4 4"
              dot={false}
              activeDot={{ r: 4 }}
            />

            <Line 
              yAxisId="temp" 
              type="monotone" 
              dataKey="temp_min" 
              name="Temp. Mín (°C)" 
              stroke="#8b5cf6" 
              strokeWidth={2} 
              dot={{ r: 3, fill: "#8b5cf6", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
