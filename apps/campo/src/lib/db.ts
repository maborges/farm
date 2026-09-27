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
  | "PESAGEM"
  | "PESAGEM_ANIMAL"
  | "VACINACAO"
  | "VACINACAO_LOTE"
  | "COBERTURA"
  | "DIAGNOSTICO_PRENHEZ"
  | "DESMAME"
  | "MEDICACAO_ANIMAL"
  | "MOVIMENTACAO_LOTE"
  | "PARTO"
  | "PARTO_REGISTRO"
  | "MORTE_REGISTRO"
  | "INSEMINACAO"
  | "ABASTECIMENTO_MAQUINA"
  | "MANUTENCAO_OCORRENCIA"
  | "CHECKLIST_CAMPO";

export type TaskModule = "agricola" | "pecuaria";

export type TaskStatus = "PENDENTE" | "EM_ANDAMENTO" | "CONCLUIDA" | "CANCELADA";
export type TaskOrigem = "MANUAL" | "PROGRAMADA";
export type TaskStatusExecucao = "PENDENTE" | "EM_EXECUCAO" | "CONCLUIDA" | "CANCELADA";
export type TaskPrioridade = "BAIXA" | "NORMAL" | "ALTA" | "URGENTE";

export type SyncQueueStatus = "PENDING" | "IN_FLIGHT" | "DONE" | "FAILED";
export type CadernoOfflineSyncStatus = "PENDING" | "SYNCING" | "SYNCED" | "ERROR" | "CONFLICT";
export type CadernoEvidenciaUploadStatus = "LOCAL" | "PENDENTE_UPLOAD" | "ENVIANDO" | "ENVIADA" | "ERRO_UPLOAD";

export type CadernoEventoTipo =
  | "PLANTIO"
  | "PULVERIZACAO"
  | "APLICACAO"
  | "IRRIGACAO"
  | "COLHEITA"
  | "INSPECAO"
  | "OCORRENCIA"
  | "MANUTENCAO"
  | "ABASTECIMENTO"
  | "EXECUCAO_OPERACIONAL"
  | "MONITORAMENTO"
  | "VISITA_TECNICA"
  | "EPI_ENTREGA"
  | "OBSERVACAO"
  | "CLIMA"
  | "SOLO";

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
  user_avatar_url?: string;
  last_sync_at: string | null;
  modules: string[];
  fazenda_ids: string[];
  active_fazenda_id?: string;
}

export interface LocalTask {
  id: string;                       // UUID gerado localmente (MANUAL) ou server_id (PROGRAMADA)
  server_id?: string;               // UUID do servidor após sync confirmado
  type: TaskType | string;
  module: TaskModule;
  fazenda_id: string;
  talhao_id?: string;
  lote_id?: string;
  dispositivo_id?: string;
  operador_id?: string;
  status: TaskStatus;
  // Campos de tarefas programadas
  origem: TaskOrigem;
  status_execucao: TaskStatusExecucao;
  titulo?: string;
  data_programada?: string;         // ISO date YYYY-MM-DD
  prioridade: TaskPrioridade;
  dados: Record<string, unknown>;
  fotos: string[];                  // base64 comprimido (máx 2 por tarefa)
  localizacao_status: LocalizacaoStatus;
  latitude?: number;
  longitude?: number;
  iniciada_em?: string;             // ISO
  concluida_em?: string;            // ISO
  created_at: string;               // ISO
  updated_at: string;               // ISO
  synced: boolean;
  sync_conflict?: string;
}

export type NaturezaItemCampo = "CONSUMIVEL" | "RETORNAVEL";
export type ResultadoRecebimentoCampo =
  | "RECEBIDO_INTEGRAL"
  | "RECEBIDO_PARCIAL"
  | "RECUSADO"
  | "DIVERGENTE";

export interface CachedEntregaRequisicao {
  id: string;
  quantidade_entregue: number;
  quantidade_recebida: number;
  quantidade_recusada: number;
  quantidade_pendente_conferencia: number;
  quantidade_consumida?: number;
  quantidade_devolvida?: number;
  quantidade_perdida?: number;
  quantidade_danificada?: number;
  quantidade_extraviada?: number;
  quantidade_em_posse?: number;
  status_conciliacao?: string;
  lote_id?: string | null;
  deposito_id?: string | null;
  unidade: string;
  entregue_em: string;
}

export interface CachedItemRequisicao {
  id: string;
  requisicao_id: string;
  tenant_id: string;
  produto_id: string;
  produto_nome?: string | null;
  natureza_item?: NaturezaItemCampo | null;
  unidade: string;
  quantidade_aprovada: number;
  quantidade_entregue: number;
  quantidade_recebida: number;
  quantidade_recusada: number;
  quantidade_pendente_conferencia: number;
  quantidade_em_posse: number;
  quantidade_consumida?: number;
  quantidade_devolvida?: number;
  quantidade_perdida?: number;
  quantidade_danificada?: number;
  quantidade_extraviada?: number;
  status_conferencia: string;
  status_conciliacao?: string;
  entregas: CachedEntregaRequisicao[];
  updated_at: string;
}

export interface CachedRequisicao {
  id: string;
  tenant_id: string;
  numero?: string | null;
  unidade_produtiva_id: string;
  safra_id?: string | null;
  safra_tarefa_id?: string | null;
  operacao_agricola_id?: string | null;
  responsavel_pessoa_id?: string | null;
  responsavel_autorizado: boolean;
  version: number;
  status: string;
  status_efetivo: string;
  status_conciliacao?: string;
  data_solicitacao: string;
  execucoes?: Array<{ id: string; status: string; data_execucao: string }>;
  itens: CachedItemRequisicao[];
  updated_at: string;
}

export type MaterialReceiptLocalStatus = "PENDING" | "IN_FLIGHT" | "ACK" | "CONFLICT" | "ERROR";

export interface RequisicaoOperacaoPendente {
  id: string; // client_operation_id estável
  tenant_id: string;
  usuario_id: string;
  pessoa_id?: string | null;
  device_id: string;
  requisicao_id: string;
  item_id: string;
  entrega_evento_id: string;
  quantidade_recebida: number;
  resultado: ResultadoRecebimentoCampo;
  motivo?: string | null;
  base_version: number;
  tipo_evento?: "CONSUMO" | "DEVOLUCAO" | "PERDA" | "DANO" | "EXTRAVIO";
  operacao_execucao_id?: string | null;
  deposito_id?: string | null;
  lote_id?: string | null;
  created_at_device: string;
  status: MaterialReceiptLocalStatus;
  server_event_id?: string | null;
  error?: string | null;
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

export interface CadernoEvidenciaOffline {
  /** Identificador único local da evidência — gerado no dispositivo, usado para idempotência no upload */
  local_evidence_id: string;
  tipo: string;
  upload_status: CadernoEvidenciaUploadStatus;
  upload_attempts: number;
  last_upload_error: string | null;
  /** ID do arquivo no servidor após upload bem-sucedido */
  server_file_id: string | null;
  /** URL pública no servidor após upload bem-sucedido */
  server_url: string | null;
  local_uri?: string;
  nome_arquivo?: string;
  mime_type?: string;
  tamanho?: number;
  captured_at?: string;
  url?: string;
  latitude?: number;
  longitude?: number;
  data_captura?: string;
  metadata?: Record<string, unknown>;
}

export interface CampoEventoOffline {
  local_id: string;
  server_id?: string;
  tenant_id: string;
  safra_nome?: string | null;
  talhao_nome?: string | null;
  descricao: string;
  unidade_produtiva_id?: string | null;
  safra_id: string;
  talhao_id?: string | null;
  tarefa_id?: string | null;
  operacao_id?: string | null;
  tipo_evento: CadernoEventoTipo | string;
  origem_evento: "PWA_OFFLINE";
  origem_tecnica: "SYNC_PWA";
  status_evento:
    | "RASCUNHO"
    | "PENDENTE_SINCRONIZACAO"
    | "SYNCING"
    | "SINCRONIZADO"
    | "PENDENTE_APROVACAO"
    | "APROVADO"
    | "REJEITADO"
    | "CONSOLIDADO"
    | "CANCELADO";
  client_created_at: string;
  client_updated_at: string;
  device_id: string;
  usuario_id?: string | null;
  executado_por_pessoa_id?: string | null;
  payload_operacional: Record<string, unknown>;
  evidencias: CadernoEvidenciaOffline[];
  documental_status?: string | null;
  origem_invalidada?: boolean;
  motivo_invalidacao_origem?: string | null;
  retifica_evento_id?: string | null;
  retificado_por_evento_id?: string | null;
  oficial_justificativa?: string | null;
  reconciled_at?: string | null;
  review_required?: boolean;
  conflict_reason?: string | null;
  sync_status: CadernoOfflineSyncStatus;
  sync_attempts: number;
  last_sync_error?: string | null;
  synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampoEventoOficial {
  server_id: string;
  local_id?: string | null;
  device_id?: string | null;
  safra_id: string;
  talhao_id: string;
  tipo: string;
  tipo_evento?: string | null;
  descricao: string;
  data_registro: string;
  executado_por_pessoa_id?: string | null;
  status_evento: string;
  documental_status: string;
  versao_vigente: boolean;
  retificado: boolean;
  retificador: boolean;
  invalidado: boolean;
  origem_invalidada: boolean;
  motivo_invalidacao_origem?: string | null;
  motivo_retificacao?: string | null;
  retifica_evento_id?: string | null;
  retificado_por_evento_id?: string | null;
  justificativa?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
}

export interface CadernoDraft {
  id: string;
  task_id?: string | null;
  user_id: string;
  step: "contexto" | "registro" | "evidencias";
  fazenda_id?: string | null;
  safra_id?: string | null;
  talhao_id?: string | null;
  tipo_evento: CadernoEventoTipo | string;
  descricao: string;
  observacao: string;
  executado_por_pessoa_id?: string | null;
  fotos: string[];
  updated_at: string;
}

// Entidades cacheadas do servidor (read-only local)
export interface CachedFazenda {
  id: string;
  nome: string;
  municipio?: string;
  uf?: string;
  logo_url?: string | null;
}

export type CachedImageKind = "user_avatar" | "fazenda_logo";

export interface CachedImage {
  id: string;
  kind: CachedImageKind;
  owner_id: string;
  source_url: string;
  blob: Blob;
  mime_type: string;
  updated_at: string;
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

export interface CachedAnimal {
  id: string;
  unidade_produtiva_id: string;
  lote_id?: string | null;
  numero_brinco?: string | null;
  numero_sisbov?: string | null;
  nome?: string | null;
  sexo?: string | null;
  categoria?: string | null;
  status?: string | null;
  especie?: string | null;
  dados_extras?: Record<string, unknown> | null;
  updated_at?: string;
}

export interface CachedInsumo {
  id: string;
  nome: string;
  tipo: string;
  unidade_medida?: string;
}

export interface CachedSafra {
  id: string;
  ano_safra: string;
  cultura?: string | null;
  cultura_id?: string | null;
  cultura_nome?: string | null;
  cultura_source?: string | null;
  status: string;
}

export interface CachedColaborador {
  id: string;
  nome: string;
  cpf?: string | null;
  cargo?: string | null;
}

export interface PessoaOperacional {
  id: string; // `${unidade_produtiva_id}:${pessoa_id}`
  pessoa_id: string;
  nome_exibicao: string;
  unidade_produtiva_id: string;
  papeis: string[];
}

export interface CachedRecomendacaoClimatica {
  id: string; // "unidade_produtiva_id-tipo_operacao"
  unidade_produtiva_id: string;
  tipo_operacao: string;
  status: string;
  severidade: string;
  motivo: string;
  dados_utilizados: Record<string, unknown>;
  data_referencia: string;
  fonte: string;
  validade_horas: number;
}

export interface CachedRecomendacaoOperacional {
  id: string;
  tenant_id: string;
  unidade_produtiva_id: string | null;
  domain: string;
  status: string;
  priority: string;
  source_type: string;
  action_type: string;
  provider_name: string;
  rule_code: string;
  scope_type: string;
  scope_id: string;
  title: string;
  summary: string;
  rationale: string;
  dedupe_key: string;
  source_signal_ids: string[];
  confidence?: number | null;
  action_label?: string | null;
  action_target?: string | null;
  context?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  expires_at?: string | null;
  viewed_at?: string | null;
  accepted_at?: string | null;
  dismissed_at?: string | null;
  postponed_until?: string | null;
  executed_at?: string | null;
  superseded_at?: string | null;
  superseded_by_id?: string | null;
}

// ---------------------------------------------------------------------------
// Database
// ---------------------------------------------------------------------------

export class CampoDatabase extends Dexie {
  session!: Table<LocalSession>;
  tasks!: Table<LocalTask>;
  sync_queue!: Table<SyncQueueItem>;
  caderno_events!: Table<CampoEventoOffline>;
  caderno_server_events!: Table<CampoEventoOficial>;
  caderno_drafts!: Table<CadernoDraft>;
  fazendas!: Table<CachedFazenda>;
  talhoes!: Table<CachedTalhao>;
  lotes!: Table<CachedLote>;
  animais!: Table<CachedAnimal>;
  insumos!: Table<CachedInsumo>;
  safras!: Table<CachedSafra>;
  colaboradores!: Table<CachedColaborador>;
  recomendacoes_climaticas!: Table<CachedRecomendacaoClimatica>;
  recomendacoes_operacionais!: Table<CachedRecomendacaoOperacional>;
  pessoas_operacionais!: Table<PessoaOperacional>;
  cached_images!: Table<CachedImage>;
  requisicoes!: Table<CachedRequisicao>;
  requisicao_itens!: Table<CachedItemRequisicao>;
  requisicao_operacoes!: Table<RequisicaoOperacaoPendente>;

  constructor() {
    super("campo_db");
    this.version(1).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    });
    this.version(2).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    }).upgrade((tx) =>
      tx.table("tasks").toCollection().modify((t) => {
        if (!t.origem) t.origem = "MANUAL";
        if (!t.status_execucao) t.status_execucao = "CONCLUIDA";
        if (!t.prioridade) t.prioridade = "NORMAL";
      })
    );
    this.version(3).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    });
    this.version(4).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    });
    this.version(5).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    });
    this.version(6).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, created_at",
      caderno_server_events: "server_id, local_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    });
    this.version(7).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    }).upgrade((tx) =>
      tx.table("caderno_events").toCollection().modify((evento) => {
        if (!evento.sync_status) evento.sync_status = "PENDING";
        if (typeof evento.review_required !== "boolean") evento.review_required = false;
        if (typeof evento.conflict_reason === "undefined") evento.conflict_reason = null;
        if (typeof evento.documental_status === "undefined") evento.documental_status = null;
        if (typeof evento.origem_invalidada === "undefined") evento.origem_invalidada = false;
        if (typeof evento.reconciled_at === "undefined") evento.reconciled_at = null;
        if (!Array.isArray(evento.evidencias)) {
          evento.evidencias = [];
          return;
        }

        evento.evidencias = evento.evidencias.map((evidencia: CadernoEvidenciaOffline) => ({
          ...evidencia,
          upload_status: evidencia.upload_status ?? (evidencia.url ? "ENVIADA" : "LOCAL"),
        }));
      })
    );
    this.version(8).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
    }).upgrade((tx) =>
      tx.table("caderno_events").toCollection().modify((evento) => {
        if (!Array.isArray(evento.evidencias)) {
          evento.evidencias = [];
          return;
        }
        // Migra evidências existentes para o novo contrato com local_evidence_id e campos de upload
        evento.evidencias = evento.evidencias.map((ev: Partial<CadernoEvidenciaOffline>) => ({
          ...ev,
          local_evidence_id: ev.local_evidence_id ?? crypto.randomUUID(),
          upload_status: ev.upload_status ?? (ev.url ? "ENVIADA" : "LOCAL"),
          upload_attempts: ev.upload_attempts ?? 0,
          last_upload_error: ev.last_upload_error ?? null,
          server_file_id: ev.server_file_id ?? null,
          server_url: ev.server_url ?? ev.url ?? null,
        }));
      })
    );
    this.version(9).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
    });
    this.version(10).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
    });
    this.version(11).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
      recomendacoes_climaticas: "id, unidade_produtiva_id, tipo_operacao",
    });
    this.version(12).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
      recomendacoes_climaticas: "id, unidade_produtiva_id, tipo_operacao",
      recomendacoes_operacionais: "id, unidade_produtiva_id, domain, status, priority, updated_at",
    });
    this.version(13).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
      recomendacoes_climaticas: "id, unidade_produtiva_id, tipo_operacao",
      recomendacoes_operacionais: "id, unidade_produtiva_id, domain, status, priority, updated_at",
    });
    this.version(14).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
      recomendacoes_climaticas: "id, unidade_produtiva_id, tipo_operacao",
      recomendacoes_operacionais: "id, unidade_produtiva_id, domain, status, priority, updated_at",
      pessoas_operacionais: "id, unidade_produtiva_id, pessoa_id",
    });
    this.version(15).stores({
      session: "id",
      tasks:
        "id, server_id, type, module, fazenda_id, talhao_id, lote_id, status, origem, status_execucao, data_programada, synced, created_at",
      sync_queue: "id, entity_id, entity_type, status, created_at",
      caderno_events: "local_id, server_id, tenant_id, safra_id, talhao_id, device_id, sync_status, review_required, created_at",
      caderno_server_events:
        "server_id, local_id, device_id, safra_id, talhao_id, status_evento, documental_status, updated_at, data_registro",
      caderno_drafts: "id, user_id, task_id, updated_at",
      fazendas: "id",
      talhoes: "id, fazenda_id",
      lotes: "id, fazenda_id",
      animais: "id, unidade_produtiva_id, lote_id, numero_brinco, nome, categoria, sexo, status",
      insumos: "id, categoria",
      safras: "id, status",
      colaboradores: "id",
      recomendacoes_climaticas: "id, unidade_produtiva_id, tipo_operacao",
      recomendacoes_operacionais: "id, unidade_produtiva_id, domain, status, priority, updated_at",
      pessoas_operacionais: "id, unidade_produtiva_id, pessoa_id",
      cached_images: "id, kind, owner_id, source_url, updated_at",
    });
    this.version(16).stores({
      requisicoes: "id, tenant_id, unidade_produtiva_id, operacao_agricola_id, status_efetivo, updated_at",
      requisicao_itens: "id, requisicao_id, tenant_id, quantidade_pendente_conferencia, status_conferencia, updated_at",
      requisicao_operacoes: "id, tenant_id, requisicao_id, item_id, status, created_at_device",
    });
    this.version(17).upgrade((tx) =>
      tx.table("requisicao_operacoes").toCollection().modify((operation) => {
        if (typeof operation.tipo_evento === "undefined") operation.tipo_evento = undefined;
        if (typeof operation.operacao_execucao_id === "undefined") operation.operacao_execucao_id = null;
        if (typeof operation.deposito_id === "undefined") operation.deposito_id = null;
        if (typeof operation.lote_id === "undefined") operation.lote_id = null;
      })
    );
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

export function generatePessoaOperacionalId(upId: string, pessoaId: string): string {
  return `${upId}:${pessoaId}`;
}
