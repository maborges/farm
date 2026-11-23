"use client";

import React, { useState, useMemo } from "react";
import { DollarSign, RotateCcw, AlertCircle, Info, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  calcularCustoEquilibrio,
  type CustoEquilibrioResultado,
} from "@/lib/calculadoras/core";
import {
  parseNumeroPtBr,
  formatarNumero,
  formatarMoeda,
  formatarMoedaOuNaoCalculavel,
  formatarNumeroOuNaoCalculavel,
  formatarPercentualOuNaoCalculavel,
  detectarEntradaAmbiguaPtBr,
} from "@/lib/calculadoras/format";

export function CalculadoraCustoHectare() {
  const [areaTexto, setAreaTexto] = useState<string>("100");
  const [custoTotalTexto, setCustoTotalTexto] = useState<string>("350000");
  const [produtividadeTexto, setProdutividadeTexto] = useState<string>("60");
  const [precoVendaTexto, setPrecoVendaTexto] = useState<string>("115");

  const avisoAmbiguo = useMemo(() => {
    return (
      detectarEntradaAmbiguaPtBr(areaTexto) ||
      detectarEntradaAmbiguaPtBr(custoTotalTexto) ||
      detectarEntradaAmbiguaPtBr(produtividadeTexto) ||
      detectarEntradaAmbiguaPtBr(precoVendaTexto)
    );
  }, [areaTexto, custoTotalTexto, produtividadeTexto, precoVendaTexto]);

  const { resultado, erro } = useMemo<{
    resultado: CustoEquilibrioResultado | null;
    erro: string | null;
  }>(() => {
    const areaHectares = parseNumeroPtBr(areaTexto);
    const custoTotal = parseNumeroPtBr(custoTotalTexto);
    const produtividadeEsperadaPorHa = parseNumeroPtBr(produtividadeTexto);
    const precoVendaUnitario = parseNumeroPtBr(precoVendaTexto);

    if (
      areaHectares === null ||
      custoTotal === null ||
      produtividadeEsperadaPorHa === null ||
      precoVendaUnitario === null
    ) {
      return { resultado: null, erro: null };
    }

    try {
      const res = calcularCustoEquilibrio({
        areaHectares,
        custoTotal,
        produtividadeEsperadaPorHa,
        precoVendaUnitario,
      });
      return { resultado: res, erro: null };
    } catch (err) {
      return {
        resultado: null,
        erro: err instanceof Error ? err.message : "Erro no cálculo",
      };
    }
  }, [areaTexto, custoTotalTexto, produtividadeTexto, precoVendaTexto]);

  const handleLimpar = () => {
    setAreaTexto("");
    setCustoTotalTexto("");
    setProdutividadeTexto("");
    setPrecoVendaTexto("");
  };

  return (
    <Card>
      <CardHeader className="border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-sm bg-emerald-600/10 text-emerald-700 dark:text-emerald-400">
            <DollarSign className="size-5" />
          </div>
          <div>
            <CardTitle className="text-base font-semibold">
              Custo por Hectare e Ponto de Equilíbrio
            </CardTitle>
            <CardDescription className="text-xs">
              Planejamento financeiro de safra: custo/ha, custo unitário, receita bruta, margem e metas mínimas de equilíbrio (break-even).
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
        <div className="grid grid-cols-1 @[480px]/main:grid-cols-2 @[780px]/main:grid-cols-4 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="area-ha" className="text-xs">Área Cultivada (ha)</Label>
            <Input
              id="area-ha"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 100"
              value={areaTexto}
              onChange={(e) => setAreaTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="custo-total" className="text-xs">Custo Total de Produção (R$)</Label>
            <Input
              id="custo-total"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 350.000,00"
              value={custoTotalTexto}
              onChange={(e) => setCustoTotalTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="prod-esperada" className="text-xs">Produtividade Esperada (sc/ha)</Label>
            <Input
              id="prod-esperada"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 60"
              value={produtividadeTexto}
              onChange={(e) => setProdutividadeTexto(e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="preco-venda" className="text-xs">Preço de Venda Estimado (R$/sc)</Label>
            <Input
              id="preco-venda"
              type="text"
              inputMode="decimal"
              placeholder="Ex: 115,00"
              value={precoVendaTexto}
              onChange={(e) => setPrecoVendaTexto(e.target.value)}
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
          <div className="flex flex-col gap-3">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Diagnóstico Econômico da Lavoura
            </h4>

            {/* Linha 1: Custos e Produção */}
            <div className="grid grid-cols-1 @[560px]/main:grid-cols-3 gap-2.5">
              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Custo Médio por Hectare</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarMoeda(resultado.custoPorHectare)} / ha
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Custo total ÷ {formatarNumero(resultado.areaHectares, 1)} ha
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Produção Total Estimada</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarNumero(resultado.producaoTotalEsperada, 0)} sacas
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {formatarNumero(resultado.areaHectares, 0)} ha × {produtividadeTexto} sc/ha
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Custo de Produção por Saca</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarMoedaOuNaoCalculavel(resultado.custoPorUnidadeProduzida, "/ saca")}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {resultado.custoPorUnidadeProduzida !== null
                      ? "Custo total ÷ total de sacas"
                      : "Exige produção total maior que zero"}
                  </span>
                </CardContent>
              </Card>
            </div>

            {/* Linha 2: Receita, Resultado Estimado e Margem */}
            <div className="grid grid-cols-1 @[560px]/main:grid-cols-3 gap-2.5">
              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Receita Bruta Estimada</span>
                  <span className="text-base sm:text-lg font-bold text-foreground">
                    {formatarMoeda(resultado.receitaBrutaEstimada)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">Faturamento bruto sem deduções</span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-muted-foreground">
                      Resultado estimado (receita menos custos informados)
                    </span>
                    {resultado.resultadoEstimado >= 0 ? (
                      <TrendingUp className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <TrendingDown className="size-3.5 text-destructive" />
                    )}
                  </div>
                  <span
                    className={`text-base sm:text-lg font-bold ${
                      resultado.resultadoEstimado >= 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-destructive"
                    }`}
                  >
                    {formatarMoeda(resultado.resultadoEstimado)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Receita estimada menos os custos manuais declarados
                  </span>
                </CardContent>
              </Card>

              <Card variant="muted" size="sm">
                <CardContent className="flex flex-col gap-0.5">
                  <span className="text-[11px] text-muted-foreground">Margem sobre Receita Bruta</span>
                  <span
                    className={`text-base sm:text-lg font-bold ${
                      (resultado.margemLucroPct ?? 0) >= 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-destructive"
                    }`}
                  >
                    {formatarPercentualOuNaoCalculavel(resultado.margemLucroPct, 1)}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {resultado.margemLucroPct !== null
                      ? "Resultado ÷ Receita Bruta estimada"
                      : "Exige receita bruta maior que zero"}
                  </span>
                </CardContent>
              </Card>
            </div>

            {/* Linha 3: Ponto de Equilíbrio (Break-Even) */}
            <Card variant="success" size="sm">
              <CardContent className="flex flex-col gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="recommendation">
                    Metas de Equilíbrio Estimado (Break-Even)
                  </Badge>
                  <span className="text-[11px]">Condição para cobrir custos informados (Resultado = R$ 0)</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <span className="text-[11px] block">
                      Preço de Equilíbrio (Preço Mínimo de Venda):
                    </span>
                    <span className="text-base font-bold text-foreground block">
                      {formatarMoedaOuNaoCalculavel(resultado.precoDeEquilibrio, "/ saca")}
                    </span>
                    <span className="text-[10px] opacity-85">
                      {resultado.precoDeEquilibrio !== null
                        ? `Preço necessário para a produtividade de ${produtividadeTexto} sc/ha`
                        : "Não calculável quando a produção total for zero"}
                    </span>
                  </div>

                  <div>
                    <span className="text-[11px] block">
                      Produtividade de Equilíbrio (Mínimo a Colher):
                    </span>
                    <span className="text-base font-bold text-foreground block">
                      {formatarNumeroOuNaoCalculavel(resultado.produtividadeDeEquilibrioPorHa, 2, "sc / ha")}
                    </span>
                    <span className="text-[10px] opacity-85">
                      {resultado.producaoTotalDeEquilibrio !== null
                        ? `Total mínimo da fazenda: ${formatarNumero(resultado.producaoTotalDeEquilibrio, 0)} sacas ao preço de ${formatarMoeda(parseNumeroPtBr(precoVendaTexto))}`
                        : "Não calculável quando o preço de venda for zero"}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Separator />

        {/* Memória de Cálculo e Ações */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Info className="size-3.5 text-muted-foreground shrink-0" />
            <span>Fórmulas: Custo/ha = Custo ÷ Área | Break-Even Preço = Custo ÷ Produção | Break-Even Prod = Custo/ha ÷ Preço</span>
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
