"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import {
  Beef,
  BookText,
  ClipboardList,
  CloudSun,
  RefreshCw,
  Sparkles,
  Sprout,
} from "lucide-react";
import { PwaAlertStrip } from "@/components/campo/pwa-alert-strip";
import { PwaModuleCard } from "@/components/campo/pwa-module-card";
import { PwaProgressRing } from "@/components/campo/pwa-progress-ring";
import { PwaQuickAction } from "@/components/campo/pwa-quick-action";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
import { CampoButton } from "@/components/campo/ui";
import { db } from "@/lib/db";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { formatInt } from "@/lib/format";
import {
  consumeSessionClearNotice,
  useSessionStore,
  type SessionClearNotice,
} from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";
import { resolveTaskDomain } from "@/lib/task-domain";

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
  const { layoutProfile } = useDeviceContext();
  const [clearNotice, setClearNotice] = useState<SessionClearNotice | null>(null);

  useEffect(() => {
    setClearNotice(consumeSessionClearNotice());
  }, []);

  const hoje = new Date().toISOString().slice(0, 10);
  const greeting = resolveGreeting();
  const shortDate = formatShortDate();
  const firstName = (session?.user_name ?? "").split(" ")[0] || "Operador";

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

  const recomendacoesOperacionais = useLiveQuery(
    () => db.recomendacoes_operacionais.toArray(),
    []
  );

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
    () =>
      (recomendacoesOperacionais ?? []).filter(
        (r) =>
          r.priority === "URGENT" &&
          ["CREATED", "VIEWED", "REOPENED"].includes(r.status)
      ),
    [recomendacoesOperacionais]
  );

  const totalTarefas =
    (tarefasPendentes?.length ?? 0) + (tarefasConcluidas?.length ?? 0);
  const doneCount = tarefasConcluidas?.length ?? 0;

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
    <div
      data-device-category={layoutProfile.deviceCategory}
      className="flex flex-col gap-4 pb-8"
    >
      {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}

      {/* ── Cabeçalho Operacional Adaptativo ── */}
      <div
        className="campo-pwa-card-stagger rounded-sm border border-border bg-card/90 px-4 py-3.5 shadow-xs backdrop-blur-xs sm:px-5 sm:py-4"
        style={{ "--campo-pwa-delay": "0ms" } as CSSProperties}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary">
              {shortDate} • Turno de Campo
            </p>
            <h1 className="mt-0.5 text-lg sm:text-xl font-bold tracking-tight text-foreground">
              {greeting}, {firstName}
            </h1>
            {activeFazendaNome && (
              <p className="mt-0.5 text-xs text-muted-foreground">
                Unidade ativa:{" "}
                <span className="font-semibold text-foreground">{activeFazendaNome}</span>
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-sm border border-border bg-muted/60 px-2.5 py-1 text-[11px] font-semibold text-foreground">
              {formatInt(tarefasPendentes?.length ?? 0)} pendente
              {(tarefasPendentes?.length ?? 0) !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      {/* ── Alertas Operacionais ── */}
      {alertItems.length > 0 && (
        <PwaAlertStrip items={alertItems} onTap={() => router.push("/tarefas")} />
      )}

      {/* ── Lançador Rápido de Operação Diária (estilo App Nativo) ── */}
      <section id="nova-atividade">
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          Acesso Rápido
        </p>
        <div className="grid grid-cols-4 gap-2">
          <PwaQuickAction
            label="Tarefas"
            icon={ClipboardList}
            color="agro"
            badge={
              (tarefasPendentes?.length ?? 0) > 0
                ? String(tarefasPendentes?.length)
                : undefined
            }
            onClick={() => router.push("/tarefas")}
          />
          <PwaQuickAction
            label="Caderno"
            icon={BookText}
            color="agro"
            onClick={() => router.push("/caderno")}
          />
          <PwaQuickAction
            label="Alertas"
            icon={Sparkles}
            color="neutral"
            badge={
              urgentRecomendacoes.length > 0
                ? String(urgentRecomendacoes.length)
                : undefined
            }
            onClick={() => router.push("/recomendacoes")}
          />
          <PwaQuickAction
            label="Sync"
            icon={RefreshCw}
            color="neutral"
            badge={pendingCount > 0 ? String(pendingCount) : undefined}
            onClick={() => router.push("/sync")}
          />
        </div>
      </section>

      {/* ── Módulos Contratados ── */}
      <section>
        <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
          Módulos Contratados
        </p>
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
              animDelay="140ms"
              onClick={() => router.push("/pecuaria")}
            />
          )}
          {!hasAgricola && !hasPecuaria && (
            <div className="col-span-full flex min-h-[120px] flex-col items-center justify-center rounded-sm border border-dashed border-border bg-muted/30 p-6 text-center">
              <CloudSun className="size-8 text-muted-foreground" strokeWidth={1.5} />
              <p className="mt-3 text-sm font-medium text-foreground">
                Nenhum módulo ativo
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Entre em contato com o administrador para liberar acesso.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── Progresso do dia ── */}
      <PwaProgressRing done={doneCount} total={totalTarefas} />

      {/* ── Acesso rápido ao sync quando há pendentes ── */}
      {pendingCount > 0 && (
        <div
          className="campo-pwa-card-stagger"
          style={{ "--campo-pwa-delay": "240ms" } as CSSProperties}
        >
          <CampoButton
            variant="secondary"
            size="sm"
            className="w-full rounded-sm py-2.5"
            onClick={() => router.push("/sync")}
          >
            Sincronizar {formatInt(pendingCount)} item{pendingCount !== 1 ? "s" : ""} pendente
            {pendingCount !== 1 ? "s" : ""}
          </CampoButton>
        </div>
      )}
    </div>
  );
}
