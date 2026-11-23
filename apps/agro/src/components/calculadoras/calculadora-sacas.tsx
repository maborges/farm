"use client";

import React, { useState, useMemo } from "react";
import { Scale, RotateCcw, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  converterSacasKgToneladas,
  type UnidadeMassaAgricola,
  type ConversaoMassaResultado,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";
import { cn } from "@/lib/utils";

export function CalculadoraSacas() {
  const [valorTexto, setValorTexto] = useState<string>("100");
  const [unidade, setUnidade] = useState<UnidadeMassaAgricola>("SACAS");
  const [kgPorSacaTexto, setKgPorSacaTexto] = useState<string>("60");

  const avisoAmbiguo = useMemo(() => {
    return detectarEntradaAmbiguaPtBr(valorTexto) || detectarEntradaAmbiguaPtBr(kgPorSacaTexto);
  }, [valorTexto, kgPorSacaTexto]);

  const { resultado, erro } = useMemo<{
    resultado: ConversaoMassaResultado | null;
    erro: string | null;
  }>(() => {
    const valor = parseNumeroPtBr(valorTexto);
    const kgPorSaca = parseNumeroPtBr(kgPorSacaTexto);

    if (valor === null) {
      return { resultado: null, erro: null };
    }

    if (kgPorSaca === null || kgPorSaca <= 0) {
      return {
        resultado: null,
        erro: "Informe um peso por saca válido maior que zero.",
      };
    }

    try {
      const res = converterSacasKgToneladas({
        valor,
        unidadeOrigem: unidade,
        kgPorSaca,
      });
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro no cálculo",
      };
    }
  }, [valorTexto, unidade, kgPorSacaTexto]);

  const handleLimpar = () => {
    setValorTexto("");
    setKgPorSacaTexto("60");
    setUnidade("SACAS");
  };

  return (
    <Card>
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
            <Scale className="size-5" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold">
              Sacas, Quilogramas e Toneladas
            </CardTitle>
            <CardDescription className="text-xs">
              Conversão bidirecional entre sacas de grãos, quilogramas e toneladas com peso de saca configurável.
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
        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 @[560px]/main:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1.5 sm:col-span-1">
            <Label htmlFor="valor-massa" className="text-xs">Quantidade</Label>
            <Input
              id="valor-massa"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 100 ou 6.000"
              value={valorTexto}
              onChange={(e) => setValorTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5 sm:col-span-1">
            <Label htmlFor="unidade-massa" className="text-xs">Unidade de Entrada</Label>
            <select
              id="unidade-massa"
              value={unidade}
              onChange={(e) => setUnidade(e.target.value as UnidadeMassaAgricola)}
              className={cn(inputBaseClassName, "md:text-xs")}
            >
              <option value="SACAS">Sacas agrícolas</option>
              <option value="QUILOGRAMAS">Quilogramas (kg)</option>
              <option value="TONELADAS">Toneladas métricas (t)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5 sm:col-span-1">
            <div className="flex items-center justify-between">
              <Label htmlFor="kg-saca" className="text-xs">Massa por Saca (kg)</Label>
              <span className="text-[11px] text-muted-foreground">Padrão: 60 kg</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Input
                id="kg-saca"
                type="text"
                inputMode="decimal"
                value={kgPorSacaTexto}
                onChange={(e) => setKgPorSacaTexto(e.target.value)}
                placeholder="60"
              />
              <Button
                type="button"
                variant={kgPorSacaTexto === "60" ? "default" : "outline"}
                size="sm"
                onClick={() => setKgPorSacaTexto("60")}
                title="Redefinir para 60 kg (padrão soja/milho)"
                className="h-11 md:h-8 px-2.5 md:px-2 text-xs"
              >
                60kg
              </Button>
              <Button
                type="button"
                variant={kgPorSacaTexto === "50" ? "default" : "outline"}
                size="sm"
                onClick={() => setKgPorSacaTexto("50")}
                title="Definir 50 kg (feijão/trigo/especiais)"
                className="h-11 md:h-8 px-2.5 md:px-2 text-xs"
              >
                50kg
              </Button>
            </div>
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
              Resultados Equivalentes
            </h4>
            <div className="grid grid-cols-1 @[560px]/main:grid-cols-3 gap-2.5">
              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Sacas ({resultado.kgPorSaca} kg cada)</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.sacas, 2)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">sacas agrícolas</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Massa em Quilogramas</span>
                  <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400">
                    {formatarNumero(resultado.quilogramas, 2)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">kg líquidos</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Massa em Toneladas</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.toneladas, 4)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">toneladas métricas (t)</span>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        <Separator />

        {/* Memória de Cálculo e Ações */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="size-3.5 text-muted-foreground shrink-0" />
            <span>
              Fórmulas: kg = sacas × {kgPorSacaTexto || "60"} | t = kg / 1.000 | sacas = kg / {kgPorSacaTexto || "60"}
            </span>
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
