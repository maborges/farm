"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";

export interface FluxoCaixaPeriodo {
  periodo: string;
  receitas_realizadas: number;
  despesas_realizadas: number;
  saldo_realizado: number;
  receitas_previstas: number;
  despesas_previstas: number;
  saldo_previsto: number;
  saldo_acumulado: number;
  saldo_projetado: number;
  saldo_acumulado_projetado: number;
  em_vale_caixa: boolean;
}

export interface AnaliseDecisaoReativa {
  possui_vale_caixa: boolean;
  pior_vale_valor: number;
  mes_pior_vale: string | null;
  primeiro_mes_vale: string | null;
  meses_em_deficit: number;
  dias_antecedencia_primeiro_vale: number | null;
  saldo_inicial_considerado: number;
  taxa_credito_planejado_aa: number;
  taxa_credito_reativo_aa: number;
  custo_juros_planejado: number;
  custo_juros_reativo: number;
  custo_decisao_reativa: number;
  nivel_risco: "SAUDAVEL" | "ALERTA" | "CRITICO";
  recomendacao: string;
}

export interface FluxoCaixaTotais {
  total_receitas_realizadas: number;
  total_despesas_realizadas: number;
  total_saldo_realizado: number;
  total_receitas_previstas: number;
  total_despesas_previstas: number;
  total_saldo_previsto: number;
}

export interface FluxoCaixaResponse {
  data_inicio: string;
  data_fim: string;
  unidade_produtiva_id?: string | null;
  periodos: FluxoCaixaPeriodo[];
  totais: FluxoCaixaTotais;
  analise_decisao_reativa?: AnaliseDecisaoReativa | null;
}

function formatBRL(v: number | undefined | null): string {
  if (v === undefined || v === null || Number.isNaN(v)) return "R$ 0,00";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatMesLabel(isoDate: string): string {
  const parsed = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("pt-BR", { month: "short", year: "numeric" });
}

function computeHorizonDates(monthsAhead: number): { inicio: string; fim: string } {
  const hoje = new Date();
  const start = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  const end = new Date(hoje.getFullYear(), hoje.getMonth() + monthsAhead, 0);
  const toIso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { inicio: toIso(start), fim: toIso(end) };
}

export function FluxoCaixaClient({
  initialFluxo,
  initialInicio,
  initialFim,
  initialActiveFazendaId,
}: {
  initialFluxo: FluxoCaixaResponse | null;
  initialInicio: string;
  initialFim: string;
  initialActiveFazendaId?: string;
}) {
  const activeFazendaId = useAppStore((s) => s.activeFazendaId);
  const effectiveFazendaId = activeFazendaId ?? initialActiveFazendaId ?? null;

  const [inicio, setInicio] = useState(initialInicio);
  const [fim, setFim] = useState(initialFim);
  const [saldoInicial, setSaldoInicial] = useState<number>(0);
  const [taxaPlanejadoAa, setTaxaPlanejadoAa] = useState<number>(8.5);
  const [taxaReativoAa, setTaxaReativoAa] = useState<number>(24.0);

  const isDefaultQuery =
    inicio === initialInicio &&
    fim === initialFim &&
    saldoInicial === 0 &&
    taxaPlanejadoAa === 8.5 &&
    taxaReativoAa === 24.0 &&
    effectiveFazendaId === (initialActiveFazendaId ?? null);

  const { data: fluxo, isLoading } = useQuery<FluxoCaixaResponse>({
    queryKey: [
      "financeiro",
      "fluxo-caixa",
      inicio,
      fim,
      saldoInicial,
      taxaPlanejadoAa,
      taxaReativoAa,
      effectiveFazendaId,
    ],
    queryFn: () => {
      const qs = new URLSearchParams({
        data_inicio: inicio,
        data_fim: fim,
        saldo_inicial: String(saldoInicial),
        taxa_credito_planejado_aa: String(taxaPlanejadoAa),
        taxa_credito_reativo_aa: String(taxaReativoAa),
      });
      if (effectiveFazendaId) qs.set("unidade_produtiva_id", effectiveFazendaId);
      return apiFetch<FluxoCaixaResponse>(`/relatorios/fluxo-caixa?${qs.toString()}`);
    },
    initialData: isDefaultQuery && initialFluxo ? initialFluxo : undefined,
    placeholderData: (prev) => prev,
  });

  const periodos = useMemo(() => fluxo?.periodos ?? [], [fluxo]);
  const analise = fluxo?.analise_decisao_reativa ?? null;

  const chartData = useMemo(
    () =>
      periodos.map((p) => ({
        mes: formatMesLabel(p.periodo),
        saldo_projetado: p.saldo_projetado,
        saldo_acumulado_projetado: p.saldo_acumulado_projetado,
      })),
    [periodos]
  );

  const ultimoAcumuladoProjetado =
    periodos.length > 0 ? periodos[periodos.length - 1].saldo_acumulado_projetado : 0;

  const applyHorizon = (monthsCount: number) => {
    const next = computeHorizonDates(monthsCount);
    setInicio(next.inicio);
    setFim(next.fim);
  };

  const kpis = fluxo
    ? [
        {
          label: "Receitas Realizadas",
          value: fluxo.totais.total_receitas_realizadas,
          tone: "border-l-emerald-500 text-emerald-700 dark:text-emerald-300",
        },
        {
          label: "Despesas Realizadas",
          value: fluxo.totais.total_despesas_realizadas,
          tone: "border-l-destructive text-destructive",
        },
        {
          label: "Saldo Previsto (A Vencer)",
          value: fluxo.totais.total_saldo_previsto,
          tone:
            fluxo.totais.total_saldo_previsto >= 0
              ? "border-l-amber-500 text-amber-700 dark:text-amber-300"
              : "border-l-destructive text-destructive",
        },
        {
          label: "Acumulado Projetado Final",
          value: ultimoAcumuladoProjetado,
          tone:
            ultimoAcumuladoProjetado >= 0
              ? "border-l-primary text-primary"
              : "border-l-destructive text-destructive",
        },
      ]
    : [];

  const columns: ColumnDef<FluxoCaixaPeriodo>[] = [
    {
      id: "periodo",
      header: "Mês",
      accessorKey: "periodo",
      sortable: true,
      exportFormat: (v) => formatMesLabel(String(v)),
      cell: (v) => <span className="font-medium text-xs capitalize">{formatMesLabel(String(v))}</span>,
    },
    {
      id: "receitas_realizadas",
      header: "Entradas Real.",
      accessorKey: "receitas_realizadas",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span className="tabular-nums text-xs text-emerald-700 dark:text-emerald-300">
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "despesas_realizadas",
      header: "Saídas Real.",
      accessorKey: "despesas_realizadas",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => <span className="tabular-nums text-xs text-destructive">{formatBRL(Number(v))}</span>,
    },
    {
      id: "receitas_previstas",
      header: "Entradas Prev.",
      accessorKey: "receitas_previstas",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => <span className="tabular-nums text-xs text-muted-foreground">{formatBRL(Number(v))}</span>,
    },
    {
      id: "despesas_previstas",
      header: "Saídas Prev.",
      accessorKey: "despesas_previstas",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => <span className="tabular-nums text-xs text-muted-foreground">{formatBRL(Number(v))}</span>,
    },
    {
      id: "saldo_projetado",
      header: "Saldo Projetado",
      accessorKey: "saldo_projetado",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span
          className={`tabular-nums text-xs font-medium ${
            Number(v) >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-destructive"
          }`}
        >
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "saldo_acumulado_projetado",
      header: "Acumulado Projetado",
      accessorKey: "saldo_acumulado_projetado",
      sortable: true,
      exportFormat: (v) => formatBRL(Number(v)),
      cell: (v) => (
        <span
          className={`tabular-nums text-xs font-semibold ${
            Number(v) >= 0 ? "text-primary" : "text-destructive"
          }`}
        >
          {formatBRL(Number(v))}
        </span>
      ),
    },
    {
      id: "em_vale_caixa",
      header: "Situação",
      accessorKey: "em_vale_caixa",
      sortable: true,
      exportFormat: (v) => (v ? "Vale de Caixa" : "Saudável"),
      cell: (v) =>
        v ? (
          <Badge className="rounded-sm bg-destructive/15 text-destructive border-destructive/30 text-[10px]">
            Vale de Caixa
          </Badge>
        ) : (
          <Badge className="rounded-sm bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px]">
            Saudável
          </Badge>
        ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Fluxo de Caixa e Capital de Giro"
        description="Realizado, previsto a vencer, detecção de vales de caixa e custo da decisão reativa."
        breadcrumbs={[
          { label: "Financeiro", href: "/dashboard/financeiro" },
          { label: "Fluxo de Caixa" },
        ]}
        icon={<TrendingUp className="text-primary" size={22} />}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => applyHorizon(1)}>
              <Calendar className="size-3.5 mr-1.5" />
              Mês Atual
            </Button>
            <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => applyHorizon(6)}>
              <Calendar className="size-3.5 mr-1.5" />
              6 Meses
            </Button>
            <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => applyHorizon(12)}>
              <Calendar className="size-3.5 mr-1.5" />
              12 Meses
            </Button>
          </div>
        }
      />

      {/* Parâmetros de Horizonte e Simulação de Capital de Giro */}
      <Card className="rounded-sm">
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">De</Label>
              <Input
                type="date"
                value={inicio}
                onChange={(e) => setInicio(e.target.value)}
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Até</Label>
              <Input
                type="date"
                value={fim}
                onChange={(e) => setFim(e.target.value)}
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Saldo Inicial em Caixa (R$)</Label>
              <Input
                type="number"
                step="1000"
                value={saldoInicial}
                onChange={(e) => setSaldoInicial(Number(e.target.value) || 0)}
                className="h-8 text-xs rounded-sm tabular-nums"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Crédito Planejado (% a.a.)</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                value={taxaPlanejadoAa}
                onChange={(e) => setTaxaPlanejadoAa(Number(e.target.value) || 0)}
                className="h-8 text-xs rounded-sm tabular-nums"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Crédito Reativo (% a.a.)</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                value={taxaReativoAa}
                onChange={(e) => setTaxaReativoAa(Number(e.target.value) || 0)}
                className="h-8 text-xs rounded-sm tabular-nums"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diagnóstico de Decisão Reativa e Vale de Capital de Giro */}
      {analise && (
        <Alert
          variant={
            analise.nivel_risco === "CRITICO"
              ? "destructive"
              : analise.nivel_risco === "ALERTA"
                ? "warning"
                : "success"
          }
        >
          {analise.nivel_risco === "CRITICO" ? (
            <ShieldAlert />
          ) : analise.nivel_risco === "ALERTA" ? (
            <AlertTriangle />
          ) : (
            <CheckCircle2 />
          )}
          <div className="flex flex-col gap-3 w-full lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <AlertTitle className="text-sm font-semibold flex items-center gap-2">
                Radar de Custo da Decisão Reativa
                <Badge variant="outline" className="rounded-sm text-[10px]">
                  {analise.nivel_risco === "SAUDAVEL"
                    ? "Caixa Saudável"
                    : analise.nivel_risco === "ALERTA"
                      ? "Vale Previsto (Planejar)"
                      : "Déficit Imediato"}
                </Badge>
              </AlertTitle>
              <AlertDescription className="text-xs">
                {analise.recomendacao}
              </AlertDescription>
              {analise.possui_vale_caixa && (
                <div className="flex flex-wrap gap-4 pt-1 text-xs">
                  <span>
                    Pior Vale: <strong className="text-destructive">{formatBRL(analise.pior_vale_valor)}</strong>
                  </span>
                  <span>
                    Meses em déficit: <strong>{analise.meses_em_deficit}</strong>
                  </span>
                  <span>
                    Juros Planejado ({analise.taxa_credito_planejado_aa}%):{" "}
                    <strong>{formatBRL(analise.custo_juros_planejado)}</strong>
                  </span>
                  <span>
                    Juros Reativo ({analise.taxa_credito_reativo_aa}%):{" "}
                    <strong className="text-destructive">{formatBRL(analise.custo_juros_reativo)}</strong>
                  </span>
                  <span>
                    Economia Planejando:{" "}
                    <strong className="text-emerald-700 dark:text-emerald-300">
                      {formatBRL(analise.custo_decisao_reativa)}
                    </strong>
                  </span>
                </div>
              )}
            </div>
            <Button type="button" variant="outline" size="sm" className="rounded-sm shrink-0" asChild>
              <Link href="/dashboard/financeiro/viabilidade">
                <ArrowUpRight className="size-3.5 mr-1.5" />
                Avaliar Viabilidade (TMA)
              </Link>
            </Button>
          </div>
        </Alert>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="rounded-sm">
                <CardHeader className="pb-2">
                  <Skeleton className="h-3 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-28" />
                </CardContent>
              </Card>
            ))
          : kpis.map((k) => (
              <Card key={k.label} className={`rounded-sm border-l-4 ${k.tone}`}>
                <CardHeader className="pb-1">
                  <CardTitle className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {k.label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold tabular-nums ${k.tone}`}>{formatBRL(k.value)}</div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Gráfico Projetado */}
      {chartData.length > 0 && (
        <Card className="rounded-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">
              Curva de Caixa Projetada e Vales de Capital de Giro
            </CardTitle>
            <CardDescription className="text-xs">
              Saldo mensal líquido (realizado + previsto) e evolução do caixa acumulado partindo do saldo inicial.
            </CardDescription>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val: number | string) => formatBRL(Number(val))} />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="3 3" />
                <Bar dataKey="saldo_projetado" name="Saldo Mensal Projetado" fill="#0ea5e9" radius={[2, 2, 0, 0]} />
                <Line
                  type="monotone"
                  dataKey="saldo_acumulado_projetado"
                  name="Acumulado Projetado"
                  stroke="#10b981"
                  strokeWidth={2.5}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Tabela DataTable Mensal */}
      <div className="space-y-2">
        <h2 className="text-sm font-semibold">Detalhamento Mensal (Realizado, Previsto e Projeção de Caixa)</h2>
        <DataTable
          data={periodos}
          columns={columns}
          isLoading={isLoading}
          searchable
          searchPlaceholder="Filtrar mês ou situação..."
          exportable
          exportFileName="fluxo-caixa-capital-giro"
          emptyMessage="Nenhum lançamento encontrado para o período selecionado."
        />
      </div>
    </div>
  );
}
