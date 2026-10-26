"use client";

import React, { useState, useMemo } from "react";
import { Truck, RotateCcw, AlertCircle, Info, ShieldAlert, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  calcularFreteAgricola,
  type UnidadeMassaAgricola,
  type TipoTarifaFrete,
  type FreteAgricolaResultado,
} from "@/lib/calculadoras/core";
import {
  parseNumeroPtBr,
  formatarNumero,
  formatarMoeda,
  detectarEntradaAmbiguaPtBr,
} from "@/lib/calculadoras/format";

export function CalculadoraFrete() {
  const [quantidadeTexto, setQuantidadeTexto] = useState<string>("32");
  const [unidadeQuantidade, setUnidadeQuantidade] = useState<UnidadeMassaAgricola>("TONELADAS");
  const [kgPorSacaTexto, setKgPorSacaTexto] = useState<string>("60");
  const [tipoTarifa, setTipoTarifa] = useState<TipoTarifaFrete>("POR_TONELADA");
  const [tarifaTexto, setTarifaTexto] = useState<string>("120");
  const [custosAdicionaisTexto, setCustosAdicionaisTexto] = useState<string>("0");

  const avisoAmbiguo = useMemo(() => {
    return (
      detectarEntradaAmbiguaPtBr(quantidadeTexto) ||
      detectarEntradaAmbiguaPtBr(tarifaTexto) ||
      detectarEntradaAmbiguaPtBr(custosAdicionaisTexto)
    );
  }, [quantidadeTexto, tarifaTexto, custosAdicionaisTexto]);

  const { resultado, erro } = useMemo<{
    resultado: FreteAgricolaResultado | null;
    erro: string | null;
  }>(() => {
    const quantidade = parseNumeroPtBr(quantidadeTexto);
    const valorTarifa = parseNumeroPtBr(tarifaTexto);
    const kgPorSaca = parseNumeroPtBr(kgPorSacaTexto) ?? 60;
    const custosAdicionais = parseNumeroPtBr(custosAdicionaisTexto) ?? 0;

    if (quantidade === null || valorTarifa === null) {
      return { resultado: null, erro: null };
    }

    try {
      const res = calcularFreteAgricola({
        quantidade,
        unidadeQuantidade,
        valorTarifa,
        tipoTarifa,
        kgPorSaca,
        custosAdicionais,
      });
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro no cálculo do frete",
      };
    }
  }, [
    quantidadeTexto,
    unidadeQuantidade,
    tarifaTexto,
    tipoTarifa,
    kgPorSacaTexto,
    custosAdicionaisTexto,
  ]);

  const handleLimpar = () => {
    setQuantidadeTexto("");
    setUnidadeQuantidade("TONELADAS");
    setTarifaTexto("");
    setCustosAdicionaisTexto("0");
    setKgPorSacaTexto("60");
  };

  return (
    <Card className="border border-border/80 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/60">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">
                Estimativa de Frete Agrícola
              </CardTitle>
              <CardDescription className="text-xs">
                Simulação de custo total de transporte, frete por saca e frete por tonelada com despesas acessórias.
              </CardDescription>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px] hidden sm:inline-flex">
            Offline
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Aviso de Não Vinculação */}
        <div className="p-2.5 rounded-sm border border-amber-500/30 bg-amber-500/5 text-xs text-foreground flex items-start gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-[11px] text-muted-foreground leading-relaxed">
            <span className="font-semibold text-foreground">Aviso de Simulação:</span> Esta ferramenta realiza cálculos matemáticos baseados exclusivamente nas tarifas e valores informados pelo produtor. Não consulta tabelas de fretes ou ANTT e não constitui cotação comercial vinculante.
          </div>
        </div>

        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="quantidade-frete">Carga a Transportar</Label>
            <Input
              id="quantidade-frete"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 32"
              value={quantidadeTexto}
              onChange={(e) => setQuantidadeTexto(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="unidade-carga">Unidade da Carga</Label>
            <select
              id="unidade-carga"
              value={unidadeQuantidade}
              onChange={(e) => setUnidadeQuantidade(e.target.value as UnidadeMassaAgricola)}
              className="flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="TONELADAS">Toneladas métricas (t)</option>
              <option value="SACAS">Sacas agrícolas</option>
              <option value="QUILOGRAMAS">Quilogramas (kg)</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="kg-saca-frete">Peso por Saca (kg)</Label>
            <Input
              id="kg-saca-frete"
              type="text"
              inputMode="decimal"
              placeholder="60"
              value={kgPorSacaTexto}
              onChange={(e) => setKgPorSacaTexto(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="tipo-tarifa">Base da Tarifa</Label>
            <select
              id="tipo-tarifa"
              value={tipoTarifa}
              onChange={(e) => setTipoTarifa(e.target.value as TipoTarifaFrete)}
              className="flex h-8 w-full rounded-sm border border-border bg-background px-2.5 py-1 text-xs text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="POR_TONELADA">R$ por Tonelada (R$/t)</option>
              <option value="POR_SACA">R$ por Saca (R$/saca)</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="valor-tarifa">
              Valor da Tarifa ({tipoTarifa === "POR_TONELADA" ? "R$/t" : "R$/saca"})
            </Label>
            <Input
              id="valor-tarifa"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 120,00"
              value={tarifaTexto}
              onChange={(e) => setTarifaTexto(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="custos-adicionais">Custos Adicionais Opcionais (R$)</Label>
            <Input
              id="custos-adicionais"
              type="text"
              inputMode="decimal"
              placeholder="Pedágio, seguro, descarga"
              value={custosAdicionaisTexto}
              onChange={(e) => setCustosAdicionaisTexto(e.target.value)}
            />
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
              Estimativa do Frete
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Valor Total Estimado</span>
                <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400 block mt-1">
                  {formatarMoeda(resultado.totalFrete)}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Base: {formatarMoeda(resultado.freteBase)} + Extras: {formatarMoeda(resultado.custosAdicionais)}
                </span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Custo Efetivo por Tonelada</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarMoeda(resultado.custoEfetivoPorTonelada)} / t
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Total ÷ {formatarNumero(resultado.massaToneladas, 2)} t
                </span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Custo Efetivo por Saca</span>
                <span className="text-base sm:text-lg font-bold text-foreground block mt-1">
                  {formatarMoeda(resultado.custoEfetivoPorSaca)} / saca
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Total ÷ {formatarNumero(resultado.totalSacas, 1)} sacas
                </span>
              </div>

              <div className="p-3 rounded-sm bg-muted/40 border border-border/60">
                <span className="text-[11px] text-muted-foreground block">Volume da Carga</span>
                <span className="text-sm font-semibold text-foreground block mt-1">
                  {formatarNumero(resultado.massaToneladas, 2)} t ({formatarNumero(resultado.totalSacas, 0)} sacas)
                </span>
                <span className="text-[10px] text-muted-foreground">
                  Total líquido: {formatarNumero(resultado.massaKg, 0)} kg
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Memória de Cálculo e Ações */}
        <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-t border-border/60">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span>Fórmula: Total = (Quantidade normalizada × Tarifa) + Custos Adicionais</span>
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
