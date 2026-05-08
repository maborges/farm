import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function pullSync(): Promise<void> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const params = new URLSearchParams({ device_id: session.device_id });
  if (session.last_sync_at) {
    params.set("last_sync_at", session.last_sync_at);
  }

  const res = await fetch(`${API_BASE}/sync/pull?${params}`, {
    headers: { Authorization: `Bearer ${session.device_token}` },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro ao sincronizar");
  }

  const data = await res.json();

  // Atualiza caches no IndexedDB em transação
  await db.transaction("rw", [db.fazendas, db.talhoes, db.lotes, db.insumos, db.tasks], async () => {
    // Fazendas
    if (data.fazendas?.length) {
      await db.fazendas.bulkPut(data.fazendas);
    }

    // Talhões
    if (data.talhoes?.length) {
      await db.talhoes.bulkPut(
        data.talhoes.map((t: any) => ({ ...t, fazenda_id: t.unidade_produtiva_id }))
      );
    }

    // Lotes
    if (data.lotes?.length) {
      await db.lotes.bulkPut(
        data.lotes.map((l: any) => ({ ...l, fazenda_id: l.unidade_produtiva_id }))
      );
    }

    // Insumos
    if (data.insumos?.length) {
      await db.insumos.bulkPut(data.insumos);
    }

    // Tombstones — remove entidades deletadas no servidor
    const tombstones = data.tombstones ?? {};
    if (tombstones.talhoes?.length) {
      await db.talhoes.bulkDelete(tombstones.talhoes);
    }
    if (tombstones.lotes?.length) {
      await db.lotes.bulkDelete(tombstones.lotes);
    }
    if (tombstones.tarefas?.length) {
      // Marcar tarefas locais como canceladas
      for (const id of tombstones.tarefas) {
        const task = await db.tasks.get(id) ?? await db.tasks.where("server_id").equals(id).first();
        if (task) {
          await db.tasks.update(task.id, { status: "CANCELADA" });
        }
      }
    }
  });

  // Atualiza last_sync_at na sessão
  await useSessionStore.getState().updateLastSync(data.sync_at);
}
