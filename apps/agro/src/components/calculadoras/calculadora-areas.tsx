"use client";

import React, { useState, useMemo } from "react";
import { Map, RotateCcw, AlertCircle, Info, ShieldAlert, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  converterAreaRural,
  type UnidadeAreaRural,
  type ConversaoAreaResultado,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";
import { cn } from "@/lib/utils";

export function CalculadoraAreas() {
  const [valorTexto, setValorTexto] = useState<string>("10");
  const [unidade, setUnidade] = useState<UnidadeAreaRural>("HECTARES");

  const avisoAmbiguo = useMemo(() => {
    return detectarEntradaAmbiguaPtBr(valorTexto);
  }, [valorTexto]);

  const { resultado, erro } = useMemo<{
    resultado: ConversaoAreaResultado | null;
    erro: string | null;
  }>(() => {
    const valor = parseNumeroPtBr(valorTexto);

    if (valor === null) {
      return { resultado: null, erro: null };
    }

    try {
      const res = converterAreaRural({
        valor,
        unidadeOrigem: unidade,
      });
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro no cálculo de área",
      };
    }
  }, [valorTexto, unidade]);

  const handleLimpar = () => {
    setValorTexto("");
    setUnidade("HECTARES");
  };

  return (
    <Card>
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
            <Map className="size-5" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold">
              Conversão de Áreas Rurais
            </CardTitle>
            <CardDescription className="text-xs">
              Conversão exata entre Hectares, Metros Quadrados e os principais Alqueires regionais do Brasil.
            </CardDescription>
          </div>
        </div>
        <CardAction>
          <Badge variant="outline" className="hidden sm:inline-flex">
            Offline
          </Badge>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Aviso de Variação Regional do Alqueire com Fundamentação Geométrica */}
        <Alert variant="warning">
          <ShieldAlert className="size-4" />
          <AlertTitle className="text-xs">Fundamentação dos Alqueires</AlertTitle>
          <AlertDescription className="text-xs">
            <p>
              No Brasil colonial, a medida agrária base era a <em>braça linear</em> (2,20 m), correspondendo a braça quadrada de 4,84 m². O Alqueire Paulista adota 5.000 braças² (24.200 m²), o Alqueire Mineiro adota 10.000 braças² (48.400 m²), o Alqueire do Norte adota o padrão de 75×75 braças (5.625 braças² = 27.225 m²) e o Alqueire Baiano adota 50×50 braças (2.500 braças² = 12.100 m²).
            </p>
            <p className="text-[11px] font-medium mt-1">
              Sempre verifique a especificação exata da escritura do imóvel antes de transações comerciais.
            </p>
          </AlertDescription>
        </Alert>

        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="valor-area" className="text-xs">Área a Converter</Label>
            <Input
              id="valor-area"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 50 ou 120,5"
              value={valorTexto}
              onChange={(e) => setValorTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="unidade-area" className="text-xs">Unidade de Origem</Label>
            <select
              id="unidade-area"
              value={unidade}
              onChange={(e) => setUnidade(e.target.value as UnidadeAreaRural)}
              className={cn(inputBaseClassName, "text-xs")}
            >
              <option value="HECTARES">Hectares (ha) — 10.000 m²</option>
              <option value="METROS_QUADRADOS">Metros Quadrados (m²)</option>
              <option value="ALQUEIRE_PAULISTA">Alqueire Paulista — 24.200 m² (2,42 ha)</option>
              <option value="ALQUEIRE_MINEIRO">Alqueire Mineiro / Goiano — 48.400 m² (4,84 ha)</option>
              <option value="ALQUEIRE_NORTE">Alqueire do Norte (75×75 braças) — 27.225 m² (2,7225 ha)</option>
              <option value="ALQUEIRE_BAIANO">Alqueire Baiano / Pequeno (50×50 braças) — 12.100 m² (1,21 ha)</option>
            </select>
          </div>
        </div>

        {/* Aviso de Ambiguidade Numérica */}
        {avisoAmbiguo && (
          <Alert variant="warning">
            <AlertTriangle className="size-4" />
            <AlertDescription className="text-xs">{avisoAmbiguo}</AlertDescription>
          </Alert>
        )}

        {/* Mensagem de Erro de Validação */}
        {erro && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertDescription className="text-xs">{erro}</AlertDescription>
          </Alert>
        )}

        {/* Painel de Resultados */}
        {resultado && (
          <div className="flex flex-col gap-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Equivalências Calculadas
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">Hectares (ha)</span>
                    <Badge variant="outline" className="text-[9px]">Padrão Oficial (SI)</Badge>
                  </div>
                  <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400">
                    {formatarNumero(resultado.hectares, 4)} ha
                  </span>
                  <span className="text-[10px] text-muted-foreground">1 ha = 10.000 m²</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Metros Quadrados (m²)</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.metrosQuadrados, 2)} m²
                  </span>
                  <span className="text-[10px] text-muted-foreground">Área geométrica total</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Alqueire Paulista</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.alqueiresPaulistas, 4)} alq
                  </span>
                  <span className="text-[10px] text-muted-foreground">Fator: 24.200 m² (5.000 braças² = 2,42 ha)</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Alqueire Mineiro / Goiano</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.alqueiresMineiros, 4)} alq
                  </span>
                  <span className="text-[10px] text-muted-foreground">Fator: 48.400 m² (100×100 braças = 4,84 ha)</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Alqueire do Norte</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.alqueiresNorte, 4)} alq
                  </span>
                  <span className="text-[10px] text-muted-foreground">Fator: 27.225 m² (75×75 braças = 2,7225 ha)</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Alqueire Baiano / Pequeno</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.alqueiresBaianos, 4)} alq
                  </span>
                  <span className="text-[10px] text-muted-foreground">Fator: 12.100 m² (50×50 braças = 1,21 ha - BA/MA/PI)</span>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        <Separator />

        {/* Memória e Ações */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="size-3.5 text-muted-foreground shrink-0" />
            <span>Fatores verificados nas tabelas de medidas agrárias tradicionais do INCRA/IBGE.</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleLimpar}
            className="self-end sm:self-auto"
          >
            <RotateCcw className="size-3.5" />
            <span>Limpar</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
