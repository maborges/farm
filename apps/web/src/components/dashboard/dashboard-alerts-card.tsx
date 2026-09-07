"use client";

import { BellRing, CircleAlert, RefreshCw, ShieldAlert, TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { MetricCard } from "@/components/dashboard/dashboard-metric-card";
import { SectionShell, SectionSkeleton } from "@/components/dashboard/dashboard-section";
import { cn } from "@/lib/utils";

type DashboardAlertSeverity = "INFO" | "WARNING" | "CRITICAL" | "EMERGENCY";
type DashboardAlertPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";
type DashboardAlertDomain = "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";

type AlertSummaryByDomain = {
  open: number;
  critical: number;
  urgent: number;
};

type OperationalAlertItem = {
  id?: string;
  title?: string;
  message?: string;
  domain?: DashboardAlertDomain;
  severity?: DashboardAlertSeverity;
  priority?: DashboardAlertPriority;
  created_at?: string;
  createdAt?: string;
  source_type?: string;
  sourceType?: string;
};

export type AlertSummaryPayload = {
  total_open?: number;
  totalOpen?: number;
  max_severity?: DashboardAlertSeverity | null;
  maxSeverity?: DashboardAlertSeverity | null;
  max_priority?: DashboardAlertPriority | null;
  maxPriority?: DashboardAlertPriority | null;
  most_critical_domain?: DashboardAlertDomain | null;
  mostCriticalDomain?: DashboardAlertDomain | null;
  by_domain?: Partial<Record<DashboardAlertDomain, Partial<AlertSummaryByDomain>>>;
  byDomain?: Partial<Record<DashboardAlertDomain, Partial<AlertSummaryByDomain>>>;
  top_alerts?: OperationalAlertItem[];
  topAlerts?: OperationalAlertItem[];
};

type NormalizedAlertSummary = {
  totalOpen: number;
  maxSeverity: DashboardAlertSeverity | null;
  maxPriority: DashboardAlertPriority | null;
  mostCriticalDomain: DashboardAlertDomain | null;
  byDomain: Record<DashboardAlertDomain, AlertSummaryByDomain>;
  topAlerts: OperationalAlertItem[];
};

const DOMAIN_LABELS: Record<DashboardAlertDomain, string> = {
  AGRICULTURE: "Agricultura",
  LIVESTOCK: "Pecuária",
  FINANCE: "Financeiro",
  OPERATIONS: "Operacional",
  FIELD: "Campo",
  SYSTEM: "Sistema",
};

const SEVERITY_LABELS: Record<DashboardAlertSeverity, string> = {
  INFO: "Informativo",
  WARNING: "Atenção",
  CRITICAL: "Crítico",
  EMERGENCY: "Emergência",
};

const PRIORITY_LABELS: Record<DashboardAlertPriority, string> = {
  LOW: "Baixa",
  NORMAL: "Normal",
  HIGH: "Alta",
  URGENT: "Urgente",
};

const DOMAIN_ORDER: DashboardAlertDomain[] = ["AGRICULTURE", "LIVESTOCK", "FINANCE", "OPERATIONS", "FIELD", "SYSTEM"];

const EMPTY_DOMAIN_SUMMARY: AlertSummaryByDomain = { open: 0, critical: 0, urgent: 0 };

function normalizeSummary(summary?: AlertSummaryPayload): NormalizedAlertSummary {
  const byDomain = DOMAIN_ORDER.reduce<Record<DashboardAlertDomain, AlertSummaryByDomain>>((acc, domain) => {
    const entry = summary?.by_domain?.[domain] ?? summary?.byDomain?.[domain] ?? {};
    acc[domain] = {
      open: Number(entry.open ?? 0),
      critical: Number(entry.critical ?? 0),
      urgent: Number(entry.urgent ?? 0),
    };
    return acc;
  }, {} as Record<DashboardAlertDomain, AlertSummaryByDomain>);

  return {
    totalOpen: Number(summary?.total_open ?? summary?.totalOpen ?? 0),
    maxSeverity: summary?.max_severity ?? summary?.maxSeverity ?? null,
    maxPriority: summary?.max_priority ?? summary?.maxPriority ?? null,
    mostCriticalDomain: summary?.most_critical_domain ?? summary?.mostCriticalDomain ?? null,
    byDomain,
    topAlerts: Array.isArray(summary?.top_alerts)
      ? summary.top_alerts
      : Array.isArray(summary?.topAlerts)
        ? summary.topAlerts
        : [],
  };
}

function formatCount(value: number): string {
  return value.toLocaleString("pt-BR");
}

function formatTimestamp(value?: string): string {
  if (!value) return "Sem data";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Sem data";
  return parsed.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function severityVariant(severity?: DashboardAlertSeverity | null) {
  switch (severity) {
    case "EMERGENCY":
    case "CRITICAL":
      return "critical";
    case "WARNING":
      return "warning";
    case "INFO":
      return "info";
    default:
      return "outline";
  }
}

function priorityVariant(priority?: DashboardAlertPriority | null) {
  switch (priority) {
    case "URGENT":
      return "critical";
    case "HIGH":
      return "attention";
    case "NORMAL":
      return "warning";
    case "LOW":
      return "secondary";
    default:
      return "outline";
  }
}

export type DashboardAlertsCardProps = {
  summary?: AlertSummaryPayload;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
};

export function DashboardAlertsCard({ summary, isLoading = false, isError = false, onRetry }: DashboardAlertsCardProps) {
  return (
    <SectionShell
      title="Alertas Operacionais"
      description="Sinais oficiais do Alert Engine para atenção imediata da fazenda."
      action={
        onRetry ? (
          <Button variant="outline" size="sm" className="rounded-sm" onClick={onRetry}>
            <RefreshCw className="size-4" />
            Atualizar
          </Button>
        ) : undefined
      }
    >
      {isLoading ? (
        <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
      ) : isError ? (
        <EmptyState
          icon={<ShieldAlert />}
          title="Não foi possível carregar os alertas operacionais"
          description="Tente recarregar a seção para recuperar o resumo oficial do Alert Engine."
          action={onRetry ? { label: "Tentar novamente", onClick: onRetry } : undefined}
        />
      ) : renderSummary(normalizeSummary(summary))}
    </SectionShell>
  );
}

function renderSummary(summary: NormalizedAlertSummary) {
  if (summary.totalOpen <= 0) {
    return (
      <EmptyState
        icon={<BellRing />}
        title="Nenhum alerta operacional aberto no momento."
        description="Quando o Alert Engine detectar um desvio ativo, ele aparecerá aqui antes da interpretação do Copiloto."
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Alertas abertos"
          value={formatCount(summary.totalOpen)}
          description="Eventos ativos no contexto atual"
          icon={<CircleAlert className="size-5 text-rose-600" />}
          tone="bg-rose-500/10"
        />
        <MetricCard
          label="Severidade máxima"
          value={summary.maxSeverity ? SEVERITY_LABELS[summary.maxSeverity] : "Sem severidade"}
          description="Maior severidade ativa"
          icon={<TriangleAlert className="size-5 text-amber-600" />}
          tone="bg-amber-500/10"
        />
        <MetricCard
          label="Prioridade máxima"
          value={summary.maxPriority ? PRIORITY_LABELS[summary.maxPriority] : "Sem prioridade"}
          description="Maior prioridade ativa"
          icon={<RefreshCw className="size-5 text-sky-600" />}
          tone="bg-sky-500/10"
        />
        <MetricCard
          label="Domínio mais crítico"
          value={summary.mostCriticalDomain ? DOMAIN_LABELS[summary.mostCriticalDomain] : "Sem domínio"}
          description="Domínio com maior pressão"
          icon={<ShieldAlert className="size-5 text-primary" />}
          tone="bg-primary/10"
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Contagem por domínio</p>
            <p className="text-sm text-muted-foreground">Alertas abertos, críticos e urgentes no contexto atual.</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {DOMAIN_ORDER.map((domain) => {
            const item = summary.byDomain[domain] ?? EMPTY_DOMAIN_SUMMARY;
            return (
              <Card key={domain} className="border shadow-sm">
                <CardContent className="space-y-3 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{DOMAIN_LABELS[domain]}</p>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{domain}</p>
                    </div>
                    <Badge variant="outline" className="rounded-sm">
                      {formatCount(item.open)} abertos
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <DomainMiniStat label="Críticos" value={item.critical} tone="text-rose-600" />
                    <DomainMiniStat label="Urgentes" value={item.urgent} tone="text-fuchsia-600" />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Top alerts</p>
          <p className="text-sm text-muted-foreground">Os alertas mais relevantes, ordenados por severidade, prioridade e recência.</p>
        </div>
        <div className="grid gap-3">
          {summary.topAlerts.slice(0, 3).map((alert, index) => {
            const title = alert.title ?? "Alerta operacional";
            const message = alert.message ?? "Sem mensagem detalhada.";
            const domain = alert.domain ? DOMAIN_LABELS[alert.domain] : "Domínio indefinido";
            const createdAt = formatTimestamp(alert.created_at ?? alert.createdAt);
            const sourceType = alert.source_type ?? alert.sourceType;

            return (
              <Card key={alert.id ?? `${title}-${index}`} className="overflow-hidden border shadow-sm">
                <CardContent className="space-y-3 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className="rounded-sm">
                          {domain}
                        </Badge>
                        <Badge variant={severityVariant(alert.severity)} className="rounded-sm">
                          {alert.severity ? SEVERITY_LABELS[alert.severity] : "Sem severidade"}
                        </Badge>
                        <Badge variant={priorityVariant(alert.priority)} className="rounded-sm">
                          {alert.priority ? PRIORITY_LABELS[alert.priority] : "Sem prioridade"}
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-foreground">{title}</p>
                        <p className="text-sm text-muted-foreground">{message}</p>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground lg:text-right">
                      <p className="font-semibold text-foreground">#{index + 1}</p>
                      <p>{createdAt}</p>
                      {sourceType ? <p>{sourceType}</p> : null}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DomainMiniStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-sm border border-border bg-muted/25 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-lg font-semibold tabular-nums", tone)}>{formatCount(value)}</p>
    </div>
  );
}
