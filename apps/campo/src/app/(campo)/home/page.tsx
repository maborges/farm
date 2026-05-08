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

export default function HomePage() {
  const router = useRouter();
  const { session, logout } = useSessionStore();
  const { pendingCount, isOnline } = useSyncStore();

  const recentTasks = useLiveQuery(
    () => db.tasks.orderBy("created_at").reverse().limit(5).toArray(),
    []
  );

  const pendingTasks = useLiveQuery(
    () => db.tasks.where("synced").equals(0).count(),
    []
  );

  const availableActivities = ACTIVITIES.filter(
    (a) => session?.modules?.includes(a.module)
  );

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

      {/* Destaque: não sincronizados */}
      {(pendingTasks ?? 0) > 0 && (
        <button
          onClick={() => router.push("/sync")}
          className="bg-amber-950 border border-amber-800/60 rounded-2xl p-4 text-left flex items-center justify-between"
        >
          <div>
            <p className="text-sm font-semibold text-amber-300">
              {pendingTasks} registro{pendingTasks! > 1 ? "s" : ""} aguardando sync
            </p>
            <p className="text-xs text-amber-500 mt-0.5">Toque para ver detalhes</p>
          </div>
          <span className="text-amber-400 text-lg">→</span>
        </button>
      )}

      {/* Atividades disponíveis */}
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

      {/* Registros recentes */}
      {recentTasks && recentTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
            Últimos Registros
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
