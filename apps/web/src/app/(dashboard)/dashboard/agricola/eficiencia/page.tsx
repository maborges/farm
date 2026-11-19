"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  CalendarRange,
  Factory,
  LineChart,
  Tractor,
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

interface EficienciaWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
}

interface EficienciaItem {
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION";
  id: string;
  label: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  equipamento_id?: string | null;
  operacao_id?: string | null;
  area_total_ha: number;
  hectares_totais: number;
  horas_totais: number;
  quantidade_operacoes: number;
  quantidade_jornadas: number;
  quantidade_apontamentos: number;
  custo_operacional_total: number;
  custo_operacional_por_hectare: number | null;
  custo_operacional_por_operacao: number | null;
  horas_por_hectare: number | null;
  hectares_por_jornada: number | null;
  resultado_operacional: number | null;
  resultado_por_hectare: number | null;
  margem_pct: number | null;
  sujeito_reconciliacao: boolean;
  observacao_reconciliacao: string | null;
  warnings_relevantes: string[];
  posicao?: number | null;
}

interface EficienciaResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  data_inicio?: string | null;
  data_fim?: string | null;
  safra: EficienciaItem;
  production_units: EficienciaItem[];
  equipamentos: EficienciaItem[];
  operacoes: EficienciaItem[];
  ranking: EficienciaItem[];
  warnings: EficienciaWarning[];
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

export default function EficienciaOperacionalAgricolaPage() {
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
    queryKey: ["agricola-eficiencia", "safras", safraScopeId],
        queryFn: () => apiFetch(`/safras/${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-eficiencia", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const eficienciaParams = useMemo(() => {
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
    data: eficiencia,
    isLoading: isLoadingEficiencia,
    isError: isErrorEficiencia,
    error: eficienciaError,
  } = useQuery<EficienciaResponse>({
    queryKey: ["agricola-eficiencia", "v1", eficienciaParams],
    queryFn: () => apiFetch("/agricola/eficiencia/v1", { params: eficienciaParams ?? undefined }),
    enabled: hasProfessionalTier && !!eficienciaParams,
  });

  const safraAtual = safras.find((safra) => safra.id === effectiveSafraId) ?? null;
  const highlightedUnit =
    eficiencia?.ranking.find((item) => item.id === selectedProductionUnitId) ??
    eficiencia?.ranking[0] ??
    null;
  const periodLabel =
    eficiencia?.data_inicio || eficiencia?.data_fim
      ? `${formatDate(eficiencia?.data_inicio)} → ${formatDate(eficiencia?.data_fim)}`
      : "Sem recorte temporal";
  const hasWarnings = Boolean(eficiencia?.warnings?.length);

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="Eficiência Operacional Agrícola"
          description="Leitura oficial de custo e produtividade derivada da DRE agrícola v1."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "Eficiência Operacional" },
          ]}
          icon={<Activity className="size-5" />}
        />
        <TierUpgradeCard
          title="Eficiência operacional disponível no PROFISSIONAL"
          description="A visão oficial reutiliza DRE agrícola v1, rentabilidade oficial e registros operacionais."
          requiredTier="PROFISSIONAL"
          feature="agricola.eficiencia_v1"
          surface="agricola.eficiencia.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Eficiência Operacional Agrícola"
        description="Base oficial de custo, horas e produtividade derivada da DRE agrícola v1 e dos registros operacionais."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "DRE Agrícola v1", href: "/dashboard/agricola/dre" },
          { label: "Eficiência Operacional", href: "/dashboard/agricola/eficiencia" },
        ]}
        actions={(
          <Button asChild variant="outline" size="sm" className="rounded-sm">
            <Link href="/dashboard/agricola/dre">
              <LineChart className="size-4" />
              Voltar à DRE
            </Link>
          </Button>
        )}
        icon={<Activity className="size-5" />}
      />

      <Alert variant="info">
        <AlertCircle />
        <AlertTitle>Leitura oficial</AlertTitle>
        <AlertDescription>
          A eficiência consome DREAgricolaV1Service, AgricolaDreKpiService, RentabilidadeService e registros operacionais já existentes. Não há recalculo fora da DRE.
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
              <label id="eficiencia-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="eficiencia-safra-label" data-testid="eficiencia-safra-select">
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
              <label id="eficiencia-unidade-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade produtiva
              </label>
              <Select
                value={selectedUnidadeProdutivaId || "TODAS"}
                onValueChange={(value) => {
                  setSelectedUnidadeProdutivaId(value === "TODAS" ? "" : value);
                  setSelectedProductionUnitId("TODAS");
                }}
                disabled={!unidadesProdutivas.length}
              >
                <SelectTrigger aria-labelledby="eficiencia-unidade-label" data-testid="eficiencia-unidade-produtiva-select">
                  <SelectValue placeholder="Todas as unidades" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODAS">Todas as unidades</SelectItem>
                  {unidadesProdutivas.map((unidade) => (
                    <SelectItem key={unidade.id} value={unidade.id}>
                      {unidade.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="eficiencia-pu-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={isLoadingProductionUnits || productionUnits.length === 0}
              >
                <SelectTrigger aria-labelledby="eficiencia-pu-label" data-testid="eficiencia-production-unit-select">
                  <SelectValue placeholder={isLoadingProductionUnits ? "Carregando..." : "Todas as unidades"} />
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

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="eficiencia-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Início
                </label>
                <Input
                  id="eficiencia-data-inicio"
                  data-testid="eficiencia-data-inicio"
                  type="date"
                  value={dataInicio}
                  onChange={(event) => setDataInicio(event.target.value)}
                  className="rounded-sm"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="eficiencia-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Fim
                </label>
                <Input
                  id="eficiencia-data-fim"
                  data-testid="eficiencia-data-fim"
                  type="date"
                  value={dataFim}
                  onChange={(event) => setDataFim(event.target.value)}
                  className="rounded-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="rounded-sm">DREAgricolaV1Service</Badge>
            <Badge variant="secondary" className="rounded-sm">AgricolaDreKpiService</Badge>
            <Badge variant="secondary" className="rounded-sm">RentabilidadeService</Badge>
          </div>
        </CardContent>
      </Card>

      {isErrorSafras ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao carregar safras</AlertTitle>
          <AlertDescription>{safraError instanceof Error ? safraError.message : "Não foi possível listar as safras para consolidar a eficiência operacional."}</AlertDescription>
        </Alert>
      ) : isErrorEficiencia ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao consolidar a eficiência</AlertTitle>
          <AlertDescription>{eficienciaError instanceof Error ? eficienciaError.message : "Não foi possível carregar a visão oficial de eficiência operacional."}</AlertDescription>
        </Alert>
      ) : eficiencia ? (
        <div className="flex flex-col gap-6">
          {hasWarnings && (
            <Alert variant="warning">
              <AlertCircle />
              <AlertTitle>indicadores sujeitos à reconciliação.</AlertTitle>
              <AlertDescription>
                A visão utiliza DRE agrícola v1, rentabilidade oficial e registros operacionais. Warnings relevantes foram propagados para preservar a leitura oficial.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard
              icon={Wallet}
              label="Custo operacional da safra"
              value={formatCurrency(eficiencia.safra.custo_operacional_total)}
              subtitle={safraAtual ? getSafraLabel(safraAtual) : "Safra consolidada"}
              color="destructive"
            />
            <StatCard
              icon={Factory}
              label="Custo operacional por hectare"
              value={formatCurrency(eficiencia.safra.custo_operacional_por_hectare)}
              subtitle="Base oficial da DRE v1"
              color="primary"
            />
            <StatCard
              icon={Activity}
              label="Horas por hectare"
              value={eficiencia.safra.horas_por_hectare === null ? "—" : eficiencia.safra.horas_por_hectare.toFixed(2)}
              subtitle="Jornadas / hectares"
              color="agro"
            />
            <StatCard
              icon={Tractor}
              label="Hectares por jornada"
              value={eficiencia.safra.hectares_por_jornada === null ? "—" : eficiencia.safra.hectares_por_jornada.toFixed(2)}
              subtitle="Produtividade operacional"
              color="success"
            />
            <StatCard
              icon={TrendingUp}
              label="Resultado por hectare"
              value={formatCurrency(eficiencia.safra.resultado_por_hectare)}
              subtitle="Eficiência econômica"
              color={eficiencia.safra.resultado_por_hectare !== null && eficiencia.safra.resultado_por_hectare < 0 ? "destructive" : "success"}
            />
          </div>

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
                        icon={Wallet}
                        label="Custo operacional"
                        value={formatCurrency(highlightedUnit.custo_operacional_total)}
                        subtitle="Base oficial da DRE v1"
                        color="destructive"
                      />
                      <StatCard
                        icon={Activity}
                        label="Horas por hectare"
                        value={highlightedUnit.horas_por_hectare === null ? "—" : highlightedUnit.horas_por_hectare.toFixed(2)}
                        subtitle="Eficiência operacional"
                        color="primary"
                      />
                      <StatCard
                        icon={Factory}
                        label="Custo por hectare"
                        value={formatCurrency(highlightedUnit.custo_operacional_por_hectare)}
                        subtitle="Ranking simples"
                        color="agro"
                      />
                      <StatCard
                        icon={TrendingUp}
                        label="Resultado por hectare"
                        value={formatCurrency(highlightedUnit.resultado_por_hectare)}
                        subtitle="Rentabilidade oficial"
                        color={highlightedUnit.resultado_por_hectare !== null && highlightedUnit.resultado_por_hectare < 0 ? "destructive" : "success"}
                      />
                    </div>
                  </>
                ) : (
                  <EmptyState
                    icon={<Tractor />}
                    title="Nenhuma Unidade Operacional no recorte atual"
                    description="A visão oficial de eficiência só exibe unidades derivadas da DRE v1 com os filtros informados."
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
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">ProductionUnit</p>
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
                  <p className="mt-1 font-medium">{formatDate(eficiencia.gerado_em)}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rankeadas</p>
                  <p className="mt-1 font-medium">{eficiencia.ranking.length} unidade(s)</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <TrendingUp className="size-4 text-muted-foreground" />
                Ranking simples de eficiência
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {eficiencia.ranking.length === 0 ? (
                <EmptyState
                  icon={<TrendingUp />}
                  title="Nenhuma unidade para ranquear"
                  description="A visão atual não encontrou Units Operacionais após aplicar os filtros oficiais."
                />
              ) : (
                <Table data-testid="eficiencia-ranking-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-20">Pos.</TableHead>
                      <TableHead>Unidade Operacional</TableHead>
                      <TableHead className="text-right">Custo/ha</TableHead>
                      <TableHead className="text-right">Horas/ha</TableHead>
                      <TableHead className="text-right">Resultado/ha</TableHead>
                      <TableHead className="text-right">Warnings</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {eficiencia.ranking.map((item) => (
                      <TableRow key={item.id} className={cn(item.id === selectedProductionUnitId && "bg-muted/30")}>
                        <TableCell className="font-black tabular-nums">{item.posicao ?? "—"}</TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold">{item.label}</span>
                            <span className="text-xs text-muted-foreground">{item.area_total_ha.toFixed(1)} ha</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.custo_operacional_por_hectare)}</TableCell>
                        <TableCell className="text-right font-bold tabular-nums">{item.horas_por_hectare === null ? "—" : item.horas_por_hectare.toFixed(2)}</TableCell>
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

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="size-4 text-muted-foreground" />
                  Equipamentos
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {eficiencia.equipamentos.length === 0 ? (
                  <EmptyState
                    icon={<Activity />}
                    title="Nenhum equipamento no recorte atual"
                    description="Os equipamentos aparecem quando há jornadas ou apontamentos operacionais no período."
                  />
                ) : (
                  <Table data-testid="eficiencia-equipamentos-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Equipamento</TableHead>
                        <TableHead className="text-right">Horas</TableHead>
                        <TableHead className="text-right">Hectares</TableHead>
                        <TableHead className="text-right">Custo total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {eficiencia.equipamentos.slice(0, 8).map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-semibold">{item.label}</TableCell>
                          <TableCell className="text-right tabular-nums">{item.horas_totais.toFixed(1)}</TableCell>
                          <TableCell className="text-right tabular-nums">{item.hectares_totais.toFixed(1)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.custo_operacional_total)}</TableCell>
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
                  <Factory className="size-4 text-muted-foreground" />
                  Operações
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {eficiencia.operacoes.length === 0 ? (
                  <EmptyState
                    icon={<Factory />}
                    title="Nenhuma operação no recorte atual"
                    description="As operações aparecem quando há produção agrícola registrada no período."
                  />
                ) : (
                  <Table data-testid="eficiencia-operacoes-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Operação</TableHead>
                        <TableHead className="text-right">Hectares</TableHead>
                        <TableHead className="text-right">Custo total</TableHead>
                        <TableHead className="text-right">Custo/ha</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {eficiencia.operacoes.slice(0, 8).map((item) => (
                        <TableRow key={item.id}>
                          <TableCell className="font-semibold">{item.label}</TableCell>
                          <TableCell className="text-right tabular-nums">{item.hectares_totais.toFixed(1)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.custo_operacional_total)}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums">{formatCurrency(item.custo_operacional_por_hectare)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="size-4 text-muted-foreground" />
                Warnings propagados
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {eficiencia.warnings.length === 0 ? (
                <EmptyState
                  icon={<AlertCircle />}
                  title="Nenhum warning no recorte atual"
                  description="A eficiência operacional não encontrou inconsistências relevantes no período e filtros aplicados."
                />
              ) : (
                eficiencia.warnings.map((warning) => {
                  const tone = warningTone(warning.severidade);
                  return (
                    <div key={`${warning.codigo}-${warning.origem}`} className="rounded-sm border border-border/70 p-4 flex flex-col gap-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex flex-col gap-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={tone.badge} className="rounded-sm">
                              {tone.label}
                            </Badge>
                            <span className="text-xs text-muted-foreground">{warning.codigo}</span>
                          </div>
                          <p className="font-semibold text-sm">{warning.titulo}</p>
                          <p className="text-sm text-muted-foreground">{warning.mensagem}</p>
                        </div>
                        <Badge variant="outline" className="rounded-sm">
                          {warning.origem}
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
