import { db, type CampoEventoOffline, type LocalSession, type SyncQueueItem } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import { promoverEvidenciasParaUpload } from "@/lib/caderno-offline";

const API_BASE = "/api/v1";

const MAX_BATCH = 50;

export async function pushSync(): Promise<void> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  while (true) {
    const pending = await db.sync_queue
      .where("status")
      .equals("PENDING")
      .sortBy("created_at")
      .then((items) => items.slice(0, MAX_BATCH));

    if (pending.length === 0) return;

    const taskItems = pending.filter((item) => item.entity_type === "task");
    const cadernoItems = pending.filter((item) => item.entity_type === "caderno_event");

    if (taskItems.length > 0) {
      await pushTaskSync(session, taskItems);
    }

    if (cadernoItems.length > 0) {
      await pushCadernoSync(session, cadernoItems);
    }
  }
}

async function pushTaskSync(session: LocalSession, pending: SyncQueueItem[]): Promise<void> {
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
    await db.sync_queue.bulkUpdate(pending.map((item) => ({ key: item.id, changes: { status: "PENDING" as const } })));
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro no push de sincronização");
  }

  const data = await res.json();

  // Processa resultados
  await db.transaction("rw", [db.sync_queue, db.tasks], async () => {
    for (const [index, result] of data.results.entries()) {
      const queueItem = pending[index];
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

async function pushCadernoSync(session: LocalSession, pending: SyncQueueItem[]): Promise<void> {
  const now = new Date().toISOString();
  const pendingLocais = await db.caderno_events.bulkGet(pending.map((item) => item.entity_id));
  const sendable: SyncQueueItem[] = [];

  await db.transaction("rw", [db.sync_queue, db.caderno_events], async () => {
    for (const item of pending) {
      const evento = pendingLocais.find((entry) => entry?.local_id === item.entity_id);
      if (!evento) {
        await db.sync_queue.update(item.id, {
          status: "DONE",
          last_error: "Registro local não encontrado. Item removido da fila.",
        });
        continue;
      }

      if (evento.server_id) {
        await db.sync_queue.update(item.id, {
          status: "DONE",
          last_error: "Registro já reconciliado com o servidor. Retry descartado.",
        });
        continue;
      }

      if (evento.conflict_reason || evento.sync_status === "CONFLICT") {
        await db.sync_queue.update(item.id, {
          status: "DONE",
          last_error: evento.conflict_reason ?? "Registro em conflito com o servidor.",
        });
        await db.caderno_events.update(evento.local_id, {
          sync_status: "CONFLICT",
          updated_at: now,
        });
        continue;
      }

      if (evento.status_evento === "REJEITADO" || evento.status_evento === "CONSOLIDADO" || evento.status_evento === "CANCELADO") {
        await db.sync_queue.update(item.id, {
          status: "DONE",
          last_error: `Retry bloqueado para status oficial ${evento.status_evento}.`,
        });
        continue;
      }

      sendable.push(item);
    }
  });

  if (sendable.length === 0) {
    return;
  }

  await db.sync_queue.bulkUpdate(
    sendable.map((item) => ({ key: item.id, changes: { status: "IN_FLIGHT" as const } }))
  );

  const eventos = sendable.map((item) => item.payload);
  const res = await fetch(`${API_BASE}/agricola/caderno/offline-sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.device_token}`,
    },
    body: JSON.stringify({ eventos }),
  });

  if (!res.ok) {
    await db.transaction("rw", [db.sync_queue, db.caderno_events], async () => {
      for (const item of sendable) {
        const current = await db.caderno_events.get(item.entity_id);
        const attempts = (current?.sync_attempts ?? 0) + 1;
        await db.sync_queue.update(item.id, {
          status: attempts >= 5 ? "FAILED" : "PENDING",
          attempts,
          last_error: res.statusText,
        });
        await db.caderno_events.update(item.entity_id, {
          sync_status: "ERROR",
          sync_attempts: attempts,
          last_sync_error: res.statusText,
          // Não altera o status das evidências — o upload é independente do sync do evento
          updated_at: new Date().toISOString(),
        });
      }
    });
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro no push do caderno offline");
  }

  const data: Array<{ local_id: string; server_id?: string; status: "SYNCED" | "ERROR"; status_evento?: string | null; erro?: string | null }> = await res.json();

  await db.transaction("rw", [db.sync_queue, db.caderno_events], async () => {
    for (const result of data) {
      const queueItem = sendable.find((p) => p.entity_id === result.local_id);
      if (!queueItem) continue;

      if (result.status === "SYNCED") {
        await db.sync_queue.update(queueItem.id, { status: "DONE" });
        const current = await db.caderno_events.get(result.local_id);
        await db.caderno_events.update(result.local_id, {
          server_id: result.server_id,
          status_evento: (result.status_evento as CampoEventoOffline["status_evento"] | undefined) ?? "SINCRONIZADO",
          sync_status: "SYNCED",
          last_sync_error: null,
          conflict_reason: null,
          review_required: current?.review_required ?? false,
          // Não marca evidências como ENVIADA aqui — o upload de mídia ocorre em etapa separada
          synced_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
        // Promove evidências LOCAL para PENDENTE_UPLOAD agora que o server_id está disponível
        if (result.server_id) {
          await promoverEvidenciasParaUpload(result.local_id);
        }
      } else {
        const current = await db.caderno_events.get(result.local_id);
        const attempts = (current?.sync_attempts ?? 0) + 1;
        const newStatus: SyncQueueItem["status"] = attempts >= 5 ? "FAILED" : "PENDING";
        await db.sync_queue.update(queueItem.id, {
          status: newStatus,
          attempts,
          last_error: result.erro ?? "Erro desconhecido",
        });
        await db.caderno_events.update(result.local_id, {
          status_evento:
            (result.status_evento as CampoEventoOffline["status_evento"] | undefined) ??
            current?.status_evento ??
            "PENDENTE_SINCRONIZACAO",
          sync_status: "ERROR",
          sync_attempts: attempts,
          last_sync_error: result.erro ?? "Erro desconhecido",
          // Não altera evidências — upload é independente do sync do evento
          updated_at: new Date().toISOString(),
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
