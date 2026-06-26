"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { useGps } from "@/hooks/useGps";
import { useCamera } from "@/hooks/useCamera";
import { executarTarefa } from "@/lib/task-factory";
import { mapTaskTypeToCadernoTipo } from "@/lib/caderno-offline";
import { isPecuariaTaskType, formatPecuariaTaskType } from "@/lib/pecuaria-tasks";
import { TaskDomainBadge } from "@/components/campo/task-domain-badge";
import { GpsWarning } from "@/components/campo/gps-warning";
import { CameraCapture } from "@/components/campo/camera-capture";
import { PecuariaTaskExecution } from "@/components/campo/pecuaria-task-execution";
import { useSessionStore } from "@/lib/stores/session-store";
import { CampoShell, CampoSurface, CampoButton } from "@/components/campo/ui";
import { CampoPill } from "@/components/campo/ui";
import { resolveTaskDomain } from "@/lib/task-domain";

import { ArrowLeft, Play, Check } from "lucide-react";

const PRIORIDADE_LABEL: Record<string, string> = {
  URGENTE: "Urgente",
  ALTA: "Alta",
  NORMAL: "Normal",
  BAIXA: "Baixa",
};

const STATUS_LABEL: Record<string, string> = {
  PENDENTE: "Pendente",
  EM_EXECUCAO: "Em Execução",
  CONCLUIDA: "Concluída",
  CANCELADA: "Cancelada",
};

export default function TarefaDetailPage() {
  const router = useRouter();
  const { id } = useParams() as { id: string };
  const { session } = useSessionStore();
  const gps = useGps();
  const cam = useCamera();

  const [obs, setObs] = useState("");
  const [saving, setSaving] = useState(false);

  const task = useLiveQuery(() => db.tasks.get(id), [id]);

  const talhao = useLiveQuery(
    async () => task?.talhao_id ? db.talhoes.get(task.talhao_id) : undefined,
    [task?.talhao_id]
  );

  const safras = useLiveQuery(() => db.safras.toArray(), []);

  const lote = useLiveQuery(
    async () => task?.lote_id ? db.lotes.get(task.lote_id) : undefined,
    [task?.lote_id]
  );

  const fazenda = useLiveQuery(
    async () => task?.fazenda_id ? db.fazendas.get(task.fazenda_id) : undefined,
    [task?.fazenda_id]
  );

  const activeFazenda = useLiveQuery(
    async () => {
      const fazendaId = session?.active_fazenda_id ?? session?.fazenda_ids?.[0];
      if (!fazendaId) return undefined;
      return db.fazendas.get(fazendaId);
    },
    [session?.active_fazenda_id, session?.fazenda_ids?.join("|")]
  );

  if (!task) {
    return (
      <div className="flex items-center justify-center min-h-dvh">
        <p className="text-neutral-500 text-sm">Tarefa não encontrada</p>
      </div>
    );
  }

  const isMinhasTarefa =
    !task.operador_id || task.operador_id === session?.user_id;
  const cadernoTipo = mapTaskTypeToCadernoTipo(task.type);
  const pecuariaTask = isPecuariaTaskType(task.type);
  const taskDomain = resolveTaskDomain(task);
  const taskDados = task.dados ?? {};
  const safraId = typeof taskDados.safra_id === "string" ? taskDados.safra_id : undefined;
  const safra = safras?.find((item) => item.id === safraId);
  const animaisIds = Array.isArray(taskDados.animais_ids)
    ? taskDados.animais_ids.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
  const pecuariaQuantidade = animaisIds.length > 0
    ? animaisIds.length
    : typeof taskDados.quantidade_animais === "number"
      ? taskDados.quantidade_animais
      : undefined;
  const pecuariaAreaId = typeof taskDados.area_id === "string" ? taskDados.area_id : undefined;
  const cultura = typeof taskDados.cultura_nome === "string"
    ? taskDados.cultura_nome
    : typeof taskDados.cultura === "string"
      ? taskDados.cultura
      : undefined;

  const canStart = task.status_execucao === "PENDENTE" && isMinhasTarefa;
  const canFinish = task.status_execucao === "EM_EXECUCAO" && isMinhasTarefa;
  const isDone =
    task.status_execucao === "CONCLUIDA" || task.status_execucao === "CANCELADA";
  const hasContextMismatch =
    !!session?.active_fazenda_id &&
    !!task.fazenda_id &&
    task.fazenda_id !== session.active_fazenda_id;

  async function handleIniciar() {
    if (!canStart) return;
    setSaving(true);
    try {
      await executarTarefa(id, { status_execucao: "EM_EXECUCAO" });
    } finally {
      setSaving(false);
    }
  }

  async function handleConcluir() {
    if (!canFinish) return;
    setSaving(true);
    try {
      await executarTarefa(id, {
        status_execucao: "CONCLUIDA",
        obs: obs.trim() || undefined,
        fotos: cam.fotos,
        localizacao_status: gps.status === "DISPONIVEL" ? "DISPONIVEL" : "INDISPONIVEL",
        latitude: gps.latitude ?? undefined,
        longitude: gps.longitude ?? undefined,
      });
      router.replace("/home");
    } catch (err) {
      setSaving(false);
      alert(err instanceof Error ? err.message : "Erro ao concluir tarefa");
    }
  }

  async function handleCancelar() {
    if (isDone) return;
    setSaving(true);
    try {
      await executarTarefa(id, { status_execucao: "CANCELADA" });
      router.replace("/home");
    } catch {
      setSaving(false);
    }
  }

  return (
    <CampoShell className="gap-5">
      <CampoSurface className="p-3.5 sm:p-4">
        <div className="flex items-start gap-3">
          <CampoButton variant="secondary" size="sm" onClick={() => router.back()} className="size-10 px-0 shrink-0 border-border bg-card shadow-sm flex items-center justify-center">
            <ArrowLeft className="size-5 text-muted-foreground" />
          </CampoButton>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-[0.16em] text-primary">Detalhe da tarefa</p>
            <h1 className="truncate text-lg font-semibold sm:text-xl">
              {task.titulo ?? formatTaskType(task.type)}
            </h1>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <CampoPill
                className={`${
                  task.status_execucao === "CONCLUIDA"
                    ? "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200"
                    : task.status_execucao === "EM_EXECUCAO"
                    ? "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-200"
                    : task.status_execucao === "CANCELADA"
                    ? "border-border bg-muted text-muted-foreground"
                    : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
                }`}
              >
                {STATUS_LABEL[task.status_execucao] ?? task.status_execucao}
              </CampoPill>
              {task.origem === "PROGRAMADA" && !isMinhasTarefa && (
                <CampoPill className="border-border bg-muted text-muted-foreground">
                  Leitura apenas
                </CampoPill>
              )}
              {hasContextMismatch && (
                <CampoPill className="border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                  Outra unidade ativa
                </CampoPill>
              )}
              {task.status_execucao === "CONCLUIDA" && (
                <CampoPill className="border-border bg-muted text-muted-foreground">
                  Esta tarefa já integra o histórico operacional.
                </CampoPill>
              )}
              <TaskDomainBadge domain={taskDomain} />
            </div>
          </div>
        </div>
      </CampoSurface>

      {/* Contexto */}
      <CampoSurface className="flex flex-col gap-1 p-4 text-sm">
        <p className="mb-1 text-[11px] uppercase tracking-[0.18em] text-primary">Contexto operacional</p>
        {taskDomain === "AGRICULTURA" ? (
          <>
            <InfoRow label="Talhão" value={talhao?.nome ?? (task.talhao_id ? `${task.talhao_id.slice(0, 8)}…` : "—")} />
            <InfoRow label="Cultura" value={cultura ?? "—"} />
            <InfoRow label="Safra" value={safra?.ano_safra ?? (safraId ? `${safraId.slice(0, 8)}…` : "—")} />
          </>
        ) : (
          <>
            <InfoRow label="Lote" value={lote?.identificacao ?? (task.lote_id ? `${task.lote_id.slice(0, 8)}…` : "—")} />
            <InfoRow label="Piquete" value={pecuariaAreaId ? `${pecuariaAreaId.slice(0, 8)}…` : "—"} />
            <InfoRow label="Animais" value={pecuariaQuantidade !== undefined ? String(pecuariaQuantidade) : "—"} />
          </>
        )}
      </CampoSurface>

      {/* Detalhes */}
      <CampoSurface className="flex flex-col gap-1 p-4 text-sm">
        <InfoRow
          label="Unidade ativa"
          value={activeFazenda?.nome ?? (session?.active_fazenda_id ? `${session.active_fazenda_id.slice(0, 8)}…` : "—")}
        />
        <InfoRow label="Fazenda" value={fazenda?.nome ?? task.fazenda_id.slice(0, 8) + "…"} />
        {talhao && <InfoRow label="Talhão" value={talhao.nome} />}
        {lote && <InfoRow label="Lote" value={lote.identificacao} />}
        {task.data_programada && (
          <InfoRow
            label="Data"
            value={new Date(task.data_programada + "T00:00:00").toLocaleDateString("pt-BR")}
          />
        )}
        <InfoRow label="Prioridade" value={PRIORIDADE_LABEL[task.prioridade] ?? task.prioridade} />
        {task.origem === "PROGRAMADA" && !isMinhasTarefa && (
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
            Tarefa atribuída a outro operador — somente leitura
          </p>
        )}
        {hasContextMismatch && (
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
            Esta tarefa pertence a uma unidade produtiva diferente da unidade ativa selecionada no app.
          </p>
        )}
      </CampoSurface>

      {/* Dados da tarefa */}
      {Object.keys(task.dados).length > 0 && !pecuariaTask && (
        <CampoSurface className="flex flex-col gap-2 p-4 text-sm">
          <p className="mb-1 text-[11px] uppercase tracking-[0.18em] text-primary">Instruções</p>
          {Object.entries(task.dados).map(([k, v]) => (
            <InfoRow key={k} label={k} value={String(v)} />
          ))}
        </CampoSurface>
      )}

      {/* Execução — só aparece se pode agir */}
      {pecuariaTask ? (
        <PecuariaTaskExecution task={task} canInteract={isMinhasTarefa} />
      ) : canFinish ? (
        <div className="flex flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="p-4">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[104px] w-full resize-none rounded-sm border border-border bg-card px-4 py-3 text-sm outline-none transition-colors focus:border-ring focus:bg-muted placeholder:text-muted-foreground/50"
            />
          </CampoSurface>

          <CameraCapture
            fotos={cam.fotos}
            inputRef={cam.inputRef}
            canAddMore={cam.canAddMore}
            onOpen={cam.openCamera}
            onFileChange={cam.handleFileChange}
            onRemove={cam.removePhoto}
          />
        </div>
      ) : null}

      {/* Timestamps de execução */}
      {task.iniciada_em && (
        <p className="text-xs text-neutral-500">
          Iniciada em: {new Date(task.iniciada_em).toLocaleString("pt-BR")}
        </p>
      )}
      {task.concluida_em && (
        <p className="text-xs text-neutral-500">
          Concluída em: {new Date(task.concluida_em).toLocaleString("pt-BR")}
        </p>
      )}

      {/* Ações */}
      {!pecuariaTask && !isDone && isMinhasTarefa ? (
        <div className="mt-auto flex flex-col gap-3 pt-4">
          {canStart && (
            <CampoButton
              onClick={handleIniciar}
              disabled={saving}
              className="w-full"
              size="lg"
              variant="primary"
            >
              {saving ? "Aguarde..." : <><Play className="size-4 shrink-0 fill-current" /> Iniciar Tarefa</>}
            </CampoButton>
          )}
          {canFinish && (
            <CampoButton
              onClick={handleConcluir}
              disabled={saving}
              className="w-full"
              size="lg"
              variant="primary"
            >
              {saving ? "Salvando..." : <><Check className="size-4 shrink-0" /> Concluir Tarefa</>}
            </CampoButton>
          )}
          <CampoButton
            variant="secondary"
            onClick={() =>
              router.push(
                `/caderno?task_id=${encodeURIComponent(task.id)}&talhao_id=${encodeURIComponent(task.talhao_id ?? "")}&tipo_evento=${encodeURIComponent(cadernoTipo)}`
              )
            }
          >
            Registrar no Caderno
          </CampoButton>
          <button
            onClick={handleCancelar}
            disabled={saving}
            className="rounded-sm border border-border bg-card py-3 text-sm font-medium text-destructive transition-all active:scale-[0.99]"
          >
            Cancelar tarefa
          </button>
        </div>
      ) : null}
    </CampoShell>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border py-2 last:border-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="text-right font-medium text-foreground">{value}</span>
    </div>
  );
}

function formatTaskType(type: string): string {
  const map: Record<string, string> = {
    APLICACAO_DEFENSIVO: "Aplicação de Defensivo",
    APLICACAO_FERTILIZANTE: "Aplicação de Fertilizante",
    PLANTIO_REGISTRO: "Plantio",
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
