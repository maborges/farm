"use client";

import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertTriangle,
  Calculator,
  CheckCircle2,
  Shield,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { apiFetch } from "@/lib/api";

export interface CenarioSensibilidadeCambio {
  cenario: string;
  taxa_cambio: number;
  preco_estimado_sc: number;
  vpl_safra: number;
  supera_tma: boolean;
}

export interface PrecoEquilibrioTmaOutput {
  preco_equilibrio_contabil_sc: number;
  preco_equilibrio_tma_sc: number;
  premio_custo_capital_sc: number;
  fator_capitalizacao_tma: number;
  vpl_safra_atual: number;
  margem_sobre_tma_sc: number;
  acao_hedge_recomendada: "TRAVAR_MARGEM" | "ATENCAO_TMA" | "DEFESA_CAIXA";
  mensagem_recomendacao: string;
  sensibilidade_cambio: CenarioSensibilidadeCambio[];
}

function formatBRL(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function PrecoEquilibrioTmaCard({
  defaultProducaoSc,
  defaultCoberturaPct,
  defaultTmaAa,
}: {
  defaultProducaoSc?: number;
  defaultCoberturaPct?: number;
  defaultTmaAa?: number;
}) {
  const [custoTotal, setCustoTotal] = useState<number>(
    defaultProducaoSc && defaultProducaoSc > 0 ? Math.round(defaultProducaoSc * 95) : 1_000_000
  );
  const [producaoSc, setProducaoSc] = useState<number>(
    defaultProducaoSc && defaultProducaoSc > 0 ? Math.round(defaultProducaoSc) : 10_000
  );
  const [tmaAa, setTmaAa] = useState<number>(defaultTmaAa ?? 12.0);
  const [cicloMeses, setCicloMeses] = useState<number>(8);
  const [precoMercado, setPrecoMercado] = useState<number>(125);
  const [cambioBase, setCambioBase] = useState<number>(5.8);
  const [jaTravadoPct, setJaTravadoPct] = useState<number>(
    defaultCoberturaPct !== undefined ? Number(defaultCoberturaPct.toFixed(1)) : 20
  );

  const simular = useMutation<PrecoEquilibrioTmaOutput, Error, void>({
    mutationFn: () =>
      apiFetch<PrecoEquilibrioTmaOutput>("/financeiro/viabilidade/preco-equilibrio-tma", {
        method: "POST",
        body: JSON.stringify({
          custo_total_safra: custoTotal,
          producao_estimada_sc: producaoSc,
          tma_aa: tmaAa,
          prazo_ciclo_meses: cicloMeses,
          preco_mercado_atual_sc: precoMercado,
          taxa_cambio_base: cambioBase,
          percentual_ja_travado: jaTravadoPct,
        }),
      }),
    onError: (err) => {
      toast.error(err.message || "Erro ao calcular preço de equilíbrio por TMA.");
    },
  });

  const res = simular.data;

  return (
    <Card className="rounded-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Shield className="size-4 text-primary" />
              Preço de Equilíbrio Econômico (TMA) e Trava Cambial
            </CardTitle>
            <CardDescription className="text-xs">
              Compare o ponto de empate contábil vs. o preço necessário para remunerar a TMA (VPL = 0) com sensibilidade ao dólar.
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-sm shrink-0"
            disabled={simular.isPending || custoTotal <= 0 || producaoSc <= 0 || precoMercado <= 0}
            onClick={() => simular.mutate()}
          >
            <Calculator className="size-3.5 mr-1.5" />
            {simular.isPending ? "Calculando..." : "Calcular Equilíbrio TMA"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          <div className="space-y-1">
            <Label className="text-xs">Custo Safra (R$)</Label>
            <Input
              type="number"
              min="1"
              step="1000"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={custoTotal}
              onChange={(e) => setCustoTotal(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Produção (sc)</Label>
            <Input
              type="number"
              min="1"
              step="100"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={producaoSc}
              onChange={(e) => setProducaoSc(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">TMA (% a.a.)</Label>
            <Input
              type="number"
              min="0"
              step="0.25"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={tmaAa}
              onChange={(e) => setTmaAa(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Ciclo (meses)</Label>
            <Input
              type="number"
              min="1"
              max="60"
              step="1"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={cicloMeses}
              onChange={(e) => setCicloMeses(Number(e.target.value) || 1)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Preço Atual (R$/sc)</Label>
            <Input
              type="number"
              min="1"
              step="1"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={precoMercado}
              onChange={(e) => setPrecoMercado(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Câmbio Base (R$/US$)</Label>
            <Input
              type="number"
              min="0.1"
              step="0.05"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={cambioBase}
              onChange={(e) => setCambioBase(Number(e.target.value) || 0)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Já Travado (%)</Label>
            <Input
              type="number"
              min="0"
              max="100"
              step="5"
              className="h-8 text-xs rounded-sm tabular-nums"
              value={jaTravadoPct}
              onChange={(e) => setJaTravadoPct(Number(e.target.value) || 0)}
            />
          </div>
        </div>

        {res && (
          <div className="space-y-4 pt-1">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="rounded-sm border p-3">
                <p className="text-[11px] text-muted-foreground">Equilíbrio Contábil</p>
                <p className="text-lg font-bold tabular-nums">
                  {formatBRL(res.preco_equilibrio_contabil_sc)}/sc
                </p>
              </div>
              <div className="rounded-sm border p-3 border-primary/30 bg-primary/5">
                <p className="text-[11px] text-muted-foreground">Equilíbrio Econômico (TMA)</p>
                <p className="text-lg font-bold tabular-nums text-primary">
                  {formatBRL(res.preco_equilibrio_tma_sc)}/sc
                </p>
              </div>
              <div className="rounded-sm border p-3">
                <p className="text-[11px] text-muted-foreground">Custo de Capital / sc</p>
                <p className="text-lg font-bold tabular-nums">
                  +{formatBRL(res.premio_custo_capital_sc)}/sc
                </p>
              </div>
              <div className="rounded-sm border p-3">
                <p className="text-[11px] text-muted-foreground">VPL da Safra (Atual)</p>
                <p
                  className={`text-lg font-bold tabular-nums ${
                    res.vpl_safra_atual >= 0
                      ? "text-emerald-700 dark:text-emerald-300"
                      : "text-destructive"
                  }`}
                >
                  {formatBRL(res.vpl_safra_atual)}
                </p>
              </div>
            </div>

            <Alert
              variant={
                res.acao_hedge_recomendada === "TRAVAR_MARGEM"
                  ? "success"
                  : res.acao_hedge_recomendada === "ATENCAO_TMA"
                    ? "warning"
                    : "destructive"
              }
            >
              {res.acao_hedge_recomendada === "TRAVAR_MARGEM" ? (
                <CheckCircle2 />
              ) : res.acao_hedge_recomendada === "ATENCAO_TMA" ? (
                <AlertTriangle />
              ) : (
                <ShieldAlert />
              )}
              <AlertTitle className="text-xs font-semibold flex items-center gap-2">
                Recomendação de Hedge Comercial
                <Badge variant="outline" className="rounded-sm text-[10px]">
                  {res.acao_hedge_recomendada === "TRAVAR_MARGEM"
                    ? "Travar Margem (Acima TMA)"
                    : res.acao_hedge_recomendada === "ATENCAO_TMA"
                      ? "Abaixo da TMA"
                      : "Defesa de Caixa"}
                </Badge>
              </AlertTitle>
              <AlertDescription className="text-xs">
                {res.mensagem_recomendacao}
              </AlertDescription>
            </Alert>

            <div className="rounded-sm border overflow-x-auto">
              <Table className="text-xs">
                <TableHeader>
                  <TableRow>
                    <TableHead className="h-8">Cenário Cambial</TableHead>
                    <TableHead className="h-8">Câmbio (R$/US$)</TableHead>
                    <TableHead className="h-8">Preço Projetado</TableHead>
                    <TableHead className="h-8">VPL da Safra</TableHead>
                    <TableHead className="h-8">Meta TMA</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {res.sensibilidade_cambio.map((item) => (
                    <TableRow key={item.cenario}>
                      <TableCell className="font-medium">{item.cenario}</TableCell>
                      <TableCell className="tabular-nums">R$ {item.taxa_cambio.toFixed(2)}</TableCell>
                      <TableCell className="tabular-nums">{formatBRL(item.preco_estimado_sc)}/sc</TableCell>
                      <TableCell
                        className={`tabular-nums font-semibold ${
                          item.vpl_safra >= 0
                            ? "text-emerald-700 dark:text-emerald-300"
                            : "text-destructive"
                        }`}
                      >
                        {formatBRL(item.vpl_safra)}
                      </TableCell>
                      <TableCell>
                        {item.supera_tma ? (
                          <Badge className="rounded-sm bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px]">
                            Supera TMA
                          </Badge>
                        ) : (
                          <Badge className="rounded-sm bg-destructive/15 text-destructive border-destructive/30 text-[10px]">
                            Abaixo TMA
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
