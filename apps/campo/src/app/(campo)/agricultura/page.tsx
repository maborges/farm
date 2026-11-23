"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { BookText, ChevronDown, ChevronUp, ShieldHalf, Sprout, Wheat } from "lucide-react";
import { PwaModuleNav } from "@/components/campo/pwa-module-nav";
import { PwaQuickAction } from "@/components/campo/pwa-quick-action";
import { TaskDomainBadge } from "@/components/campo/task-domain-badge";
import { CampoSectionTitle, CampoSurface } from "@/components/campo/ui";
import { db } from "@/lib/db";
import { formatDate, formatInt } from "@/lib/format";

const QUICK_ACTIONS = [
  { key: "caderno", label: "Caderno", icon: BookText, path: "/caderno" },
  { key: "aplicacao", label: "Aplicação", icon: Sprout, path: "/campo/aplicacao" },
  { key: "colheita", label: "Colheita", icon: Wheat, path: "/campo/colheita" },
  { key: "epi", label: "Entrega EPI", icon: ShieldHalf, path: "/campo/epi" },
] as const;

export default function AgriculturaPage() {
  const router = useRouter();
  const [recsOpen, setRecsOpen] = useState(false);
  const hoje = new Date().toISOString().slice(0, 10);

  const tarefasPendentes = useLiveQuery(
    () =>
      db.tasks
        .where("origem")
        .equals("PROGRAMADA")
        .filter((t) => t.status_execucao === "PENDENTE" || t.status_execucao === "EM_EXECUCAO")
        .toArray(),
    []
  );

  const tarefasAgricolas = useMemo(() => {
    const agricolaTipos = new Set([
      "APLICACAO_DEFENSIVO",
      "APLICACAO_FERTILIZANTE",
      "COLHEITA_REGISTRO",
      "PREPARO_SOLO",
      "PLANTIO_REGISTRO",
      "IRRIGACAO_EVENTO",
      "MONITORAMENTO_PRAGA",
      "AMOSTRAGEM_SOLO",
      "CHECKLIST_CAMPO",
    ]);
    return (tarefasPendentes ?? [])
      .filter((t) => agricolaTipos.has(t.type))
      .sort((a, b) => {
        const rank: Record<string, number> = { EM_EXECUCAO: 0, PENDENTE: 1 };
        const d = (rank[a.status_execucao] ?? 2) - (rank[b.status_execucao] ?? 2);
        if (d !== 0) return d;
        const p: Record<string, number> = { URGENTE: 0, ALTA: 1, NORMAL: 2, BAIXA: 3 };
        return (p[a.prioridade] ?? 9) - (p[b.prioridade] ?? 9);
      });
  }, [tarefasPendentes]);

  const recomendacoes = useLiveQuery(
    () =>
      db.recomendacoes_operacionais
        .filter(
          (r) =>
            ["AGRICULTURE", "FIELD"].includes(r.domain) &&
            ["CREATED", "VIEWED", "REOPENED"].includes(r.status)
        )
        .toArray(),
    []
  );

  const atrasadas = tarefasAgricolas.filter(
    (t) => !!t.data_programada && t.data_programada < hoje
  );
  const hoje_ = tarefasAgricolas.filter((t) => t.data_programada === hoje);
  const emExecucao = tarefasAgricolas.filter((t) => t.status_execucao === "EM_EXECUCAO");

  return (
    <div className="flex flex-col gap-4 pb-8">
      <PwaModuleNav title="Agricultura" color="agro" />

      {/* ── Ações rápidas ── */}
      <section>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          Ações rápidas
        </p>
        <div className="grid grid-cols-4 gap-2">
          {QUICK_ACTIONS.map((act) => (
            <PwaQuickAction
              key={act.key}
              label={act.label}
              icon={act.icon}
              color="agro"
              onClick={() => router.push(act.path)}
            />
          ))}
        </div>
      </section>

      {/* ── Em execução ── */}
      {emExecucao.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Agora"
            title="Em execução"
            description="Tarefas iniciadas neste dispositivo."
            action={
              <span className="rounded-sm bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
                {formatInt(emExecucao.length)}
              </span>
            }
          />
          <div className="mt-2.5 grid grid-cols-1 gap-2 @[580px]/main:grid-cols-2">
            {emExecucao.map((task) => (
              <AgricolaTaskCard
                key={task.id}
                title={task.titulo ?? task.type}
                status="EM_EXECUCAO"
                prioridade={task.prioridade}
                dataProgramada={task.data_programada}
                hoje={hoje}
                onClick={() => router.push(`/campo/tarefa/${task.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Tarefas de hoje ── */}
      {hoje_.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Hoje"
            title="Programadas para hoje"
            action={
              <span className="rounded-sm bg-[var(--campo-pwa-agro-light)] px-2 py-0.5 text-[11px] font-semibold text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]">
                {formatInt(hoje_.length)}
              </span>
            }
          />
          <div className="mt-2.5 grid grid-cols-1 gap-2 @[580px]/main:grid-cols-2">
            {hoje_.map((task) => (
              <AgricolaTaskCard
                key={task.id}
                title={task.titulo ?? task.type}
                status={task.status_execucao}
                prioridade={task.prioridade}
                dataProgramada={task.data_programada}
                hoje={hoje}
                onClick={() => router.push(`/campo/tarefa/${task.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Atrasadas ── */}
      {atrasadas.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Atenção"
            title="Atrasadas"
            action={
              <span className="rounded-sm bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                {formatInt(atrasadas.length)}
              </span>
            }
          />
          <div className="mt-2.5 grid grid-cols-1 gap-2 @[580px]/main:grid-cols-2">
            {atrasadas.map((task) => (
              <AgricolaTaskCard
                key={task.id}
                title={task.titulo ?? task.type}
                status={task.status_execucao}
                prioridade={task.prioridade}
                dataProgramada={task.data_programada}
                hoje={hoje}
                onClick={() => router.push(`/campo/tarefa/${task.id}`)}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Nenhuma tarefa ── */}
      {tarefasAgricolas.length === 0 && (
        <CampoSurface className="py-8 text-center">
          <p className="text-sm font-medium text-foreground">
            Nenhuma tarefa agrícola pendente
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Use as ações rápidas acima para fazer um registro manual.
          </p>
        </CampoSurface>
      )}

      {/* ── Recomendações (colapsável) ── */}
      {(recomendacoes?.length ?? 0) > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setRecsOpen((v) => !v)}
            className="flex w-full items-center justify-between rounded-sm border border-border bg-card px-4 py-3 shadow-2xs transition-all active:scale-[0.99]"
          >
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Inteligência
              </p>
              <p className="mt-0.5 text-sm font-semibold text-foreground">
                Recomendações ({recomendacoes?.length ?? 0})
              </p>
            </div>
            {recsOpen ? (
              <ChevronUp className="size-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="size-4 text-muted-foreground" />
            )}
          </button>

          {recsOpen && (
            <div className="mt-2 grid grid-cols-1 gap-2 @[580px]/main:grid-cols-2">
              {(recomendacoes ?? []).slice(0, 6).map((rec) => (
                <button
                  key={rec.id}
                  type="button"
                  onClick={() => router.push("/recomendacoes")}
                  className="flex w-full flex-col rounded-sm border border-border bg-card p-3.5 text-left shadow-2xs transition-all active:scale-[0.99]"
                >
                  <p className="text-sm font-semibold text-foreground">{rec.title}</p>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                    {rec.summary}
                  </p>
                </button>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function AgricolaTaskCard({
  title,
  status,
  prioridade,
  dataProgramada,
  hoje,
  onClick,
}: {
  title: string;
  status: string;
  prioridade: string;
  dataProgramada?: string | null;
  hoje: string;
  onClick: () => void;
}) {
  const isAtrasada = !!dataProgramada && dataProgramada < hoje;
  const isEmExecucao = status === "EM_EXECUCAO";

  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full items-start justify-between rounded-sm border p-3.5 text-left shadow-2xs",
        "transition-all duration-150 active:scale-[0.99]",
        isEmExecucao
          ? "border-sky-200 bg-sky-50 dark:border-sky-900/60 dark:bg-sky-950/30"
          : isAtrasada
            ? "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/30"
            : "border-border bg-card",
      ].join(" ")}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <TaskDomainBadge domain="AGRICULTURA" />
          {isEmExecucao && (
            <span className="rounded-sm bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
              Em execução
            </span>
          )}
          {isAtrasada && !isEmExecucao && (
            <span className="rounded-sm bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
              Atrasada
            </span>
          )}
        </div>
        <p className="mt-1.5 truncate text-sm font-semibold text-foreground">{title}</p>
        {dataProgramada && (
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            {formatDate(dataProgramada)}
          </p>
        )}
      </div>
      <span
        className={[
          "ml-2 shrink-0 rounded-sm px-2 py-0.5 text-[10px] font-semibold",
          prioridade === "URGENTE"
            ? "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200"
            : prioridade === "ALTA"
              ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
              : "bg-muted text-muted-foreground",
        ].join(" ")}
      >
        {prioridade === "URGENTE"
          ? "Urgente"
          : prioridade === "ALTA"
            ? "Alta"
            : prioridade === "NORMAL"
              ? "Normal"
              : "Baixa"}
      </span>
    </button>
  );
}
