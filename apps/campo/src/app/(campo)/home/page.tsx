"use client";

import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Sprout, Beef, CloudSun } from "lucide-react";
import { db } from "@/lib/db";
import { consumeSessionClearNotice, useSessionStore, type SessionClearNotice } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
import { PwaModuleCard } from "@/components/campo/pwa-module-card";
import { PwaAlertStrip } from "@/components/campo/pwa-alert-strip";
import { PwaProgressRing } from "@/components/campo/pwa-progress-ring";
import { resolveTaskDomain } from "@/lib/task-domain";
import { CampoButton } from "@/components/campo/ui";
import { formatInt } from "@/lib/format";

function resolveGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

function formatShortDate(): string {
  return new Date().toLocaleDateString("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

export default function HomePage() {
  const router = useRouter();
  const { session } = useSessionStore();
  const { pendingCount } = useSyncStore();
  const [clearNotice, setClearNotice] = useState<SessionClearNotice | null>(null);

  useEffect(() => {
    setClearNotice(consumeSessionClearNotice());
  }, []);

  const hoje = new Date().toISOString().slice(0, 10);
  const greeting = resolveGreeting();
  const shortDate = formatShortDate();
  const firstName = (session?.user_name ?? "").split(" ")[0] ?? "Operador";

  const fazendas = useLiveQuery(async () => {
    const ids = session?.fazenda_ids ?? [];
    if (ids.length === 0) return [];
    const rows = await db.fazendas.bulkGet(ids);
    return rows.filter(Boolean);
  }, [session?.fazenda_ids?.join("|")]);

  const activeFazendaNome = useMemo(
    () => (fazendas ?? []).find((f) => f?.id === session?.active_fazenda_id)?.nome,
    [fazendas, session?.active_fazenda_id]
  );

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

  const tarefasConcluidas = useLiveQuery(
    () =>
      db.tasks
        .where("status_execucao")
        .equals("CONCLUIDA")
        .filter((t) => {
          if (!t.concluida_em) return false;
          return t.concluida_em.slice(0, 10) === hoje;
        })
        .toArray(),
    []
  );

  const hasAgricola = session?.modules?.includes("agricola") ?? false;
  const hasPecuaria = session?.modules?.includes("pecuaria") ?? false;

  const pendingByDomain = useMemo(() => {
    const counts = { AGRICULTURA: 0, PECUARIA: 0 };
    for (const task of tarefasPendentes ?? []) {
      counts[resolveTaskDomain(task)] += 1;
    }
    return counts;
  }, [tarefasPendentes]);

  const urgentByDomain = useMemo(() => {
    const counts = { AGRICULTURA: 0, PECUARIA: 0 };
    for (const task of tarefasPendentes ?? []) {
      if (task.prioridade === "URGENTE") {
        counts[resolveTaskDomain(task)] += 1;
      }
    }
    return counts;
  }, [tarefasPendentes]);

  const atrasadas = useMemo(
    () =>
      (tarefasPendentes ?? []).filter(
        (t) => !!t.data_programada && t.data_programada < hoje
      ),
    [tarefasPendentes, hoje]
  );

  const urgentRecomendacoes = useMemo(
    () => (recomendacoesOperacionais ?? []).filter((r) => r.priority === "URGENT" && ["CREATED", "VIEWED", "REOPENED"].includes(r.status)),
    [recomendacoesOperacionais]
  );

  const totalTarefas =
    (tarefasPendentes?.length ?? 0) + (tarefasConcluidas?.length ?? 0);
  const doneCount = tarefasConcluidas?.length ?? 0;

  // Alertas para exibição
  const alertItems = useMemo(() => {
    const items: { id: string; label: string; severity: "urgent" | "warning" | "info" }[] = [];
    if (atrasadas.length > 0) {
      items.push({
        id: "atrasadas",
        label: `${formatInt(atrasadas.length)} tarefa${atrasadas.length !== 1 ? "s" : ""} atrasada${atrasadas.length !== 1 ? "s" : ""}`,
        severity: "warning",
      });
    }
    if (urgentRecomendacoes.length > 0) {
      items.push({
        id: "recomendacoes-urgentes",
        label: `${formatInt(urgentRecomendacoes.length)} recomendaç${urgentRecomendacoes.length !== 1 ? "ões" : "ão"} urgente${urgentRecomendacoes.length !== 1 ? "s" : ""}`,
        severity: "urgent",
      });
    }
    if (pendingCount > 0) {
      items.push({
        id: "sync-pending",
        label: `${formatInt(pendingCount)} registro${pendingCount !== 1 ? "s" : ""} aguardando sincronização`,
        severity: "info",
      });
    }
    return items;
  }, [atrasadas.length, urgentRecomendacoes.length, pendingCount]);

  return (
    <div className="flex flex-col gap-5 pb-32">
      {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}

      {/* ── Cabeçalho de boas-vindas ── */}
      <div
        className="campo-pwa-card-stagger rounded-2xl border border-border bg-card px-5 py-5 shadow-sm"
        style={{ "--campo-pwa-delay": "0ms" } as React.CSSProperties}
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {shortDate}
        </p>
        <h1 className="mt-1 text-xl font-bold tracking-tight text-foreground">
          {greeting}, {firstName}
        </h1>
        {activeFazendaNome && (
          <p className="mt-0.5 text-sm text-muted-foreground">
            Unidade ativa:{" "}
            <span className="font-semibold text-foreground">{activeFazendaNome}</span>
          </p>
        )}
        <p className="mt-1.5 text-xs text-muted-foreground">
          O que você vai fazer hoje?
        </p>
      </div>

      {/* ── Cards de módulo ── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {hasAgricola && (
          <PwaModuleCard
            label="Agricultura"
            sublabel="Caderno, aplicações, colheita e EPI"
            icon={Sprout}
            taskCount={pendingByDomain.AGRICULTURA}
            urgentCount={urgentByDomain.AGRICULTURA}
            color="agro"
            animDelay="60ms"
            onClick={() => router.push("/agricultura")}
          />
        )}
        {hasPecuaria && (
          <PwaModuleCard
            label="Pecuária"
            sublabel="Pesagem, vacinação e reprodução"
            icon={Beef}
            taskCount={pendingByDomain.PECUARIA}
            urgentCount={urgentByDomain.PECUARIA}
            color="pecuaria"
            animDelay="160ms"
            onClick={() => router.push("/pecuaria")}
          />
        )}
        {!hasAgricola && !hasPecuaria && (
          <div className="flex min-h-[120px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-muted/30 p-6 text-center">
            <CloudSun className="size-8 text-muted-foreground" strokeWidth={1.5} />
            <p className="mt-3 text-sm font-medium text-foreground">Nenhum módulo ativo</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Entre em contato com o administrador para liberar acesso.
            </p>
          </div>
        )}
      </div>

      {/* ── Alertas ── */}
      {alertItems.length > 0 && (
        <PwaAlertStrip
          items={alertItems}
          onTap={() => router.push("/tarefas")}
        />
      )}

      {/* ── Progresso do dia ── */}
      <PwaProgressRing done={doneCount} total={totalTarefas} />

      {/* ── Acesso rápido ao sync quando há pendentes ── */}
      {pendingCount > 0 && (
        <div
          className="campo-pwa-card-stagger"
          style={{ "--campo-pwa-delay": "300ms" } as React.CSSProperties}
        >
          <CampoButton
            variant="secondary"
            className="w-full rounded-2xl py-3"
            onClick={() => router.push("/sync")}
          >
            Sincronizar {formatInt(pendingCount)} item{pendingCount !== 1 ? "s" : ""} pendente{pendingCount !== 1 ? "s" : ""}
          </CampoButton>
        </div>
      )}
    </div>
  );
}
