"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { type LucideIcon, BookText, Sprout, Wheat, ShieldHalf, Scale, Syringe, CloudSun, Dna, HeartPulse, Baby, Scissors } from "lucide-react";
import { db, type CachedRecomendacaoOperacional, type LocalTask } from "@/lib/db";
import { consumeSessionClearNotice, useSessionStore, type SessionClearNotice } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { CampoButton, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
import { TaskDomainBadge } from "@/components/campo/task-domain-badge";
import { formatPecuariaTaskType } from "@/lib/pecuaria-tasks";
import { formatTaskDomainLabel, resolveTaskDomain, type TaskDomain } from "@/lib/task-domain";

interface Activity {
  key: string;
  label: string;
  icon: LucideIcon;
  path: string;
  module: "agricola" | "pecuaria";
}

const ACTIVITIES: Activity[] = [
  { key: "caderno", label: "Caderno", icon: BookText, path: "/caderno", module: "agricola" },
  { key: "aplicacao", label: "Aplicação", icon: Sprout, path: "/campo/aplicacao", module: "agricola" },
  { key: "colheita", label: "Colheita", icon: Wheat, path: "/campo/colheita", module: "agricola" },
  { key: "epi", label: "Entrega EPI", icon: ShieldHalf, path: "/campo/epi", module: "agricola" },
  { key: "pesagem", label: "Pesagem", icon: Scale, path: "/campo/pesagem", module: "pecuaria" },
  { key: "vacinacao", label: "Vacinação", icon: Syringe, path: "/campo/vacinacao", module: "pecuaria" },
  { key: "cobertura", label: "Cobertura", icon: Dna, path: "/campo/reproducao/cobertura", module: "pecuaria" },
  { key: "diagnostico", label: "Diagnóstico", icon: HeartPulse, path: "/campo/reproducao/diagnostico-prenhez", module: "pecuaria" },
  { key: "parto", label: "Parto", icon: Baby, path: "/campo/reproducao/parto", module: "pecuaria" },
  { key: "desmama", label: "Desmama", icon: Scissors, path: "/campo/reproducao/desmama", module: "pecuaria" },
];

const PRIORIDADE_COLOR: Record<string, string> = {
  URGENTE: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
  ALTA: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
  NORMAL: "border-border bg-muted text-muted-foreground",
  BAIXA: "border-border bg-card text-muted-foreground",
};

const PRIORIDADE_LABEL: Record<string, string> = {
  URGENTE: "Urgente",
  ALTA: "Alta",
  NORMAL: "Normal",
  BAIXA: "Baixa",
};

type DomainFilter = "ALL" | TaskDomain;

export default function HomePage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const { pendingCount } = useSyncStore();
  const [domainFilter, setDomainFilter] = useState<DomainFilter>("ALL");
  const [clearNotice, setClearNotice] = useState<SessionClearNotice | null>(null);

  useEffect(() => {
    setClearNotice(consumeSessionClearNotice());
  }, []);

  const hoje = new Date().toISOString().slice(0, 10);

  const talhoes = useLiveQuery(() => db.talhoes.toArray(), []);
  const lotes = useLiveQuery(() => db.lotes.toArray(), []);
  const safras = useLiveQuery(() => db.safras.toArray(), []);
  const recomendacoesOperacionais = useLiveQuery(() => db.recomendacoes_operacionais.toArray(), []);

  const tarefasPendentes = useLiveQuery(
    () =>
      db.tasks
        .where("origem")
        .equals("PROGRAMADA")
        .filter((t) => t.status_execucao === "PENDENTE")
        .toArray(),
    []
  );

  const tarefasEmExecucao = useLiveQuery(
    () =>
      db.tasks
        .where("status_execucao")
        .equals("EM_EXECUCAO")
        .toArray(),
    []
  );

  const recentTasks = useLiveQuery(
    () =>
      db.tasks
        .orderBy("created_at")
        .reverse()
        .filter((t) => t.origem === "MANUAL")
        .limit(5)
        .toArray(),
    []
  );

  const availableActivities = ACTIVITIES.filter((a) => session?.modules?.includes(a.module));

  const talhoesById = useMemo(() => new Map((talhoes ?? []).map((item) => [item.id, item])), [talhoes]);
  const lotesById = useMemo(() => new Map((lotes ?? []).map((item) => [item.id, item])), [lotes]);
  const safrasById = useMemo(() => new Map((safras ?? []).map((item) => [item.id, item])), [safras]);
  const activeRecommendations = useMemo(
    () => sortRecommendations((recomendacoesOperacionais ?? []).filter((item) => isActiveRecommendation(item.status))),
    [recomendacoesOperacionais]
  );

  const emExecucaoCount = tarefasEmExecucao?.length ?? 0;
  const tarefasAtribuidas = (tarefasPendentes ?? []).filter((t) => t.dispositivo_id === session?.device_id);
  const tarefasHoje = (tarefasPendentes ?? []).filter(
    (t) => t.dispositivo_id !== session?.device_id && t.data_programada === hoje
  );
  const tarefasAtrasadas = (tarefasPendentes ?? []).filter(
    (t) => t.dispositivo_id !== session?.device_id && !!t.data_programada && t.data_programada < hoje
  );
  const atribuidasCount = tarefasAtribuidas.length;
  const hojeCount = tarefasHoje.length;
  const atrasadasCount = tarefasAtrasadas.length;

  const pendingByDomain = useMemo(() => {
    const counts: Record<TaskDomain, number> = { AGRICULTURA: 0, PECUARIA: 0 };
    for (const task of tarefasPendentes ?? []) {
      counts[resolveTaskDomain(task)] += 1;
    }
    return counts;
  }, [tarefasPendentes]);

  const operationalTasks = useMemo(() => {
    const merged = new Map<string, LocalTask>();
    for (const task of [...(tarefasPendentes ?? []), ...(tarefasEmExecucao ?? [])]) {
      merged.set(task.id, task);
    }
    return [...merged.values()].sort(sortTaskCard);
  }, [tarefasPendentes, tarefasEmExecucao]);

  const filteredOperationalTasks = useMemo(
    () =>
      domainFilter === "ALL"
        ? operationalTasks
        : operationalTasks.filter((task) => resolveTaskDomain(task) === domainFilter),
    [domainFilter, operationalTasks]
  );

  const operationalGroups = useMemo(() => {
    const groups: Array<{ domain: TaskDomain; tasks: LocalTask[] }> = [];
    for (const domain of ["AGRICULTURA", "PECUARIA"] as TaskDomain[]) {
      const tasks = filteredOperationalTasks.filter((task) => resolveTaskDomain(task) === domain);
      if (tasks.length > 0) {
        groups.push({ domain, tasks });
      }
    }
    return groups;
  }, [filteredOperationalTasks]);

  const historyTasks = useMemo(() => {
    const items = (recentTasks ?? []).filter((task) =>
      domainFilter === "ALL" ? true : resolveTaskDomain(task) === domainFilter
    );
    return items.sort(sortTaskCard);
  }, [domainFilter, recentTasks]);

  const summaryCards = useMemo(() => {
    const items = [
      { domain: "AGRICULTURA" as TaskDomain, count: pendingByDomain.AGRICULTURA },
      { domain: "PECUARIA" as TaskDomain, count: pendingByDomain.PECUARIA },
    ];
    return items.filter((item) => item.count > 0 || domainFilter === item.domain);
  }, [domainFilter, pendingByDomain]);

  return (
    <div className="flex flex-col gap-4 pb-28">
      {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}
      <CampoSurface className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <h1 className="text-xl font-semibold tracking-tight">Tarefas</h1>
              <CampoPill className="ml-auto shrink-0">{availableActivities.length} atalhos ativos</CampoPill>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">Tudo pronto para registrar o dia no campo.</p>
          </div>
          {pendingCount > 0 && (
            <CampoButton variant="secondary" size="sm" onClick={() => router.push("/sync")}>
              Sync
              <span className="ml-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                {pendingCount}
              </span>
            </CampoButton>
          )}
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <CampoPill className="w-full justify-center border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
            Em execução {emExecucaoCount}
          </CampoPill>
          <CampoPill className="w-full justify-center border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">
            Hoje {hojeCount}
          </CampoPill>
          <CampoPill className="w-full justify-center border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
            Atrasadas {atrasadasCount}
          </CampoPill>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {pendingCount > 0 && (
            <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
              {pendingCount} itens aguardando sync
            </CampoPill>
          )}
          <CampoPill className="border-border bg-muted text-muted-foreground">
            Filtro atual: {domainFilter === "ALL" ? "Todas" : formatTaskDomainLabel(domainFilter)}
          </CampoPill>
        </div>
      </CampoSurface>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {summaryCards.map((item) => (
          <CampoSurface
            key={item.domain}
            className={`p-4 ${
              item.domain === "PECUARIA"
                ? "border-sky-200 bg-sky-50/60 dark:border-sky-900/60 dark:bg-sky-950/20"
                : "border-green-200 bg-green-50/60 dark:border-green-900/60 dark:bg-green-950/20"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <TaskDomainBadge domain={item.domain} />
                <p className="mt-2 text-lg font-semibold text-foreground">
                  {item.count} tarefa{item.count === 1 ? "" : "s"} pendente{item.count === 1 ? "" : "s"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.domain === "AGRICULTURA"
                    ? "Operações agrícolas em andamento"
                    : "Manejos pecuários em andamento"}
                </p>
              </div>
              <div className="rounded-sm border border-border bg-card px-3 py-2 text-right">
                <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Status</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {item.domain === "AGRICULTURA" ? "Agrícola" : "Pecuário"}
                </p>
              </div>
            </div>
          </CampoSurface>
        ))}
      </div>

      {recomendacoesOperacionais !== undefined && (
        <CampoSurface className="p-4 sm:p-5">
          <CampoSectionTitle
            eyebrow="Inteligência"
            title="Recomendações operacionais"
            description="Orientações persistidas no dispositivo e atualizadas no sync."
            action={
              <CampoButton variant="secondary" size="sm" onClick={() => router.push("/recomendacoes")}>
                Abrir painel
              </CampoButton>
            }
          />

          <div className="mt-4 flex flex-wrap gap-2">
            <CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">
              {activeRecommendations.length} ativas
            </CampoPill>
            <CampoPill className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
              {activeRecommendations.filter((item) => item.priority === "URGENT").length} urgentes
            </CampoPill>
            <CampoPill className="border-border bg-muted text-muted-foreground">
              {new Set(activeRecommendations.map((item) => item.domain)).size} domínios
            </CampoPill>
          </div>

          {activeRecommendations.length > 0 ? (
            <div className="mt-4 grid gap-2">
              {activeRecommendations.slice(0, 3).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => router.push("/recomendacoes")}
                  className="flex w-full items-start justify-between gap-3 rounded-sm border border-border bg-card p-3 text-left shadow-sm transition-all hover:border-primary/20 hover:bg-muted/50 active:scale-[0.99]"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <CampoPill className="border-border bg-muted text-muted-foreground">
                        {formatRecommendationDomain(item.domain)}
                      </CampoPill>
                      <CampoPill className={getPriorityTone(item.priority)}>
                        {formatRecommendationPriority(item.priority)}
                      </CampoPill>
                    </div>
                    <p className="mt-2 truncate text-sm font-semibold text-foreground">{item.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.summary}</p>
                  </div>
                  <div className="shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    {item.provider_name}
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="mt-4 flex min-h-[132px] flex-col items-center justify-center rounded-sm border border-dashed border-border bg-muted/30 px-6 text-center">
              <p className="text-sm font-medium text-foreground">Nenhuma recomendação operacional disponível para esta unidade.</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Sincronize quando houver conexão para carregar orientações persistidas no aparelho.
              </p>
            </div>
          )}
        </CampoSurface>
      )}

      <div className="flex flex-wrap gap-2">
        {(["ALL", "AGRICULTURA", "PECUARIA"] as DomainFilter[]).map((filter) => {
          const active = domainFilter === filter;
          const label = filter === "ALL" ? "Todas" : filter === "AGRICULTURA" ? "Agricultura" : "Pecuária";
          return (
            <CampoButton
              key={filter}
              type="button"
              variant={active ? "primary" : "secondary"}
              size="sm"
              onClick={() => setDomainFilter(filter)}
            >
              {label}
            </CampoButton>
          );
        })}
      </div>

      {operationalGroups.length > 0 ? (
        <section className="flex flex-col gap-4">
          {operationalGroups.map(({ domain, tasks }) => (
            <div key={domain} className="flex flex-col gap-2">
              <CampoSectionTitle
                eyebrow={domain}
                title={formatTaskDomainLabel(domain)}
                description={
                  domain === "AGRICULTURA"
                    ? "Plantio, aplicação e colheita aparecem agrupados no mesmo contexto."
                    : "Pesagem, vacinação e demais manejos pecuários ficam concentrados aqui."
                }
                action={
                  <CampoPill className="border-border bg-muted text-muted-foreground">
                    {tasks.length} item{tasks.length === 1 ? "" : "s"}
                  </CampoPill>
                }
              />
              <div className="flex flex-col gap-2">
                {tasks.map((task) => (
                  <TarefaCard
                    key={task.id}
                    task={task}
                    domain={resolveTaskDomain(task)}
                    activeFazendaId={session?.active_fazenda_id}
                    talhoesById={talhoesById}
                    lotesById={lotesById}
                    safrasById={safrasById}
                    onClick={() => router.push(`/campo/tarefa/${task.id}`)}
                    highlight={task.status_execucao === "EM_EXECUCAO"}
                  />
                ))}
              </div>
            </div>
          ))}
        </section>
      ) : (
        <CampoSurface className="p-4 text-center text-sm text-muted-foreground">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-border bg-muted">
            <CloudSun className="size-6 text-muted-foreground" strokeWidth={1.5} />
          </div>
          <p className="mt-3 text-sm font-medium text-foreground">Nenhuma tarefa encontrada para este filtro.</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Você pode alternar o filtro acima ou revisar a sincronização do dispositivo.
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <CampoButton variant="secondary" className="flex-1" onClick={() => router.push("/sync")}>
              Ver sync
            </CampoButton>
            <CampoButton variant="primary" className="flex-1" onClick={() => router.push("/caderno")}>
              Abrir caderno
            </CampoButton>
          </div>
        </CampoSurface>
      )}

      {historyTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Histórico"
            title="Registros offline recentes"
            description="Itens salvos localmente aguardando a próxima sincronização."
          />
          <div className="flex flex-col gap-2">
            {historyTasks.map((task) => (
              <TarefaCard
                key={task.id}
                task={task}
                domain={resolveTaskDomain(task)}
                activeFazendaId={session?.active_fazenda_id}
                talhoesById={talhoesById}
                lotesById={lotesById}
                safrasById={safrasById}
                onClick={() => router.push(`/campo/tarefa/${task.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      <section id="nova-atividade" className="flex scroll-mt-24 flex-col gap-2.5">
        <CampoSectionTitle
          eyebrow="Entrada rápida"
          title="Nova atividade"
          description="Abra um registro manual com acesso rápido."
        />
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {availableActivities.map((act) => {
            const Icon = act.icon;
            return (
              <button
                key={act.key}
                onClick={() => router.push(act.path)}
                className="group flex flex-col items-start rounded-sm border border-border bg-card p-4 text-left shadow-sm transition-all hover:border-primary/30 hover:bg-muted active:scale-[0.98]"
              >
                <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-hover:scale-110">
                  <Icon className="size-5" strokeWidth={2} />
                </div>
                <span className="mt-3 block text-sm font-semibold">{act.label}</span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function isActiveRecommendation(status: string): boolean {
  return ["CREATED", "VIEWED", "ACCEPTED", "POSTPONED", "REOPENED"].includes(status);
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

function formatRecommendationDomain(domain: string): string {
  return (
    {
      FIELD: "Campo",
      AGRICULTURE: "Agricultura",
      LIVESTOCK: "Pecuária",
      OPERATIONS: "Operações",
      FINANCE: "Financeiro",
      SYSTEM: "Sistema",
      INTEGRATIONS: "Integrações",
    }[domain] ?? domain
  );
}

function formatRecommendationPriority(priority: string): string {
  return { URGENT: "Urgente", HIGH: "Alta", NORMAL: "Normal", LOW: "Baixa" }[priority] ?? priority;
}

function getPriorityTone(priority: string): string {
  return (
    {
      URGENT:
        "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200",
      HIGH:
        "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200",
      NORMAL:
        "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200",
      LOW: "border-border bg-muted text-muted-foreground",
    }[priority] ?? "border-border bg-muted text-muted-foreground"
  );
}

function TarefaCard({
  task,
  activeFazendaId,
  domain,
  talhoesById,
  lotesById,
  safrasById,
  onClick,
  highlight,
}: {
  task: LocalTask;
  activeFazendaId?: string;
  domain: TaskDomain;
  talhoesById: Map<string, { nome: string }>;
  lotesById: Map<string, { identificacao: string }>;
  safrasById: Map<string, { ano_safra: string }>;
  onClick: () => void;
  highlight?: boolean;
}) {
  const hasContextMismatch = !!activeFazendaId && !!task.fazenda_id && task.fazenda_id !== activeFazendaId;
  const contextLines = getTaskContextLines(task, domain, talhoesById, lotesById, safrasById);

  return (
    <button
      onClick={onClick}
      className={`flex w-full items-start justify-between gap-3 rounded-sm border p-3.5 text-left shadow-sm transition-transform active:scale-[0.99] ${highlight
          ? "border-sky-200 bg-sky-50 dark:border-sky-900/60 dark:bg-sky-950/30"
        : "border-border bg-card"
        }`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <TaskDomainBadge domain={domain} />
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${getTaskStatusTone(task)}`}>
            {getTaskStatusLabel(task)}
          </span>
        </div>
        <p className="mt-1 truncate text-sm font-semibold text-foreground">
          {task.titulo ?? formatTaskType(task.type)}
        </p>
        {contextLines.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
            {contextLines.map((line) => (
              <span key={line} className="text-[11px] text-muted-foreground">
                {line}
              </span>
            ))}
          </div>
        )}
        {task.data_programada || task.created_at ? (
          <p className="mt-1 text-xs text-muted-foreground">
            {formatDate(task.data_programada ? `${task.data_programada}T00:00:00` : task.created_at)}
          </p>
        ) : null}
        {task.status_execucao === "CONCLUIDA" && task.concluida_em && (
          <p className="text-xs text-muted-foreground">
            Concluída em {new Date(task.concluida_em).toLocaleString("pt-BR")}
          </p>
        )}
        {hasContextMismatch && (
          <p className="text-[11px] font-medium text-amber-700 dark:text-amber-300">
            Fora da unidade ativa
          </p>
        )}
      </div>
      <span
        className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${PRIORIDADE_COLOR[task.prioridade] ?? PRIORIDADE_COLOR.NORMAL
          }`}
      >
        {PRIORIDADE_LABEL[task.prioridade] ?? task.prioridade}
      </span>
    </button>
  );
}

function formatTaskType(type: string): string {
  const map: Record<string, string> = {
    APLICACAO_DEFENSIVO: "Aplicação de Defensivo",
    APLICACAO_FERTILIZANTE: "Aplicação de Fertilizante",
    PLANTIO_REGISTRO: "Plantio",
    COLHEITA_REGISTRO: "Registro de Colheita",
    PESAGEM: "Pesagem",
    PESAGEM_ANIMAL: "Pesagem de Animal",
    VACINACAO: "Vacinação",
    VACINACAO_LOTE: "Vacinação de Lote",
    PARTO_REGISTRO: "Registro de Parto",
    MONITORAMENTO_PRAGA: "Monitoramento de Praga",
  };
  return map[type] ?? formatPecuariaTaskType(type);
}

function sortTaskCard(a: LocalTask, b: LocalTask): number {
  const statusRank: Record<LocalTask["status_execucao"], number> = {
    EM_EXECUCAO: 0,
    PENDENTE: 1,
    CONCLUIDA: 2,
    CANCELADA: 3,
  };
  const priorityRank: Record<string, number> = {
    URGENTE: 0,
    ALTA: 1,
    NORMAL: 2,
    BAIXA: 3,
  };
  const statusDelta = statusRank[a.status_execucao] - statusRank[b.status_execucao];
  if (statusDelta !== 0) return statusDelta;
  const priorityDelta = (priorityRank[a.prioridade] ?? 99) - (priorityRank[b.prioridade] ?? 99);
  if (priorityDelta !== 0) return priorityDelta;
  return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
}

function getTaskStatusLabel(task: LocalTask): string {
  if (task.status_execucao === "EM_EXECUCAO") return "Em execução";
  if (task.status_execucao === "CONCLUIDA") return "Concluída";
  if (task.status_execucao === "CANCELADA") return "Cancelada";
  return "Pendente";
}

function getTaskStatusTone(task: LocalTask): string {
  if (task.status_execucao === "EM_EXECUCAO") {
    return "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200";
  }
  if (task.status_execucao === "CONCLUIDA") {
    return "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200";
  }
  if (task.status_execucao === "CANCELADA") {
    return "border-border bg-muted text-muted-foreground";
  }
  return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200";
}

function getTaskContextLines(
  task: LocalTask,
  domain: TaskDomain,
  talhoesById: Map<string, { nome: string }>,
  lotesById: Map<string, { identificacao: string }>,
  safrasById: Map<string, { ano_safra: string }>
): string[] {
  const dados = task.dados ?? {};

  if (domain === "AGRICULTURA") {
    const lines: string[] = [];
    const talhao = task.talhao_id ? talhoesById.get(task.talhao_id) : undefined;
    const cultura =
      typeof dados.cultura_nome === "string"
        ? dados.cultura_nome
        : typeof dados.cultura === "string"
          ? dados.cultura
          : undefined;
    const safraId = typeof dados.safra_id === "string" ? dados.safra_id : undefined;
    const safra = safraId ? safrasById.get(safraId) : undefined;

    if (talhao?.nome) lines.push(`Talhão: ${talhao.nome}`);
    if (cultura) lines.push(`Cultura: ${cultura}`);
    if (safra?.ano_safra) lines.push(`Safra: ${safra.ano_safra}`);
    return lines;
  }

  const lines: string[] = [];
  const lote = task.lote_id ? lotesById.get(task.lote_id) : undefined;
  const animaisIds = Array.isArray(dados.animais_ids)
    ? dados.animais_ids.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
  const quantidadeAnimais =
    animaisIds.length > 0
      ? animaisIds.length
      : typeof dados.quantidade_animais === "number"
        ? dados.quantidade_animais
        : undefined;
  const areaId = typeof dados.area_id === "string" ? dados.area_id : undefined;

  if (lote?.identificacao) lines.push(`Lote: ${lote.identificacao}`);
  if (areaId) lines.push(`Piquete: ${areaId.slice(0, 8)}…`);
  if (quantidadeAnimais !== undefined) lines.push(`Animais: ${quantidadeAnimais}`);
  return lines;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
