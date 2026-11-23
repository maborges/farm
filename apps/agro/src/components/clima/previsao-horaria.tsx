"use client";

import * as React from "react";
import { Clock, Droplets, Wind, CloudRain } from "lucide-react";
import { HorizontalScrollRail } from "@/components/layout/horizontal-scroll-rail";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  formatarHorario,
  type PrevisaoHorariaItemClima,
} from "@/lib/clima/previsao";
import { ClimaIcon } from "./clima-icon";

interface PrevisaoHorariaProps {
  itens: PrevisaoHorariaItemClima[];
  fusoHorario?: string;
}

export function PrevisaoHoraria({
  itens,
  fusoHorario = "America/Sao_Paulo",
}: PrevisaoHorariaProps): React.ReactElement {
  if (!itens || itens.length === 0) {
    return (
      <Card id="card-previsao-horaria">
        <CardHeader className="border-b border-border/60">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="size-4 text-primary" />
            Previsão Horária
          </CardTitle>
          <CardDescription className="text-xs">
            Projeção meteorológica hora a hora para planejamento de pulverização e manejo.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center py-6 text-xs text-muted-foreground">
          Nenhuma projeção horária disponível para esta localidade.
        </CardContent>
      </Card>
    );
  }

  const lista24h = itens.slice(0, 24);

  return (
    <Card id="previsao-horaria">
      <CardHeader className="flex flex-col gap-2 border-b border-border/60 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="size-4 text-primary shrink-0" />
            <span>Previsão Horária para Pulverização</span>
          </CardTitle>
          <CardDescription className="text-xs mt-0.5">
            Condições hora a hora para acompanhar temperatura, vento e chuva antes de intervenções no campo.
          </CardDescription>
        </div>
        <Badge variant="outline" className="self-start sm:self-auto shrink-0 whitespace-normal h-auto py-0.5 leading-snug">
          Próximas 24 Horas ({fusoHorario})
        </Badge>
      </CardHeader>

      <CardContent>
        {/* Faixa deslizante horizontal responsiva */}
        <HorizontalScrollRail
          ariaLabel="Projeção horária das próximas 24 horas"
          testId="scroll-previsao-horaria"
          contentClassName="pb-2 pt-1"
        >
          {lista24h.map((item, idx) => {
            const horaFormatada = formatarHorario(item.horaIso, fusoHorario);
            const temp = item.temperaturaC !== null ? `${Math.round(item.temperaturaC)}°` : "—";
            const chuvaPct = item.probabilidadeChuvaPct !== null ? `${item.probabilidadeChuvaPct}%` : null;
            const chuvaMm = item.precipitacaoMm !== null ? `${item.precipitacaoMm.toFixed(1)}mm` : null;
            const vento = item.ventoKmH !== null ? `${Math.round(item.ventoKmH)}` : null;
            const umidade = item.umidadePct !== null ? `${item.umidadePct}%` : null;

            return (
              <div
                key={item.horaIso || idx}
                className="shrink-0 w-[104px] md:w-24 p-3 md:p-2.5 rounded-xl md:rounded-sm border border-border/60 bg-muted/20 flex flex-col items-center text-center gap-1.5 snap-start hover:border-primary/40 hover:bg-muted/40 transition-colors"
                data-hora-iso={item.horaIso}
                data-horario-item="true"
              >
                {/* Horário */}
                <span className="text-xs font-semibold text-foreground font-mono">
                  {horaFormatada}
                </span>

                {/* Ícone */}
                <div className="my-0.5">
                  <ClimaIcon icone={item.condicaoIcone} className="size-6" />
                </div>

                {/* Temperatura */}
                <span className="text-base md:text-sm font-bold text-foreground font-mono">
                  {temp}
                </span>

                {/* Chuva */}
                <div className="flex items-center gap-1 text-xs md:text-[10px] text-blue-600 dark:text-blue-400">
                  <CloudRain className="size-3 shrink-0" />
                  <span>{chuvaPct ?? chuvaMm ?? "0%"}</span>
                </div>

                {/* Vento */}
                <div className="flex items-center gap-1 text-xs md:text-[10px] text-teal-600 dark:text-teal-400">
                  <Wind className="size-3 shrink-0" />
                  <span>{vento ? `${vento}km/h` : "—"}</span>
                </div>

                {/* Umidade */}
                <div className="flex items-center gap-1 text-xs md:text-[10px] text-muted-foreground">
                  <Droplets className="size-3 shrink-0 text-blue-500/70" />
                  <span>{umidade ?? "—"}</span>
                </div>
              </div>
            );
          })}
        </HorizontalScrollRail>
      </CardContent>
    </Card>
  );
}
