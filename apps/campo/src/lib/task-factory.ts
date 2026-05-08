import { db, newLocalId, isoNow, type LocalTask, type TaskType, type TaskModule, type TaskStatusExecucao } from "./db";
import { enqueueSync } from "./sync/push";
import { useSessionStore } from "./stores/session-store";

export interface TaskPayload {
  type: TaskType;
  module: TaskModule;
  fazenda_id: string;
  talhao_id?: string;
  lote_id?: string;
  dados: Record<string, unknown>;
  fotos?: string[];
  latitude?: number;
  longitude?: number;
  localizacao_status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}

export async function createTask(payload: TaskPayload): Promise<string> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const id = newLocalId();
  const now = isoNow();

  // AGUARDANDO → INDISPONIVEL para persistência (estado transitório não salvo)
  const localizacao_status: "DISPONIVEL" | "INDISPONIVEL" =
    payload.localizacao_status === "DISPONIVEL" ? "DISPONIVEL" : "INDISPONIVEL";

  const task: LocalTask = {
    id,
    type: payload.type,
    module: payload.module,
    fazenda_id: payload.fazenda_id,
    talhao_id: payload.talhao_id,
    lote_id: payload.lote_id,
    operador_id: session.user_id,
    status: "PENDENTE",
    origem: "MANUAL",
    status_execucao: "CONCLUIDA",
    prioridade: "NORMAL",
    dados: payload.dados,
    fotos: payload.fotos ?? [],
    localizacao_status,
    latitude: payload.latitude,
    longitude: payload.longitude,
    created_at: now,
    updated_at: now,
    synced: false,
  };

  // 1. Salva no IndexedDB primeiro (offline-first)
  await db.tasks.add(task);

  // 2. Enfileira no outbox para sync posterior
  await enqueueSync("CREATE", "task", id, {
    type: task.type,
    module: task.module,
    fazenda_id: task.fazenda_id,
    talhao_id: task.talhao_id,
    lote_id: task.lote_id,
    status: task.status,
    dados: task.dados,
    fotos: task.fotos,
    localizacao_status: task.localizacao_status,
    latitude: task.latitude,
    longitude: task.longitude,
    updated_at: now,
  });

  return id;
}

export interface ExecucaoPayload {
  status_execucao: TaskStatusExecucao;
  obs?: string;
  fotos?: string[];
  latitude?: number;
  longitude?: number;
  localizacao_status?: "DISPONIVEL" | "INDISPONIVEL";
}

// Enfileira execução de tarefa programada para sync posterior
export async function executarTarefa(taskId: string, payload: ExecucaoPayload): Promise<void> {
  const now = isoNow();
  const task = await db.tasks.get(taskId);
  if (!task) throw new Error("Tarefa não encontrada");

  const changes: Partial<LocalTask> = {
    status_execucao: payload.status_execucao,
    updated_at: now,
    synced: false,
  };

  if (payload.status_execucao === "EM_EXECUCAO" && !task.iniciada_em) {
    changes.iniciada_em = now;
  }
  if (payload.status_execucao === "CONCLUIDA") {
    changes.concluida_em = now;
    if (payload.fotos?.length) {
      changes.fotos = [...(task.fotos ?? []), ...payload.fotos];
    }
    if (payload.obs) {
      changes.dados = { ...task.dados, obs_execucao: payload.obs };
    }
    if (payload.localizacao_status) {
      changes.localizacao_status = payload.localizacao_status;
      changes.latitude = payload.latitude;
      changes.longitude = payload.longitude;
    }
  }

  await db.tasks.update(taskId, changes);

  await enqueueSync("UPDATE", "task", taskId, {
    status_execucao: payload.status_execucao,
    obs: payload.obs,
    fotos: payload.fotos ?? [],
    localizacao_status: payload.localizacao_status ?? "INDISPONIVEL",
    latitude: payload.latitude,
    longitude: payload.longitude,
    updated_at: now,
  }, task.server_id);
}
