import { apiFetch } from "@/lib/api";
import { db, getSession } from "@/lib/db";

interface SyncPushItemResult {
  local_id: string;
  status: "CREATED" | "UPDATED" | "CONFLICT" | "ERROR";
  server_id: string | null;
  error_message?: string | null;
}

interface SyncPushResponse {
  processed_at: string;
  results: SyncPushItemResult[];
}

const MAX_BATCH = 50;
const MAX_ATTEMPTS = 5;

export async function pushSync(): Promise<{ ok: boolean; sincronizados: number; error?: string }> {
  const session = await getSession();
  if (!session) return { ok: false, sincronizados: 0, error: "Estação não ativada." };

  const pendentes = await db.sync_queue.where("status").equals("PENDING").limit(MAX_BATCH).toArray();
  if (pendentes.length === 0) return { ok: true, sincronizados: 0 };

  await Promise.all(pendentes.map((item) => db.sync_queue.update(item.id!, { status: "IN_FLIGHT" })));

  const items = await Promise.all(
    pendentes.map(async (queueItem) => {
      const pesagem = await db.pesagens.get(queueItem.local_id);
      return {
        local_id: queueItem.local_id,
        operation: queueItem.operation,
        entity_type: "pesagem" as const,
        server_id: queueItem.server_id,
        payload: pesagem
          ? {
              ordem_id: pesagem.ordem_id,
              numero_ticket: pesagem.numero_ticket,
              peso_bruto_kg: pesagem.peso_bruto_kg,
              peso_tara_kg: pesagem.peso_tara_kg,
              peso_liquido_kg: pesagem.peso_liquido_kg,
              captured_via: pesagem.captured_via,
              leitura_bruta: pesagem.leitura_bruta,
              placa: pesagem.placa,
              motorista: pesagem.motorista,
              animal_id: pesagem.animal_id,
              pessoa_id: pesagem.pessoa_id,
              data_entrada: pesagem.data_entrada,
              data_saida: pesagem.data_saida,
            }
          : {},
        client_created_at: pesagem?.client_created_at ?? new Date().toISOString(),
        client_updated_at: pesagem?.client_updated_at ?? new Date().toISOString(),
      };
    }),
  );

  try {
    const data = await apiFetch<SyncPushResponse>("/api/v1/balanca/sync/push", {
      method: "POST",
      body: JSON.stringify({ device_id: session.device_id, last_sync_at: session.last_sync_at, items }),
    });

    let sincronizados = 0;
    for (const result of data.results) {
      const queueItem = pendentes.find((p) => p.local_id === result.local_id);
      if (!queueItem) continue;

      if (result.status === "CREATED" || result.status === "UPDATED") {
        await db.sync_queue.update(queueItem.id!, { status: "DONE", server_id: result.server_id });
        await db.pesagens.update(result.local_id, { synced: 1, server_id: result.server_id });
        sincronizados += 1;
      } else if (result.status === "CONFLICT") {
        // Servidor já tem versão mais recente — não reenviar, sinaliza para revisão manual.
        await db.sync_queue.update(queueItem.id!, { status: "DONE" });
      } else {
        const attempts = queueItem.attempts + 1;
        await db.sync_queue.update(queueItem.id!, {
          status: attempts >= MAX_ATTEMPTS ? "FAILED" : "PENDING",
          attempts,
        });
      }
    }
    return { ok: true, sincronizados };
  } catch (err) {
    await Promise.all(
      pendentes.map((item) =>
        db.sync_queue.update(item.id!, {
          status: item.attempts + 1 >= MAX_ATTEMPTS ? "FAILED" : "PENDING",
          attempts: item.attempts + 1,
        }),
      ),
    );
    return { ok: false, sincronizados: 0, error: err instanceof Error ? err.message : "Falha ao sincronizar." };
  }
}

export async function enqueuePesagem(localId: string): Promise<void> {
  await db.sync_queue.add({
    local_id: localId,
    entity_type: "pesagem",
    operation: "CREATE",
    server_id: null,
    status: "PENDING",
    attempts: 0,
    created_at: new Date().toISOString(),
  });
}
