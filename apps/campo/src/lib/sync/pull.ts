import { db, type LocalTask, type TaskModule } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface SyncPullPayload {
  fazendas?: Array<{
    id: string;
    nome: string;
    municipio?: string;
    uf?: string;
  }>;
  talhoes?: Array<{
    id: string;
    nome: string;
    unidade_produtiva_id: string;
    area_ha?: number | null;
    tipo: string;
  }>;
  lotes?: Array<{
    id: string;
    identificacao: string;
    especie: string;
    quantidade_cabecas: number;
    unidade_produtiva_id: string;
  }>;
  insumos?: Array<{
    id: string;
    nome: string;
    tipo: string;
    unidade_medida?: string | null;
  }>;
  tarefas_pendentes?: Array<{
    id: string;
    client_id?: string | null;
    type: string;
    module: string;
    status?: string;
    origem?: string;
    status_execucao?: string;
    titulo?: string | null;
    data_programada?: string | null;
    prioridade?: string;
    operador_id?: string | null;
    dados?: Record<string, unknown>;
    unidade_produtiva_id?: string | null;
    area_rural_id?: string | null;
    lote_id?: string | null;
    client_created_at?: string | null;
    client_updated_at?: string | null;
  }>;
  tombstones?: {
    talhoes?: string[];
    lotes?: string[];
    tarefas?: string[];
    insumos?: string[];
  };
  sync_at: string;
}

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

  const data = (await res.json()) as SyncPullPayload;

  // Atualiza caches no IndexedDB em transação
  await db.transaction("rw", [db.fazendas, db.talhoes, db.lotes, db.insumos, db.tasks], async () => {
    // Fazendas
    if (data.fazendas?.length) {
      await db.fazendas.bulkPut(data.fazendas);
    }

    // Talhões
    if (data.talhoes?.length) {
      await db.talhoes.bulkPut(
        data.talhoes.map((t) => ({
          id: t.id,
          nome: t.nome,
          fazenda_id: t.unidade_produtiva_id,
          area_ha: t.area_ha ?? undefined,
          tipo: t.tipo,
        }))
      );
    }

    // Lotes
    if (data.lotes?.length) {
      await db.lotes.bulkPut(data.lotes.map((l) => ({ ...l, fazenda_id: l.unidade_produtiva_id })));
    }

    // Insumos
    if (data.insumos?.length) {
      await db.insumos.bulkPut(
        data.insumos.map((i) => ({
          id: i.id,
          nome: i.nome,
          tipo: i.tipo,
          unidade_medida: i.unidade_medida ?? undefined,
        }))
      );
    }

    // Tarefas programadas recebidas do servidor
    if (data.tarefas_pendentes?.length) {
      const now = new Date().toISOString();
      await db.tasks.bulkPut(
        data.tarefas_pendentes.map((t) => ({
          id: t.client_id ?? String(t.id),
          server_id: String(t.id),
          type: t.type,
          module: (t.module === "pecuaria" ? "pecuaria" : "agricola") as TaskModule,
          fazenda_id: t.unidade_produtiva_id ?? "",
          talhao_id: t.area_rural_id ?? undefined,
          lote_id: t.lote_id ?? undefined,
          operador_id: t.operador_id ?? undefined,
          status: (t.status ?? "PENDENTE") as LocalTask["status"],
          origem: (t.origem ?? "MANUAL") as LocalTask["origem"],
          status_execucao: (t.status_execucao ?? "PENDENTE") as LocalTask["status_execucao"],
          titulo: t.titulo ?? undefined,
          data_programada: t.data_programada ?? undefined,
          prioridade: (t.prioridade ?? "NORMAL") as LocalTask["prioridade"],
          dados: t.dados ?? {},
          fotos: [],
          localizacao_status: "INDISPONIVEL" as LocalTask["localizacao_status"],
          created_at: t.client_created_at ?? now,
          updated_at: t.client_updated_at ?? now,
          synced: true,
        }))
      );
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
          await db.tasks.update(task.id, { status_execucao: "CANCELADA" });
        }
      }
    }
  });

  // Atualiza last_sync_at na sessão
  await useSessionStore.getState().updateLastSync(data.sync_at);
}
