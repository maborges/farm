"use client";

import React, { useState, useMemo } from "react";
import { Scale, RotateCcw, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  converterSacasKgToneladas,
  type UnidadeMassaAgricola,
  type ConversaoMassaResultado,
} from "@/lib/calculadoras/core";
import { parseNumeroPtBr, formatarNumero, detectarEntradaAmbiguaPtBr } from "@/lib/calculadoras/format";

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
    <Card className="border border-border/80 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
              <Scale className="w-5 h-5" />
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
          <Badge variant="outline" className="text-[10px] hidden sm:inline-flex">
            Offline
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1.5 sm:col-span-1">
            <Label htmlFor="valor-massa">Quantidade</Label>
            <Input
              id="valor-massa"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 100 ou 6.000"
              value={valorTexto}
              onChange={(e) => setValorTexto(e.target.value)}
            />
          </div>

          <div className="space-y-1.5 sm:col-span-1">
            <Label htmlFor="unidade-massa">Unidade de Entrada</Label>
            <select
              id="unidade-massa"
              value={unidade}
              onChange={(e) => setUnidade(e.target.value as UnidadeMassaAgricola)}
              className="flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="SACAS">Sacas agrícolas</option>
              <option value="QUILOGRAMAS">Quilogramas (kg)</option>
              <option value="TONELADAS">Toneladas métricas (t)</option>
            </select>
          </div>

          <div className="space-y-1.5 sm:col-span-1">
            <div className="flex items-center justify-between">
              <Label htmlFor="kg-saca">Massa por Saca (kg)</Label>
              <span className="text-[10px] text-muted-foreground">Padrão: 60 kg</span>
            </div>
            <div className="flex gap-1.5">
              <Input
                id="kg-saca"
                type="text"
                inputMode="decimal"
                value={kgPorSacaTexto}
                onChange={(e) => setKgPorSacaTexto(e.target.value)}
                placeholder="60"
              />
              <button
                type="button"
                onClick={() => setKgPorSacaTexto("60")}
                className="px-2 py-1 text-[11px] rounded-sm border border-border bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title="Redefinir para 60 kg (padrão soja/milho)"
              >
                60kg
              </button>
              <button
                type="button"
                onClick={() => setKgPorSacaTexto("50")}
                className="px-2 py-1 text-[11px] rounded-sm border border-border bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title="Definir 50 kg (feijão/trigo/especiais)"
              >
                50kg
              </button>
            </div>
          </div>
        </div>

        {/* Aviso de Ambiguidade Numérica */}
        {avisoAmbiguo && (
          <div className="p-2.5 rounded-sm border border-amber-500/30 bg-amber-500/5 text-amber-900 dark:text-amber-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <span className="leading-relaxed">{avisoAmbiguo}</span>
          </div>
        )}

        {/* Mensagem de Erro de Validação */}
        {erro && (
          <div className="p-2.5 rounded-sm border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{erro}</span>
          </div>
        )}

        {/* Painel de Resultados */}
        {resultado && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Resultados Equivalentes
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Sacas ({resultado.kgPorSaca} kg cada)</span>
                <span className="text-base sm:text-lg font-bold text-foreground block">
                  {formatarNumero(resultado.sacas, 2)}
                </span>
                <span className="text-[10px] text-muted-foreground">sacas agrícolas</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Massa em Quilogramas</span>
                <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400 block">
                  {formatarNumero(resultado.quilogramas, 2)}
                </span>
                <span className="text-[10px] text-muted-foreground">kg líquidos</span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Massa em Toneladas</span>
                <span className="text-base sm:text-lg font-bold text-foreground block">
                  {formatarNumero(resultado.toneladas, 4)}
                </span>
                <span className="text-[10px] text-muted-foreground">toneladas métricas (t)</span>
              </div>
            </div>
          </div>
        )}

        {/* Memória de Cálculo e Ações */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-border/60">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span>
              Fórmulas: kg = sacas × {kgPorSacaTexto || "60"} | t = kg / 1.000 | sacas = kg / {kgPorSacaTexto || "60"}
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleLimpar}
            className="flex items-center gap-1.5 self-end sm:self-auto cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Limpar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
