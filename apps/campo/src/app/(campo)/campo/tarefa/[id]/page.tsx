"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { useGps } from "@/hooks/useGps";
import { useCamera } from "@/hooks/useCamera";
import { executarTarefa } from "@/lib/task-factory";
import { GpsWarning } from "@/components/campo/gps-warning";
import { CameraCapture } from "@/components/campo/camera-capture";
import { useSessionStore } from "@/lib/stores/session-store";
import { CampoShell, CampoSurface, CampoButton, CampoSectionTitle } from "@/components/campo/ui";
import { CampoPill } from "@/components/campo/ui";

const PRIORIDADE_LABEL: Record<string, string> = {
  URGENTE: "🔴 Urgente",
  ALTA: "🟠 Alta",
  NORMAL: "🟡 Normal",
  BAIXA: "⚪ Baixa",
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

  const lote = useLiveQuery(
    async () => task?.lote_id ? db.lotes.get(task.lote_id) : undefined,
    [task?.lote_id]
  );

  const fazenda = useLiveQuery(
    async () => task?.fazenda_id ? db.fazendas.get(task.fazenda_id) : undefined,
    [task?.fazenda_id]
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

  const canStart = task.status_execucao === "PENDENTE" && isMinhasTarefa;
  const canFinish = task.status_execucao === "EM_EXECUCAO" && isMinhasTarefa;
  const isDone =
    task.status_execucao === "CONCLUIDA" || task.status_execucao === "CANCELADA";

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
      <CampoSurface className="p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <CampoButton variant="secondary" size="sm" onClick={() => router.back()}>
            ←
          </CampoButton>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] uppercase tracking-[0.22em] text-emerald-300/80">Detalhe da tarefa</p>
            <h1 className="truncate text-xl font-semibold sm:text-2xl">
              {task.titulo ?? formatTaskType(task.type)}
            </h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <CampoPill
                className={`${
                  task.status_execucao === "CONCLUIDA"
                    ? "border-emerald-400/20 bg-emerald-400/12 text-emerald-100"
                    : task.status_execucao === "EM_EXECUCAO"
                    ? "border-sky-400/20 bg-sky-400/12 text-sky-100"
                    : task.status_execucao === "CANCELADA"
                    ? "border-white/10 bg-white/6 text-white/55"
                    : "border-amber-400/20 bg-amber-400/12 text-amber-100"
                }`}
              >
                {STATUS_LABEL[task.status_execucao] ?? task.status_execucao}
              </CampoPill>
              {task.origem === "PROGRAMADA" && !isMinhasTarefa && (
                <CampoPill className="border-white/10 bg-white/6 text-white/55">
                  Leitura apenas
                </CampoPill>
              )}
            </div>
          </div>
        </div>
      </CampoSurface>

      {/* Detalhes */}
      <CampoSurface className="flex flex-col gap-1 p-4 text-sm">
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
          <p className="text-xs text-amber-400 mt-1">
            Tarefa atribuída a outro operador — somente leitura
          </p>
        )}
      </CampoSurface>

      {/* Dados da tarefa */}
      {Object.keys(task.dados).length > 0 && (
        <CampoSurface className="flex flex-col gap-2 p-4 text-sm">
          <p className="mb-1 text-[11px] uppercase tracking-[0.22em] text-emerald-300/80">Instruções</p>
          {Object.entries(task.dados).map(([k, v]) => (
            <InfoRow key={k} label={k} value={String(v)} />
          ))}
        </CampoSurface>
      )}

      {/* Execução — só aparece se pode agir */}
      {canFinish && (
        <div className="flex flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <CampoSurface className="p-4">
            <textarea
              placeholder="Observação (opcional)"
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              rows={3}
              className="min-h-[104px] w-full resize-none rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06] placeholder:text-white/30"
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
      )}

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
      {!isDone && isMinhasTarefa && (
        <div className="mt-auto flex flex-col gap-3 pt-4">
          {canStart && (
            <CampoButton
              onClick={handleIniciar}
              disabled={saving}
              className="w-full"
              size="lg"
              variant="primary"
            >
              {saving ? "Aguarde..." : "▶ Iniciar Tarefa"}
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
              {saving ? "Salvando..." : "✅ Concluir Tarefa"}
            </CampoButton>
          )}
          <button
            onClick={handleCancelar}
            disabled={saving}
            className="rounded-2xl border border-white/10 bg-white/[0.04] py-3 text-sm font-medium text-rose-200 transition-all active:scale-[0.99]"
          >
            Cancelar tarefa
          </button>
        </div>
      )}
    </CampoShell>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/8 py-2 last:border-0">
      <span className="shrink-0 text-white/45">{label}</span>
      <span className="text-right font-medium text-white/85">{value}</span>
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
