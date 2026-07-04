"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { ArrowLeft, CloudOff, Clock3, RefreshCw, Sparkles } from "lucide-react";
import { db, type CachedRecomendacaoOperacional } from "@/lib/db";
import { useSyncStore } from "@/lib/stores/sync-store";
import { CampoButton, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

const ACTIVE_STATUS_LABELS: Record<string, string> = {
  CREATED: "Nova",
  VIEWED: "Vista",
  ACCEPTED: "Aceita",
  POSTPONED: "Adiada",
  REOPENED: "Reaberta",
};

const DOMAIN_LABELS: Record<string, string> = {
  FIELD: "Campo",
  AGRICULTURE: "Agricultura",
  LIVESTOCK: "Pecuária",
  OPERATIONS: "Operações",
  FINANCE: "Financeiro",
  SYSTEM: "Sistema",
  INTEGRATIONS: "Integrações",
};

const PRIORITY_LABELS: Record<string, string> = {
  URGENT: "Urgente",
  HIGH: "Alta",
  NORMAL: "Normal",
  LOW: "Baixa",
};

const PRIORITY_TONE: Record<string, string> = {
  URGENT: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
  HIGH: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
  NORMAL: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
  LOW: "border-border bg-muted text-muted-foreground",
};

const DOMAIN_ORDER = ["FIELD", "AGRICULTURE", "LIVESTOCK", "OPERATIONS", "FINANCE", "SYSTEM", "INTEGRATIONS"] as const;
const ACTIVE_STATUSES = Object.keys(ACTIVE_STATUS_LABELS);

type DomainFilter = "ALL" | (typeof DOMAIN_ORDER)[number];
type StatusFilter = "ALL" | (typeof ACTIVE_STATUSES)[number];
type PriorityFilter = "ALL" | "URGENT" | "HIGH" | "NORMAL" | "LOW";

export default function RecomendacoesPage() {
  const router = useRouter();
  const { isOnline, lastSyncAt } = useSyncStore();
  const recommendations = useLiveQuery(() => db.recomendacoes_operacionais.toArray(), []);
  const [domainFilter, setDomainFilter] = useState<DomainFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("ALL");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sortedRecommendations = useMemo(
    () => sortRecommendations(recommendations ?? []),
    [recommendations]
  );

  const filteredRecommendations = useMemo(
    () =>
      sortedRecommendations.filter((item) => {
        if (domainFilter !== "ALL" && item.domain !== domainFilter) return false;
        if (statusFilter !== "ALL" && item.status !== statusFilter) return false;
        if (priorityFilter !== "ALL" && item.priority !== priorityFilter) return false;
        return true;
      }),
    [domainFilter, priorityFilter, sortedRecommendations, statusFilter]
  );

  useEffect(() => {
    if (filteredRecommendations.length === 0) {
      setSelectedId(null);
      return;
    }

    if (!selectedId || !filteredRecommendations.some((item) => item.id === selectedId)) {
      setSelectedId(filteredRecommendations[0].id);
    }
  }, [filteredRecommendations, selectedId]);

  const selectedRecommendation =
    filteredRecommendations.find((item) => item.id === selectedId) ?? filteredRecommendations[0] ?? null;

  const domainOptions = useMemo(() => {
    const present = new Set(sortedRecommendations.map((item) => item.domain));
    return DOMAIN_ORDER.filter((domain) => present.has(domain));
  }, [sortedRecommendations]);

  const activeCount = sortedRecommendations.length;
  const urgentCount = sortedRecommendations.filter((item) => item.priority === "URGENT").length;
  const domainsCount = new Set(sortedRecommendations.map((item) => item.domain)).size;

  if (recommendations === undefined) {
    return <RecommendationsSkeleton />;
  }

  return (
    <div className="flex flex-col gap-4 pb-28">
      <CampoSurface className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <CampoButton variant="secondary" size="sm" type="button" className="gap-1.5" onClick={() => router.push("/home")}>
                <ArrowLeft className="size-4" />
                Voltar
              </CampoButton>
              <CampoPill className="border-border bg-muted text-muted-foreground">
                {isOnline ? "Online" : "Offline"}
              </CampoPill>
            </div>
            <h1 className="mt-3 text-xl font-semibold tracking-tight">Recomendações</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              Leitura local, atualizada no sync e pronta para consulta mesmo sem conexão.
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            {lastSyncAt && (
              <CampoPill className="border-border bg-muted text-muted-foreground">
                <Clock3 className="size-3.5" />
                {new Date(lastSyncAt).toLocaleString("pt-BR")}
              </CampoPill>
            )}
            {!isOnline && (
              <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                <CloudOff className="size-3.5" />
                Dados locais
              </CampoPill>
            )}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <StatPill label="Ativas" value={activeCount} tone="sky" />
          <StatPill label="Urgentes" value={urgentCount} tone="rose" />
          <StatPill label="Domínios" value={domainsCount} tone="emerald" />
        </div>
      </CampoSurface>

      <CampoSurface className="p-4 sm:p-5">
        <CampoSectionTitle
          eyebrow="Filtros"
          title="Ajuste rápido"
          description="Combine domínio, status e prioridade para localizar o que importa."
          action={
            <CampoButton
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setDomainFilter("ALL");
                setStatusFilter("ALL");
                setPriorityFilter("ALL");
              }}
            >
              <RefreshCw className="size-4" />
              Limpar
            </CampoButton>
          }
        />

        <div className="mt-4 flex flex-col gap-4">
          <FilterGroup
            label="Domínio"
            current={domainFilter}
            options={[
              { value: "ALL", label: "Todos" },
              ...domainOptions.map((domain) => ({ value: domain, label: DOMAIN_LABELS[domain] ?? domain })),
            ]}
            onChange={(value) => setDomainFilter(value as DomainFilter)}
          />
          <FilterGroup
            label="Status"
            current={statusFilter}
            options={[
              { value: "ALL", label: "Todos" },
              ...ACTIVE_STATUSES.map((status) => ({ value: status, label: ACTIVE_STATUS_LABELS[status] ?? status })),
            ]}
            onChange={(value) => setStatusFilter(value as StatusFilter)}
          />
          <FilterGroup
            label="Prioridade"
            current={priorityFilter}
            options={[
              { value: "ALL", label: "Todas" },
              { value: "URGENT", label: "Urgente" },
              { value: "HIGH", label: "Alta" },
              { value: "NORMAL", label: "Normal" },
              { value: "LOW", label: "Baixa" },
            ]}
            onChange={(value) => setPriorityFilter(value as PriorityFilter)}
          />
        </div>
      </CampoSurface>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <CampoSurface className="p-4 sm:p-5">
          <CampoSectionTitle
            eyebrow="Lista"
            title="Recomendações persistidas"
            description="Itens ativos armazenados no dispositivo após a sincronização."
            action={<CampoPill className="border-border bg-muted text-muted-foreground">{filteredRecommendations.length} itens</CampoPill>}
          />

          <div className="mt-4 flex flex-col gap-2">
            {filteredRecommendations.length > 0 ? (
              filteredRecommendations.map((item) => (
                <RecommendationListItem
                  key={item.id}
                  item={item}
                  selected={item.id === selectedRecommendation?.id}
                  onClick={() => setSelectedId(item.id)}
                />
              ))
            ) : (
              <EmptyRecommendationsState hasAnyData={sortedRecommendations.length > 0} />
            )}
          </div>
        </CampoSurface>

        <CampoSurface className="p-4 sm:p-5 lg:sticky lg:top-4 lg:self-start">
          <CampoSectionTitle eyebrow="Detalhe" title="Leitura operacional" description="Resumo completo da recomendação selecionada." />

          {selectedRecommendation ? (
            <div className="mt-4 flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                <CampoPill className="border-border bg-muted text-muted-foreground">
                  {DOMAIN_LABELS[selectedRecommendation.domain] ?? selectedRecommendation.domain}
                </CampoPill>
                <CampoPill className={PRIORITY_TONE[selectedRecommendation.priority] ?? PRIORITY_TONE.NORMAL}>
                  {PRIORITY_LABELS[selectedRecommendation.priority] ?? selectedRecommendation.priority}
                </CampoPill>
                <CampoPill className="border-border bg-muted text-muted-foreground">
                  {ACTIVE_STATUS_LABELS[selectedRecommendation.status] ?? selectedRecommendation.status}
                </CampoPill>
              </div>

              <div className="space-y-2">
                <h2 className="text-lg font-semibold leading-tight text-foreground">{selectedRecommendation.title}</h2>
                <p className="text-sm leading-6 text-muted-foreground">{selectedRecommendation.summary}</p>
              </div>

              <DetailBlock label="Justificativa" value={selectedRecommendation.rationale} />
              <DetailBlock
                label="Ação recomendada"
                value={selectedRecommendation.action_label ?? selectedRecommendation.action_type}
              />
              <DetailBlock
                label="Origem / regra"
                value={`${selectedRecommendation.provider_name} · ${selectedRecommendation.rule_code}`}
              />
              <DetailBlock
                label="Contexto"
                value={[
                  selectedRecommendation.scope_type,
                  selectedRecommendation.scope_id,
                  selectedRecommendation.unidade_produtiva_id ?? "",
                ]
                  .filter(Boolean)
                  .join(" · ")}
              />
              <DetailBlock
                label="Linha do tempo"
                value={[
                  `Criada em ${formatDateTime(selectedRecommendation.created_at)}`,
                  `Atualizada em ${formatDateTime(selectedRecommendation.updated_at)}`,
                  selectedRecommendation.expires_at ? `Expira em ${formatDateTime(selectedRecommendation.expires_at)}` : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              />

              {selectedRecommendation.action_target && (
                <CampoPill className="border-border bg-muted text-muted-foreground">
                  Alvo: {selectedRecommendation.action_target}
                </CampoPill>
              )}
            </div>
          ) : (
            <div className="mt-4 flex min-h-[260px] flex-col items-center justify-center rounded-sm border border-dashed border-border bg-muted/30 px-6 text-center">
              <div className="flex size-12 items-center justify-center rounded-full border border-border bg-card">
                <Sparkles className="size-6 text-primary" />
              </div>
              <p className="mt-3 text-sm font-medium text-foreground">Selecione uma recomendação para ver o detalhe.</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Use os filtros para encontrar a recomendação operacional mais útil para o operador.
              </p>
            </div>
          )}
        </CampoSurface>
      </div>
    </div>
  );
}

function RecommendationListItem({
  item,
  selected,
  onClick,
}: {
  item: CachedRecomendacaoOperacional;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-start justify-between gap-3 rounded-sm border p-3 text-left shadow-sm transition-all active:scale-[0.99] ${
        selected
          ? "border-primary/40 bg-primary/5"
          : "border-border bg-card hover:border-primary/20 hover:bg-muted/50"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <CampoPill className="border-border bg-muted text-muted-foreground">
            {DOMAIN_LABELS[item.domain] ?? item.domain}
          </CampoPill>
          <CampoPill className={PRIORITY_TONE[item.priority] ?? PRIORITY_TONE.NORMAL}>
            {PRIORITY_LABELS[item.priority] ?? item.priority}
          </CampoPill>
        </div>
        <p className="mt-2 truncate text-sm font-semibold text-foreground">{item.title}</p>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.summary}</p>
        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
          <span>{ACTIVE_STATUS_LABELS[item.status] ?? item.status}</span>
          <span>·</span>
          <span>{formatDateTime(item.updated_at)}</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {item.provider_name}
        </span>
      </div>
    </button>
  );
}

function FilterGroup({
  label,
  current,
  options,
  onChange,
}: {
  label: string;
  current: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <CampoButton
            key={option.value}
            type="button"
            size="sm"
            variant={current === option.value ? "primary" : "secondary"}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </CampoButton>
        ))}
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "sky" | "rose" | "emerald";
}) {
  const toneClasses = {
    sky: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
    rose: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
    emerald:
      "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200",
  }[tone];

  return (
    <div className={`rounded-sm border p-3 shadow-sm ${toneClasses}`}>
      <p className="text-[10px] uppercase tracking-[0.16em] opacity-70">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="rounded-sm border border-border bg-muted/30 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm leading-6 text-foreground">{value}</p>
    </div>
  );
}

function EmptyRecommendationsState({ hasAnyData }: { hasAnyData: boolean }) {
  return (
    <div className="flex min-h-[260px] flex-col items-center justify-center rounded-sm border border-dashed border-border bg-muted/30 px-6 text-center">
      <div className="flex size-12 items-center justify-center rounded-full border border-border bg-card">
        <CloudOff className="size-6 text-muted-foreground" />
      </div>
      <p className="mt-3 text-sm font-medium text-foreground">
        {hasAnyData ? "Nenhuma recomendação encontrada para os filtros atuais." : "Nenhuma recomendação operacional disponível para esta unidade."}
      </p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        {hasAnyData
          ? "Limpe os filtros ou revise a sincronização do dispositivo."
          : "Sincronize quando houver conexão para carregar novas orientações persistidas."}
      </p>
    </div>
  );
}

function RecommendationsSkeleton() {
  return (
    <div className="flex flex-col gap-4 pb-28">
      <CampoSurface className="p-4 sm:p-5">
        <div className="h-24 animate-pulse rounded-sm border border-border bg-muted/40" />
      </CampoSurface>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <CampoSurface className="p-4 sm:p-5">
          <div className="space-y-3">
            <div className="h-6 w-44 animate-pulse rounded bg-muted/60" />
            <div className="h-4 w-64 animate-pulse rounded bg-muted/40" />
            <div className="space-y-2 pt-2">
              <div className="h-20 animate-pulse rounded-sm border border-border bg-muted/30" />
              <div className="h-20 animate-pulse rounded-sm border border-border bg-muted/30" />
              <div className="h-20 animate-pulse rounded-sm border border-border bg-muted/30" />
            </div>
          </div>
        </CampoSurface>
        <CampoSurface className="p-4 sm:p-5">
          <div className="space-y-3">
            <div className="h-6 w-36 animate-pulse rounded bg-muted/60" />
            <div className="h-4 w-52 animate-pulse rounded bg-muted/40" />
            <div className="h-32 animate-pulse rounded-sm border border-border bg-muted/30" />
          </div>
        </CampoSurface>
      </div>
    </div>
  );
}

function sortRecommendations(items: CachedRecomendacaoOperacional[]): CachedRecomendacaoOperacional[] {
  return [...items].sort((left, right) => {
    const priorityDelta = priorityScore(right.priority) - priorityScore(left.priority);
    if (priorityDelta !== 0) return priorityDelta;
    return dateScore(right.updated_at) - dateScore(left.updated_at);
  });
}

function priorityScore(priority: string): number {
  return { URGENT: 4, HIGH: 3, NORMAL: 2, LOW: 1 }[priority] ?? 0;
}

function dateScore(value: string): number {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("pt-BR");
}
