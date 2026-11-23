"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import {
  ArrowRight,
  Beef,
  BookText,
  ClipboardList,
  CloudSun,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Sprout,
  WifiOff,
} from "lucide-react";
import { PwaAlertStrip } from "@/components/campo/pwa-alert-strip";
import { PwaModuleCard } from "@/components/campo/pwa-module-card";
import { PwaProgressRing } from "@/components/campo/pwa-progress-ring";
import { PwaQuickAction } from "@/components/campo/pwa-quick-action";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
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
      className="flex flex-col gap-4 sm:gap-6"
    >
      {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}

      {/* Cabeçalho Compacto de App Mobile / Hero Adaptativo no Desktop */}
      <section className="rounded-xl md:rounded-sm border border-border bg-card p-3.5 sm:p-5 shadow-xs relative overflow-hidden">
        <div className="max-w-2xl flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <span className="inline-flex items-center rounded-md md:rounded-sm border px-2 py-0.5 text-[11px] md:text-[10px] font-semibold border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400">
              {shortDate} • Turno Ativo
            </span>
            {activeFazendaNome && (
              <span className="text-xs md:text-[11px] text-muted-foreground flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" /> {activeFazendaNome}
              </span>
            )}
            <span className="text-[11px] text-muted-foreground hidden sm:inline-flex items-center gap-1">
              • <WifiOff className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> Modo Offline Ativo
            </span>
          </div>
          <h1 className="text-base sm:text-xl md:text-2xl font-bold tracking-tight text-foreground leading-snug">
            {greeting}, {firstName} — Operação de Campo
          </h1>
          <p className="hidden sm:block text-xs text-muted-foreground leading-relaxed">
            Execute tarefas programadas, registre apontamentos no caderno oficial com fotos e GPS e acompanhe recomendações técnicas da propriedade.
          </p>
        </div>
      </section>

      {/* Alertas Operacionais */}
      {alertItems.length > 0 && (
        <PwaAlertStrip items={alertItems} onTap={() => router.push("/tarefas")} />
      )}

      {/* Atalhos Rápidos e Módulos Contratados (mesmo padrão visual de App Launcher + Cards do Agro) */}
      <section id="nova-atividade" className="flex flex-col gap-2.5" aria-label="Acesso rápido às ferramentas">
        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Acesso Rápido às Operações
          </h2>
          <span className="text-[10px] text-muted-foreground sm:hidden">
            Toque para abrir
          </span>
        </div>

        {/* Grade de Ícones Rápidos para Toque (App Tiles) */}
        <div className="grid grid-cols-4 gap-2" data-testid="mobile-launcher-tiles">
          <PwaQuickAction
            label="Tarefas"
            icon={ClipboardList}
            color="blue"
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
            color="pecuaria"
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

        {/* Cards Detalhados dos Módulos Contratados */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {hasAgricola && (
            <PwaModuleCard
              label="Módulo Agrícola"
              sublabel="Caderno de campo, aplicações de insumos, registro de colheita e entrega de EPI."
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
              label="Módulo Pecuária"
              sublabel="Pesagem de animais e lotes, vacinação sanitária, cobertura, diagnóstico e parto."
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

      {/* Progresso do dia */}
      <PwaProgressRing done={doneCount} total={totalTarefas} />

      {/* Rodapé de status de sincronização (Tablet/Desktop; no mobile fica no Header e Dock) */}
      <section className="hidden sm:flex p-3.5 sm:p-4 rounded-sm border border-border/80 bg-muted/40 flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex flex-col gap-1 max-w-xl">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <RefreshCw className="w-4 h-4 text-primary" />
            <span>
              {pendingCount > 0
                ? `${formatInt(pendingCount)} apontamento${pendingCount !== 1 ? "s" : ""} aguardando envio ao servidor`
                : "Fila offline sincronizada e pronta para operação sem rede"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Todos os registros feitos no <strong className="text-foreground font-semibold">DeepFarms Campo</strong> ficam protegidos no dispositivo até a confirmação do servidor.
          </p>
        </div>
        <button
          type="button"
          onClick={() => router.push("/sync")}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-sm bg-background hover:bg-accent text-foreground transition-colors shrink-0"
        >
          <span>Abrir Sincronização</span>
          <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      </section>
    </div>
  );
}
