"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarRange,
  LineChart,
  Percent,
  Sprout,
  Tractor,
  TrendingUp,
  Wallet,
  Wheat,
  Info
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

interface RentabilidadeWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface RentabilidadeSacaKpis {
  quantidade_sacas: number;
  base_volume: "REAL" | "ESTIMADO" | "INDISPONIVEL";
  custo_por_saca: number | null;
  receita_por_saca: number | null;
  margem_por_saca: number | null;
  lucro_por_saca: number | null;
  preco_equilibrio: number | null;
}

interface RentabilidadeItem {
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
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
  warnings_relevantes: string[];
  posicao?: number | null;
  kpis_fisicos?: RentabilidadeSacaKpis | null;
}

interface RentabilidadeResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  safra: RentabilidadeItem;
  production_units: RentabilidadeItem[];
  ranking: RentabilidadeItem[];
  warnings: RentabilidadeWarning[];
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

function warningTone(severidade: string) {
  if (severidade === "RISCO_ECONOMICO") {
    return { label: "Risco econômico", badge: "destructive" as const };
  }
  if (severidade === "INCONSISTENCIA_MODERADA") {
    return { label: "Inconsistência moderada", badge: "warning" as const };
  }
  return { label: "Warning leve", badge: "secondary" as const };
}

const WARNING_ORIGEM_LABELS: Record<string, string> = {
  dre_agricola_v1: "Consolidação DRE",
  reconciliacao_economica: "Reconciliação econômica",
  estoque_movimentos: "Movimentação de estoque",
};

function warningOrigemLabel(origem: string) {
  return WARNING_ORIGEM_LABELS[origem] ?? origem.replace(/_/g, " ");
}

export default function RentabilidadeAgricolaPage() {
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

  const { data: safras = [], isLoading: isLoadingSafras, isError: isErrorSafras, error: safraError } = useQuery<SafraResumo[]>({
    queryKey: ["agricola-rentabilidade", "safras", safraScopeId],
    queryFn: () => apiFetch(`/safras/${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-rentabilidade", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const rentabilidadeParams = useMemo(() => {
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
    data: rentabilidade,
    isLoading: isLoadingRentabilidade,
    isError: isErrorRentabilidade,
    error: rentabilidadeError,
  } = useQuery<RentabilidadeResponse>({
    queryKey: ["agricola-rentabilidade", "v1", rentabilidadeParams],
    queryFn: () => apiFetch("/agricola/rentabilidade/v1", { params: rentabilidadeParams ?? undefined }),
    enabled: hasProfessionalTier && !!rentabilidadeParams,
  });

  const safraAtual = safras.find((safra) => safra.id === effectiveSafraId) ?? null;
  const highlightedUnit =
    rentabilidade?.ranking.find((item) => item.id === selectedProductionUnitId) ??
    rentabilidade?.ranking[0] ??
    null;
  const periodLabel =
    rentabilidade?.data_inicio || rentabilidade?.data_fim
      ? `${formatDate(rentabilidade?.data_inicio)} → ${formatDate(rentabilidade?.data_fim)}`
      : "Sem recorte temporal";
  const hasWarnings = Boolean(rentabilidade?.warnings?.length);

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Rentabilidade Agrícola"
          description="Leitura oficial derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Rentabilidade Agrícola" },
          ]}
          icon={<LineChart className="size-5" />}
        />
        <TierUpgradeCard
          title="Rentabilidade agrícola disponível no PROFISSIONAL"
          description="A visão oficial de rentabilidade reutiliza somente a DRE agrícola v1 e os KPIs oficiais."
          requiredTier="PROFISSIONAL"
          feature="agricola.rentabilidade_v1"
          surface="agricola.rentabilidade.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Rentabilidade Agrícola"
        description="Base oficial de margem e eficiência econômica derivada da DRE agrícola v1."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Rentabilidade Agrícola" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/dre">
              <LineChart className="size-4" />
              Voltar à DRE
            </Link>
          </Button>
        )}
        icon={<TrendingUp className="size-5" />}
      />

      <Alert className="rounded-sm">
        <AlertCircle className="size-4" />
        <AlertTitle>Leitura oficial</AlertTitle>
        <AlertDescription>
          Os valores de rentabilidade vêm exclusivamente da consolidação oficial da DRE e dos KPIs agrícolas. Não há recálculo de receita ou custo fora da DRE.
        </AlertDescription>
      </Alert>

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
              <label id="rentabilidade-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="rentabilidade-safra-label" data-testid="rentabilidade-safra-select">
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
              <label id="rentabilidade-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade produtiva
              </label>
              <Select
                value={effectiveUnidadeProdutivaId || "TODAS"}
                onValueChange={(value) => {
                  setSelectedUnidadeProdutivaId(value === "TODAS" ? "" : value);
                }}
                disabled={unidadesProdutivas.length === 0}
              >
                <SelectTrigger aria-labelledby="rentabilidade-unidade-label" data-testid="rentabilidade-unidade-produtiva-select">
                  <SelectValue placeholder="Todas as fazendas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as fazendas</SelectItem>
                  {unidadesProdutivas.map((unidade) => (
                    <SelectItem key={unidade.id} value={unidade.id}>
                      {unidade.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="rentabilidade-pu-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade Operacional
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={!selectedSafraId || isLoadingProductionUnits}
              >
                <SelectTrigger aria-labelledby="rentabilidade-pu-label" data-testid="rentabilidade-production-unit-select">
                  <SelectValue placeholder={isLoadingProductionUnits ? "Carregando unidades..." : "Todas as unidades"} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {productionUnits.map((unit) => (
                    <SelectItem key={unit.id} value={unit.id}>
                      {unit.cultivo_nome ?? "Cultivo"} • {unit.area_nome ?? unit.id.slice(0, 8)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="rentabilidade-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input
                  id="rentabilidade-data-inicio"
                  data-testid="rentabilidade-data-inicio"
                  type="date"
                  value={dataInicio}
                  onChange={(event) => setDataInicio(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="rentabilidade-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input
                  id="rentabilidade-data-fim"
                  data-testid="rentabilidade-data-fim"
                  type="date"
                  value={dataFim}
                  onChange={(event) => setDataFim(event.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="rounded-sm">Somente leitura</Badge>
            <Badge variant="secondary" className="rounded-sm">DRE agrícola oficial</Badge>
            <Badge variant="secondary" className="rounded-sm">KPIs oficiais</Badge>
          </div>
        </CardContent>
      </Card>

      {isLoadingSafras || isLoadingRentabilidade ? (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-28 rounded-sm" />
            ))}
          </div>
          <Skeleton className="h-52 rounded-sm" />
          <Skeleton className="h-64 rounded-sm" />
        </div>
      ) : isErrorSafras ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao carregar safras</AlertTitle>
          <AlertDescription>{safraError instanceof Error ? safraError.message : "Não foi possível listar as safras para consolidar a rentabilidade."}</AlertDescription>
        </Alert>
      ) : isErrorRentabilidade ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao consolidar a rentabilidade</AlertTitle>
          <AlertDescription>{rentabilidadeError instanceof Error ? rentabilidadeError.message : "Não foi possível carregar a visão oficial de rentabilidade."}</AlertDescription>
        </Alert>
      ) : rentabilidade ? (
        <div className="flex flex-col gap-6">
          {hasWarnings && (
            <Alert className="rounded-sm border-amber-300 bg-amber-50/60">
              <AlertCircle className="size-4 text-amber-600" />
              <AlertTitle>rentabilidade sujeita à reconciliação.</AlertTitle>
              <AlertDescription>
                A visão utiliza somente a DRE agrícola v1. Warnings relevantes foram propagados para manter a leitura econômica oficial.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              icon={LineChart}
              label="Resultado operacional da safra"
              value={formatCurrency(rentabilidade.safra.resultado_operacional)}
              subtitle={safraAtual ? getSafraLabel(safraAtual) : "Safra consolidada"}
              color="success"
            />
            <StatCard
              icon={Percent}
              label="Margem % da safra"
              value={formatPercent(rentabilidade.safra.margem_pct)}
              subtitle="Resultado operacional / receita líquida"
              color={rentabilidade.safra.margem_pct !== null && rentabilidade.safra.margem_pct < 0 ? "destructive" : "primary"}
            />
            <StatCard
              icon={Sprout}
              label="Receita líquida por hectare"
              value={formatCurrency(rentabilidade.safra.receita_liquida_por_hectare)}
              subtitle={rentabilidade.safra.area_total_ha > 0 ? `${rentabilidade.safra.area_total_ha.toFixed(1)} ha` : "Área indisponível"}
              color="agro"
            />
            <StatCard
              icon={Wallet}
              label="Resultado por hectare"
              value={formatCurrency(rentabilidade.safra.resultado_por_hectare)}
              subtitle="Eficiência econômica da safra"
              color={rentabilidade.safra.resultado_por_hectare !== null && rentabilidade.safra.resultado_por_hectare < 0 ? "destructive" : "success"}
            />
          </div>

          <Card className="rounded-sm shadow-sm border-agro/20">
            <CardHeader className="pb-3 border-b bg-muted/20">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Wheat className="size-4 text-agro" />
                  Rentabilidade Física (Por Saca)
                </CardTitle>
                {rentabilidade.safra.kpis_fisicos && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Base de volume:</span>
                    <Badge 
                      variant={rentabilidade.safra.kpis_fisicos.base_volume === "REAL" ? "success" : rentabilidade.safra.kpis_fisicos.base_volume === "ESTIMADO" ? "warning" : "secondary"}
                      className="rounded-sm"
                    >
                      {rentabilidade.safra.kpis_fisicos.base_volume}
                    </Badge>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              {!rentabilidade.safra.kpis_fisicos || rentabilidade.safra.kpis_fisicos.base_volume === "INDISPONIVEL" ? (
                <EmptyState
                  icon={<Info />}
                  title="Volume físico indisponível"
                  description="Não há registros de colheita real nem estimativas cadastradas para o escopo selecionado."
                />
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <StatCard
                    icon={Wheat}
                    label="Total de Sacas"
                    value={rentabilidade.safra.kpis_fisicos.quantidade_sacas.toLocaleString("pt-BR")}
                    subtitle="Volume total estimado ou real"
                    color="primary"
                  />
                  <StatCard
                    icon={Wallet}
                    label="Receita por Saca"
                    value={formatCurrency(rentabilidade.safra.kpis_fisicos.receita_por_saca)}
                    subtitle="Valor médio de venda"
                    color="agro"
                  />
                  <StatCard
                    icon={LineChart}
                    label="Custo por Saca"
                    value={formatCurrency(rentabilidade.safra.kpis_fisicos.custo_por_saca)}
                    subtitle="Custo operacional total"
                    color="destructive"
                  />
                  <StatCard
                    icon={TrendingUp}
                    label="Margem por Saca"
                    value={formatCurrency(rentabilidade.safra.kpis_fisicos.margem_por_saca)}
                    subtitle="Receita - Custos Diretos"
                    color="primary"
                  />
                  <StatCard
                    icon={Percent}
                    label="Lucro por Saca"
                    value={formatCurrency(rentabilidade.safra.kpis_fisicos.lucro_por_saca)}
                    subtitle="Resultado / Total de sacas"
                    color={rentabilidade.safra.kpis_fisicos.lucro_por_saca !== null && rentabilidade.safra.kpis_fisicos.lucro_por_saca < 0 ? "destructive" : "success"}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Tractor className="size-4 text-muted-foreground" />
                  Unidade Operacional em destaque
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {highlightedUnit ? (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary" className="rounded-sm">
                        {highlightedUnit.posicao ? `#${highlightedUnit.posicao}` : "Destaque"}
                      </Badge>
                      <span className="text-sm font-semibold">{highlightedUnit.label}</span>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <StatCard
                        icon={LineChart}
                        label="Resultado operacional"
                        value={formatCurrency(highlightedUnit.resultado_operacional)}
                        subtitle="Unidade Operacional selecionada ou líder"
                        color="success"
                      />
                      <StatCard
                        icon={Percent}
                        label="Margem %"
                        value={formatPercent(highlightedUnit.margem_pct)}
                        subtitle="Resultado operacional / receita líquida"
                        color="primary"
                      />
                      <StatCard
                        icon={Sprout}
                        label="Receita líquida por hectare"
                        value={formatCurrency(highlightedUnit.receita_liquida_por_hectare)}
                        subtitle={highlightedUnit.area_total_ha > 0 ? `${highlightedUnit.area_total_ha.toFixed(1)} ha` : "Área indisponível"}
                        color="agro"
                      />
                      <StatCard
                        icon={Wallet}
                        label="Resultado por hectare"
                        value={formatCurrency(highlightedUnit.resultado_por_hectare)}
                        subtitle="Ranking simples de rentabilidade"
                        color={highlightedUnit.resultado_por_hectare !== null && highlightedUnit.resultado_por_hectare < 0 ? "destructive" : "success"}
                      />
                    </div>
                  </>
                ) : (
                  <EmptyState
                    icon={<Tractor />}
                    title="Nenhuma Unidade Operacional no recorte atual"
                    description="A visão oficial de rentabilidade só exibe Unidade Operacional derivadas da DRE v1 com os filtros informados."
                  />
                )}
              </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertCircle className="size-4 text-muted-foreground" />
                  Contexto do recorte
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2 text-sm">
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Safra</p>
                  <p className="mt-1 font-medium">{safraAtual ? getSafraLabel(safraAtual) : "—"}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Unidade produtiva</p>
                  <p className="mt-1 font-medium">
                    {!selectedUnidadeProdutivaId
                      ? "Todas as fazendas"
                      : unidadesProdutivas.find((unidade) => unidade.id === selectedUnidadeProdutivaId)?.nome ?? selectedUnidadeProdutivaId}
                  </p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Unidade Operacional</p>
                  <p className="mt-1 font-medium">
                    {selectedProductionUnitId === "TODAS"
                      ? "Todas as unidades"
                      : productionUnits.find((unit) => unit.id === selectedProductionUnitId)
                        ? `${productionUnits.find((unit) => unit.id === selectedProductionUnitId)?.cultivo_nome ?? "Cultivo"} • ${productionUnits.find((unit) => unit.id === selectedProductionUnitId)?.area_nome ?? selectedProductionUnitId.slice(0, 8)}`
                        : selectedProductionUnitId}
                  </p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Período</p>
                  <p className="mt-1 font-medium">{periodLabel}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Gerado em</p>
                  <p className="mt-1 font-medium">{formatDate(rentabilidade.gerado_em)}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Unidade Operacional</p>
                  <p className="mt-1 font-medium">{rentabilidade.ranking.length} unidade(s) ranqueada(s)</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <TrendingUp className="size-4 text-muted-foreground" />
                Ranking simples de rentabilidade
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {rentabilidade.ranking.length === 0 ? (
                <EmptyState
                  icon={<TrendingUp />}
                  title="Nenhuma unidade para ranquear"
                  description="A visão atual não encontrou Unidades Operacionais após aplicar os filtros oficiais."
                />
              ) : (
                <Table data-testid="rentabilidade-ranking-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-20">Pos.</TableHead>
                      <TableHead>Unidade Operacional</TableHead>
                      <TableHead className="text-right">Volume (Sc)</TableHead>
                      <TableHead className="text-right">Resultado op.</TableHead>
                      <TableHead className="text-right">Margem %</TableHead>
                      <TableHead className="text-right">Lucro/Saca</TableHead>
                      <TableHead className="text-right">Receita/ha</TableHead>
                      <TableHead className="text-right">Resultado/ha</TableHead>
                      <TableHead className="text-right">Warnings</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rentabilidade.ranking.map((item) => (
                      <TableRow key={item.id} className={cn(item.id === selectedProductionUnitId && "bg-muted/30")}>
                        <TableCell className="font-black tabular-nums">{item.posicao ?? "—"}</TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold">{item.label}</span>
                            <span className="text-xs text-muted-foreground">{item.area_total_ha.toFixed(1)} ha</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {item.kpis_fisicos?.quantidade_sacas ? (
                            <div className="flex flex-col items-end">
                              <span className="font-bold">{item.kpis_fisicos.quantidade_sacas.toLocaleString("pt-BR")}</span>
                              <span className="text-[10px] text-muted-foreground">{item.kpis_fisicos.base_volume}</span>
                            </div>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.resultado_operacional)}</TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{formatPercent(item.margem_pct)}</TableCell>
                        <TableCell className="text-right font-bold tabular-nums text-agro">{formatCurrency(item.kpis_fisicos?.lucro_por_saca)}</TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.receita_liquida_por_hectare)}</TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.resultado_por_hectare)}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant={item.warnings_relevantes.length > 0 ? "warning" : "secondary"} className="rounded-sm">
                            {item.warnings_relevantes.length}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="size-4 text-muted-foreground" />
                Warnings propagados
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {rentabilidade.warnings.length === 0 ? (
                <EmptyState
                  icon={<AlertCircle />}
                  title="Nenhum warning no recorte atual"
                  description="A rentabilidade oficial não encontrou inconsistências relevantes no período e filtros aplicados."
                />
              ) : (
                rentabilidade.warnings.map((warning) => {
                  const tone = warningTone(warning.severidade);
                  return (
                    <div key={`${warning.codigo}-${warning.origem}`} className="rounded-sm border border-border/70 p-4 flex flex-col gap-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex flex-col gap-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={tone.badge} className="rounded-sm">
                              {tone.label}
                            </Badge>
                          </div>
                          <p className="font-semibold text-sm">{warning.titulo}</p>
                          <p className="text-sm text-muted-foreground">{warning.mensagem}</p>
                        </div>
                        <Badge variant="outline" className="rounded-sm">
                          {warningOrigemLabel(warning.origem)}
                        </Badge>
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
