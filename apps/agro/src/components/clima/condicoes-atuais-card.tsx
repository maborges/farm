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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card id="card-condicoes-atuais">
      <CardHeader className="border-b border-border/60">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2 flex-wrap">
            <CardTitle className="text-base sm:text-lg font-bold tracking-tight text-foreground flex items-center gap-1.5">
              {tipoOrigem === "GPS" ? (
                <Crosshair className="size-4 text-primary shrink-0" />
              ) : (
                <MapPin className="size-4 text-primary shrink-0" />
              )}
              <span>{localidadeNome} {localidadeUf ? `— ${localidadeUf}` : ""}</span>
            </CardTitle>

            <Badge variant="secondary">
              {tipoOrigem === "GPS" ? "Localização GPS (Dispositivo)" : "Centroide Municipal (IBGE)"}
            </Badge>

            {dados.dadosSinteticos && (
              <Badge
                variant="destructive"
                id="badge-dados-sinteticos"
              >
                <ShieldAlert className="size-3" />
                <span>Dados Sintéticos (Ambiente de Testes)</span>
              </Badge>
            )}

            <Badge variant="outline">
              {dados.tipoDado === "OBSERVADO" ? "Observação Real" : "Previsão Numérica"}
            </Badge>

            {(isStale || dados.desatualizado) && (
              <Badge
                variant="warning"
                id="badge-previsao-desatualizada"
              >
                Previsão Desatualizada
              </Badge>
            )}

            {isOffline && (
              <Badge
                variant="warning"
                id="badge-modo-offline"
              >
                Modo Offline (Cache Local)
              </Badge>
            )}
          </div>

          <CardDescription className="text-xs">
            Coordenadas de referência: {dados.latitude.toFixed(2)}°, {dados.longitude.toFixed(2)}°
            {tipoOrigem === "CENTROIDE_IBGE" ? " (Sede urbana municipal)" : " (Sensor do aparelho)"}
          </CardDescription>
        </div>

        {onRefresh && (
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              id="btn-atualizar-previsao"
              aria-label="Atualizar previsão do tempo"
            >
              <RotateCw className={`size-3.5 ${isRefreshing ? "animate-spin text-primary" : ""}`} />
              <span>{isRefreshing ? "Atualizando..." : "Atualizar"}</span>
            </Button>
          </CardAction>
        )}
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Bloco Central de Temperatura e Condição do Céu */}
        <Card variant="muted" size="sm">
          <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-sm bg-background border border-border/50 shrink-0">
                <ClimaIcon icone={dados.condicaoIcone} className="size-12" />
              </div>

              <div className="flex flex-col gap-0.5">
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
            <div className="text-xs text-muted-foreground flex flex-col gap-1 sm:text-right border-t sm:border-t-0 pt-2 sm:pt-0 border-border/40">
              <div className="flex sm:justify-end items-center gap-1.5">
                <Clock className="size-3.5 text-muted-foreground/80" />
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
          </CardContent>
        </Card>

        {/* Grade de Variáveis Agrometeorológicas Operacionais */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Umidade Relativa */}
          <Card variant="muted" size="sm">
            <CardContent className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Droplets className="size-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                <span className="font-medium">Umidade Relativa</span>
              </div>
              <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="umidade-valor">
                {dados.umidadeRelativaPct !== null ? `${dados.umidadeRelativaPct}%` : "—"}
              </p>
              <span className="text-[10px] text-muted-foreground">
                {dados.umidadeRelativaPct !== null && dados.umidadeRelativaPct < 40
                  ? "Atenção: baixa umidade"
                  : "Taxa do ar na superfície"}
              </span>
            </CardContent>
          </Card>

          {/* Velocidade do Vento e Rajadas */}
          <Card variant="muted" size="sm">
            <CardContent className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Wind className="size-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
                <span className="font-medium">Velocidade do Vento</span>
              </div>
              <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="vento-velocidade-valor">
                {dados.ventoVelocidadeKmH !== null ? `${Math.round(dados.ventoVelocidadeKmH)} km/h` : "—"}
              </p>
              <span className="text-[10px] text-muted-foreground">
                {dados.ventoRajadasKmH !== null
                  ? `Rajadas até ${Math.round(dados.ventoRajadasKmH)} km/h`
                  : "Sem rajadas registradas"}
              </span>
            </CardContent>
          </Card>

          {/* Direção do Vento */}
          <Card variant="muted" size="sm">
            <CardContent className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Compass className="size-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                <span className="font-medium">Direção do Vento</span>
              </div>
              <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="vento-direcao-valor">
                {formatarDirecaoVento(dados.ventoDirecaoGraus)}
              </p>
              <span className="text-[10px] text-muted-foreground">
                Orientação de deriva
              </span>
            </CardContent>
          </Card>

          {/* Precipitação e Probabilidade */}
          <Card variant="muted" size="sm">
            <CardContent className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <CloudRain className="size-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span className="font-medium">Chuva Prevista</span>
              </div>
              <p className="text-base sm:text-lg font-bold text-foreground font-mono" id="precipitacao-valor">
                {dados.precipitacaoMm !== null ? `${dados.precipitacaoMm.toFixed(1)} mm` : "—"}
              </p>
              <span className="text-[10px] text-muted-foreground">
                {dados.probabilidadeChuvaPct !== null
                  ? `Probabilidade: ${dados.probabilidadeChuvaPct}%`
                  : "Sem volume estimado"}
              </span>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>
  );
}
