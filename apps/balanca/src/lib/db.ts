import Dexie, { type EntityTable } from "dexie";

export interface OrdemPendenteLocal {
  id: string; // UUID do servidor
  origem_tipo: string;
  origem_id: string | null;
  subject_type: "VEICULO" | "ANIMAL" | "PESSOA";
  tipo_pesagem: "UNICA" | "DUPLA";
  status: "PENDENTE" | "EM_PESAGEM" | "CONCLUIDA" | "CANCELADA";
  contexto: Record<string, unknown>;
  created_at: string;
}

export interface PesagemLocal {
  local_id: string; // UUID gerado no dispositivo — chave de idempotência do sync
  ordem_id: string;
  server_id: string | null;
  numero_ticket: string | null;
  peso_bruto_kg: string | null;
  peso_tara_kg: string | null;
  peso_liquido_kg: string | null;
  captured_via: "MANUAL" | "ELETRONICA";
  leitura_bruta: Record<string, unknown> | null;
  placa: string | null;
  motorista: string | null;
  animal_id: string | null;
  pessoa_id: string | null;
  data_entrada: string | null;
  data_saida: string | null;
  client_created_at: string;
  client_updated_at: string;
  synced: 0 | 1; // Dexie não indexa booleans — usar 0/1
}

export type SyncQueueStatus = "PENDING" | "IN_FLIGHT" | "DONE" | "FAILED";

export interface SyncQueueItem {
  id?: number;
  local_id: string;
  entity_type: "pesagem";
  operation: "CREATE" | "UPDATE";
  server_id: string | null;
  status: SyncQueueStatus;
  attempts: number;
  created_at: string;
}

export interface SessionRow {
  id: 1;
  device_id: string;
  device_token: string;
  tenant_id: string;
  nome: string;
  fazenda_ids: string[];
  expires_at: string;
  last_sync_at: string | null;
}

class BalancaDB extends Dexie {
  ordens!: EntityTable<OrdemPendenteLocal, "id">;
  pesagens!: EntityTable<PesagemLocal, "local_id">;
  sync_queue!: EntityTable<SyncQueueItem, "id">;
  session!: EntityTable<SessionRow, "id">;

  constructor() {
    super("balanca_db");
    this.version(1).stores({
      ordens: "id, status, origem_tipo, subject_type",
      pesagens: "local_id, ordem_id, server_id, synced",
      sync_queue: "++id, local_id, status",
      session: "id",
    });
  }
}

export const db = new BalancaDB();

export async function getSession(): Promise<SessionRow | undefined> {
  return db.session.get(1);
}

export async function setSession(row: Omit<SessionRow, "id">): Promise<void> {
  await db.session.put({ id: 1, ...row });
}

export async function clearSession(): Promise<void> {
  await db.session.delete(1);
}
