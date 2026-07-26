"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ClipboardList } from "lucide-react";
import { db } from "@/lib/db";
import { CampoSectionTitle, CampoSurface, CampoButton } from "@/components/campo/ui";
import { TaskDomainBadge } from "@/components/campo/task-domain-badge";
import { resolveTaskDomain, type TaskDomain, formatTaskDomainLabel } from "@/lib/task-domain";
import { formatInt, formatDate } from "@/lib/format";

type DomainFilter = "ALL" | TaskDomain;

export default function TarefasPage() {
  const router = useRouter();
  const [domainFilter, setDomainFilter] = useState<DomainFilter>("ALL");
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
    () => db.tasks.where("status_execucao").equals("EM_EXECUCAO").toArray(),
    []
  );

  const filteredPendentes = useMemo(() => {
    const all = tarefasPendentes ?? [];
    return domainFilter === "ALL"
      ? all
      : all.filter((t) => resolveTaskDomain(t) === domainFilter);
  }, [tarefasPendentes, domainFilter]);

  const filteredEmExecucao = useMemo(() => {
    const all = tarefasEmExecucao ?? [];
    return domainFilter === "ALL"
      ? all
      : all.filter((t) => resolveTaskDomain(t) === domainFilter);
  }, [tarefasEmExecucao, domainFilter]);

  const atrasadas = filteredPendentes.filter(
    (t) => !!t.data_programada && t.data_programada < hoje
  );
  const hoje_ = filteredPendentes.filter((t) => t.data_programada === hoje);
  const futuras = filteredPendentes.filter(
    (t) => !t.data_programada || t.data_programada > hoje
  );

  const total = (tarefasPendentes?.length ?? 0) + (tarefasEmExecucao?.length ?? 0);

  return (
    <div className="flex flex-col gap-4 pb-32">
      {/* Header */}
      <div className="campo-pwa-card-stagger rounded-2xl border border-border bg-card px-5 py-4 shadow-sm"
           style={{ "--campo-pwa-delay": "0ms" } as React.CSSProperties}>
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <ClipboardList className="size-5" strokeWidth={2} />
          </span>
          <div>
            <h1 className="text-base font-bold tracking-tight text-foreground">Tarefas</h1>
            <p className="text-xs text-muted-foreground">{formatInt(total)} tarefa{total !== 1 ? "s" : ""} no total</p>
          </div>
        </div>

        {/* Filtros */}
        <div className="mt-3.5 flex gap-2">
          {(["ALL", "AGRICULTURA", "PECUARIA"] as DomainFilter[]).map((f) => {
            const active = domainFilter === f;
            const label = f === "ALL" ? "Todas" : f === "AGRICULTURA" ? "Agricultura" : "Pecuária";
            return (
              <CampoButton
                key={f}
                type="button"
                variant={active ? "primary" : "secondary"}
                size="sm"
                onClick={() => setDomainFilter(f)}
                className="rounded-xl"
              >
                {label}
              </CampoButton>
            );
          })}
        </div>
      </div>

      {/* Em execução */}
      {filteredEmExecucao.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Agora"
            title="Em execução"
            action={
              <span className="rounded-full bg-sky-100 px-2.5 py-0.5 text-[11px] font-semibold text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
                {formatInt(filteredEmExecucao.length)}
              </span>
            }
          />
          <div className="mt-3 flex flex-col gap-2">
            {filteredEmExecucao.map((task) => (
              <TarefaRow
                key={task.id}
                domain={resolveTaskDomain(task)}
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

      {/* Atrasadas */}
      {atrasadas.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Atenção"
            title="Atrasadas"
            action={
              <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
                {formatInt(atrasadas.length)}
              </span>
            }
          />
          <div className="mt-3 flex flex-col gap-2">
            {atrasadas.map((task) => (
              <TarefaRow
                key={task.id}
                domain={resolveTaskDomain(task)}
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

      {/* Hoje */}
      {hoje_.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Hoje"
            title="Programadas para hoje"
            action={
              <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                {formatInt(hoje_.length)}
              </span>
            }
          />
          <div className="mt-3 flex flex-col gap-2">
            {hoje_.map((task) => (
              <TarefaRow
                key={task.id}
                domain={resolveTaskDomain(task)}
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

      {/* Futuras */}
      {futuras.length > 0 && (
        <section>
          <CampoSectionTitle
            eyebrow="Próximas"
            title="Tarefas futuras"
            action={
              <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                {formatInt(futuras.length)}
              </span>
            }
          />
          <div className="mt-3 flex flex-col gap-2">
            {futuras.map((task) => (
              <TarefaRow
                key={task.id}
                domain={resolveTaskDomain(task)}
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

      {/* Nenhuma */}
      {filteredPendentes.length === 0 && filteredEmExecucao.length === 0 && (
        <CampoSurface className="py-10 text-center">
          <ClipboardList className="mx-auto size-8 text-muted-foreground" strokeWidth={1.5} />
          <p className="mt-3 text-sm font-medium text-foreground">Nenhuma tarefa encontrada</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {domainFilter !== "ALL"
              ? `Sem tarefas de ${formatTaskDomainLabel(domainFilter)} — tente "Todas"`
              : "Você está em dia. Bom trabalho!"}
          </p>
        </CampoSurface>
      )}
    </div>
  );
}

function TarefaRow({
  domain,
  title,
  status,
  prioridade,
  dataProgramada,
  hoje,
  onClick,
}: {
  domain: TaskDomain;
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
        "flex w-full items-start justify-between rounded-2xl border p-3.5 text-left shadow-sm",
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
          <TaskDomainBadge domain={domain} />
          {isEmExecucao && (
            <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
              Em execução
            </span>
          )}
          {isAtrasada && !isEmExecucao && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
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
          "ml-2 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold",
          prioridade === "URGENTE"
            ? "bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200"
            : prioridade === "ALTA"
            ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
            : "bg-muted text-muted-foreground",
        ].join(" ")}
      >
        {prioridade === "URGENTE" ? "Urgente" : prioridade === "ALTA" ? "Alta" : prioridade === "NORMAL" ? "Normal" : "Baixa"}
      </span>
    </button>
  );
}
