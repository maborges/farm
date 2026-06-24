"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { CampoButton, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";
import { formatPecuariaTaskType } from "@/lib/pecuaria-tasks";

interface Activity {
  key: string;
  label: string;
  icon: string;
  path: string;
  module: "agricola" | "pecuaria";
}

const ACTIVITIES: Activity[] = [
  { key: "caderno", label: "Caderno", icon: "📓", path: "/caderno", module: "agricola" },
  { key: "aplicacao", label: "Aplicação", icon: "🌿", path: "/campo/aplicacao", module: "agricola" },
  { key: "colheita", label: "Colheita", icon: "🌾", path: "/campo/colheita", module: "agricola" },
  { key: "epi", label: "Entrega EPI", icon: "🦺", path: "/campo/epi", module: "agricola" },
  { key: "pesagem", label: "Pesagem", icon: "⚖️", path: "/campo/pesagem", module: "pecuaria" },
  { key: "vacinacao", label: "Vacinação", icon: "💉", path: "/campo/vacinacao", module: "pecuaria" },
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

export default function HomePage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const { pendingCount } = useSyncStore();

  const hoje = new Date().toISOString().slice(0, 10);

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

  const availableActivities = ACTIVITIES.filter(
    (a) => session?.modules?.includes(a.module)
  );

  const emExecucaoCount = (tarefasEmExecucao?.length ?? 0);
  const tarefasAtribuidas = (tarefasPendentes ?? []).filter(
    (t) => t.dispositivo_id === session?.device_id
  );
  const tarefasHoje = (tarefasPendentes ?? []).filter(
    (t) => t.dispositivo_id !== session?.device_id && t.data_programada === hoje
  );
  const tarefasAtrasadas = (tarefasPendentes ?? []).filter(
    (t) =>
      t.dispositivo_id !== session?.device_id &&
      !!t.data_programada &&
      t.data_programada < hoje
  );
  const atribuidasCount = tarefasAtribuidas.length;
  const hojeCount = tarefasHoje.length;
  const atrasadasCount = tarefasAtrasadas.length;

  return (
    <div className="flex flex-col gap-4 pb-28">
      <CampoSurface className="p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <h1 className="text-xl font-semibold tracking-tight">Taréfas</h1>
              <CampoPill className="ml-auto shrink-0">
                {availableActivities.length} talhões ativos
              </CampoPill>
            </div>
            <div>
              <p className="mt-0.5 text-xs text-muted-foreground">Tudo pronto para registrar o dia no campo.</p>
            </div>
          </div>
          {pendingCount > 0 && (
            <CampoButton variant="secondary" size="sm" onClick={() => router.push("/sync")}>
              Sync
              <span className="ml-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">{pendingCount}</span>
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
        </div>
      </CampoSurface>

      {/* Tarefas atribuídas ao dispositivo */}
      {atribuidasCount > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Dispositivo"
            title="Atribuídas a este aparelho"
            description="Tarefas já liberadas para este dispositivo, inclusive as futuras."
            action={<CampoPill className="border-violet-200 bg-violet-50 text-violet-800 dark:border-violet-900/60 dark:bg-violet-950/30 dark:text-violet-200">{atribuidasCount}</CampoPill>}
          />
          <div className="flex flex-col gap-2">
            {tarefasAtribuidas.map((t) => (
              <TarefaCard
                key={t.id}
                task={t}
                activeFazendaId={session?.active_fazenda_id}
                onClick={() => router.push(`/campo/tarefa/${t.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Em execução — destaque máximo */}
      {emExecucaoCount > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Prioridade"
            title="Em execução"
            description="Tarefas que estão sendo conduzidas neste momento."
            action={<CampoPill className="border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200">{emExecucaoCount}</CampoPill>}
          />
          <div className="flex flex-col gap-2">
            {tarefasEmExecucao?.map((t) => (
              <TarefaCard
                key={t.id}
                task={t}
                activeFazendaId={session?.active_fazenda_id}
                onClick={() => router.push(`/campo/tarefa/${t.id}`)}
                highlight
              />
            ))}
          </div>
        </section>
      )}

      {/* Tarefas atrasadas */}
      {atrasadasCount > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Atenção"
            title="Atrasadas"
            description="Pendências que já passaram da data programada."
            action={<CampoPill className="border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">{atrasadasCount}</CampoPill>}
          />
          <div className="flex flex-col gap-2">
            {tarefasAtrasadas?.map((t) => (
              <TarefaCard
                key={t.id}
                task={t}
                activeFazendaId={session?.active_fazenda_id}
                onClick={() => router.push(`/campo/tarefa/${t.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Tarefas de hoje */}
      {hojeCount > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Agenda"
            title="Para hoje"
            description="Tarefas programadas para executar ainda hoje."
            action={<CampoPill className="border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200">{hojeCount}</CampoPill>}
          />
          <div className="flex flex-col gap-2">
            {tarefasHoje?.map((t) => (
              <TarefaCard
                key={t.id}
                task={t}
                activeFazendaId={session?.active_fazenda_id}
                onClick={() => router.push(`/campo/tarefa/${t.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Sem tarefas programadas */}
      {hojeCount === 0 && atrasadasCount === 0 && emExecucaoCount === 0 && atribuidasCount === 0 && (
        <CampoSurface className="p-4 text-center text-sm text-muted-foreground">
          <div className="mx-auto flex size-12 items-center justify-center rounded-sm border border-border bg-muted text-xl">
            🌤️
          </div>
          <p className="mt-3 text-sm font-medium text-foreground">Nenhuma tarefa programada para hoje.</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Você pode iniciar uma nova atividade manual ou revisar a sincronização do dispositivo.
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

      {/* Nova Atividade Manual */}
      <section id="nova-atividade" className="flex scroll-mt-24 flex-col gap-2.5">
        <CampoSectionTitle
          eyebrow="Entrada rápida"
          title="Nova atividade"
          description="Abra um registro manual com acesso rápido."
        />
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {availableActivities.map((act) => (
            <button
              key={act.key}
              onClick={() => router.push(act.path)}
              className="group rounded-sm border border-border bg-card p-4 text-left shadow-sm transition-all hover:border-primary/30 hover:bg-muted active:scale-[0.98]"
            >
              <span className="text-2xl transition-transform group-hover:scale-105">{act.icon}</span>
              <span className="mt-1.5 block text-sm font-semibold">{act.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Registros offline recentes */}
      {recentTasks && recentTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Histórico"
            title="Registros offline recentes"
            description="Itens salvos localmente aguardando a próxima sincronização."
          />
          <div className="flex flex-col gap-2">
            {recentTasks.map((task) => (
              <div
                key={task.id}
                className="rounded-sm border border-border bg-card px-3.5 py-3 shadow-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{formatTaskType(task.type)}</p>
                    <p className="text-xs text-muted-foreground">{formatDate(task.created_at)}</p>
                  </div>
                  <span
                    className={`text-xs rounded-full px-2.5 py-1 font-medium ${task.synced
                        ? "bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-200"
                        : task.sync_conflict
                          ? "bg-rose-50 text-rose-800 dark:bg-rose-950/30 dark:text-rose-200"
                          : "bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
                      }`}
                  >
                    {task.synced ? "✓ Sync" : task.sync_conflict ? "Conflito" : "Pendente"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function TarefaCard({
  task,
  activeFazendaId,
  onClick,
  highlight,
}: {
  task: { id: string; titulo?: string; type: string; data_programada?: string; prioridade: string; fazenda_id?: string; talhao_id?: string; lote_id?: string; operador_id?: string };
  activeFazendaId?: string;
  onClick: () => void;
  highlight?: boolean;
}) {
  const hasContextMismatch = !!activeFazendaId && !!task.fazenda_id && task.fazenda_id !== activeFazendaId;

  return (
    <button
      onClick={onClick}
      className={`flex w-full items-start justify-between gap-3 rounded-sm border p-3.5 text-left shadow-sm transition-transform active:scale-[0.99] ${highlight
          ? "border-sky-200 bg-sky-50 dark:border-sky-900/60 dark:bg-sky-950/30"
          : "border-border bg-card"
        }`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="truncate text-sm font-semibold text-foreground">
          {task.titulo ?? formatTaskType(task.type)}
        </p>
        {task.data_programada && (
          <p className="text-xs text-muted-foreground">
            {new Date(task.data_programada + "T00:00:00").toLocaleDateString("pt-BR")}
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

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
