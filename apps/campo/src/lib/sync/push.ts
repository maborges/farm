import { db, type SyncQueueItem } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const MAX_BATCH = 50;

export async function pushSync(): Promise<void> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  // Busca itens PENDING em ordem FIFO (máx MAX_BATCH)
  const pending = await db.sync_queue
    .where("status")
    .equals("PENDING")
    .sortBy("created_at")
    .then((items) => items.slice(0, MAX_BATCH));

  if (pending.length === 0) return;

  // Marca como IN_FLIGHT para evitar reprocessamento concorrente
  await db.sync_queue.bulkUpdate(
    pending.map((item) => ({ key: item.id, changes: { status: "IN_FLIGHT" as const } }))
  );

  const body = {
    device_id: session.device_id,
    last_sync_at: session.last_sync_at ?? null,
    items: pending.map((item) => ({
      local_id: item.entity_id,
      operation: item.operation,
      entity_type: item.entity_type,
      server_id: item.server_id ?? null,
      payload: item.payload,
      client_created_at: item.created_at,
      client_updated_at: item.payload.updated_at ?? item.created_at,
    })),
  };

  const res = await fetch(`${API_BASE}/sync/push`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.device_token}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    // Reverte IN_FLIGHT → PENDING para retry
    await db.sync_queue.bulkUpdate(
      pending.map((item) => ({ key: item.id, changes: { status: "PENDING" as const } }))
    );
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro no push de sincronização");
  }

  const data = await res.json();

  // Processa resultados
  await db.transaction("rw", [db.sync_queue, db.tasks], async () => {
    for (const result of data.results) {
      const queueItem = pending.find((p) => p.entity_id === result.local_id);
      if (!queueItem) continue;

      if (result.status === "CREATED" || result.status === "UPDATED" || result.status === "DELETED") {
        // Sucesso: marca fila como DONE
        await db.sync_queue.update(queueItem.id, { status: "DONE" });

        // Atualiza server_id na tarefa local
        if (result.server_id) {
          await db.tasks.update(queueItem.entity_id, {
            server_id: result.server_id,
            synced: true,
            sync_conflict: undefined,
          });
        }
      } else if (result.status === "CONFLICT") {
        // Conflito: registra na tarefa e marca fila como DONE (não reenvia)
        await db.sync_queue.update(queueItem.id, { status: "DONE" });
        await db.tasks.update(queueItem.entity_id, {
          sync_conflict: `Conflito: servidor tem versão mais recente. Dados do servidor: ${JSON.stringify(result.server_data)}`,
          synced: false,
        });
      } else {
        // Erro: incrementa tentativas
        const newAttempts = (queueItem.attempts ?? 0) + 1;
        const newStatus: SyncQueueItem["status"] = newAttempts >= 5 ? "FAILED" : "PENDING";
        await db.sync_queue.update(queueItem.id, {
          status: newStatus,
          attempts: newAttempts,
          last_error: result.error_message ?? "Erro desconhecido",
        });
      }
    }
  });
}

// Enfileira uma operação no outbox (chamado por todos os formulários de campo)
export async function enqueueSync(
  operation: SyncQueueItem["operation"],
  entityType: string,
  entityId: string,
  payload: Record<string, unknown>,
  serverId?: string
): Promise<void> {
  await db.sync_queue.add({
    id: crypto.randomUUID(),
    operation,
    entity_type: entityType,
    entity_id: entityId,
    server_id: serverId,
    payload,
    created_at: new Date().toISOString(),
    attempts: 0,
    status: "PENDING",
  });
}
