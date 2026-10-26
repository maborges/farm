"use client";

import * as React from "react";
import {
  Droplets,
  Wind,
  Compass,
  CloudRain,
  RotateCw,
  Clock,
  MapPin,
  Crosshair,
  ShieldAlert,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatarDirecaoVento,
  formatarHorario,
  type ClimaPrevisaoData,
} from "@/lib/clima/previsao";
import { ClimaIcon } from "./clima-icon";

interface CondicoesAtuaisCardProps {
  dados: ClimaPrevisaoData;
  localidadeNome: string;
  localidadeUf: string;
  tipoOrigem: "GPS" | "CENTROIDE_IBGE";
  isRefreshing?: boolean;
  onRefresh?: () => void;
  isOffline?: boolean;
  isStale?: boolean;
  salvoEmIso?: string;
}

export function CondicoesAtuaisCard({
  dados,
  localidadeNome,
  localidadeUf,
  tipoOrigem,
  isRefreshing = false,
  onRefresh,
  isOffline = false,
  isStale = false,
  salvoEmIso,
}: CondicoesAtuaisCardProps): React.ReactElement {
  const tempAtual = dados.temperaturaAtualC !== null ? Math.round(dados.temperaturaAtualC) : null;
  const sensacao = dados.sensacaoTermicaC !== null ? Math.round(dados.sensacaoTermicaC) : null;

  return (
    <Card className="rounded-sm border-border shadow-xs" id="card-condicoes-atuais">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-base sm:text-lg font-bold tracking-tight text-foreground flex items-center gap-1.5">
                {tipoOrigem === "GPS" ? (
                  <Crosshair className="w-4 h-4 text-primary shrink-0" />
                ) : (
                  <MapPin className="w-4 h-4 text-primary shrink-0" />
                )}
                <span>{localidadeNome} {localidadeUf ? `— ${localidadeUf}` : ""}</span>
              </CardTitle>

              <Badge variant="secondary" className="text-[10px] font-normal">
                {tipoOrigem === "GPS" ? "Localização GPS (Dispositivo)" : "Centroide Municipal (IBGE)"}
              </Badge>

              {dados.dadosSinteticos && (
                <Badge
                  variant="destructive"
                  className="text-[10px] px-1.5 font-medium"
                  id="badge-dados-sinteticos"
                >
                  <ShieldAlert className="w-3 h-3 mr-1" />
                  Dados Sintéticos (Ambiente de Testes)
                </Badge>
              )}

              <Badge variant="outline" className="text-[10px]">
                {dados.tipoDado === "OBSERVADO" ? "Observação Real" : "Previsão Numérica"}
              </Badge>

              {(isStale || dados.desatualizado) && (
                <Badge
                  variant="outline"
                  className="text-[10px] text-amber-700 dark:text-amber-300 border-amber-500/40 bg-amber-500/10"
                  id="badge-previsao-desatualizada"
                >
                  Previsão Desatualizada
                </Badge>
              )}

              {isOffline && (
                <Badge
                  variant="outline"
                  className="text-[10px] text-amber-700 dark:text-amber-300 border-amber-500/40 bg-amber-500/10"
                  id="badge-modo-offline"
                >
                  Modo Offline (Cache Local)
                </Badge>
              )}
            </div>

            <p className="text-xs text-muted-foreground mt-0.5">
              Coordenadas de referência: {dados.latitude.toFixed(2)}°, {dados.longitude.toFixed(2)}°
              {tipoOrigem === "CENTROIDE_IBGE" ? " (Sede urbana municipal)" : " (Sensor do aparelho)"}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {onRefresh && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5 cursor-pointer rounded-sm"
                onClick={onRefresh}
                disabled={isRefreshing}
                id="btn-atualizar-previsao"
                aria-label="Atualizar previsão do tempo"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-primary" : ""}`} />
                <span>{isRefreshing ? "Atualizando..." : "Atualizar"}</span>
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Bloco Central de Temperatura e Condição do Céu */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-sm bg-muted/30 border border-border/60">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-sm bg-background border border-border/50 shrink-0">
              <ClimaIcon icone={dados.condicaoIcone} className="w-12 h-12" />
            </div>

            <div className="space-y-0.5">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl sm:text-5xl font-extrabold tracking-tight text-foreground font-mono" id="temp-atual-valor">
                  {tempAtual !== null ? `${tempAtual}°` : "—"}
                </span>
                <span className="text-sm font-medium text-muted-foreground">C</span>
              </div>

              <p className="text-sm font-semibold text-foreground" id="condicao-descricao-texto">
                {dados.condicaoDescricao || "Condição estável"}
              </p>

              {sensacao !== null && (
                <p className="text-xs text-muted-foreground">
                  Sensação térmica de <strong className="font-semibold text-foreground">{sensacao}°C</strong>
                </p>
              )}
            </div>
          </div>

          {/* Timestamp e Metadados do Provedor */}
          <div className="text-xs text-muted-foreground space-y-1 sm:text-right border-t sm:border-t-0 pt-2 sm:pt-0 border-border/40">
            <div className="flex sm:justify-end items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-muted-foreground/80" />
              <span>
                Ref: {formatarHorario(dados.horarioReferenciaIso, dados.fusoHorario)} ({dados.fusoHorario})
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground/80">
              Fonte:{" "}
              {dados.provedor === "WEATHERAPI" ? (
                <a
                  href="https://www.weatherapi.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-foreground"
                  title="WeatherAPI.com"
                >
                  WeatherAPI.com
                </a>
              ) : dados.provedor === "OPEN_METEO" ? (
                <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">
                  Open-Meteo
                </a>
              ) : dados.provedor === "OPENWEATHER" ? (
                <a href="https://openweathermap.org/" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">
                  OpenWeather
                </a>
              ) : (
                dados.provedor
              )}
            </p>
            {salvoEmIso && isOffline && (
              <p className="text-[10px] text-amber-600 dark:text-amber-400">
                Última sincronização salva: {formatarHorario(salvoEmIso, dados.fusoHorario)}
              </p>
            )}
          </div>
        </div>

        {/* Grade de Variáveis Agrometeorológicas Operacionais */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Umidade Relativa */}
          <div className="p-3 rounded-sm bg-muted/20 border border-border/50 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Droplets className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="font-medium">Umidade Relativa</span>
            </div>
            <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="umidade-valor">
              {dados.umidadeRelativaPct !== null ? `${dados.umidadeRelativaPct}%` : "—"}
            </p>
            <span className="text-[10px] text-muted-foreground block">
              {dados.umidadeRelativaPct !== null && dados.umidadeRelativaPct < 40
                ? "Atenção: baixa umidade"
                : "Taxa do ar na superfície"}
            </span>
          </div>

          {/* Velocidade do Vento e Rajadas */}
          <div className="p-3 rounded-sm bg-muted/20 border border-border/50 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Wind className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
              <span className="font-medium">Velocidade do Vento</span>
            </div>
            <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="vento-velocidade-valor">
              {dados.ventoVelocidadeKmH !== null ? `${Math.round(dados.ventoVelocidadeKmH)} km/h` : "—"}
            </p>
            <span className="text-[10px] text-muted-foreground block">
              {dados.ventoRajadasKmH !== null
                ? `Rajadas até ${Math.round(dados.ventoRajadasKmH)} km/h`
                : "Sem rajadas registradas"}
            </span>
          </div>

          {/* Direção do Vento */}
          <div className="p-3 rounded-sm bg-muted/20 border border-border/50 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Compass className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
              <span className="font-medium">Direção do Vento</span>
            </div>
            <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="vento-direcao-valor">
              {formatarDirecaoVento(dados.ventoDirecaoGraus)}
            </p>
            <span className="text-[10px] text-muted-foreground block">
              Orientação de deriva
            </span>
          </div>

          {/* Precipitação e Probabilidade */}
          <div className="p-3 rounded-sm bg-muted/20 border border-border/50 space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CloudRain className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <span className="font-medium">Chuva Prevista</span>
            </div>
            <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="precipitacao-valor">
              {dados.precipitacaoMm !== null ? `${dados.precipitacaoMm.toFixed(1)} mm` : "—"}
            </p>
            <span className="text-[10px] text-muted-foreground block">
              {dados.probabilidadeChuvaPct !== null
                ? `Probabilidade: ${dados.probabilidadeChuvaPct}%`
                : "Sem volume estimado"}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
