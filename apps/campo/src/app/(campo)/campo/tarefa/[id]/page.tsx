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
    <div className="flex flex-col gap-5 p-4 pb-10 min-h-dvh">
      {/* Header */}
      <div className="flex items-center gap-3 pt-2">
        <button onClick={() => router.back()} className="text-neutral-400 text-xl">
          ←
        </button>
        <h1 className="text-lg font-bold flex-1 truncate">
          {task.titulo ?? formatTaskType(task.type)}
        </h1>
        <span
          className={`text-xs font-semibold rounded-full px-2.5 py-1 ${
            task.status_execucao === "CONCLUIDA"
              ? "bg-green-900 text-green-300"
              : task.status_execucao === "EM_EXECUCAO"
              ? "bg-blue-900 text-blue-300"
              : task.status_execucao === "CANCELADA"
              ? "bg-neutral-700 text-neutral-400"
              : "bg-amber-900 text-amber-300"
          }`}
        >
          {STATUS_LABEL[task.status_execucao] ?? task.status_execucao}
        </span>
      </div>

      {/* Detalhes */}
      <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-3 text-sm">
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
      </div>

      {/* Dados da tarefa */}
      {Object.keys(task.dados).length > 0 && (
        <div className="bg-neutral-800 rounded-2xl p-4 flex flex-col gap-2 text-sm">
          <p className="text-xs text-neutral-500 uppercase tracking-wide mb-1">Instruções</p>
          {Object.entries(task.dados).map(([k, v]) => (
            <InfoRow key={k} label={k} value={String(v)} />
          ))}
        </div>
      )}

      {/* Execução — só aparece se pode agir */}
      {canFinish && (
        <div className="flex flex-col gap-4">
          <GpsWarning status={gps.status} onRetry={gps.capture} />

          <textarea
            placeholder="Observação (opcional)"
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={3}
            className="bg-neutral-800 border border-neutral-700 rounded-2xl px-4 py-3 text-sm resize-none outline-none focus:border-green-500 placeholder:text-neutral-600"
          />

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
            <button
              onClick={handleIniciar}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold transition-colors"
            >
              {saving ? "Aguarde..." : "▶ Iniciar Tarefa"}
            </button>
          )}
          {canFinish && (
            <button
              onClick={handleConcluir}
              disabled={saving}
              className="bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-2xl py-5 text-base font-bold transition-colors"
            >
              {saving ? "Salvando..." : "✅ Concluir Tarefa"}
            </button>
          )}
          <button
            onClick={handleCancelar}
            disabled={saving}
            className="text-red-400 text-sm underline text-center py-2"
          >
            Cancelar tarefa
          </button>
        </div>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-neutral-500 shrink-0">{label}</span>
      <span className="font-medium text-right">{value}</span>
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
