"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CalendarRange,
  CheckCircle2,
  Clock3,
  Eye,
  Filter,
  Layers3,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import {
  RecommendationDomain,
  RecommendationLifecycleActionInput,
  RecommendationListFilters,
  RecommendationListItem,
  RecommendationPriority,
  RecommendationStatus,
  RecommendationDomainMetricsItem,
  useRecommendationLifecycleAction,
  useRecommendationMetrics,
  useRecommendations,
} from "@/hooks/use-recommendations";

type Option = { label: string; value: string };

const DOMAIN_LABELS: Record<RecommendationDomain, string> = {
  AGRICULTURE: "Agricultura",
  LIVESTOCK: "Pecuária",
  FINANCE: "Financeiro",
  OPERATIONS: "Operações",
  FIELD: "Campo",
  INTEGRATIONS: "Integrações",
  SYSTEM: "Sistema",
};

const DOMAIN_ORDER: RecommendationDomain[] = [
  "AGRICULTURE",
  "LIVESTOCK",
  "FINANCE",
  "OPERATIONS",
  "FIELD",
  "INTEGRATIONS",
  "SYSTEM",
];

const PRIORITY_LABELS: Record<RecommendationPriority, string> = {
  LOW: "Baixa",
  NORMAL: "Normal",
  HIGH: "Alta",
  URGENT: "Urgente",
};

const STATUS_LABELS: Record<RecommendationStatus, string> = {
  CREATED: "Criada",
  VIEWED: "Visualizada",
  ACCEPTED: "Aceita",
  DISMISSED: "Descartada",
  POSTPONED: "Adiada",
  EXECUTED: "Executada",
  EXPIRED: "Expirada",
  AUTO_EXPIRED: "Expirada automaticamente",
  SUPERSEDED: "Superada",
  REOPENED: "Reaberta",
};

const ACTIVE_STATUSES: RecommendationStatus[] = ["CREATED", "VIEWED", "POSTPONED", "REOPENED"];
const DAY_MS = 24 * 60 * 60 * 1000;

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

function formatDateInput(value: Date) {
  return value.toISOString().slice(0, 10);
}

function formatDateTimeLocalInput(value: Date) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(value);
}

function formatConfidence(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return "—";
  return formatPercent(parsed);
}

function getPriorityVariant(priority: RecommendationPriority) {
  switch (priority) {
    case "URGENT":
      return "critical";
    case "HIGH":
      return "attention";
    case "NORMAL":
      return "warning";
    default:
      return "secondary";
  }
}

function getStatusVariant(status: RecommendationStatus) {
  switch (status) {
    case "CREATED":
      return "priority";
    case "VIEWED":
      return "secondary";
    case "ACCEPTED":
      return "success";
    case "DISMISSED":
      return "outline";
    case "POSTPONED":
      return "warning";
    case "EXECUTED":
      return "recommendation";
    case "EXPIRED":
    case "AUTO_EXPIRED":
      return "danger";
    case "SUPERSEDED":
      return "diagnostic";
    case "REOPENED":
      return "attention";
    default:
      return "outline";
  }
}

function getDomainVariant(domain: RecommendationDomain) {
  switch (domain) {
    case "AGRICULTURE":
      return "success";
    case "LIVESTOCK":
      return "warning";
    case "FINANCE":
      return "info";
    case "OPERATIONS":
      return "attention";
    case "FIELD":
      return "diagnostic";
    case "INTEGRATIONS":
      return "recommendation";
    case "SYSTEM":
      return "secondary";
    default:
      return "outline";
  }
}

function isActiveRecommendation(status: RecommendationStatus) {
  return ACTIVE_STATUSES.includes(status);
}

function toFilterParams(filters: RecommendationListFilters) {
  return {
    domain: filters.domain || undefined,
    status: filters.status || undefined,
    priority: filters.priority || undefined,
    unidade_produtiva_id: filters.unidade_produtiva_id || undefined,
    start_date: filters.start_date || undefined,
    end_date: filters.end_date || undefined,
    limit: filters.limit,
    offset: filters.offset,
  };
}

function RecommendationFilterSelect({
  label,
  value,
  onValueChange,
  options,
  placeholder,
  testId,
}: {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: Option[];
  placeholder: string;
  testId?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={testId} className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id={testId} className="rounded-sm" data-testid={testId}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function MetricSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <Card key={index} className="rounded-sm shadow-sm">
          <CardContent className="p-4">
            <Skeleton className="h-5 w-1/2" />
            <Skeleton className="mt-3 h-8 w-2/5" />
            <Skeleton className="mt-2 h-4 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SectionError({ title, description, onRetry }: { title: string; description: string; onRetry: () => void }) {
  return (
    <EmptyState
      icon={<ShieldAlert />}
      title={title}
      description={description}
      action={{ label: "Tentar novamente", onClick: onRetry }}
    />
  );
}

function DomainMetricCard({ item }: { item: RecommendationDomainMetricsItem }) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardContent className="space-y-4 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">{DOMAIN_LABELS[item.domain]}</p>
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">{item.domain}</p>
          </div>
          <Badge variant="outline" className="rounded-sm">
            {formatNumber(item.total)} recomendações
          </Badge>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <MiniMetric label="Aceite" value={formatPercent(item.accept_rate)} />
          <MiniMetric label="Execução" value={formatPercent(item.execute_rate)} />
          <MiniMetric label="Visualização" value={formatPercent(item.view_rate)} />
          <MiniMetric label="Descarte" value={formatPercent(item.dismiss_rate)} />
        </div>
      </CardContent>
    </Card>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border/70 bg-muted/20 p-2">
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold text-foreground">{value}</p>
    </div>
  );
}

function TimelineBar({ label, value, max }: { label: string; value: number; max: number }) {
  const height = max > 0 ? Math.max(8, Math.round((value / max) * 88)) : 8;
  return (
    <div className="flex flex-1 flex-col items-center gap-2">
      <div className="flex h-24 w-full items-end rounded-sm bg-muted/30 p-1">
        <div className="w-full rounded-sm bg-primary/80 transition-all" style={{ height: `${height}%` }} />
      </div>
      <div className="text-center">
        <p className="text-[10px] font-black uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
        <p className="text-xs font-semibold tabular-nums">{formatNumber(value)}</p>
      </div>
    </div>
  );
}

function RecommendationDetailSheet({
  recommendation,
  open,
  onOpenChange,
  onAction,
  actionPending,
}: {
  recommendation: RecommendationListItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAction: (input: RecommendationLifecycleActionInput) => Promise<void>;
  actionPending: boolean;
}) {
  const [dismissReason, setDismissReason] = useState("");
  const [executionNote, setExecutionNote] = useState("");
  const [postponeUntil, setPostponeUntil] = useState(() => formatDateTimeLocalInput(new Date(Date.now() + DAY_MS)));
  const [postponeReason, setPostponeReason] = useState("");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="overflow-y-auto sm:max-w-xl">
        <SheetHeader className="space-y-2 border-b border-border/60 pb-4 pr-8">
          <SheetTitle className="text-balance text-lg font-bold">
            {recommendation ? recommendation.title : "Detalhe da recomendação"}
          </SheetTitle>
          <SheetDescription className="text-pretty">
            {recommendation?.summary || "Selecione uma recomendação para ver o racional, o contexto e as ações de lifecycle."}
          </SheetDescription>
        </SheetHeader>

        {recommendation ? (
          <div className="space-y-5 p-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant={getDomainVariant(recommendation.domain)} className="rounded-sm">
                {DOMAIN_LABELS[recommendation.domain]}
              </Badge>
              <Badge variant={getPriorityVariant(recommendation.priority)} className="rounded-sm">
                {PRIORITY_LABELS[recommendation.priority]}
              </Badge>
              <Badge variant={getStatusVariant(recommendation.status)} className="rounded-sm">
                {STATUS_LABELS[recommendation.status]}
              </Badge>
            </div>

            <div className="grid gap-3 rounded-sm border border-border/70 bg-muted/20 p-3 text-sm">
              <SheetMeta label="Domínio" value={`${DOMAIN_LABELS[recommendation.domain]} · ${recommendation.domain}`} />
              <SheetMeta label="Prioridade" value={PRIORITY_LABELS[recommendation.priority]} />
              <SheetMeta label="Status" value={STATUS_LABELS[recommendation.status]} />
              <SheetMeta label="Confiança" value={formatConfidence(recommendation.confidence)} />
              <SheetMeta label="Unidade produtiva" value={recommendation.unidade_produtiva_id || "—"} />
              <SheetMeta label="Regra" value={recommendation.rule_code} />
              <SheetMeta label="Escopo" value={`${recommendation.scope_type} · ${recommendation.scope_id}`} />
              <SheetMeta label="Criada em" value={formatDateTime(recommendation.created_at)} />
              <SheetMeta label="Atualizada em" value={formatDateTime(recommendation.updated_at)} />
              <SheetMeta label="Expira em" value={formatDateTime(recommendation.expires_at)} />
            </div>

            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Resumo</p>
              <p className="text-sm text-foreground">{recommendation.summary}</p>
            </div>

            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Rationale</p>
              <p className="text-sm text-foreground">{recommendation.rationale}</p>
            </div>

            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Contexto</p>
              <pre className="max-h-44 overflow-auto rounded-sm border border-border/70 bg-background p-3 text-xs text-foreground">
                {JSON.stringify(recommendation.context ?? {}, null, 2)}
              </pre>
            </div>

            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Sinais e debug</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="rounded-sm">
                  {recommendation.provider_name}
                </Badge>
                <Badge variant="outline" className="rounded-sm">
                  {recommendation.dedupe_key}
                </Badge>
                {recommendation.source_signal_ids.map((id) => (
                  <Badge key={id} variant="outline" className="rounded-sm">
                    {id}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-3 rounded-sm border border-border/70 p-3">
              <div className="flex items-center gap-2">
                <Sparkles className="size-4 text-primary" />
                <p className="text-sm font-semibold">Ações de lifecycle</p>
              </div>

              <div className="grid gap-3">
                <div className="space-y-2">
                  <Label htmlFor="recommendation-dismiss-reason" className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                    Motivo do descarte
                  </Label>
                  <Textarea
                    id="recommendation-dismiss-reason"
                    value={dismissReason}
                    onChange={(event) => setDismissReason(event.target.value)}
                    placeholder="Opcional"
                    className="rounded-sm"
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="recommendation-postpone-until" className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                    Adiar até
                  </Label>
                  <Input
                    id="recommendation-postpone-until"
                    type="datetime-local"
                    value={postponeUntil}
                    onChange={(event) => setPostponeUntil(event.target.value)}
                    className="rounded-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="recommendation-postpone-reason" className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                    Motivo do adiamento
                  </Label>
                  <Textarea
                    id="recommendation-postpone-reason"
                    value={postponeReason}
                    onChange={(event) => setPostponeReason(event.target.value)}
                    placeholder="Opcional"
                    className="rounded-sm"
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="recommendation-execution-note" className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                    Observação da execução
                  </Label>
                  <Textarea
                    id="recommendation-execution-note"
                    value={executionNote}
                    onChange={(event) => setExecutionNote(event.target.value)}
                    placeholder="Opcional"
                    className="rounded-sm"
                    rows={3}
                  />
                </div>
              </div>

              <div className="grid gap-2 md:grid-cols-2">
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => void onAction({ recommendationId: recommendation.id, action: "view" })}
                  disabled={actionPending}
                >
                  <Eye className="size-4" />
                  Registrar visualização
                </Button>
                <Button
                  variant="default"
                  className="rounded-sm"
                  onClick={() => void onAction({ recommendationId: recommendation.id, action: "accept" })}
                  disabled={actionPending}
                >
                  <CheckCircle2 className="size-4" />
                  Aceitar
                </Button>
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => void onAction({
                    recommendationId: recommendation.id,
                    action: "dismiss",
                    payload: { reason: dismissReason.trim() || "Descartada pelo operador via dashboard." },
                  })}
                  disabled={actionPending}
                >
                  <TriangleAlert className="size-4" />
                  Descartar
                </Button>
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => void onAction({
                    recommendationId: recommendation.id,
                    action: "postpone",
                    payload: {
                      until: new Date(postponeUntil).toISOString(),
                      reason: postponeReason.trim() || "Adiada pelo operador via dashboard.",
                    },
                  })}
                  disabled={actionPending}
                >
                  <Clock3 className="size-4" />
                  Adiar
                </Button>
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => void onAction({
                    recommendationId: recommendation.id,
                    action: "execute",
                    payload: { execution_note: executionNote.trim() || "Execução registrada pelo dashboard." },
                  })}
                  disabled={actionPending}
                >
                  <ArrowRight className="size-4" />
                  Marcar executada
                </Button>
                <Button
                  variant="outline"
                  className="rounded-sm"
                  onClick={() => void onAction({ recommendationId: recommendation.id, action: "reopen" })}
                  disabled={actionPending}
                >
                  <RefreshCw className="size-4" />
                  Reabrir
                </Button>
              </div>
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function SheetMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <p className="text-[10px] font-black uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="break-all text-sm text-foreground">{value}</p>
    </div>
  );
}

export function RecommendationsDashboardClient() {
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const unidadesProdutivas = useAppStore((state) => state.unidadesProdutivasAutorizadas) as Array<{
    id: string;
    nome?: string | null;
  }>;

  const [domain, setDomain] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [priority, setPriority] = useState<string>("all");
  const [unitId, setUnitId] = useState<string>(activeFazendaId || "all");
  const [startDate, setStartDate] = useState<string>(() => formatDateInput(new Date(Date.now() - 29 * DAY_MS)));
  const [endDate, setEndDate] = useState<string>(() => formatDateInput(new Date()));
  const [selectedRecommendationId, setSelectedRecommendationId] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const filters = useMemo<RecommendationListFilters>(
    () => ({
      domain: domain !== "all" ? (domain as RecommendationDomain) : undefined,
      status: status !== "all" ? (status as RecommendationStatus) : undefined,
      priority: priority !== "all" ? (priority as RecommendationPriority) : undefined,
      unidade_produtiva_id: unitId && unitId !== "all" ? unitId : undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      limit: 200,
      offset: 0,
    }),
    [domain, endDate, priority, startDate, status, unitId],
  );

  const recommendationsQuery = useRecommendations(filters);
  const metricsQuery = useRecommendationMetrics(filters);
  const lifecycleAction = useRecommendationLifecycleAction();

  const recommendations = useMemo(() => recommendationsQuery.data?.items ?? [], [recommendationsQuery.data?.items]);
  const selectedRecommendation = selectedRecommendationId
    ? recommendations.find((item) => item.id === selectedRecommendationId) ?? null
    : null;

  const activeRecommendations = useMemo(
    () => recommendations.filter((item) => isActiveRecommendation(item.status)),
    [recommendations],
  );
  const urgentRecommendations = useMemo(
    () => recommendations.filter((item) => item.priority === "HIGH" || item.priority === "URGENT"),
    [recommendations],
  );
  const activeCount = activeRecommendations.length;
  const urgentCount = urgentRecommendations.length;

  const handleOpenDetail = async (item: RecommendationListItem) => {
    setSelectedRecommendationId(item.id);
    setDetailOpen(true);
    if (item.status === "CREATED" || item.status === "REOPENED") {
      await lifecycleAction.mutateAsync({ recommendationId: item.id, action: "view" });
    }
  };

  const metrics = metricsQuery.data;
  const domainMetrics = useMemo(() => {
    const items = metrics?.byDomain?.items ?? [];
    return DOMAIN_ORDER.flatMap((domainCode) => items.filter((item) => item.domain === domainCode));
  }, [metrics?.byDomain?.items]);

  const timeline = metrics?.summary?.timeline ?? [];
  const timelineMax = Math.max(...timeline.map((item) => item.total_recommendations), 0);
  const activeUnitLabel = unitId && unitId !== "all"
    ? unidadesProdutivas.find((item) => item.id === unitId)?.nome ?? unitId
    : "Todas as unidades";

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Recomendações Operacionais"
        description="Visão global das recomendações do Recommendation Engine, com métricas, filtros e lifecycle explícito."
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Inteligência Operacional", href: "/dashboard/inteligencia-operacional/recomendacoes" },
          { label: "Recomendações Operacionais" },
        ]}
        actions={(
          <Button
            variant="outline"
            size="sm"
            className="rounded-sm"
            onClick={() => {
              void recommendationsQuery.refetch();
              void metricsQuery.refetch();
            }}
          >
            <RefreshCw className="size-4" />
            Atualizar
          </Button>
        )}
        icon={<Sparkles className="size-5" />}
      />

      <Card className="rounded-sm shadow-sm">
        <CardHeader className="space-y-4">
          <div className="flex items-center gap-2">
            <Filter className="size-4 text-primary" />
            <CardTitle className="text-base">Filtros</CardTitle>
          </div>
          <CardDescription>Recorte por domínio, status, prioridade, unidade produtiva e período.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <RecommendationFilterSelect
            label="Domínio"
            value={domain}
            onValueChange={setDomain}
            placeholder="Todos"
            testId="recommendations-domain-filter"
            options={[
              { value: "all", label: "Todos os domínios" },
              ...DOMAIN_ORDER.map((item) => ({ value: item, label: DOMAIN_LABELS[item] })),
            ]}
          />
          <RecommendationFilterSelect
            label="Status"
            value={status}
            onValueChange={setStatus}
            placeholder="Todos"
            testId="recommendations-status-filter"
            options={[
              { value: "all", label: "Todos os status" },
              ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
            ]}
          />
          <RecommendationFilterSelect
            label="Prioridade"
            value={priority}
            onValueChange={setPriority}
            placeholder="Todas"
            testId="recommendations-priority-filter"
            options={[
              { value: "all", label: "Todas as prioridades" },
              ...Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label })),
            ]}
          />
          <RecommendationFilterSelect
            label="Unidade produtiva"
            value={unitId}
            onValueChange={setUnitId}
            placeholder="Todas"
            testId="recommendations-unit-filter"
            options={[
              { value: "all", label: "Todas as unidades" },
              ...unidadesProdutivas.map((item) => ({ value: item.id, label: item.nome ?? item.id })),
            ]}
          />
          <div className="space-y-2">
            <Label className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Período inicial</Label>
            <Input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="rounded-sm"
              data-testid="recommendations-start-date"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">Período final</Label>
            <Input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="rounded-sm"
              data-testid="recommendations-end-date"
            />
          </div>
        </CardContent>
      </Card>

      {metricsQuery.isLoading ? <MetricSkeleton /> : null}
      {metricsQuery.isError ? (
        <SectionError
          title="Não foi possível carregar as métricas de recomendações"
          description={metricsQuery.error instanceof Error ? metricsQuery.error.message : "Falha ao consultar os endpoints de métricas."}
          onRetry={() => {
            void metricsQuery.refetch();
          }}
        />
      ) : metrics ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            color="operacional"
            icon={Layers3}
            label="Recomendações ativas"
            value={formatNumber(activeCount)}
            subtitle={`No recorte atual · ${activeUnitLabel}`}
          />
          <StatCard
            color="warning"
            icon={TriangleAlert}
            label="Alta prioridade"
            value={formatNumber(urgentCount)}
            subtitle="Prioridades alta e urgente"
          />
          <StatCard
            color="success"
            icon={CheckCircle2}
            label="Taxa de aceite"
            value={formatPercent(metrics.summary.accept_rate)}
            subtitle={`${formatNumber(metrics.summary.accepted_total)} aceitas no período`}
          />
          <StatCard
            color="primary"
            icon={Eye}
            label="Taxa de execução"
            value={formatPercent(metrics.summary.execute_rate)}
            subtitle={`${formatNumber(metrics.summary.executed_total)} executadas no período`}
          />
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <Card className="rounded-sm shadow-sm">
          <CardHeader className="space-y-2">
            <CardTitle>Lista de recomendações</CardTitle>
            <CardDescription>
              Clique em uma linha para abrir o detalhe e executar o lifecycle de forma explícita.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {recommendationsQuery.isLoading ? (
              <div className="space-y-3 p-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-16 w-full rounded-sm" />
                ))}
              </div>
            ) : recommendationsQuery.isError ? (
              <SectionError
                title="Não foi possível carregar a lista de recomendações"
                description={recommendationsQuery.error instanceof Error ? recommendationsQuery.error.message : "Falha ao consultar a API de recomendações."}
                onRetry={() => {
                  void recommendationsQuery.refetch();
                }}
              />
            ) : recommendations.length === 0 ? (
              <EmptyState
                icon={<Sparkles />}
                title="Nenhuma recomendação encontrada"
                description="Ajuste os filtros para visualizar recomendações no recorte atual."
              />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Título</TableHead>
                      <TableHead>Domínio</TableHead>
                      <TableHead>Prioridade</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Confiança</TableHead>
                      <TableHead>Unidade produtiva</TableHead>
                      <TableHead>Atualização</TableHead>
                      <TableHead>Ação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recommendations.map((item) => (
                      <TableRow key={item.id} className="cursor-pointer" onClick={() => void handleOpenDetail(item)}>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <p className="font-medium text-foreground">{item.title}</p>
                            <p className="text-xs text-muted-foreground">{item.action_label || "Sem ação explícita"}</p>
                          </div>
                        </TableCell>
                        <TableCell className="align-top">
                          <Badge variant={getDomainVariant(item.domain)} className="rounded-sm">
                            {DOMAIN_LABELS[item.domain]}
                          </Badge>
                        </TableCell>
                        <TableCell className="align-top">
                          <Badge variant={getPriorityVariant(item.priority)} className="rounded-sm">
                            {PRIORITY_LABELS[item.priority]}
                          </Badge>
                        </TableCell>
                        <TableCell className="align-top">
                          <Badge variant={getStatusVariant(item.status)} className="rounded-sm">
                            {STATUS_LABELS[item.status]}
                          </Badge>
                        </TableCell>
                        <TableCell className="align-top tabular-nums">{formatConfidence(item.confidence)}</TableCell>
                        <TableCell className="align-top text-xs">{item.unidade_produtiva_id || "—"}</TableCell>
                        <TableCell className="align-top text-xs">{formatDateTime(item.updated_at)}</TableCell>
                        <TableCell className="align-top">
                          <Button variant="ghost" size="sm" className="rounded-sm">
                            Visualizar
                            <ArrowRight className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="rounded-sm shadow-sm">
            <CardHeader>
              <CardTitle>Distribuição por domínio</CardTitle>
              <CardDescription>Resumo consolidado do período selecionado.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {metricsQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-24 w-full rounded-sm" />
                  ))}
                </div>
              ) : metricsQuery.isError ? (
                <SectionError
                  title="Sem distribuição por domínio"
                  description="As métricas não puderam ser carregadas."
                  onRetry={() => {
                    void metricsQuery.refetch();
                  }}
                />
              ) : domainMetrics.length === 0 ? (
                <EmptyState
                  icon={<Layers3 />}
                  title="Sem dados por domínio"
                  description="Não há recomendações suficientes para distribuir por domínio no recorte atual."
                />
              ) : (
                <div className="grid gap-3">
                  {domainMetrics.map((item) => (
                    <DomainMetricCard key={item.domain} item={item} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-sm shadow-sm">
            <CardHeader>
              <CardTitle>Série temporal</CardTitle>
              <CardDescription>Evolução simples por dia no período aplicado.</CardDescription>
            </CardHeader>
            <CardContent>
              {metricsQuery.isLoading ? (
                <Skeleton className="h-36 w-full rounded-sm" />
              ) : timeline.length === 0 ? (
                <EmptyState
                  icon={<CalendarRange />}
                  title="Sem série temporal"
                  description="A série temporal aparece quando houver recomendações no período selecionado."
                />
              ) : (
                <div className="flex gap-3">
                  {timeline.map((item) => (
                    <TimelineBar
                      key={item.period}
                      label={new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(new Date(item.period))}
                      value={item.total_recommendations}
                      max={timelineMax}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <MetricRankingCard
          title="Top regras por volume"
          description="Regras com maior volume de recomendações no recorte."
          items={metrics?.byRule.top_by_volume ?? []}
        />
        <MetricRankingCard
          title="Top regras por aceite"
          description="Regras com maior volume de aceite no recorte."
          items={metrics?.byRule.top_by_acceptance ?? []}
        />
        <MetricRankingCard
          title="Top regras por descarte"
          description="Regras com maior volume de descarte no recorte."
          items={metrics?.byRule.top_by_dismissal ?? []}
        />
      </div>

      <RecommendationDetailSheet
        key={selectedRecommendation?.id ?? "empty"}
        recommendation={selectedRecommendation}
        open={detailOpen}
        onOpenChange={(open) => {
          setDetailOpen(open);
          if (!open) {
            setSelectedRecommendationId(null);
          }
        }}
        onAction={async (input) => {
          await lifecycleAction.mutateAsync(input);
          await recommendationsQuery.refetch();
          await metricsQuery.refetch();
          if (input.action !== "view") {
            setDetailOpen(false);
            setSelectedRecommendationId(null);
          }
        }}
        actionPending={lifecycleAction.isPending}
      />
    </div>
  );
}

function MetricRankingCard({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: Array<{
    rule_code: string;
    provider_name: string;
    domain: RecommendationDomain;
    total: number;
    accepted_total: number;
    dismissed_total: number;
    executed_total: number;
    view_rate: number;
    accept_rate: number;
    dismiss_rate: number;
    execute_rate: number;
  }>;
}) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length === 0 ? (
          <EmptyState
            icon={<ShieldAlert />}
            title="Sem itens para ranquear"
            description="O ranking aparecerá quando houver recomendações suficientes no recorte."
          />
        ) : (
          items.slice(0, 5).map((item, index) => (
            <div key={`${item.rule_code}-${index}`} className="rounded-sm border border-border/70 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-foreground">{item.rule_code}</p>
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-muted-foreground">{DOMAIN_LABELS[item.domain]}</p>
                </div>
                <Badge variant="outline" className="rounded-sm">
                  {formatNumber(item.total)}
                </Badge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <MiniMetric label="Aceites" value={formatNumber(item.accepted_total)} />
                <MiniMetric label="Descartes" value={formatNumber(item.dismissed_total)} />
                <MiniMetric label="Execuções" value={formatNumber(item.executed_total)} />
                <MiniMetric label="Aceite %" value={formatPercent(item.accept_rate)} />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
