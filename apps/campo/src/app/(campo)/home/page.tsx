"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";

interface Activity {
  key: string;
  label: string;
  icon: string;
  path: string;
  module: "agricola" | "pecuaria";
}

const ACTIVITIES: Activity[] = [
  { key: "aplicacao", label: "Aplicação", icon: "🌿", path: "/campo/aplicacao", module: "agricola" },
  { key: "colheita", label: "Colheita", icon: "🌾", path: "/campo/colheita", module: "agricola" },
  { key: "pesagem", label: "Pesagem", icon: "⚖️", path: "/campo/pesagem", module: "pecuaria" },
  { key: "vacinacao", label: "Vacinação", icon: "💉", path: "/campo/vacinacao", module: "pecuaria" },
];

const PRIORIDADE_COLOR: Record<string, string> = {
  URGENTE: "bg-red-900 text-red-300 border-red-700",
  ALTA: "bg-orange-900 text-orange-300 border-orange-700",
  NORMAL: "bg-neutral-700 text-neutral-300 border-neutral-600",
  BAIXA: "bg-neutral-800 text-neutral-500 border-neutral-700",
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
  const { pendingCount, isOnline } = useSyncStore();

  const hoje = new Date().toISOString().slice(0, 10);

  const tarefasHoje = useLiveQuery(
    () =>
      db.tasks
        .where("origem")
        .equals("PROGRAMADA")
        .filter((t) => t.data_programada === hoje && t.status_execucao === "PENDENTE")
        .toArray(),
    [hoje]
  );

  const tarefasAtrasadas = useLiveQuery(
    () =>
      db.tasks
        .where("origem")
        .equals("PROGRAMADA")
        .filter(
          (t) =>
            !!t.data_programada &&
            t.data_programada < hoje &&
            t.status_execucao === "PENDENTE"
        )
        .toArray(),
    [hoje]
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
  const hojeCount = (tarefasHoje?.length ?? 0);
  const atrasadasCount = (tarefasAtrasadas?.length ?? 0);

  return (
    <div className="flex flex-col gap-6 p-4 pb-10">
      {/* Header */}
      <div className="flex items-center justify-between pt-2">
        <div>
          <p className="text-xs text-neutral-500">Olá,</p>
          <h1 className="text-lg font-bold">{session?.user_name}</h1>
        </div>
        <button
          onClick={() => router.push("/sync")}
          className="flex items-center gap-1.5 text-xs bg-neutral-800 rounded-full px-3 py-1.5"
        >
          <span className={`size-1.5 rounded-full ${isOnline ? "bg-green-500" : "bg-neutral-500"}`} />
          {isOnline ? "Online" : "Offline"}
          {pendingCount > 0 && (
            <span className="bg-amber-500 text-black rounded-full px-1.5 text-xs font-bold ml-0.5">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {/* Em execução — destaque máximo */}
      {emExecucaoCount > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-blue-400 uppercase tracking-wide flex items-center gap-2">
            ▶ Em Execução
            <span className="bg-blue-900 text-blue-300 rounded-full px-2 py-0.5 text-xs">{emExecucaoCount}</span>
          </h2>
          <div className="flex flex-col gap-2">
            {tarefasEmExecucao?.map((t) => (
              <TarefaCard key={t.id} task={t} onClick={() => router.push(`/campo/tarefa/${t.id}`)} highlight />
            ))}
          </div>
        </section>
      )}

      {/* Tarefas atrasadas */}
      {atrasadasCount > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-red-400 uppercase tracking-wide flex items-center gap-2">
            ⚠ Atrasadas
            <span className="bg-red-900 text-red-300 rounded-full px-2 py-0.5 text-xs">{atrasadasCount}</span>
          </h2>
          <div className="flex flex-col gap-2">
            {tarefasAtrasadas?.map((t) => (
              <TarefaCard key={t.id} task={t} onClick={() => router.push(`/campo/tarefa/${t.id}`)} />
            ))}
          </div>
        </section>
      )}

      {/* Tarefas de hoje */}
      {hojeCount > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-green-400 uppercase tracking-wide flex items-center gap-2">
            📅 Para Hoje
            <span className="bg-green-900 text-green-300 rounded-full px-2 py-0.5 text-xs">{hojeCount}</span>
          </h2>
          <div className="flex flex-col gap-2">
            {tarefasHoje?.map((t) => (
              <TarefaCard key={t.id} task={t} onClick={() => router.push(`/campo/tarefa/${t.id}`)} />
            ))}
          </div>
        </section>
      )}

      {/* Sem tarefas programadas */}
      {hojeCount === 0 && atrasadasCount === 0 && emExecucaoCount === 0 && (
        <div className="bg-neutral-800 rounded-2xl p-5 text-center text-neutral-500 text-sm">
          Nenhuma tarefa programada para hoje
        </div>
      )}

      {/* Nova Atividade Manual */}
      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
          Nova Atividade
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {availableActivities.map((act) => (
            <button
              key={act.key}
              onClick={() => router.push(act.path)}
              className="bg-neutral-800 hover:bg-neutral-700 active:scale-95 transition-all rounded-2xl p-5 flex flex-col gap-2 text-left"
            >
              <span className="text-3xl">{act.icon}</span>
              <span className="text-sm font-semibold">{act.label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Registros offline recentes */}
      {recentTasks && recentTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
            Registros Offline
          </h2>
          <div className="flex flex-col gap-2">
            {recentTasks.map((task) => (
              <div
                key={task.id}
                className="bg-neutral-800 rounded-2xl px-4 py-3 flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium">{formatTaskType(task.type)}</p>
                  <p className="text-xs text-neutral-500">{formatDate(task.created_at)}</p>
                </div>
                <span
                  className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                    task.synced
                      ? "bg-green-900 text-green-300"
                      : task.sync_conflict
                      ? "bg-red-900 text-red-300"
                      : "bg-amber-900 text-amber-300"
                  }`}
                >
                  {task.synced ? "✓ Sync" : task.sync_conflict ? "Conflito" : "Pendente"}
                </span>
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
  onClick,
  highlight,
}: {
  task: { id: string; titulo?: string; type: string; data_programada?: string; prioridade: string; talhao_id?: string; lote_id?: string; operador_id?: string };
  onClick: () => void;
  highlight?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-2xl p-4 text-left flex items-start justify-between gap-3 border ${
        highlight
          ? "bg-blue-950/60 border-blue-800/50"
          : "bg-neutral-800 border-neutral-700"
      }`}
    >
      <div className="flex flex-col gap-1 flex-1 min-w-0">
        <p className="text-sm font-semibold truncate">
          {task.titulo ?? formatTaskType(task.type)}
        </p>
        {task.data_programada && (
          <p className="text-xs text-neutral-500">
            {new Date(task.data_programada + "T00:00:00").toLocaleDateString("pt-BR")}
          </p>
        )}
      </div>
      <span
        className={`shrink-0 text-xs rounded-full px-2 py-0.5 border ${
          PRIORIDADE_COLOR[task.prioridade] ?? PRIORIDADE_COLOR.NORMAL
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
    PESAGEM_ANIMAL: "Pesagem de Animal",
    VACINACAO_LOTE: "Vacinação de Lote",
    PARTO_REGISTRO: "Registro de Parto",
    MONITORAMENTO_PRAGA: "Monitoramento de Praga",
  };
  return map[type] ?? type;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
