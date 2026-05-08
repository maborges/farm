import { db, newLocalId, isoNow, type LocalTask, type TaskType, type TaskModule } from "./db";
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
