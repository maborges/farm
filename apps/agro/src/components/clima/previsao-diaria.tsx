"use client";

import * as React from "react";
import { Calendar, CloudRain, Wind, ArrowDown, ArrowUp } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  formatarDataDiaMes,
  type PrevisaoDiariaItemClima,
} from "@/lib/clima/previsao";
import { ClimaIcon } from "./clima-icon";

interface PrevisaoDiariaProps {
  itens: PrevisaoDiariaItemClima[];
  fusoHorario?: string;
}

export function PrevisaoDiaria({
  itens,
  fusoHorario = "America/Sao_Paulo",
}: PrevisaoDiariaProps): React.ReactElement {
  if (!itens || itens.length === 0) {
    return (
      <Card className="rounded-sm border-border" id="card-previsao-diaria">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            Previsão Diária
          </CardTitle>
          <CardDescription>
            Tendência meteorológica de precipitação e temperatura para planejamento de safra.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 text-center py-6 text-xs text-muted-foreground">
          Nenhuma projeção diária disponível para esta localidade.
        </CardContent>
      </Card>
    );
  }

  // Não completa artificialmente: apresenta exatamente a quantidade recebida (até 3 dias no MVP)
  const listaDias = itens.slice(0, 7);
  const totalDias = listaDias.length;
  const tituloPrevisao =
    totalDias === 7
      ? "Previsão dos Próximos 7 Dias"
      : `Previsão dos Próximos ${totalDias} Dias`;
  const badgeTendencia =
    totalDias === 7 ? "Tendência Semanal" : `Horizonte ${totalDias} Dias`;

  return (
    <Card className="rounded-sm border-border shadow-xs" id="previsao-diaria">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <CardTitle className="text-sm font-semibold">
              {tituloPrevisao}
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px]">
            {badgeTendencia}
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Comportamento esperado da temperatura, chuvas acumuladas e ventos para os próximos dias.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-2 divide-y divide-border/50">
        {listaDias.map((item, idx) => {
          const diaNome = item.diaSemana || (idx === 0 ? "Hoje" : `Dia ${idx + 1}`);
          const dataFormatada = formatarDataDiaMes(item.dataIso, fusoHorario);
          const tMin = item.tempMinC !== null ? `${Math.round(item.tempMinC)}°` : "—";
          const tMax = item.tempMaxC !== null ? `${Math.round(item.tempMaxC)}°` : "—";
          const probChuva = item.probabilidadeChuvaPct !== null ? `${item.probabilidadeChuvaPct}%` : null;
          const volChuva = item.precipitacaoMm !== null ? `${item.precipitacaoMm.toFixed(1)} mm` : null;
          const ventoMax = item.ventoMaxKmH !== null ? `${Math.round(item.ventoMaxKmH)} km/h` : null;

          return (
            <div
              key={item.dataIso || idx}
              className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 hover:bg-muted/20 px-2 rounded-sm transition-colors"
              data-data-iso={item.dataIso}
              data-diaria-item="true"
            >
              {/* Dia da Semana e Data */}
              <div className="flex items-center gap-3 min-w-[140px]">
                <div className="p-1.5 rounded-sm bg-muted/40 border border-border/40 shrink-0">
                  <ClimaIcon icone={item.condicaoIcone} className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground capitalize">
                    {idx === 0 ? "Hoje" : diaNome}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono">
                    {dataFormatada}
                  </p>
                </div>
              </div>

              {/* Descrição da Condição */}
              <div className="text-xs text-muted-foreground flex-1 sm:px-2">
                <span className="font-medium text-foreground">
                  {item.condicaoDescricao || "Sem descrição"}
                </span>
              </div>

              {/* Métricas: Chuva e Vento */}
              <div className="flex items-center gap-4 text-xs">
                {/* Chuva */}
                <div className="flex items-center gap-1.5 min-w-[80px]" title="Probabilidade e volume de chuva">
                  <CloudRain className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                  <div className="text-left text-[11px]">
                    <span className="font-semibold text-foreground">{probChuva ?? "0%"}</span>
                    {volChuva && (
                      <span className="text-[10px] text-muted-foreground ml-1">({volChuva})</span>
                    )}
                  </div>
                </div>

                {/* Vento Máximo */}
                <div className="flex items-center gap-1 text-[11px] text-teal-700 dark:text-teal-300 min-w-[70px]" title="Vento máximo previsto">
                  <Wind className="w-3.5 h-3.5 shrink-0" />
                  <span>{ventoMax ?? "—"}</span>
                </div>

                {/* Faixa Térmica (Min / Max) */}
                <div className="flex items-center gap-2 min-w-[90px] justify-end font-mono">
                  <span className="flex items-center text-xs text-blue-600 dark:text-blue-400 font-semibold" title="Temperatura mínima">
                    <ArrowDown className="w-3 h-3 mr-0.5" />
                    {tMin}
                  </span>
                  <span className="text-muted-foreground text-xs">/</span>
                  <span className="flex items-center text-xs text-amber-600 dark:text-amber-400 font-semibold" title="Temperatura máxima">
                    <ArrowUp className="w-3 h-3 mr-0.5" />
                    {tMax}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
