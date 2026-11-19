"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarRange,
  Factory,
  LineChart,
  Layers3,
  Sprout,
  Tractor,
  TrendingDown,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { AgricolaDreKpis } from "@/components/agricola/dre-kpis";

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

interface DREWarning {
  codigo: string;
  titulo: string;
  severidade: string;
  mensagem: string;
  origem: string;
  amostras: string[];
  meta: Record<string, unknown>;
}

interface DRESourceItem {
  natureza: string;
  fonte_oficial: string;
  origem_tipo?: string | null;
  origem_id?: string | null;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  safra_id?: string | null;
  valor: number;
  deduplicado: boolean;
  motivo?: string | null;
  meta: Record<string, unknown>;
}

interface DRESection {
  valor: number;
  itens: DRESourceItem[];
  total_registros: number;
  fontes: Record<string, number>;
}

interface DREReconcilacaoMeta {
  lancamentos_financeiros_receita: number;
  lancamentos_financeiros_custo: number;
  lancamentos_financeiros_total: number;
  estoque_movimentos_com_custo: number;
  cost_allocations_total: number;
  despesas_excluidas_por_precedencia: number;
  receitas_excluidas_por_precedencia: number;
  observacao: string | null;
  detalhes: {
    period?: {
      data_inicio?: string | null;
      data_fim?: string | null;
    };
    periodo?: {
      data_inicio?: string | null;
      data_fim?: string | null;
    };
    [key: string]: unknown;
  };
}

interface DREAgricolaResponse {
  tenant_id: string;
  gerado_em: string;
  safra_id: string | null;
  unidade_produtiva_id: string | null;
  production_unit_id: string | null;
  unidade_operacional_id: string | null;
  cultura: string | null;
  production_unit_ids: string[];
  receita_bruta: number;
  deducoes: number;
  receita_liquida: number;
  custos_diretos: number;
  custos_operacionais: number;
  margem_bruta: number;
  despesas_operacionais: number;
  resultado_operacional: number;
  kpis?: {
    area_total_ha: number;
    receita_liquida: number;
    custo_operacional_total: number;
    margem_bruta: number;
    resultado_operacional: number;
    margem_pct: number | null;
    custo_por_hectare: number | null;
    receita_por_hectare: number | null;
    resultado_por_hectare: number | null;
    sujeito_reconciliacao: boolean;
    observacao_reconciliacao: string | null;
    warnings_relevantes: string[];
  };
  receita: DRESection;
  custos_diretos_detalhe: DRESection;
  custos_operacionais_detalhe: DRESection;
  despesas_operacionais_detalhe: DRESection;
  warnings: DREWarning[];
  reconciliacao: DREReconcilacaoMeta;
}

const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function formatCurrency(value: number | null | undefined) {
  return currencyFormatter.format(value ?? 0);
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR").format(new Date(value));
}

const FONTE_LABELS: Record<string, string> = {
  OPERATION_EXECUTION: "Execução de operação",
  INVENTORY_MOVEMENT: "Movimentação de estoque",
  COMPRA: "Compra",
  ORDEM_SERVICO: "Ordem de serviço",
  ROMANEIO: "Romaneio",
  BENEFICIAMENTO: "Beneficiamento",
  VENDA: "Venda",
  MANUAL: "Lançamento manual",
  OUTRO: "Outro",
};

function fonteLabel(fonte: string) {
  return FONTE_LABELS[fonte] ?? fonte.replace(/_/g, " ");
}

function joinSourceSummary(section: DRESection) {
  const entries = Object.entries(section.fontes ?? {}).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return "Sem fontes detalhadas";
  return entries
    .slice(0, 2)
    .map(([fonte, valor]) => `${fonteLabel(fonte)}: ${formatCurrency(valor)}`)
    .join(" · ");
}

function warningTone(severidade: string) {
  if (severidade === "RISCO_ECONOMICO") {
    return { label: "Risco econômico", badge: "destructive" as const, tone: "destructive" as const };
  }
  if (severidade === "INCONSISTENCIA_MODERADA") {
    return { label: "Inconsistência moderada", badge: "warning" as const, tone: "warning" as const };
  }
  return { label: "Warning leve", badge: "secondary" as const, tone: "muted" as const };
}

const WARNING_ORIGEM_LABELS: Record<string, string> = {
  dre_agricola_v1: "Consolidação DRE",
  reconciliacao_economica: "Reconciliação econômica",
  estoque_movimentos: "Movimentação de estoque",
};

function warningOrigemLabel(origem: string) {
  return WARNING_ORIGEM_LABELS[origem] ?? origem.replace(/_/g, " ");
}

function sectionHasData(section: DRESection | undefined) {
  return Boolean(section && (section.valor !== 0 || section.total_registros > 0 || Object.keys(section.fontes ?? {}).length > 0));
}

function buildFallbackKpis(dre: DREAgricolaResponse) {
  return {
    area_total_ha: 0,
    receita_liquida: dre.receita_liquida,
    custo_operacional_total: dre.custos_diretos + dre.custos_operacionais + dre.despesas_operacionais,
    margem_bruta: dre.margem_bruta,
    resultado_operacional: dre.resultado_operacional,
    margem_pct: dre.receita_liquida > 0 ? (dre.resultado_operacional / dre.receita_liquida) * 100 : null,
    custo_por_hectare: null,
    receita_por_hectare: null,
    resultado_por_hectare: null,
    sujeito_reconciliacao: dre.warnings.length > 0,
    observacao_reconciliacao: dre.warnings.length > 0 ? "Valores sujeitos à reconciliação." : null,
    warnings_relevantes: dre.warnings
      .filter((warning) => warning.severidade === "INCONSISTENCIA_MODERADA" || warning.severidade === "RISCO_ECONOMICO")
      .map((warning) => warning.codigo),
  };
}

export default function DREAgricolaV1Page() {
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
    queryKey: ["agricola-dre", "safras", safraScopeId],
    queryFn: () => apiFetch(`/safras/${safraScopeId ? `?unidade_produtiva_id=${safraScopeId}` : ""}`),
    enabled: hasProfessionalTier,
  });

  const effectiveSafraId = selectedSafraId || safras[0]?.id || "";

  const { data: productionUnits = [], isLoading: isLoadingProductionUnits } = useQuery<ProductionUnitResumo[]>({
    queryKey: ["agricola-dre", "production-units", effectiveSafraId],
    queryFn: () => apiFetch(`/safras/${effectiveSafraId}/production-units`),
    enabled: hasProfessionalTier && !!effectiveSafraId,
  });

  const dreParams = useMemo(() => {
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
    data: dre,
    isLoading: isLoadingDre,
    isError: isErrorDre,
    error: dreError,
  } = useQuery<DREAgricolaResponse>({
      queryKey: ["agricola-dre", "v1", dreParams],
    queryFn: () => apiFetch("/agricola/dre/v1", { params: dreParams ?? undefined }),
    enabled: hasProfessionalTier && !!dreParams,
  });

  const safraAtual = safras.find((safra) => safra.id === effectiveSafraId) ?? null;
  const periodDetails = dre?.reconciliacao?.detalhes?.periodo ?? dre?.reconciliacao?.detalhes?.period ?? null;
  const kpis = dre ? (dre.kpis ?? buildFallbackKpis(dre)) : null;
  const periodLabel =
    periodDetails?.data_inicio || periodDetails?.data_fim
      ? `${formatDate(periodDetails.data_inicio)} → ${formatDate(periodDetails.data_fim)}`
      : "Sem recorte temporal";

  const hasData = Boolean(
    dre &&
      (dre.receita_bruta !== 0 ||
        dre.custos_diretos !== 0 ||
        dre.custos_operacionais !== 0 ||
        dre.despesas_operacionais !== 0 ||
        dre.warnings.length > 0 ||
        sectionHasData(dre.receita) ||
        sectionHasData(dre.custos_diretos_detalhe) ||
        sectionHasData(dre.custos_operacionais_detalhe) ||
        sectionHasData(dre.despesas_operacionais_detalhe))
  );

  const resultadoTone = dre ? (dre.resultado_operacional < 0 ? "destructive" : "success") : "muted";
  const margemTone = dre ? (dre.margem_bruta < 0 ? "destructive" : "success") : "muted";

  if (!hasProfessionalTier) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <PageHeader
          title="DRE Agrícola v1"
          description="Consolidação econômica somente leitura para validação controlada."
          breadcrumbs={[
            { label: "Agrícola", href: "/dashboard/agricola" },
            { label: "DRE Agrícola v1" },
          ]}
          icon={<LineChart className="size-5" />}
        />
        <TierUpgradeCard
          title="DRE agrícola disponível no PROFISSIONAL"
          description="A DRE agrícola v1 é uma visão técnica controlada, baseada em Receita e CostAllocation com reconciliação financeira e física."
          requiredTier="PROFISSIONAL"
          feature="agricola.dre_v1"
          surface="agricola.dre.page"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="DRE Agrícola v1"
        description="Visão técnica somente leitura, consolidada pela precedência econômica oficial."
        breadcrumbs={[
          { label: "Agrícola", href: "/dashboard/agricola" },
          { label: "Relatórios", href: "/dashboard/agricola/relatorios" },
          { label: "DRE Agrícola v1" },
        ]}
        actions={(
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola/rentabilidade">
                <TrendingUp className="size-4" />
                Rentabilidade oficial
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/agricola/relatorios">
                Voltar aos relatórios
              </Link>
            </Button>
          </div>
        )}
        icon={<LineChart className="size-5" />}
      />

      <Alert variant="info">
        <AlertCircle />
        <AlertTitle>Leitura controlada</AlertTitle>
        <AlertDescription>
          Receita e CostAllocation são fontes oficiais. LancamentoFinanceiro e EstoqueMovimento entram apenas na reconciliação.
        </AlertDescription>
      </Alert>

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <CalendarRange className="size-4 text-muted-foreground" />
            Filtros de validação
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-4">
            <div className="flex flex-col gap-1.5">
              <label id="dre-safra-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
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
                <SelectTrigger aria-labelledby="dre-safra-label" data-testid="dre-safra-select">
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
              <p className="text-xs text-muted-foreground">Obrigatório para consolidar a DRE.</p>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="dre-unidade-prod-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Unidade produtiva
              </label>
              <Select
                value={effectiveUnidadeProdutivaId || "TODAS"}
                onValueChange={(value) => {
                  setSelectedUnidadeProdutivaId(value === "TODAS" ? "" : value);
                }}
                disabled={unidadesProdutivas.length === 0}
              >
                  <SelectTrigger aria-labelledby="dre-unidade-prod-label" data-testid="dre-unidade-produtiva-select">
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
              <p className="text-xs text-muted-foreground">Opcional, filtra a origem econômica por fazenda.</p>
            </div>

            <div className="flex flex-col gap-1.5">
              <label id="dre-pu-label" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                ProductionUnit
              </label>
              <Select
                value={selectedProductionUnitId}
                onValueChange={setSelectedProductionUnitId}
                disabled={!selectedSafraId || isLoadingProductionUnits}
              >
                <SelectTrigger aria-labelledby="dre-pu-label" data-testid="dre-production-unit-select">
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
              <p className="text-xs text-muted-foreground">Opcional, refina a consolidação na safra.</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="dre-data-inicio" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data inicial
                </label>
                <Input
                  id="dre-data-inicio"
                  data-testid="dre-data-inicio"
                  type="date"
                  value={dataInicio}
                  onChange={(event) => setDataInicio(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="dre-data-fim" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Data final
                </label>
                <Input
                  id="dre-data-fim"
                  data-testid="dre-data-fim"
                  type="date"
                  value={dataFim}
                  onChange={(event) => setDataFim(event.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="rounded-sm">Somente leitura</Badge>
            <Badge variant="secondary" className="rounded-sm">Receita + CostAllocation</Badge>
            <Badge variant="warning" className="rounded-sm">Reconciliacao: LancamentoFinanceiro + EstoqueMovimento</Badge>
          </div>
        </CardContent>
      </Card>

      {isLoadingSafras || isLoadingDre ? (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} className="h-28 rounded-sm" />
            ))}
          </div>
          <Skeleton className="h-72 rounded-sm" />
          <Skeleton className="h-60 rounded-sm" />
        </div>
      ) : isErrorSafras ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao carregar safras</AlertTitle>
          <AlertDescription>{safraError instanceof Error ? safraError.message : "Não foi possível listar as safras para consolidar a DRE."}</AlertDescription>
        </Alert>
      ) : isErrorDre ? (
        <Alert variant="destructive" className="rounded-sm">
          <AlertCircle className="size-4" />
          <AlertTitle>Falha ao consolidar a DRE v1</AlertTitle>
          <AlertDescription>{dreError instanceof Error ? dreError.message : "Não foi possível carregar a DRE agrícola."}</AlertDescription>
        </Alert>
      ) : dre ? (
        <div className="flex flex-col gap-6">
          <AgricolaDreKpis kpis={kpis} fallback={dre.kpis ? undefined : buildFallbackKpis(dre)} />

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              icon={Sprout}
              label="Receita Bruta"
              value={formatCurrency(dre.receita_bruta)}
              subtitle={joinSourceSummary(dre.receita)}
              color="success"
            />
            <StatCard
              icon={TrendingDown}
              label="Deduções"
              value={formatCurrency(dre.deducoes)}
              subtitle={`${dre.receita.total_registros} lançamento(s) de receita`}
              color="warning"
            />
            <StatCard
              icon={Wallet}
              label="Receita Líquida"
              value={formatCurrency(dre.receita_liquida)}
              subtitle={`Fonte oficial: Receita`}
              color="primary"
            />
            <StatCard
              icon={Factory}
              label="Custos Diretos"
              value={formatCurrency(dre.custos_diretos)}
              subtitle={joinSourceSummary(dre.custos_diretos_detalhe)}
              color="warning"
            />
            <StatCard
              icon={Layers3}
              label="Custos Operacionais"
              value={formatCurrency(dre.custos_operacionais)}
              subtitle={joinSourceSummary(dre.custos_operacionais_detalhe)}
              color="warning"
            />
            <StatCard
              icon={TrendingUp}
              label="Margem Bruta"
              value={formatCurrency(dre.margem_bruta)}
              subtitle={`Receita Líquida - Custos Diretos`}
              color={margemTone}
            />
            <StatCard
              icon={Tractor}
              label="Despesas Operacionais"
              value={formatCurrency(dre.despesas_operacionais)}
              subtitle={joinSourceSummary(dre.despesas_operacionais_detalhe)}
              color="warning"
            />
            <StatCard
              icon={LineChart}
              label="Resultado Operacional"
              value={formatCurrency(dre.resultado_operacional)}
              subtitle={`Margem Bruta - custos operacionais - despesas`}
              color={resultadoTone}
            />
          </div>

          {!hasData && (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-0">
                <EmptyState
                  icon={<LineChart />}
                  title="DRE zerada no recorte selecionado"
                  description="Não há Receita ou CostAllocation válidos na janela econômica atual. Ajuste safra, período ou unidade para validar outro recorte."
                  action={{
                    label: "Limpar período",
                    onClick: () => {
                      setDataInicio("");
                      setDataFim("");
                    },
                  }}
                />
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Layers3 className="size-4 text-muted-foreground" />
                  Precedência e fontes oficiais
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-sm border border-border/70 bg-muted/20 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Receita</p>
                    <p className="mt-1 font-medium">Fonte oficial: Receita</p>
                    <p className="text-xs text-muted-foreground mt-1">Reflete comercialização e romaneio, sem duplicar lançamento financeiro.</p>
                  </div>
                  <div className="rounded-sm border border-border/70 bg-muted/20 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Custos</p>
                    <p className="mt-1 font-medium">Fonte oficial: CostAllocation</p>
                    <p className="text-xs text-muted-foreground mt-1">CostAllocation apropria o custo; EstoqueMovimento e LancamentoFinanceiro apenas reconciliam.</p>
                  </div>
                  <div className="rounded-sm border border-border/70 bg-muted/20 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Despesa</p>
                    <p className="mt-1 font-medium">Obrigação financeira, não linha de receita</p>
                    <p className="text-xs text-muted-foreground mt-1">Só entra quando não foi apropriada em camada superior.</p>
                  </div>
                  <div className="rounded-sm border border-border/70 bg-muted/20 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Reconciliação</p>
                    <p className="mt-1 font-medium">LancamentoFinanceiro + EstoqueMovimento</p>
                    <p className="text-xs text-muted-foreground mt-1">Usados para verificar consistência econômica e gerar warnings.</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CalendarRange className="size-4 text-muted-foreground" />
                  Metadados do recorte
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
                  <p className="mt-1 font-medium">{formatDate(dre.gerado_em)}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">ProductionUnits</p>
                  <p className="mt-1 font-medium">{dre.production_unit_ids.length} unidade(s)</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="size-4 text-muted-foreground" />
                Observabilidade econômica
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <Alert className="rounded-sm">
                <AlertDescription>
                  {dre.reconciliacao.observacao ?? "A reconciliação econômica foi calculada com base na precedência oficial da DRE agrícola v1."}
                </AlertDescription>
              </Alert>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Lançamentos de receita</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{formatCurrency(dre.reconciliacao.lancamentos_financeiros_receita)}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Lançamentos de custo</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{formatCurrency(dre.reconciliacao.lancamentos_financeiros_custo)}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">CostAllocations</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{dre.reconciliacao.cost_allocations_total}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Movimentos com custo</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{dre.reconciliacao.estoque_movimentos_com_custo}</p>
                </div>
                <div className="rounded-sm border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Deduções por precedência</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{dre.reconciliacao.receitas_excluidas_por_precedencia + dre.reconciliacao.despesas_excluidas_por_precedencia}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-sm shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="size-4 text-muted-foreground" />
                Warnings e inconsistências
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {dre.warnings.length === 0 ? (
                <EmptyState
                  icon={<AlertCircle />}
                  title="Nenhum warning no recorte atual"
                  description="A consolidação econômica não encontrou inconsistências relevantes no período e filtros aplicados."
                />
              ) : (
                dre.warnings.map((warning) => {
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
                        <Badge variant="outline" className={cn("rounded-sm", warning.severidade === "RISCO_ECONOMICO" && "border-destructive text-destructive")}>
                          {warningOrigemLabel(warning.origem)}
                        </Badge>
                      </div>
                      {warning.amostras.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {warning.amostras.slice(0, 4).map((sample, idx) => (
                            <Badge key={`${warning.codigo}-${warning.origem}-${idx}`} variant="secondary" className="rounded-sm">
                              {sample}
                            </Badge>
                          ))}
                        </div>
                      )}
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
