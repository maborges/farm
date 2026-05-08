import Dexie, { type Table } from "dexie";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type TaskType =
  | "APLICACAO_DEFENSIVO"
  | "APLICACAO_FERTILIZANTE"
  | "COLHEITA_REGISTRO"
  | "PREPARO_SOLO"
  | "PLANTIO_REGISTRO"
  | "IRRIGACAO_EVENTO"
  | "MONITORAMENTO_PRAGA"
  | "AMOSTRAGEM_SOLO"
  | "PESAGEM_ANIMAL"
  | "VACINACAO_LOTE"
  | "MEDICACAO_ANIMAL"
  | "MOVIMENTACAO_LOTE"
  | "PARTO_REGISTRO"
  | "MORTE_REGISTRO"
  | "INSEMINACAO"
  | "ABASTECIMENTO_MAQUINA"
  | "MANUTENCAO_OCORRENCIA"
  | "CHECKLIST_CAMPO";

export type TaskModule = "agricola" | "pecuaria";

export type TaskStatus = "PENDENTE" | "EM_ANDAMENTO" | "CONCLUIDA" | "CANCELADA";

export type SyncQueueStatus = "PENDING" | "IN_FLIGHT" | "DONE" | "FAILED";

export type LocalizacaoStatus = "DISPONIVEL" | "INDISPONIVEL";

// ---------------------------------------------------------------------------
// Entities
// ---------------------------------------------------------------------------

export interface LocalSession {
  id: 1; // singleton
  user_id: string;
  tenant_id: string;
  device_id: string;
  device_token: string;
  pin_hash: string;
  user_name: string;
  last_sync_at: string | null;
  modules: string[];
  fazenda_ids: string[];
}

export interface LocalTask {
  id: string;                       // UUID gerado localmente (crypto.randomUUID)
  server_id?: string;               // UUID do servidor após sync confirmado
  type: TaskType;
  module: TaskModule;
  fazenda_id: string;
  talhao_id?: string;
  lote_id?: string;
  operador_id: string;
  status: TaskStatus;
  dados: Record<string, unknown>;
  fotos: string[];                  // base64 comprimido (máx 2 por tarefa)
  localizacao_status: LocalizacaoStatus;
  latitude?: number;
  longitude?: number;
  created_at: string;               // ISO
  updated_at: string;               // ISO
  synced: boolean;
  sync_conflict?: string;
}

export interface SyncQueueItem {
  id: string;                       // UUID local
  operation: "CREATE" | "UPDATE" | "DELETE";
  entity_type: string;              // "task"
  entity_id: string;                // LocalTask.id
  server_id?: string;
  payload: Record<string, unknown>;
  created_at: string;               // ISO
  attempts: number;
  last_error?: string;
  status: SyncQueueStatus;
}

// Entidades cacheadas do servidor (read-only local)
export interface CachedFazenda {
  id: string;
  nome: string;
  municipio?: string;
  uf?: string;
}

export interface CachedTalhao {
  id: string;
  nome: string;
  area_ha?: number;
  fazenda_id: string;
  tipo: string;
}

export interface CachedLote {
  id: string;
  identificacao: string;
  especie: string;
  quantidade_cabecas: number;
  fazenda_id: string;
}

export interface CachedInsumo {
  id: string;
  nome: string;
  tipo: string;
  unidade_medida?: string;
}

// ---------------------------------------------------------------------------
// Database
// ---------------------------------------------------------------------------

export class CampoDatabase extends Dexie {
  session!: Table<LocalSession>;
  tasks!: Table<LocalTask>;
  sync_queue!: Table<SyncQueueItem>;
  fazendas!: Table<CachedFazenda>;
  talhoes!: Table<CachedTalhao>;
  lotes!: Table<CachedLote>;
  insumos!: Table<CachedInsumo>;

  constructor() {
    super("campo_db");
    this.version(1).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
    });
  }
}

export const db = new CampoDatabase();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function newLocalId(): string {
  return crypto.randomUUID();
}

export function isoNow(): string {
  return new Date().toISOString();
}
