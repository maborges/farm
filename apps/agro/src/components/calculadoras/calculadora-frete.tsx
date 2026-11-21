"use client";

import React, { useState, useMemo } from "react";
import { Truck, RotateCcw, AlertCircle, Info, ShieldAlert, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
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
import { cn } from "@/lib/utils";

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
    <Card>
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
            <Truck className="size-5" />
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
        <CardAction>
          <Badge variant="outline" className="hidden sm:inline-flex">
            Offline
          </Badge>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Aviso de Não Vinculação */}
        <Alert variant="warning">
          <ShieldAlert className="size-4" />
          <AlertTitle className="text-xs">Aviso de Simulação</AlertTitle>
          <AlertDescription className="text-xs">
            Esta ferramenta realiza cálculos matemáticos baseados exclusivamente nas tarifas e valores informados pelo produtor. Não consulta tabelas de fretes ou ANTT e não constitui cotação comercial vinculante.
          </AlertDescription>
        </Alert>

        {/* Formulário de Entradas */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quantidade-frete" className="text-xs">Carga a Transportar</Label>
            <Input
              id="quantidade-frete"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 32"
              value={quantidadeTexto}
              onChange={(e) => setQuantidadeTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="unidade-carga" className="text-xs">Unidade da Carga</Label>
            <select
              id="unidade-carga"
              value={unidadeQuantidade}
              onChange={(e) => setUnidadeQuantidade(e.target.value as UnidadeMassaAgricola)}
              className={cn(inputBaseClassName, "text-xs")}
            >
              <option value="TONELADAS">Toneladas métricas (t)</option>
              <option value="SACAS">Sacas agrícolas</option>
              <option value="QUILOGRAMAS">Quilogramas (kg)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="kg-saca-frete" className="text-xs">Peso por Saca (kg)</Label>
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
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tipo-tarifa" className="text-xs">Base da Tarifa</Label>
            <select
              id="tipo-tarifa"
              value={tipoTarifa}
              onChange={(e) => setTipoTarifa(e.target.value as TipoTarifaFrete)}
              className={cn(inputBaseClassName, "text-xs")}
            >
              <option value="POR_TONELADA">R$ por Tonelada (R$/t)</option>
              <option value="POR_SACA">R$ por Saca (R$/saca)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="valor-tarifa" className="text-xs">
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

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="custos-adicionais" className="text-xs">Custos Adicionais Opcionais (R$)</Label>
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
              Estimativa do Frete
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Valor Total Estimado</span>
                  <span className="text-base sm:text-lg font-bold text-emerald-700 dark:text-emerald-400">
                    {formatarMoeda(resultado.totalFrete)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Base: {formatarMoeda(resultado.freteBase)} + Extras: {formatarMoeda(resultado.custosAdicionais)}
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Custo Efetivo por Tonelada</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarMoeda(resultado.custoEfetivoPorTonelada)} / t
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Total ÷ {formatarNumero(resultado.massaToneladas, 2)} t
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Custo Efetivo por Saca</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarMoeda(resultado.custoEfetivoPorSaca)} / saca
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Total ÷ {formatarNumero(resultado.totalSacas, 1)} sacas
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Volume da Carga</span>
                  <span className="text-sm font-semibold text-foreground">
                    {formatarNumero(resultado.massaToneladas, 2)} t ({formatarNumero(resultado.totalSacas, 0)} sacas)
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Total líquido: {formatarNumero(resultado.massaKg, 0)} kg
                  </span>
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
            <span>Fórmula: Total = (Quantidade normalizada × Tarifa) + Custos Adicionais</span>
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
