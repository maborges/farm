"use client";

import { use, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BarChart2,
  CheckCircle2,
  Gauge,
  Layers,
  LineChart,
  RefreshCw,
  Scale,
  TrendingDown,
  TrendingUp,
  Wheat,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHasTier } from "@/hooks/use-has-tier";
import { getSafraLabel } from "@/lib/safra-label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CenarioListItem {
  id: string;
  nome: string;
  tipo: string;
  eh_base: boolean;
  status: string;
  area_total_ha: number | null;
  receita_bruta_total: number | null;
  custo_total: number | null;
  margem_contribuicao_total: number | null;
  resultado_liquido_total: number | null;
  ponto_equilibrio_sc_ha: number | null;
  calculado_em: string | null;
}

interface Safra {
  id: string;
  cultura: string | null;
  ano_safra: string;
  nome?: string | null;
}

interface CenarioUnidade {
  production_unit_id: string;
  cultivo_nome: string | null;
  area_nome: string | null;
  area_ha: number;
  produtividade_efetiva?: number | null;
  preco_efetivo?: number | null;
  custo_ha_efetivo?: number | null;
  receita_bruta: number | null;
  custo_total: number | null;
  margem_contribuicao: number | null;
  margem_pct: number | null;
  ponto_equilibrio: number | null;
}

interface ComparativoColuna {
  cenario_id: string;
  nome: string;
  tipo: string;
  eh_base: boolean;
  area_total_ha: number | null;
  receita_bruta_total: number | null;
  custo_total: number | null;
  margem_contribuicao_total: number | null;
  resultado_liquido_total: number | null;
  ponto_equilibrio_sc_ha: number | null;
  unidades: CenarioUnidade[];
}

interface ProductionUnit {
  id: string;
  cultivo_nome: string | null;
  area_nome: string | null;
  percentual_participacao: number;
  area_ha: number;
  status: "ATIVA" | "ENCERRADA";
}

interface ExecutiveAlert {
  id: string;
  severity: "critical" | "warning" | "ok";
  origin: "Cenário" | "Comparativo" | "Unidade Produtiva";
  title: string;
  description: string;
  actionLabel: string;
  actionHref?: string;
  actionMetric?: DrilldownMetric;
  entityId?: string;
}

const MAX_COMPARATIVO = 3;
const INITIAL_PU_LIMIT = 10;
const INITIAL_DRILLDOWN_LIMIT = 10;
const INITIAL_ALERT_LIMIT = 5;
const MAX_ALERTS_PER_PU = 2;
const INITIAL_SCENARIO_PU_LIMIT = 10;

type DrilldownMetric = "receita" | "custo" | "margem" | "ponto_equilibrio";

interface DrilldownConfig {
  label: string;
  description: string;
  valueLabel: string;
  emptyMessage: string;
}

const DRILLDOWN_CONFIG: Record<DrilldownMetric, DrilldownConfig> = {
  receita: {
    label: "Receita projetada",
    description: "Composição da receita bruta por unidade produtiva no cenário base.",
    valueLabel: "Receita",
    emptyMessage: "O cenário base não possui unidades com receita calculada.",
  },
  custo: {
    label: "Custo total",
    description: "Composição do custo total por unidade produtiva no cenário base.",
    valueLabel: "Custo",
    emptyMessage: "O cenário base não possui unidades com custo calculado.",
  },
  margem: {
    label: "Margem",
    description: "Ranking de margem por unidade produtiva, priorizando os piores desempenhos.",
    valueLabel: "Margem",
    emptyMessage: "O cenário base não possui unidades com margem calculada.",
  },
  ponto_equilibrio: {
    label: "Ponto de equilíbrio",
    description: "Unidades produtivas com maior ponto de equilíbrio aparecem primeiro.",
    valueLabel: "Ponto de equilíbrio",
    emptyMessage: "O cenário base não possui ponto de equilíbrio por unidade.",
  },
};

const TIPO_LABEL: Record<string, string> = {
  BASE: "Base",
  OTIMISTA: "Otimista",
  PESSIMISTA: "Pessimista",
  CUSTOM: "Personalizado",
};

function fmtBRL(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function marginPct(receita: number | null | undefined, margem: number | null | undefined): number | null {
  if (!receita || margem === null || margem === undefined) return null;
  return (margem / receita) * 100;
}

function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${fmtNum(value, 1)}%`;
}

function statusTone(margemPct: number | null, margem: number | null | undefined): "ok" | "warn" | "risk" {
  if ((margem ?? 0) < 0) return "risk";
  if (margemPct !== null && margemPct < 10) return "warn";
  return "ok";
}

function riskLabel(tone: "ok" | "warn" | "risk"): string {
  if (tone === "risk") return "Crítico";
  if (tone === "warn") return "Atenção";
  return "Saudável";
}

function pickScenarioIds(cenarios: CenarioListItem[]): string[] {
  const ativos = cenarios.filter((cenario) => cenario.status === "ATIVO");
  const base = ativos.find((cenario) => cenario.eh_base) ?? null;
  const selected: CenarioListItem[] = [];

  if (base) selected.push(base);

  const byMargin = [...ativos]
    .filter((cenario) => cenario.id !== base?.id)
    .sort((a, b) => (b.margem_contribuicao_total ?? -Infinity) - (a.margem_contribuicao_total ?? -Infinity));

  for (const cenario of byMargin) {
    if (selected.length >= MAX_COMPARATIVO) break;
    selected.push(cenario);
  }

  return selected.slice(0, MAX_COMPARATIVO).map((cenario) => cenario.id);
}

function KpiCard({
  label,
  value,
  subtitle,
  icon: Icon,
  tone = "default",
  active = false,
  onClick,
}: {
  label: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  tone?: "default" | "ok" | "warn" | "risk";
  active?: boolean;
  onClick?: () => void;
}) {
  const toneClass = {
    default: "bg-muted text-muted-foreground",
    ok: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    warn: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    risk: "bg-destructive/10 text-destructive",
  }[tone];

  return (
    <Card className={cn("rounded-sm shadow-sm transition-colors", active && "border-primary bg-primary/5")}>
      <CardContent className="p-0">
        {onClick ? (
          <button type="button" className="flex w-full items-start gap-3 p-4 text-left" onClick={onClick}>
            <KpiCardContent Icon={Icon} label={label} subtitle={subtitle} toneClass={toneClass} value={value} active={active} />
          </button>
        ) : (
          <div className="flex items-start gap-3 p-4">
            <KpiCardContent Icon={Icon} label={label} subtitle={subtitle} toneClass={toneClass} value={value} active={active} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function KpiCardContent({
  Icon,
  label,
  value,
  subtitle,
  toneClass,
  active,
}: {
  Icon: React.ElementType;
  label: string;
  value: string;
  subtitle?: string;
  toneClass: string;
  active: boolean;
}) {
  return (
    <>
        <div className={cn("rounded-sm p-2", toneClass)}>
          <Icon className="size-4" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-xs text-muted-foreground">{label}</p>
            {active && <Badge variant="secondary">Detalhando</Badge>}
          </div>
          <p className="mt-0.5 text-xl font-semibold tabular-nums">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          <p className="mt-1 text-xs text-primary">{active ? "Ocultar detalhes" : "Ver detalhes"}</p>
        </div>
    </>
  );
}

function ApiErrorAlert({ title, error }: { title: string; error: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="size-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        {error instanceof Error ? error.message : "Não foi possível carregar os dados. Tente novamente."}
      </AlertDescription>
    </Alert>
  );
}

function getMetricValue(unit: CenarioUnidade, metric: DrilldownMetric): number | null {
  if (metric === "receita") return unit.receita_bruta;
  if (metric === "custo") return unit.custo_total;
  if (metric === "margem") return unit.margem_contribuicao;
  return unit.ponto_equilibrio;
}

function getMetricTotal(scenario: ComparativoColuna | null, metric: DrilldownMetric): number | null {
  if (!scenario) return null;
  if (metric === "receita") return scenario.receita_bruta_total;
  if (metric === "custo") return scenario.custo_total;
  if (metric === "margem") return scenario.margem_contribuicao_total;
  return null;
}

function formatMetricValue(value: number | null, metric: DrilldownMetric): string {
  if (metric === "ponto_equilibrio") return value === null ? "—" : `${fmtNum(value, 2)} sc/ha`;
  return fmtBRL(value);
}

function sortUnitsByMetric(units: CenarioUnidade[], metric: DrilldownMetric): CenarioUnidade[] {
  return [...units].sort((a, b) => {
    const av = getMetricValue(a, metric) ?? (metric === "margem" ? Infinity : -Infinity);
    const bv = getMetricValue(b, metric) ?? (metric === "margem" ? Infinity : -Infinity);

    if (metric === "margem") return av - bv;
    return bv - av;
  });
}

function findUnitInScenario(scenario: ComparativoColuna, puId: string): CenarioUnidade | null {
  return scenario.unidades?.find((unit) => unit.production_unit_id === puId) ?? null;
}

function normalizeScenarioProductionUnits(scenarios: ComparativoColuna[]): CenarioUnidade[] {
  const byId = new Map<string, CenarioUnidade>();

  for (const scenario of scenarios) {
    for (const unit of scenario.unidades ?? []) {
      if (!byId.has(unit.production_unit_id)) {
        byId.set(unit.production_unit_id, unit);
      }
    }
  }

  const base = scenarios.find((scenario) => scenario.eh_base) ?? scenarios[0] ?? null;

  return [...byId.values()].sort((a, b) => {
    const aBase = base ? findUnitInScenario(base, a.production_unit_id) : null;
    const bBase = base ? findUnitInScenario(base, b.production_unit_id) : null;
    const aMargin = aBase?.margem_contribuicao;
    const bMargin = bBase?.margem_contribuicao;

    if (aMargin != null || bMargin != null) {
      return (aMargin ?? Infinity) - (bMargin ?? Infinity);
    }

    const aRevenue = aBase?.receita_bruta ?? a.receita_bruta;
    const bRevenue = bBase?.receita_bruta ?? b.receita_bruta;
    if (aRevenue != null || bRevenue != null) {
      return (bRevenue ?? -Infinity) - (aRevenue ?? -Infinity);
    }

    return (b.area_ha ?? 0) - (a.area_ha ?? 0);
  });
}

function safeDelta(value: number | null | undefined, base: number | null | undefined): { absolute: number | null; pct: number | null } {
  if (value == null || base == null) return { absolute: null, pct: null };
  const absolute = value - base;
  if (base === 0) return { absolute, pct: null };
  return { absolute, pct: (absolute / Math.abs(base)) * 100 };
}

function deltaIsGood(metric: "receita" | "custo" | "margem" | "ponto_equilibrio", absolute: number | null): boolean | null {
  if (absolute === null || Math.abs(absolute) < 0.0001) return null;
  if (metric === "custo" || metric === "ponto_equilibrio") return absolute < 0;
  return absolute > 0;
}

function formatDelta(
  value: number | null | undefined,
  base: number | null | undefined,
  metric: "receita" | "custo" | "margem" | "ponto_equilibrio",
): { label: string; tone: "ok" | "risk" | "neutral" } | null {
  const delta = safeDelta(value, base);
  if (delta.absolute === null || Math.abs(delta.absolute) < 0.0001) return null;
  const good = deltaIsGood(metric, delta.absolute);
  const formatted = metric === "ponto_equilibrio"
    ? `${delta.absolute > 0 ? "+" : ""}${fmtNum(delta.absolute, 2)} sc/ha`
    : `${delta.absolute > 0 ? "+" : ""}${fmtBRL(delta.absolute)}`;
  const pct = delta.pct === null ? "" : ` (${delta.pct > 0 ? "+" : ""}${fmtPct(delta.pct)})`;

  return {
    label: `${formatted}${pct}`,
    tone: good === null ? "neutral" : good ? "ok" : "risk",
  };
}

function getBestByMargin(scenarios: ComparativoColuna[], puId: string): { scenario: ComparativoColuna; unit: CenarioUnidade } | null {
  const rows = scenarios
    .map((scenario) => {
      const unit = findUnitInScenario(scenario, puId);
      return unit ? { scenario, unit } : null;
    })
    .filter((row): row is { scenario: ComparativoColuna; unit: CenarioUnidade } => !!row && row.unit.margem_contribuicao != null);

  return rows.sort((a, b) => (b.unit.margem_contribuicao ?? -Infinity) - (a.unit.margem_contribuicao ?? -Infinity))[0] ?? null;
}

function getWorstByMargin(scenarios: ComparativoColuna[], puId: string): { scenario: ComparativoColuna; unit: CenarioUnidade } | null {
  const rows = scenarios
    .map((scenario) => {
      const unit = findUnitInScenario(scenario, puId);
      return unit ? { scenario, unit } : null;
    })
    .filter((row): row is { scenario: ComparativoColuna; unit: CenarioUnidade } => !!row && row.unit.margem_contribuicao != null);

  return rows.sort((a, b) => (a.unit.margem_contribuicao ?? Infinity) - (b.unit.margem_contribuicao ?? Infinity))[0] ?? null;
}

function severityRank(severity: ExecutiveAlert["severity"]): number {
  if (severity === "critical") return 0;
  if (severity === "warning") return 1;
  return 2;
}

function addUniqueAlert(alerts: ExecutiveAlert[], seen: Set<string>, alert: ExecutiveAlert) {
  if (seen.has(alert.id)) return;
  seen.add(alert.id);
  alerts.push(alert);
}

function buildExecutiveAlerts({
  safraId,
  cenarios,
  cenarioBase,
  baseScenario,
  productionUnits,
  productionUnitsLoaded,
}: {
  safraId: string;
  cenarios: CenarioListItem[];
  cenarioBase: CenarioListItem | null;
  baseScenario: ComparativoColuna | null;
  productionUnits: ProductionUnit[];
  productionUnitsLoaded: boolean;
}): ExecutiveAlert[] {
  const alerts: ExecutiveAlert[] = [];
  const seen = new Set<string>();
  const activeScenarios = cenarios.filter((cenario) => cenario.status === "ATIVO");
  const activeProductionUnits = productionUnits.filter((unit) => unit.status === "ATIVA");

  if (activeScenarios.length === 0) {
    addUniqueAlert(alerts, seen, {
      id: "NO_ACTIVE_SCENARIOS",
      severity: "critical",
      origin: "Cenário",
      title: "Nenhum cenário ativo disponível",
      description: "Crie ou reative um cenário para liberar análise executiva da safra.",
      actionLabel: "Abrir Cenários",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
    return alerts;
  }

  if (!cenarioBase) {
    addUniqueAlert(alerts, seen, {
      id: "NO_BASE_SCENARIO",
      severity: "critical",
      origin: "Cenário",
      title: "Cenário base ausente",
      description: "Defina ou recalcule um cenário base antes de tomar decisão sobre a safra.",
      actionLabel: "Abrir Cenários",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
  }

  if (cenarioBase && !cenarioBase.calculado_em) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_NOT_CALCULATED",
      severity: "warning",
      origin: "Cenário",
      title: "Cenário base sem data de cálculo",
      description: "Recalcule o cenário base para garantir que os indicadores reflitam os dados atuais.",
      actionLabel: "Revisar Cenários",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
  }

  const baseMarginPct = cenarioBase
    ? marginPct(cenarioBase.receita_bruta_total, cenarioBase.margem_contribuicao_total)
    : null;

  if (cenarioBase && (cenarioBase.margem_contribuicao_total ?? 0) < 0) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_MARGIN_NEGATIVE",
      severity: "critical",
      origin: "Cenário",
      title: "Margem negativa no cenário base",
      description: "Abra o drill-down de margem para localizar as unidades que mais pressionam o resultado.",
      actionLabel: "Ver margem da unidade",
      actionMetric: "margem",
    });
  } else if (
    cenarioBase?.receita_bruta_total != null
    && cenarioBase?.custo_total != null
    && cenarioBase.custo_total > cenarioBase.receita_bruta_total
  ) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_COST_GT_REVENUE",
      severity: "critical",
      origin: "Cenário",
      title: "Custo maior que receita no cenário base",
      description: "Revise os cenários e abra o drill-down de custo para encontrar os maiores ofensores.",
      actionLabel: "Ver custo da unidade",
      actionMetric: "custo",
    });
  }

  if (cenarioBase && baseMarginPct !== null && baseMarginPct >= 0 && baseMarginPct < 10) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_MARGIN_LOW",
      severity: "warning",
      origin: "Cenário",
      title: "Margem operacional baixa",
      description: "Analise a margem por unidade produtiva antes de assumir compromissos comerciais.",
      actionLabel: "Ver margem da unidade",
      actionMetric: "margem",
    });
  }

  if (cenarioBase && cenarioBase.ponto_equilibrio_sc_ha == null) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_BREAK_EVEN_MISSING",
      severity: "warning",
      origin: "Cenário",
      title: "Ponto de equilíbrio ausente",
      description: "Recalcule ou revise o cenário para exibir o ponto de equilíbrio da safra.",
      actionLabel: "Abrir Cenários",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
  }

  if (activeScenarios.length === 1) {
    addUniqueAlert(alerts, seen, {
      id: "ONLY_ONE_ACTIVE_SCENARIO",
      severity: "warning",
      origin: "Comparativo",
      title: "Comparativo limitado a um cenário",
      description: "Crie cenários alternativos para avaliar sensibilidade de preço, custo e produtividade.",
      actionLabel: "Criar cenário",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
  }

  const pessimisticNegative = activeScenarios.find(
    (cenario) => cenario.tipo === "PESSIMISTA" && (cenario.margem_contribuicao_total ?? 0) < 0,
  );
  if (pessimisticNegative) {
    addUniqueAlert(alerts, seen, {
      id: "PESSIMISTIC_MARGIN_NEGATIVE",
      severity: "warning",
      origin: "Comparativo",
      title: "Cenário pessimista com margem negativa",
      description: "Abra o comparativo completo para avaliar o impacto do pior cenário no plano da safra.",
      actionLabel: "Abrir Comparativo",
      actionHref: `/agricola/safras/${safraId}/cenarios/comparativo`,
    });
  }

  if (baseScenario && (baseScenario.unidades?.length ?? 0) === 0) {
    addUniqueAlert(alerts, seen, {
      id: "BASE_SCENARIO_WITHOUT_UNITS",
      severity: "warning",
      origin: "Comparativo",
      title: "Cenário base sem unidades detalhadas",
      description: "Recalcule o cenário base para habilitar análise por unidade produtiva.",
      actionLabel: "Abrir Cenários",
      actionHref: `/agricola/safras/${safraId}/cenarios`,
    });
  }

  if (productionUnitsLoaded && activeProductionUnits.length === 0) {
    addUniqueAlert(alerts, seen, {
      id: "NO_ACTIVE_PRODUCTION_UNITS",
      severity: "critical",
      origin: "Unidade Produtiva",
      title: "Nenhuma unidade produtiva ativa",
      description: "Cadastre ou reative unidades produtivas antes de confiar nos indicadores executivos.",
      actionLabel: "Gerenciar unidades produtivas",
      actionHref: `/agricola/safras/${safraId}/production-units`,
    });
  }

  const baseUnits = baseScenario?.unidades ?? [];
  const baseUnitIds = new Set(baseUnits.map((unit) => unit.production_unit_id));

  if (productionUnitsLoaded && baseScenario && activeProductionUnits.length > 0) {
    const missingUnit = activeProductionUnits.find((unit) => !baseUnitIds.has(unit.id));
    if (missingUnit) {
      addUniqueAlert(alerts, seen, {
        id: "ACTIVE_PU_MISSING_FROM_BASE",
        severity: "warning",
        origin: "Unidade Produtiva",
        title: "Há unidade produtiva ativa fora do cenário base",
        description: "Recalcule o cenário base para incluir todas as unidades ativas da safra.",
        actionLabel: "Revisar Cenários",
        actionHref: `/agricola/safras/${safraId}/cenarios`,
      });
    }
  }

  const puAlertCounts = new Map<string, number>();
  const addPuAlert = (unit: CenarioUnidade, alert: ExecutiveAlert) => {
    const count = puAlertCounts.get(unit.production_unit_id) ?? 0;
    if (count >= MAX_ALERTS_PER_PU) return;
    puAlertCounts.set(unit.production_unit_id, count + 1);
    addUniqueAlert(alerts, seen, alert);
  };

  for (const unit of baseUnits) {
    const label = [unit.cultivo_nome, unit.area_nome].filter(Boolean).join(" / ") || unit.production_unit_id.slice(0, 8);
    const unitMarginPct = unit.margem_pct ?? marginPct(unit.receita_bruta, unit.margem_contribuicao);

    if ((unit.margem_contribuicao ?? 0) < 0) {
      addPuAlert(unit, {
        id: `PU_MARGIN_NEGATIVE:${unit.production_unit_id}`,
        entityId: unit.production_unit_id,
        severity: "critical",
        origin: "Unidade Produtiva",
        title: `${label} com margem negativa`,
        description: "Abra o drill-down de margem e revise preço, produtividade ou custo dessa unidade.",
        actionLabel: "Ver margem da unidade",
        actionMetric: "margem",
      });
    } else if (
      unit.receita_bruta != null
      && unit.custo_total != null
      && unit.custo_total > unit.receita_bruta
    ) {
      addPuAlert(unit, {
        id: `PU_COST_GT_REVENUE:${unit.production_unit_id}`,
        entityId: unit.production_unit_id,
        severity: "critical",
        origin: "Unidade Produtiva",
        title: `${label} com custo maior que receita`,
        description: "Abra o drill-down de custo para priorizar a revisão dessa unidade.",
        actionLabel: "Ver custo da unidade",
        actionMetric: "custo",
      });
    }

    if (unitMarginPct !== null && unitMarginPct >= 0 && unitMarginPct < 10) {
      addPuAlert(unit, {
        id: `PU_MARGIN_LOW:${unit.production_unit_id}`,
        entityId: unit.production_unit_id,
        severity: "warning",
        origin: "Unidade Produtiva",
        title: `${label} com margem baixa`,
        description: "Revise a unidade no drill-down antes de ajustar o cenário consolidado.",
        actionLabel: "Ver margem da unidade",
        actionMetric: "margem",
      });
    }

    if (unit.receita_bruta == null || unit.custo_total == null || unit.margem_contribuicao == null) {
      addPuAlert(unit, {
        id: `PU_INCOMPLETE_ECONOMICS:${unit.production_unit_id}`,
        entityId: unit.production_unit_id,
        severity: "warning",
        origin: "Unidade Produtiva",
        title: `${label} com indicador econômico incompleto`,
        description: "Recalcule o cenário base para completar receita, custo e margem da unidade.",
        actionLabel: "Abrir Cenários",
        actionHref: `/agricola/safras/${safraId}/cenarios`,
      });
    }
  }

  return alerts.sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
}

function KpiDrilldownPanel({
  metric,
  baseScenario,
  isLoading,
  error,
  isError,
  showAll,
  onShowAllChange,
  onLoadDetails,
  safraId,
}: {
  metric: DrilldownMetric;
  baseScenario: ComparativoColuna | null;
  isLoading: boolean;
  error: unknown;
  isError: boolean;
  showAll: boolean;
  onShowAllChange: (value: boolean) => void;
  onLoadDetails: () => void;
  safraId: string;
}) {
  const config = DRILLDOWN_CONFIG[metric];
  const sortedUnits = baseScenario ? sortUnitsByMetric(baseScenario.unidades ?? [], metric) : [];
  const visibleUnits = showAll ? sortedUnits : sortedUnits.slice(0, INITIAL_DRILLDOWN_LIMIT);
  const total = getMetricTotal(baseScenario, metric);

  return (
    <Card className="rounded-sm border-primary/30 shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Drill-down: {config.label}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{config.description}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/agricola/safras/${safraId}/production-units`}>Unidades produtivas</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/agricola/safras/${safraId}/cenarios`}>Cenários</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/agricola/safras/${safraId}/cenarios/comparativo`}>Comparativo</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {!baseScenario && !isLoading && !isError && (
          <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
            Os detalhes por unidade dependem do comparativo. Carregue os detalhes para investigar a origem deste KPI.
            <div className="mt-3">
              <Button size="sm" variant="outline" onClick={onLoadDetails}>
                <RefreshCw className="mr-1.5 size-3.5" />
                Carregar detalhes
              </Button>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        )}

        {isError && <ApiErrorAlert title="Erro ao carregar drill-down" error={error} />}

        {baseScenario && sortedUnits.length === 0 && (
          <Alert>
            <AlertCircle className="size-4" />
            <AlertTitle>Sem dados por unidade produtiva</AlertTitle>
            <AlertDescription>{config.emptyMessage}</AlertDescription>
          </Alert>
        )}

        {visibleUnits.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Unidade produtiva</TableHead>
                  <TableHead className="text-right">Área</TableHead>
                  <TableHead className="text-right">{config.valueLabel}</TableHead>
                  <TableHead className="text-right">Participação</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleUnits.map((unit, index) => {
                  const value = getMetricValue(unit, metric);
                  const pct = metric === "ponto_equilibrio" ? null : marginPct(total, value);
                  const unitMarginPct = unit.margem_pct ?? marginPct(unit.receita_bruta, unit.margem_contribuicao);
                  const tone = statusTone(unitMarginPct, unit.margem_contribuicao);
                  const highlightWorst = metric === "margem" ? index < 3 : tone !== "ok";

                  return (
                    <TableRow key={unit.production_unit_id} className={cn(highlightWorst && "bg-muted/30")}>
                      <TableCell>
                        <div className="flex flex-col">
                          <span className="font-medium">{unit.cultivo_nome ?? "Cultivo"}</span>
                          <span className="text-xs text-muted-foreground">{unit.area_nome ?? unit.production_unit_id.slice(0, 8)}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{fmtNum(unit.area_ha, 2)} ha</TableCell>
                      <TableCell className={cn("text-right tabular-nums", tone === "risk" && metric === "margem" && "text-destructive", tone === "warn" && metric === "margem" && "text-amber-700", tone === "ok" && metric === "margem" && "text-emerald-700")}>
                        {formatMetricValue(value, metric)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{metric === "ponto_equilibrio" ? "—" : fmtPct(pct)}</TableCell>
                      <TableCell>
                        <Badge variant={tone === "risk" ? "destructive" : tone === "warn" ? "secondary" : "outline"}>
                          {riskLabel(tone)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            {sortedUnits.length > INITIAL_DRILLDOWN_LIMIT && (
              <Button variant="outline" size="sm" onClick={() => onShowAllChange(!showAll)}>
                {showAll ? "Mostrar top 10" : `Mostrar todas (${sortedUnits.length})`}
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ExecutiveAlertsCard({
  alerts,
  showAll,
  onShowAllChange,
  onSelectMetric,
}: {
  alerts: ExecutiveAlert[];
  showAll: boolean;
  onShowAllChange: (value: boolean) => void;
  onSelectMetric: (metric: DrilldownMetric) => void;
}) {
  const criticalCount = alerts.filter((alert) => alert.severity === "critical").length;
  const warningCount = alerts.filter((alert) => alert.severity === "warning").length;
  const visibleAlerts = showAll ? alerts : alerts.slice(0, INITIAL_ALERT_LIMIT);

  if (alerts.length === 0) {
    return (
      <Card className="rounded-sm border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-950/20 shadow-sm">
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <div className="rounded-sm bg-emerald-500/20 p-2 text-emerald-700 dark:text-emerald-300">
              <CheckCircle2 className="size-4" />
            </div>
            <div>
              <p className="font-medium text-emerald-900 dark:text-emerald-200">Nenhum risco executivo detectado</p>
              <p className="text-sm text-emerald-800/80 dark:text-emerald-300/80">
                Os dados carregados da safra não indicam alertas críticos ou pontos de atenção neste momento.
              </p>
            </div>
          </div>
          <Badge variant="outline" className="border-emerald-500/30 text-emerald-800 dark:text-emerald-300 bg-emerald-500/5">
            Monitoramento saudável
          </Badge>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Alertas Executivos</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Riscos e inconsistências detectados com base nos dados carregados da safra.
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Badge variant={criticalCount > 0 ? "destructive" : "outline"}>{criticalCount} críticos</Badge>
          <Badge variant={warningCount > 0 ? "secondary" : "outline"}>{warningCount} atenção</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {visibleAlerts.map((alert) => (
          <div key={alert.id} className="flex flex-col gap-3 rounded-sm border p-3 md:flex-row md:items-start md:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <Badge variant={alert.severity === "critical" ? "destructive" : alert.severity === "warning" ? "secondary" : "outline"}>
                {alert.severity === "critical" ? "Crítico" : alert.severity === "warning" ? "Atenção" : "OK"}
              </Badge>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{alert.title}</p>
                  <Badge variant="outline">{alert.origin}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
              </div>
            </div>
            {alert.actionMetric ? (
              <Button size="sm" variant="outline" onClick={() => onSelectMetric(alert.actionMetric!)}>
                {alert.actionLabel}
              </Button>
            ) : (
              <Button size="sm" variant="outline" asChild>
                <Link href={alert.actionHref ?? "#"}>{alert.actionLabel}</Link>
              </Button>
            )}
          </div>
        ))}

        {alerts.length > INITIAL_ALERT_LIMIT && (
          <Button variant="outline" size="sm" onClick={() => onShowAllChange(!showAll)}>
            {showAll ? "Mostrar principais" : `Ver todos (${alerts.length})`}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ProductionUnitScenarioComparison({
  scenarios,
  isLoading,
  isError,
  error,
  selectedPuId,
  onSelectedPuIdChange,
  showAllUnits,
  onShowAllUnitsChange,
  onLoadComparativo,
  safraId,
}: {
  scenarios: ComparativoColuna[];
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  selectedPuId: string | null;
  onSelectedPuIdChange: (puId: string) => void;
  showAllUnits: boolean;
  onShowAllUnitsChange: (value: boolean) => void;
  onLoadComparativo: () => void;
  safraId: string;
}) {
  const limitedScenarios = scenarios.slice(0, MAX_COMPARATIVO);
  const normalizedUnits = normalizeScenarioProductionUnits(limitedScenarios);
  const visibleUnits = showAllUnits
    ? normalizedUnits
    : normalizedUnits.slice(0, INITIAL_SCENARIO_PU_LIMIT);
  const selectedUnit = normalizedUnits.find((unit) => unit.production_unit_id === selectedPuId) ?? normalizedUnits[0] ?? null;
  const selectedId = selectedUnit?.production_unit_id ?? null;
  const baseScenario = limitedScenarios.find((scenario) => scenario.eh_base) ?? null;
  const baseUnit = baseScenario && selectedId ? findUnitInScenario(baseScenario, selectedId) : null;
  const bestMargin = selectedId ? getBestByMargin(limitedScenarios, selectedId) : null;
  const worstMargin = selectedId ? getWorstByMargin(limitedScenarios, selectedId) : null;
  const highestCost = selectedId
    ? limitedScenarios
      .map((scenario) => {
        const unit = findUnitInScenario(scenario, selectedId);
        return unit ? { scenario, unit } : null;
      })
      .filter((row): row is { scenario: ComparativoColuna; unit: CenarioUnidade } => !!row && row.unit.custo_total != null)
      .sort((a, b) => (b.unit.custo_total ?? -Infinity) - (a.unit.custo_total ?? -Infinity))[0] ?? null
    : null;
  const bestBreakEven = selectedId
    ? limitedScenarios
      .map((scenario) => {
        const unit = findUnitInScenario(scenario, selectedId);
        return unit ? { scenario, unit } : null;
      })
      .filter((row): row is { scenario: ComparativoColuna; unit: CenarioUnidade } => !!row && row.unit.ponto_equilibrio != null)
      .sort((a, b) => (a.unit.ponto_equilibrio ?? Infinity) - (b.unit.ponto_equilibrio ?? Infinity))[0] ?? null
    : null;

  const metricRows: Array<{
    key: "receita" | "custo" | "margem" | "ponto_equilibrio";
    label: string;
    getValue: (unit: CenarioUnidade | null) => number | null | undefined;
    format: (value: number | null | undefined) => string;
  }> = [
    { key: "receita", label: "Receita", getValue: (unit) => unit?.receita_bruta, format: fmtBRL },
    { key: "custo", label: "Custo", getValue: (unit) => unit?.custo_total, format: fmtBRL },
    { key: "margem", label: "Margem", getValue: (unit) => unit?.margem_contribuicao, format: fmtBRL },
    {
      key: "ponto_equilibrio",
      label: "Ponto de equilíbrio",
      getValue: (unit) => unit?.ponto_equilibrio,
      format: (value) => value == null ? "—" : `${fmtNum(value, 2)} sc/ha`,
    },
  ];

  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-base">Comparação por unidade produtiva</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Compare cada unidade em até {MAX_COMPARATIVO} cenários carregados no comparativo executivo.
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/agricola/safras/${safraId}/production-units`}>Unidades produtivas</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/agricola/safras/${safraId}/cenarios/comparativo`}>Comparativo completo</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {limitedScenarios.length === 0 && !isLoading && !isError && (
          <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
            A comparação por unidade produtiva depende do comparativo. Carregue o comparativo para ver BASE, otimista,
            pessimista ou custom lado a lado.
            <div className="mt-3">
              <Button size="sm" variant="outline" onClick={onLoadComparativo}>
                <RefreshCw className="mr-1.5 size-3.5" />
                Carregar comparativo
              </Button>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {isError && <ApiErrorAlert title="Erro ao carregar comparação por unidade produtiva" error={error} />}

        {limitedScenarios.length > 0 && normalizedUnits.length === 0 && (
          <Alert>
            <AlertCircle className="size-4" />
            <AlertTitle>Nenhuma unidade disponível para comparação</AlertTitle>
            <AlertDescription>
              Os cenários carregados não retornaram unidades produtivas. Recalcule o cenário base ou revise as unidades da safra.
            </AlertDescription>
          </Alert>
        )}

        {limitedScenarios.length === 1 && normalizedUnits.length > 0 && (
          <Alert>
            <AlertCircle className="size-4" />
            <AlertTitle>Comparação limitada</AlertTitle>
            <AlertDescription>
              Há apenas um cenário carregado. Crie ou selecione cenários alternativos para comparar variações por unidade.
            </AlertDescription>
          </Alert>
        )}

        {selectedUnit && (
          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="flex flex-col gap-3">
              <div className="rounded-sm border p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Unidades produtivas</p>
                <div className="mt-3 flex flex-col gap-2">
                  {visibleUnits.map((unit) => {
                    const base = baseScenario ? findUnitInScenario(baseScenario, unit.production_unit_id) : null;
                    const unitMarginPct = base?.margem_pct ?? marginPct(base?.receita_bruta, base?.margem_contribuicao);
                    const tone = statusTone(unitMarginPct, base?.margem_contribuicao);
                    return (
                      <button
                        key={unit.production_unit_id}
                        type="button"
                        className={cn(
                          "rounded-sm border p-2 text-left transition-colors hover:bg-muted/40",
                          selectedId === unit.production_unit_id && "border-primary bg-primary/5",
                        )}
                        onClick={() => onSelectedPuIdChange(unit.production_unit_id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium">{unit.cultivo_nome ?? "Cultivo"}</p>
                            <p className="text-xs text-muted-foreground">{unit.area_nome ?? unit.production_unit_id.slice(0, 8)}</p>
                          </div>
                          <Badge variant={tone === "risk" ? "destructive" : tone === "warn" ? "secondary" : "outline"}>
                            {riskLabel(tone)}
                          </Badge>
                        </div>
                      </button>
                    );
                  })}
                </div>
                {normalizedUnits.length > INITIAL_SCENARIO_PU_LIMIT && (
                  <Button
                    className="mt-3 w-full"
                    size="sm"
                    variant="outline"
                    onClick={() => onShowAllUnitsChange(!showAllUnits)}
                  >
                    {showAllUnits ? "Mostrar top 10" : `Mostrar todas (${normalizedUnits.length})`}
                  </Button>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard title="Melhor margem" item={bestMargin} metric="margem" />
                <SummaryCard title="Pior margem" item={worstMargin} metric="margem" />
                <SummaryCard title="Maior custo" item={highestCost} metric="custo" />
                <SummaryCard title="Melhor PE" item={bestBreakEven} metric="ponto_equilibrio" />
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Indicador</TableHead>
                    {limitedScenarios.map((scenario) => (
                      <TableHead key={scenario.cenario_id} className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {scenario.nome}
                          {scenario.eh_base && <Badge variant="secondary">BASE</Badge>}
                        </div>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {metricRows.map((row) => {
                    const baseValue = row.getValue(baseUnit);
                    return (
                      <TableRow key={row.key}>
                        <TableCell className="font-medium">{row.label}</TableCell>
                        {limitedScenarios.map((scenario) => {
                          const unit = selectedId ? findUnitInScenario(scenario, selectedId) : null;
                          const value = row.getValue(unit);
                          const delta = scenario.eh_base ? null : formatDelta(value, baseValue, row.key);
                          return (
                            <TableCell key={scenario.cenario_id} className="text-right tabular-nums">
                              <div className="flex flex-col gap-0.5">
                                <span>{row.format(value)}</span>
                                {delta && (
                                  <span className={cn(
                                    "text-xs",
                                    delta.tone === "ok" && "text-emerald-700",
                                    delta.tone === "risk" && "text-destructive",
                                    delta.tone === "neutral" && "text-muted-foreground",
                                  )}>
                                    {delta.label}
                                  </span>
                                )}
                                {!unit && <span className="text-xs text-muted-foreground">Unidade produtiva ausente</span>}
                              </div>
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SummaryCard({
  title,
  item,
  metric,
}: {
  title: string;
  item: { scenario: ComparativoColuna; unit: CenarioUnidade } | null;
  metric: "margem" | "custo" | "ponto_equilibrio";
}) {
  const value = item
    ? metric === "margem"
      ? item.unit.margem_contribuicao
      : metric === "custo"
        ? item.unit.custo_total
        : item.unit.ponto_equilibrio
    : null;

  return (
    <div className="rounded-sm border p-3">
      <p className="text-xs text-muted-foreground">{title}</p>
      <p className="mt-1 text-sm font-semibold">{item?.scenario.nome ?? "—"}</p>
      <p className="text-xs tabular-nums text-muted-foreground">
        {metric === "ponto_equilibrio" ? (value == null ? "—" : `${fmtNum(value, 2)} sc/ha`) : fmtBRL(value)}
      </p>
    </div>
  );
}

function ProfessionalTierBlock({ safraId, safraLabel }: { safraId: string; safraLabel: string }) {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title={`Dashboard Executivo — ${safraLabel}`}
        icon={<Gauge className="text-primary" size={22} />}
        description="Disponível no plano Profissional."
      />
      <Alert>
        <AlertCircle className="size-4" />
        <AlertTitle>Plano Profissional necessário</AlertTitle>
        <AlertDescription>
          KPIs executivos, drill-down, alertas e comparação multi-cenário exigem o plano Profissional.
        </AlertDescription>
      </Alert>
      <Button variant="outline" size="sm" asChild className="w-fit">
        <Link href={`/agricola/safras/${safraId}`} aria-label="Voltar para a safra" title="Voltar para a safra">
          <ArrowLeft className="mr-1.5 size-3.5" />
        </Link>
      </Button>
    </div>
  );
}

function SafraExecutiveDashboardContent({ safraId, safraLabel }: { safraId: string; safraLabel: string }) {
  const [selectedMetric, setSelectedMetric] = useState<DrilldownMetric | null>(null);
  const [loadComparativo, setLoadComparativo] = useState(false);
  const [loadProductionUnits, setLoadProductionUnits] = useState(false);
  const [showAllProductionUnits, setShowAllProductionUnits] = useState(false);
  const [showAllDrilldown, setShowAllDrilldown] = useState(false);
  const [showAllAlerts, setShowAllAlerts] = useState(false);
  const [selectedScenarioPuId, setSelectedScenarioPuId] = useState<string | null>(null);
  const [showAllScenarioPus, setShowAllScenarioPus] = useState(false);

  const {
    data: cenarios = [],
    isLoading: isLoadingCenarios,
    isError: isCenariosError,
    error: cenariosError,
  } = useQuery<CenarioListItem[]>({
    queryKey: ["safra-dashboard-cenarios", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/cenarios`),
    staleTime: 2 * 60 * 1000,
  });

  const cenarioBase = useMemo(
    () => cenarios.find((cenario) => cenario.eh_base && cenario.status === "ATIVO") ?? null,
    [cenarios],
  );

  const compareIds = useMemo(() => pickScenarioIds(cenarios), [cenarios]);
  const compareParams = useMemo(() => {
    const params = new URLSearchParams();
    compareIds.forEach((id) => params.append("ids", id));
    return params.toString();
  }, [compareIds]);

  const {
    data: comparativo,
    isLoading: isLoadingComparativo,
    isError: isComparativoError,
    error: comparativoError,
  } = useQuery<{ cenarios: ComparativoColuna[] }>({
    queryKey: ["safra-dashboard-comparativo", safraId, compareIds.join(",")],
    queryFn: () => apiFetch(`/safras/${safraId}/cenarios/comparativo?${compareParams}`),
    enabled: loadComparativo && compareIds.length > 0,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
  });

  const {
    data: productionUnits = [],
    isLoading: isLoadingProductionUnits,
    isError: isProductionUnitsError,
    error: productionUnitsError,
  } = useQuery<ProductionUnit[]>({
    queryKey: ["safra-dashboard-production-units", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}/production-units`),
    enabled: loadProductionUnits,
    staleTime: 2 * 60 * 1000,
  });

  const baseMarginPct = cenarioBase
    ? marginPct(cenarioBase.receita_bruta_total, cenarioBase.margem_contribuicao_total)
    : null;
  const baseTone = cenarioBase
    ? statusTone(baseMarginPct, cenarioBase.margem_contribuicao_total)
    : "default";
  const comparativoCols = comparativo?.cenarios ?? [];
  const baseScenario = comparativoCols.find((cenario) => cenario.eh_base) ?? null;
  const activeProductionUnits = productionUnits.filter((unit) => unit.status === "ATIVA");
  const visibleProductionUnits = showAllProductionUnits
    ? activeProductionUnits
    : activeProductionUnits.slice(0, INITIAL_PU_LIMIT);

  const baseUnits = baseScenario?.unidades ?? [];
  const unitsByPuId = new Map(baseUnits.map((unit) => [unit.production_unit_id, unit]));

  const selectMetric = (metric: DrilldownMetric) => {
    setSelectedMetric((current) => {
      const next = current === metric ? null : metric;
      if (next) {
        setLoadComparativo(true);
        setShowAllDrilldown(false);
      }
      return next;
    });
  };

  const selectMetricFromAlert = (metric: DrilldownMetric) => {
    setSelectedMetric(metric);
    setLoadComparativo(true);
    setShowAllDrilldown(false);
  };

  const executiveAlerts = buildExecutiveAlerts({
    safraId,
    cenarios,
    cenarioBase,
    baseScenario,
    productionUnits,
    productionUnitsLoaded: loadProductionUnits && !isLoadingProductionUnits && !isProductionUnitsError,
  });

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title={`Dashboard Executivo — ${safraLabel}`}
        icon={<Gauge className="text-primary" size={22} />}
        description="Visão consolidada para decisão: cenário base, comparativo limitado e unidades produtivas."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/agricola/safras/${safraId}/production-units`}>
                <Layers className="mr-1.5 size-3.5" />
                Unidades produtivas
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/agricola/safras/${safraId}/cenarios`}>
                <BarChart2 className="mr-1.5 size-3.5" />
                Cenários
              </Link>
            </Button>
          </div>
        }
      />

      {isCenariosError && <ApiErrorAlert title="Erro ao carregar cenários" error={cenariosError} />}

      {isLoadingCenarios ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {[...Array(4)].map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            label="Receita projetada"
            value={fmtBRL(cenarioBase?.receita_bruta_total)}
            subtitle={cenarioBase ? `Cenário ${cenarioBase.nome}` : "Aguardando cenário base"}
            icon={TrendingUp}
            tone="ok"
            active={selectedMetric === "receita"}
            onClick={() => selectMetric("receita")}
          />
          <KpiCard
            label="Custo total"
            value={fmtBRL(cenarioBase?.custo_total)}
            subtitle="Valor calculado pelo cenário"
            icon={TrendingDown}
            tone="default"
            active={selectedMetric === "custo"}
            onClick={() => selectMetric("custo")}
          />
          <KpiCard
            label="Margem"
            value={fmtBRL(cenarioBase?.margem_contribuicao_total)}
            subtitle={fmtPct(baseMarginPct)}
            icon={LineChart}
            tone={baseTone}
            active={selectedMetric === "margem"}
            onClick={() => selectMetric("margem")}
          />
          <KpiCard
            label="Ponto de equilíbrio"
            value={cenarioBase?.ponto_equilibrio_sc_ha ? `${fmtNum(cenarioBase.ponto_equilibrio_sc_ha, 2)} sc/ha` : "—"}
            subtitle="Reutiliza cálculo do Step 20/21"
            icon={Scale}
            tone="warn"
            active={selectedMetric === "ponto_equilibrio"}
            onClick={() => selectMetric("ponto_equilibrio")}
          />
        </div>
      )}

      {selectedMetric && (
        <KpiDrilldownPanel
          metric={selectedMetric}
          baseScenario={baseScenario}
          isLoading={isLoadingComparativo}
          error={comparativoError}
          isError={isComparativoError}
          showAll={showAllDrilldown}
          onShowAllChange={setShowAllDrilldown}
          onLoadDetails={() => setLoadComparativo(true)}
          safraId={safraId}
        />
      )}

      {!isLoadingCenarios && !isCenariosError && (
        <ExecutiveAlertsCard
          alerts={executiveAlerts}
          showAll={showAllAlerts}
          onShowAllChange={setShowAllAlerts}
          onSelectMetric={selectMetricFromAlert}
        />
      )}

      {!isLoadingCenarios && !cenarioBase && !isCenariosError && (
        <Card className="rounded-sm border-dashed">
          <CardContent className="flex flex-col gap-3 p-6 text-center md:flex-row md:items-center md:justify-between md:text-left">
            <div>
              <p className="font-medium">Dashboard limitado sem cenário base</p>
              <p className="text-sm text-muted-foreground">
                Os KPIs executivos dependem dos dados já calculados pelo serviço de cenários.
              </p>
            </div>
            <Button asChild>
              <Link href={`/agricola/safras/${safraId}/cenarios`}>
                Abrir cenários
                <ArrowRight className="ml-1.5 size-3.5" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="flex flex-row items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base">Comparativo executivo</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                MVP limitado a {MAX_COMPARATIVO} cenários: base e melhores margens ativas.
              </p>
            </div>
            {!loadComparativo && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setLoadComparativo(true)}
                disabled={compareIds.length === 0}
              >
                <RefreshCw className="mr-1.5 size-3.5" />
                Carregar
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {!loadComparativo && (
              <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                Comparativo carregado sob demanda para evitar chamada desnecessária. Cenários selecionados:
                <div className="mt-2 flex flex-wrap gap-2">
                  {compareIds.length > 0 ? (
                    cenarios
                      .filter((cenario) => compareIds.includes(cenario.id))
                      .map((cenario) => (
                        <Badge key={cenario.id} variant={cenario.eh_base ? "secondary" : "outline"}>
                          {cenario.nome}
                        </Badge>
                      ))
                  ) : (
                    <span>Nenhum cenário ativo disponível.</span>
                  )}
                </div>
              </div>
            )}

            {isLoadingComparativo && (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            )}

            {isComparativoError && <ApiErrorAlert title="Erro ao carregar comparativo" error={comparativoError} />}

            {!isLoadingComparativo && comparativoCols.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cenário</TableHead>
                    <TableHead className="text-right">Receita</TableHead>
                    <TableHead className="text-right">Custo</TableHead>
                    <TableHead className="text-right">Margem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {comparativoCols.slice(0, MAX_COMPARATIVO).map((cenario) => {
                    const pct = marginPct(cenario.receita_bruta_total, cenario.margem_contribuicao_total);
                    const tone = statusTone(pct, cenario.margem_contribuicao_total);
                    return (
                      <TableRow key={cenario.cenario_id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{cenario.nome}</span>
                            {cenario.eh_base && <Badge variant="secondary">BASE</Badge>}
                            <Badge variant="outline">{TIPO_LABEL[cenario.tipo] ?? cenario.tipo}</Badge>
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{fmtBRL(cenario.receita_bruta_total)}</TableCell>
                        <TableCell className="text-right tabular-nums">{fmtBRL(cenario.custo_total)}</TableCell>
                        <TableCell className={cn("text-right tabular-nums", tone === "risk" && "text-destructive", tone === "warn" && "text-amber-700", tone === "ok" && "text-emerald-700")}>
                          {fmtBRL(cenario.margem_contribuicao_total)}
                          <span className="ml-1 text-muted-foreground">({fmtPct(pct)})</span>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}

            {loadComparativo && !isLoadingComparativo && !isComparativoError && comparativoCols.length === 0 && (
              <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                Nenhum comparativo disponível para os cenários selecionados.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm">
          <CardHeader className="flex flex-row items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base">Unidades produtivas</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Carregamento lazy com limite inicial de {INITIAL_PU_LIMIT} unidades ativas.
              </p>
            </div>
            {!loadProductionUnits && (
              <Button size="sm" variant="outline" onClick={() => setLoadProductionUnits(true)}>
                <Layers className="mr-1.5 size-3.5" />
                Carregar
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {!loadProductionUnits && (
              <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                As unidades são carregadas sob demanda para preservar performance do dashboard.
              </div>
            )}

            {isLoadingProductionUnits && (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            )}

            {isProductionUnitsError && <ApiErrorAlert title="Erro ao carregar unidades produtivas" error={productionUnitsError} />}

            {loadProductionUnits && !isLoadingProductionUnits && !isProductionUnitsError && activeProductionUnits.length === 0 && (
              <div className="flex flex-col gap-3 rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                Nenhuma unidade produtiva ativa encontrada.
                <div>
                  <Button size="sm" variant="outline" asChild>
                    <Link href={`/agricola/safras/${safraId}/production-units`}>Gerenciar unidades produtivas</Link>
                  </Button>
                </div>
              </div>
            )}

            {visibleProductionUnits.length > 0 && (
              <div className="flex flex-col gap-3">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Unidade produtiva</TableHead>
                      <TableHead className="text-right">Área</TableHead>
                      <TableHead className="text-right">Margem base</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleProductionUnits.map((unit) => {
                      const economics = unitsByPuId.get(unit.id);
                      const pct = economics?.margem_pct ?? marginPct(economics?.receita_bruta, economics?.margem_contribuicao);
                      const tone = statusTone(pct, economics?.margem_contribuicao);
                      return (
                        <TableRow key={unit.id}>
                          <TableCell>
                            <div className="flex flex-col">
                              <span className="font-medium">{unit.cultivo_nome ?? "Cultivo"}</span>
                              <span className="text-xs text-muted-foreground">{unit.area_nome ?? unit.id.slice(0, 8)}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">{fmtNum(unit.area_ha, 2)} ha</TableCell>
                          <TableCell className={cn("text-right tabular-nums", tone === "risk" && "text-destructive", tone === "warn" && "text-amber-700", tone === "ok" && "text-emerald-700")}>
                            {economics ? fmtBRL(economics.margem_contribuicao) : "Carregue comparativo"}
                            {economics && <span className="ml-1 text-muted-foreground">({fmtPct(pct)})</span>}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>

                {activeProductionUnits.length > INITIAL_PU_LIMIT && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAllProductionUnits((value) => !value)}
                  >
                    {showAllProductionUnits
                      ? "Mostrar menos"
                      : `Mostrar todas (${activeProductionUnits.length})`}
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <ProductionUnitScenarioComparison
        scenarios={comparativoCols}
        isLoading={isLoadingComparativo}
        isError={isComparativoError}
        error={comparativoError}
        selectedPuId={selectedScenarioPuId}
        onSelectedPuIdChange={setSelectedScenarioPuId}
        showAllUnits={showAllScenarioPus}
        onShowAllUnitsChange={setShowAllScenarioPus}
        onLoadComparativo={() => setLoadComparativo(true)}
        safraId={safraId}
      />

      <Card className="rounded-sm shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Ações recomendadas</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <Button variant="outline" className="justify-between" asChild>
            <Link href={`/agricola/safras/${safraId}/cenarios`}>
              Revisar cenários
              <BarChart2 className="size-3.5" />
            </Link>
          </Button>
          <Button variant="outline" className="justify-between" asChild>
              <Link href={`/agricola/safras/${safraId}/production-units`}>
              Ajustar unidades produtivas
              <Layers className="size-3.5" />
            </Link>
          </Button>
          <Button variant="outline" className="justify-between" asChild>
            <Link href={`/agricola/safras/${safraId}/cenarios/comparativo`}>
              Abrir comparativo completo
              <Wheat className="size-3.5" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function SafraExecutiveDashboardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: safraId } = use(params);
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const { data: safra } = useQuery<Safra>({
    queryKey: ["safra", safraId],
    queryFn: () => apiFetch(`/safras/${safraId}`),
  });
  const safraLabel = safra ? getSafraLabel(safra) : "Safra";

  if (!hasProfessionalTier) {
    return <ProfessionalTierBlock safraId={safraId} safraLabel={safraLabel} />;
  }

  return <SafraExecutiveDashboardContent safraId={safraId} safraLabel={safraLabel} />;
}
