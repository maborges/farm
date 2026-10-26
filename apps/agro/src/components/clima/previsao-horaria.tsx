"use client";

import * as React from "react";
import { Clock, Droplets, Wind, CloudRain } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
      <Card className="rounded-sm border-border" id="card-previsao-horaria">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            Previsão Horária
          </CardTitle>
          <CardDescription>
            Projeção meteorológica hora a hora para planejamento de pulverização e manejo.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4 text-center py-6 text-xs text-muted-foreground">
          Nenhuma projeção horária disponível para esta localidade.
        </CardContent>
      </Card>
    );
  }

  // Limita até 24 itens (horizonte das próximas 24 horas)
  const lista24h = itens.slice(0, 24);

  return (
    <Card className="rounded-sm border-border shadow-xs" id="previsao-horaria">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm font-semibold">
              Previsão Horária para Pulverização
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-[10px]">
            Próximas 24 Horas ({fusoHorario})
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Condições hora a hora para acompanhar temperatura, vento e chuva antes de intervenções no campo.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-4 px-3 sm:px-6">
        {/* Faixa deslizante horizontal responsiva */}
        <div
          className="flex gap-2.5 overflow-x-auto pb-3 pt-1 scroll-smooth snap-x snap-mandatory focus:outline-none"
          tabIndex={0}
          role="region"
          aria-label="Projeção horária das próximas 24 horas"
          id="scroll-previsao-horaria"
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
                className="flex-shrink-0 w-24 p-2.5 rounded-sm border border-border/60 bg-muted/20 flex flex-col items-center text-center gap-1.5 snap-start hover:border-primary/40 hover:bg-muted/40 transition-colors"
                data-hora-iso={item.horaIso}
                data-horario-item="true"
              >
                {/* Horário */}
                <span className="text-xs font-semibold text-foreground font-mono">
                  {horaFormatada}
                </span>

                {/* Ícone */}
                <div className="my-0.5">
                  <ClimaIcon icone={item.condicaoIcone} className="w-6 h-6" />
                </div>

                {/* Temperatura */}
                <span className="text-sm font-bold text-foreground font-mono">
                  {temp}
                </span>

                {/* Chuva */}
                <div className="flex items-center gap-1 text-[10px] text-blue-600 dark:text-blue-400">
                  <CloudRain className="w-3 h-3 shrink-0" />
                  <span>{chuvaPct ?? chuvaMm ?? "0%"}</span>
                </div>

                {/* Vento */}
                <div className="flex items-center gap-1 text-[10px] text-teal-600 dark:text-teal-400">
                  <Wind className="w-3 h-3 shrink-0" />
                  <span>{vento ? `${vento}km/h` : "—"}</span>
                </div>

                {/* Umidade */}
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Droplets className="w-3 h-3 shrink-0 text-blue-500/70" />
                  <span>{umidade ?? "—"}</span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
