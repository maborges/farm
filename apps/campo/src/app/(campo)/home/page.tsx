"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";

export default function HomePage() {
  const router = useRouter();
  const { session, logout } = useSessionStore();
  const { pendingCount, isOnline } = useSyncStore();

  const pendingTasks = useLiveQuery(
    () => db.tasks.where("status").anyOf(["PENDENTE", "EM_ANDAMENTO"]).toArray(),
    []
  );

  const modules: { label: string; key: string; icon: string; path: string }[] = [
    ...(session?.modules.includes("agricola")
      ? [
          { label: "Aplicação", key: "aplicacao", icon: "🌿", path: "/agricola/aplicacao" },
          { label: "Colheita", key: "colheita", icon: "🌾", path: "/agricola/colheita" },
          { label: "Monitoramento", key: "monitoramento", icon: "🔍", path: "/agricola/monitoramento" },
        ]
      : []),
    ...(session?.modules.includes("pecuaria")
      ? [
          { label: "Pesagem", key: "pesagem", icon: "⚖️", path: "/pecuaria/pesagem" },
          { label: "Vacinação", key: "vacinacao", icon: "💉", path: "/pecuaria/vacinacao" },
          { label: "Parto", key: "parto", icon: "🐄", path: "/pecuaria/parto" },
        ]
      : []),
  ];

  return (
    <div className="flex flex-col gap-6 p-4 pb-8">
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
            <span className="bg-amber-500 text-black rounded-full px-1.5 text-xs font-bold">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {/* Tarefas pendentes */}
      {pendingTasks && pendingTasks.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
            Registros Pendentes
          </h2>
          <div className="flex flex-col gap-2">
            {pendingTasks.slice(0, 5).map((task) => (
              <div
                key={task.id}
                className="bg-neutral-800 rounded-2xl p-4 flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium">{formatTaskType(task.type)}</p>
                  <p className="text-xs text-neutral-500">{formatDate(task.created_at)}</p>
                </div>
                <span
                  className={`text-xs rounded-full px-2 py-0.5 font-medium ${
                    task.synced
                      ? "bg-green-900 text-green-300"
                      : "bg-amber-900 text-amber-300"
                  }`}
                >
                  {task.synced ? "Sincronizado" : "Pendente"}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Módulos disponíveis */}
      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
          Novo Registro
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {modules.map((mod) => (
            <button
              key={mod.key}
              onClick={() => router.push(mod.path)}
              className="bg-neutral-800 hover:bg-neutral-700 active:scale-95 transition-all rounded-2xl p-5 flex flex-col gap-2 text-left"
            >
              <span className="text-3xl">{mod.icon}</span>
              <span className="text-sm font-semibold">{mod.label}</span>
            </button>
          ))}
        </div>
      </section>
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
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
