"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BarChart3,
  CalendarRange,
  LineChart,
  Trophy,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { getSafraLabel } from "@/lib/safra-label";
import { useHasTier } from "@/hooks/use-has-tier";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface SafraResumo {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface ProductionUnitResumo {
  id: string;
  cultivo_nome: string | null;
  area_nome: string | null;
}

interface BenchmarkWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface BenchmarkItem {
  scope: "SAFRA" | "PRODUCTION_UNIT";
  id: string;
  label: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  area_total_ha: number;
  resultado_operacional: number;
  margem_pct: number | null;
  receita_liquida_por_hectare: number | null;
  resultado_por_hectare: number | null;
  custo_operacional_total: number;
  custo_operacional_por_hectare: number | null;
  custo_operacional_por_operacao: number | null;
  horas_por_hectare: number | null;
  hectares_por_jornada: number | null;
  quantidade_operacoes: number;
  quantidade_jornadas: number;
  quantidade_apontamentos: number;
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
  warnings_relevantes: string[];
  posicao?: number | null;
  destaque?: "MELHOR" | "REFERENCIA" | "PONTO_ATENCAO" | null;
}

interface BenchmarkDestaques {
  melhor: BenchmarkItem | null;
  referencia: BenchmarkItem | null;
  ponto_atencao: BenchmarkItem | null;
}

interface BenchmarkResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  safra: BenchmarkItem;
  production_units: BenchmarkItem[];
  ranking: BenchmarkItem[];
  destaques: BenchmarkDestaques;
  warnings: BenchmarkWarning[];
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
}

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function formatCurrency(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : currencyFormatter.format(value);
}

function formatPercent(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)}%`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

function destaqueTone(destaque: BenchmarkItem["destaque"]) {
  if (destaque === "MELHOR") {
    return { label: "Melhor", className: "bg-emerald-100 text-emerald-700 border-emerald-200" };
  }
  if (destaque === "REFERENCIA") {
    return { label: "Referência", className: "bg-slate-100 text-slate-700 border-slate-200" };
  }
  if (destaque === "PONTO_ATENCAO") {
    return { label: "Ponto de atenção", className: "bg-amber-100 text-amber-700 border-amber-200" };
  }
  return { label: "—", className: "bg-muted text-muted-foreground border-border" };
}

export default function BenchmarkOperacionalEconomicoAgricolaPage() {
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesProdutivas = useAppStore((state) => state.unidadesProdutivasAutorizadas);

  const [selectedSafraId, setSelectedSafraId] = useState<string>("");
  const [selectedProductionUnitId, setSelectedProductionUnitId] = useState<string>("TODAS");
  const [selectedUnidadeProdutivaId, setSelectedUnidadeProdutivaId] = useState<string>("");
  const [dataInicio, setDataInicio] = useState<string>("");
  const [dataFim, setDataFim] = useState<string>("");

  const effectiveUnidadeProdutivaId = selectedUnidadeProdutivaId || activeFazendaId || "";
  const safraScopeId = effectiveUnidadeProdutivaId || undefined;

  const { data: safras = [], isLoading: isLoadingSafras, error: safraError } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-benchmark", "safras", safraScopeId],
        queryFn: () => apiFetch(`/safras/${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-benchmark", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const benchmarkParams = useMemo(() => {
    if (!effectiveSafraId) return null;
    return {
      safra_id: effectiveSafraId,
      production_unit_id: selectedProductionUnitId !== "TODAS" ? selectedProductionUnitId : undefined,
      unidade_produtiva_id: effectiveUnidadeProdutivaId || undefined,
      data_inicio: dataInicio || undefined,
      data_fim: dataFim || undefined,
    };
  }, [dataFim, dataInicio, effectiveSafraId, effectiveUnidadeProdutivaId, selectedProductionUnitId]);

  const {
    data: benchmark,
    isLoading: isLoadingBenchmark,
    isError: isErrorBenchmark,
    error: benchmarkError,
  } = useQuery<BenchmarkResponse>({
    queryKey: ["agricola-benchmark", "v1", benchmarkParams],
    queryFn: () => apiFetch("/agricola/benchmark/v1", { params: benchmarkParams ?? undefined }),
    enabled: hasProfessionalTier && !!benchmarkParams,
  });

  const periodoLabel =
    benchmark?.data_inicio || benchmark?.data_fim
      ? `${formatDate(benchmark?.data_inicio)} → ${formatDate(benchmark?.data_fim)}`
      : "Sem recorte temporal";
  const hasWarnings = Boolean(benchmark?.warnings?.length);

  const summary = useMemo(() => {
    const items = benchmark?.production_units ?? [];
    if (!items.length) {
      return {
        quantidade: 0,
        margem_media: null as number | null,
        custo_medio: null as number | null,
        resultado_medio: null as number | null,
        receita_media: null as number | null,
      };
    }
    const total = items.length;
    const margemMedia = items.reduce((acc, item) => acc + (item.margem_pct ?? 0), 0) / total;
    const custoMedio = items.reduce((acc, item) => acc + (item.custo_operacional_por_hectare ?? 0), 0) / total;
    const resultadoMedio = items.reduce((acc, item) => acc + (item.resultado_por_hectare ?? 0), 0) / total;
    const receitaMedia = items.reduce((acc, item) => acc + (item.receita_liquida_por_hectare ?? 0), 0) / total;
    return {
      quantidade: total,
      margem_media: Number.isFinite(margemMedia) ? margemMedia : null,
      custo_medio: Number.isFinite(custoMedio) ? custoMedio : null,
      resultado_medio: Number.isFinite(resultadoMedio) ? resultadoMedio : null,
      receita_media: Number.isFinite(receitaMedia) ? receitaMedia : null,
    };
  }, [benchmark?.production_units]);

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Benchmark Operacional e Econômico"
          description="Leitura oficial comparativa derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Benchmark Operacional e Econômico" },
          ]}
          icon={<BarChart3 className="size-5" />}
        />
        <TierUpgradeCard
          title="Benchmark agrícola disponível no PROFISSIONAL"
          description="A visão oficial de benchmark reutiliza DRE agrícola v1, rentabilidade oficial e eficiência operacional oficial."
          requiredTier="PROFISSIONAL"
          feature="agricola.benchmark_v1"
          surface="agricola.benchmark.page"
        />
      </div>
    );
  }

  const benchmarkSource = benchmark?.destaques?.melhor ?? benchmark?.ranking?.[0] ?? null;
  const referenceSource = benchmark?.destaques?.referencia ?? benchmark?.ranking?.[Math.floor((benchmark?.ranking?.length ?? 1) / 2)] ?? null;
  const attentionSource = benchmark?.destaques?.ponto_atencao ?? benchmark?.ranking?.[benchmark?.ranking?.length ? benchmark.ranking.length - 1 : 0] ?? null;

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Benchmark Operacional e Econômico"
        description="Comparativo oficial de margem, resultado, custo e eficiência derivado exclusivamente da DRE agrícola v1."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Benchmark Operacional e Econômico" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/dre">
              <LineChart className="size-4" />
              Voltar à DRE
            </Link>
          </Button>
        )}
        icon={<BarChart3 className="size-5" />}
      />

      <Alert className="rounded-sm">
        <AlertCircle className="size-4" />
        <AlertTitle>Leitura oficial</AlertTitle>
        <AlertDescription>
          O benchmark consome DREAgricolaV1Service, AgricolaDreKpiService, RentabilidadeService e EficienciaOperacionalService já consolidados. Não há recalculo fora da DRE.
        </AlertDescription>
      </Alert>

      {hasWarnings && (
        <Alert className="rounded-sm border-amber-200 bg-amber-50/70 text-amber-950">
          <AlertCircle className="size-4" />
          <AlertTitle>Reconciliação pendente</AlertTitle>
          <AlertDescription>Benchmark sujeito à reconciliação.</AlertDescription>
        </Alert>
      )}

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <CalendarRange className="size-4 text-muted-foreground" />
            Filtros oficiais
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-4">
            <div className="flex flex-col gap-1.5">
              <label id="benchmark-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Safra
              </label>
              <Select
                value={effectiveSafraId}
                onValueChange={(value) => {
                  setSelectedSafraId(value);
                  setSelectedProductionUnitId("TODAS");
                }}
                disabled={isLoadingSafras || safras.length === 0}
              >
                <SelectTrigger aria-labelledby="benchmark-safra-label" data-testid="benchmark-safra-select">
                  <SelectValue placeholder={isLoadingSafras ? "Carregando safras..." : "Selecionar safra"} />
                </SelectTrigger>
                <SelectContent>
                  {safras.map((safra) => (
                    <SelectItem key={safra.id} value={safra.id}>
                      {getSafraLabel(safra)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="benchmark-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade produtiva
              </label>
              <Select
                value={effectiveUnidadeProdutivaId}
                onValueChange={(value) => {
                  setSelectedUnidadeProdutivaId(value === "TODAS" ? "" : value);
                  setSelectedSafraId("");
                  setSelectedProductionUnitId("TODAS");
                }}
              >
                <SelectTrigger aria-labelledby="benchmark-unidade-label" data-testid="benchmark-unidade-produtiva-select">
                  <SelectValue placeholder="Selecionar unidade" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {unidadesProdutivas.map((unidade) => (
                    <SelectItem key={unidade.id} value={unidade.id}>
                      {unidade.nome ?? unidade.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="benchmark-production-unit-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={isLoadingProductionUnits || productionUnits.length === 0}
              >
                <SelectTrigger aria-labelledby="benchmark-production-unit-label" data-testid="benchmark-production-unit-select">
                  <SelectValue placeholder={isLoadingProductionUnits ? "Carregando unidades..." : "Todas as unidades"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {productionUnits.map((unit) => (
                    <SelectItem key={unit.id} value={unit.id}>
                      {unit.area_nome ?? unit.cultivo_nome ?? unit.id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="benchmark-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input id="benchmark-data-inicio" data-testid="benchmark-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="benchmark-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input id="benchmark-data-fim" data-testid="benchmark-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoadingBenchmark ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Card key={item} className="rounded-sm shadow-sm">
              <CardContent className="p-5 flex items-start gap-4">
                <Skeleton className="size-10 rounded-sm" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-8 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            color="agro"
            icon={Trophy}
            label="Melhor benchmark"
            value={benchmarkSource ? formatCurrency(benchmarkSource.resultado_por_hectare) : "—"}
            subtitle={benchmarkSource ? `${benchmarkSource.label} • margem ${formatPercent(benchmarkSource.margem_pct)}` : "Sem dados"}
          />
          <StatCard
            color="operacional"
            icon={TrendingUp}
            label="Referência"
            value={referenceSource ? formatCurrency(referenceSource.resultado_por_hectare) : "—"}
            subtitle={referenceSource ? `${referenceSource.label} • custo ${formatCurrency(referenceSource.custo_operacional_por_hectare)}/ha` : "Sem dados"}
          />
          <StatCard
            color="warning"
            icon={Wallet}
            label="Custo médio/ha"
            value={formatCurrency(summary.custo_medio)}
            subtitle={`Comparadas ${summary.quantidade} ProductionUnits`}
          />
          <StatCard
            color="primary"
            icon={BarChart3}
            label="Resultado médio/ha"
            value={formatCurrency(summary.resultado_medio)}
            subtitle={periodoLabel}
          />
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Trophy className="size-4 text-emerald-600" />
              Melhor destaque
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-semibold">{benchmarkSource?.label ?? "Sem dados"}</p>
            <p className="text-xs text-muted-foreground">Resultado operacional por hectare: {formatCurrency(benchmarkSource?.resultado_por_hectare)}</p>
            <p className="text-xs text-muted-foreground">Margem: {formatPercent(benchmarkSource?.margem_pct)}</p>
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="size-4 text-slate-600" />
              Referência comparativa
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-semibold">{referenceSource?.label ?? "Sem dados"}</p>
            <p className="text-xs text-muted-foreground">Receita líquida por hectare: {formatCurrency(referenceSource?.receita_liquida_por_hectare)}</p>
            <p className="text-xs text-muted-foreground">Custo operacional por hectare: {formatCurrency(referenceSource?.custo_operacional_por_hectare)}</p>
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="size-4 text-amber-600" />
              Ponto de atenção
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-semibold">{attentionSource?.label ?? "Sem dados"}</p>
            <p className="text-xs text-muted-foreground">Horas por hectare: {attentionSource?.horas_por_hectare ?? "—"}</p>
            <p className="text-xs text-muted-foreground">Benchmark sujeito à reconciliação.</p>
          </CardContent>
        </Card>
      </div>

      {benchmark?.safra && (
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Wallet className="size-4 text-muted-foreground" />
              Safra benchmark
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard color="agro" label="Margem %" value={formatPercent(benchmark.safra.margem_pct)} />
            <StatCard color="operacional" label="Resultado operacional" value={formatCurrency(benchmark.safra.resultado_operacional)} />
            <StatCard color="warning" label="Receita líquida/ha" value={formatCurrency(benchmark.safra.receita_liquida_por_hectare)} />
            <StatCard color="primary" label="Custo/ha" value={formatCurrency(benchmark.safra.custo_operacional_por_hectare)} />
          </CardContent>
        </Card>
      )}

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="size-4 text-muted-foreground" />
            Ranking comparativo simples
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isErrorBenchmark ? (
            <div className="p-6">
              <EmptyState
                icon={<BarChart3 />}
                title="Não foi possível carregar o benchmark"
                description={(benchmarkError as Error)?.message || (safraError as Error)?.message || "Verifique o recorte selecionado e tente novamente."}
              />
            </div>
          ) : benchmark?.ranking.length ? (
            <div className="overflow-x-auto">
              <Table data-testid="benchmark-ranking-table">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Pos.</TableHead>
                    <TableHead>ProductionUnit</TableHead>
                    <TableHead>Margem %</TableHead>
                    <TableHead>Resultado/ha</TableHead>
                    <TableHead>Receita líquida/ha</TableHead>
                    <TableHead>Custo/ha</TableHead>
                    <TableHead>Horas/ha</TableHead>
                    <TableHead>Destaque</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {benchmark.ranking.map((item) => {
                    const destaque = destaqueTone(item.destaque);
                    return (
                      <TableRow key={item.id}>
                        <TableCell className="font-black tabular-nums">{item.posicao ?? "—"}</TableCell>
                        <TableCell className="font-medium">{item.label}</TableCell>
                        <TableCell>{formatPercent(item.margem_pct)}</TableCell>
                        <TableCell>{formatCurrency(item.resultado_por_hectare)}</TableCell>
                        <TableCell>{formatCurrency(item.receita_liquida_por_hectare)}</TableCell>
                        <TableCell>{formatCurrency(item.custo_operacional_por_hectare)}</TableCell>
                        <TableCell>{item.horas_por_hectare === null || item.horas_por_hectare === undefined ? "—" : item.horas_por_hectare.toFixed(2)}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn("rounded-sm", destaque.className)}>
                            {destaque.label}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="p-6">
              <EmptyState
                icon={<BarChart3 />}
                title="Nenhum benchmark encontrado"
                description="Selecione uma safra com ProductionUnits válidas para visualizar o comparativo."
              />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
