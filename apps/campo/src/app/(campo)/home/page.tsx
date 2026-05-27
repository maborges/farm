"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { CampoButton, CampoMetric, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

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
  URGENTE: "border-rose-400/20 bg-rose-400/12 text-rose-100",
  ALTA: "border-amber-400/20 bg-amber-400/12 text-amber-100",
  NORMAL: "border-white/10 bg-white/[0.05] text-white/75",
  BAIXA: "border-white/10 bg-white/[0.03] text-white/45",
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

  const scrollToNovaAtividade = () => {
    document.getElementById("nova-atividade")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="flex flex-col gap-5 pb-32">
      <CampoSurface className="p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <CampoPill className="border-emerald-400/20 bg-emerald-400/12 text-emerald-100">
              Modo campo
            </CampoPill>
            <div className="mt-3">
              <p className="text-xs text-white/45">Olá,</p>
              <h1 className="text-2xl font-semibold tracking-tight">{session?.user_name}</h1>
              <p className="mt-1 text-sm text-white/50">Tudo pronto para registrar o dia no campo.</p>
            </div>
          </div>
          <CampoButton variant="secondary" size="sm" onClick={() => router.push("/sync")}>
            <span className={`size-2 rounded-full ${isOnline ? "bg-emerald-400" : "bg-white/35"}`} />
            {isOnline ? "Online" : "Offline"}
            {pendingCount > 0 && <span className="ml-1 rounded-full bg-amber-400/20 px-2 py-0.5 text-[11px] text-amber-100">{pendingCount}</span>}
          </CampoButton>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <CampoMetric label="Em execução" value={emExecucaoCount} tone="sky" />
          <CampoMetric label="Hoje" value={hojeCount} tone="emerald" />
          <CampoMetric label="Atrasadas" value={atrasadasCount} tone="rose" />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <CampoPill className="border-white/10 bg-white/[0.06] text-white/68">
            {availableActivities.length} atalhos ativos
          </CampoPill>
          <CampoPill className={isOnline ? "border-emerald-400/20 bg-emerald-400/12 text-emerald-100" : "border-white/10 bg-white/[0.06] text-white/68"}>
            {isOnline ? "Conectado" : "Sem conexão"}
          </CampoPill>
          {pendingCount > 0 && (
            <CampoPill className="border-amber-400/20 bg-amber-400/12 text-amber-100">
              {pendingCount} itens aguardando sync
            </CampoPill>
          )}
        </div>
      </CampoSurface>

      {/* Em execução — destaque máximo */}
      {emExecucaoCount > 0 && (
        <section className="flex flex-col gap-2">
          <CampoSectionTitle
            eyebrow="Prioridade"
            title="Em execução"
            description="Tarefas que estão sendo conduzidas neste momento."
            action={<CampoPill className="border-sky-400/20 bg-sky-400/12 text-sky-100">{emExecucaoCount}</CampoPill>}
          />
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
          <CampoSectionTitle
            eyebrow="Atenção"
            title="Atrasadas"
            description="Pendências que já passaram da data programada."
            action={<CampoPill className="border-rose-400/20 bg-rose-400/12 text-rose-100">{atrasadasCount}</CampoPill>}
          />
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
          <CampoSectionTitle
            eyebrow="Agenda"
            title="Para hoje"
            description="Tarefas programadas para executar ainda hoje."
            action={<CampoPill className="border-emerald-400/20 bg-emerald-400/12 text-emerald-100">{hojeCount}</CampoPill>}
          />
          <div className="flex flex-col gap-2">
            {tarefasHoje?.map((t) => (
              <TarefaCard key={t.id} task={t} onClick={() => router.push(`/campo/tarefa/${t.id}`)} />
            ))}
          </div>
        </section>
      )}

      {/* Sem tarefas programadas */}
      {hojeCount === 0 && atrasadasCount === 0 && emExecucaoCount === 0 && (
        <CampoSurface className="p-5 text-center text-sm text-white/55">
          <div className="mx-auto flex size-14 items-center justify-center rounded-[22px] bg-white/[0.06] text-2xl">
            🌤️
          </div>
          <p className="mt-4 text-base font-medium text-white/85">Nenhuma tarefa programada para hoje.</p>
          <p className="mt-1 text-xs leading-5 text-white/50">
            Você pode iniciar uma nova atividade manual ou revisar a sincronização do dispositivo.
          </p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <CampoButton variant="secondary" className="flex-1" onClick={() => router.push("/sync")}>
              Ver sync
            </CampoButton>
            <CampoButton variant="primary" className="flex-1" onClick={scrollToNovaAtividade}>
              Nova atividade
            </CampoButton>
          </div>
        </CampoSurface>
      )}

      {/* Nova Atividade Manual */}
      <section id="nova-atividade" className="flex scroll-mt-28 flex-col gap-3">
        <CampoSectionTitle
          eyebrow="Entrada rápida"
          title="Nova atividade"
          description="Abra um registro manual com acesso rápido."
        />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {availableActivities.map((act) => (
            <button
              key={act.key}
              onClick={() => router.push(act.path)}
              className="group rounded-[24px] border border-white/10 bg-white/[0.04] p-5 text-left shadow-[0_12px_30px_rgba(0,0,0,0.12)] transition-all hover:border-emerald-400/25 hover:bg-white/[0.07] active:scale-[0.98]"
            >
              <span className="text-3xl transition-transform group-hover:scale-105">{act.icon}</span>
              <span className="mt-2 block text-sm font-semibold">{act.label}</span>
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
                className="rounded-[24px] border border-white/10 bg-white/[0.04] px-4 py-3.5 shadow-[0_16px_40px_rgba(0,0,0,0.16)]"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-white">{formatTaskType(task.type)}</p>
                    <p className="text-xs text-white/40">{formatDate(task.created_at)}</p>
                  </div>
                  <span
                    className={`text-xs rounded-full px-2.5 py-1 font-medium ${
                    task.synced
                      ? "bg-emerald-400/12 text-emerald-100"
                      : task.sync_conflict
                      ? "bg-rose-400/12 text-rose-100"
                      : "bg-amber-400/12 text-amber-100"
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
      className={`w-full rounded-[24px] border p-4 text-left flex items-start justify-between gap-3 shadow-[0_16px_40px_rgba(0,0,0,0.16)] transition-transform active:scale-[0.99] ${
        highlight
          ? "border-sky-400/20 bg-sky-400/12"
          : "border-white/10 bg-white/[0.04]"
      }`}
    >
      <div className="flex flex-col gap-1 flex-1 min-w-0">
        <p className="truncate text-sm font-semibold text-white">
          {task.titulo ?? formatTaskType(task.type)}
        </p>
        {task.data_programada && (
          <p className="text-xs text-white/40">
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
