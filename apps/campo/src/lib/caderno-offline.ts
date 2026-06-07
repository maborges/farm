"use client";

import {
  db,
  isoNow,
  newLocalId,
  type CampoEventoOffline,
  type CadernoEvidenciaOffline,
  type CadernoEventoTipo,
} from "./db";
import { enqueueSync } from "./sync/push";
import { useSessionStore } from "./stores/session-store";

export interface CreateOfflineCadernoEventPayload {
  tipo_evento: CadernoEventoTipo | string;
  safra_id: string;
  safra_nome?: string | null;
  talhao_id?: string | null;
  talhao_nome?: string | null;
  unidade_produtiva_id?: string | null;
  tarefa_id?: string | null;
  operacao_id?: string | null;
  descricao?: string;
  payload_operacional?: Record<string, unknown>;
  evidencias?: CadernoEvidenciaOffline[];
  usuario_id?: string | null;
}

type OfflineQueuePayload = Omit<
  CampoEventoOffline,
  "sync_status" | "sync_attempts" | "last_sync_error" | "synced_at" | "created_at" | "updated_at" | "evidencias"
> & {
  evidencias: Record<string, unknown>[];
  payload_operacional: Record<string, unknown>;
};

export const PWA_CADERNO_EVENT_TYPES = [
  "MONITORAMENTO",
  "OCORRENCIA",
  "INSPECAO",
  "OBSERVACAO",
  "APLICACAO",
  "PULVERIZACAO",
] as const;

const TASK_TO_CADERNO_TYPE: Record<string, CadernoEventoTipo> = {
  APLICACAO_DEFENSIVO: "PULVERIZACAO",
  APLICACAO_FERTILIZANTE: "APLICACAO",
  COLHEITA_REGISTRO: "OBSERVACAO",
  PREPARO_SOLO: "OBSERVACAO",
  PLANTIO_REGISTRO: "OBSERVACAO",
  IRRIGACAO_EVENTO: "OBSERVACAO",
  MONITORAMENTO_PRAGA: "MONITORAMENTO",
  AMOSTRAGEM_SOLO: "INSPECAO",
  CHECKLIST_CAMPO: "INSPECAO",
};

/**
 * Converte uma evidência offline para o formato que vai no payload de sync de evento.
 * O blob (local_uri) NÃO é enviado no sync do evento — apenas metadados.
 */
function toBackendEvidence(evidence: CadernoEvidenciaOffline): Record<string, unknown> {
  const {
    local_uri: _localUri,
    nome_arquivo,
    mime_type,
    tamanho,
    captured_at,
    metadata,
    local_evidence_id,
    upload_status: _uploadStatus,
    upload_attempts: _attempts,
    last_upload_error: _error,
    server_file_id: _sfid,
    server_url,
    ...rest
  } = evidence;

  return {
    ...rest,
    // Se já foi enviada, usa server_url; senão mantém referência local
    url: server_url ?? evidence.url ?? undefined,
    local_evidence_id,
    data_captura: captured_at ?? evidence.data_captura ?? undefined,
    metadata: {
      ...(metadata ?? {}),
      ...(nome_arquivo ? { nome_arquivo } : {}),
      ...(mime_type ? { mime_type } : {}),
      ...(typeof tamanho === "number" ? { tamanho } : {}),
      ...(captured_at ? { captured_at } : {}),
      local_evidence_id,
    },
  };
}

export function mapTaskTypeToCadernoTipo(taskType: string): CadernoEventoTipo {
  return TASK_TO_CADERNO_TYPE[taskType] ?? "OBSERVACAO";
}

export function buildEvidenceFromImage({
  localUri,
  index,
  gpsLatitude,
  gpsLongitude,
  capturedAt,
}: {
  localUri: string;
  index: number;
  gpsLatitude?: number | null;
  gpsLongitude?: number | null;
  capturedAt?: string;
}): CadernoEvidenciaOffline {
  const mimeType = localUri.startsWith("data:image/png") ? "image/png" : "image/jpeg";
  const base64Size = Math.max(0, Math.round((localUri.length - localUri.indexOf(",") - 1) * 0.75));

  return {
    local_evidence_id: newLocalId(),
    tipo: "FOTO",
    upload_status: "LOCAL",
    upload_attempts: 0,
    last_upload_error: null,
    server_file_id: null,
    server_url: null,
    local_uri: localUri,
    nome_arquivo: `evidencia-${index + 1}.jpg`,
    mime_type: mimeType,
    tamanho: base64Size,
    captured_at: capturedAt ?? isoNow(),
    latitude: gpsLatitude ?? undefined,
    longitude: gpsLongitude ?? undefined,
    data_captura: capturedAt ?? isoNow(),
  };
}

export async function createOfflineCadernoEvent(payload: CreateOfflineCadernoEventPayload): Promise<string> {
  const session = useSessionStore.getState().session;
  if (!session) throw new Error("Sessão não encontrada");

  const localId = newLocalId();
  const now = isoNow();
  const descricao = payload.descricao?.trim() || payload.tipo_evento.replaceAll("_", " ").toLowerCase();

  const event: CampoEventoOffline = {
    local_id: localId,
    tenant_id: session.tenant_id,
    safra_id: payload.safra_id,
    safra_nome: payload.safra_nome ?? null,
    talhao_id: payload.talhao_id ?? null,
    talhao_nome: payload.talhao_nome ?? null,
    unidade_produtiva_id: payload.unidade_produtiva_id ?? null,
    tarefa_id: payload.tarefa_id ?? null,
    operacao_id: payload.operacao_id ?? null,
    descricao,
    tipo_evento: payload.tipo_evento,
    origem_evento: "PWA_OFFLINE",
    origem_tecnica: "SYNC_PWA",
    status_evento: "PENDENTE_SINCRONIZACAO",
    client_created_at: now,
    client_updated_at: now,
    device_id: session.device_id,
    usuario_id: payload.usuario_id ?? session.user_id,
    payload_operacional: {
      ...(payload.payload_operacional ?? {}),
      descricao,
    },
    evidencias: payload.evidencias ?? [],
    sync_status: "PENDING",
    sync_attempts: 0,
    last_sync_error: null,
    synced_at: null,
    created_at: now,
    updated_at: now,
  };

  await db.caderno_events.add(event);
  await enqueueSync("CREATE", "caderno_event", localId, {
    ...event,
    // Apenas metadados das evidências vão no payload de sync do evento (sem blob)
    evidencias: event.evidencias.map(toBackendEvidence),
    payload_operacional: {
      ...event.payload_operacional,
      evidencias: event.evidencias.map(toBackendEvidence),
    },
  } as unknown as OfflineQueuePayload);

  return localId;
}

export async function retryOfflineCadernoEvent(localId: string): Promise<void> {
  const event = await db.caderno_events.get(localId);
  if (!event) return;
  if (event.server_id) {
    throw new Error("Registro já reconciliado com o servidor. O retry local foi bloqueado.");
  }
  if (event.sync_status !== "ERROR") {
    throw new Error("Retry disponível apenas para registros com erro de envio.");
  }
  if (event.status_evento === "REJEITADO" || event.status_evento === "CONSOLIDADO") {
    throw new Error("Retry bloqueado para registros oficiais rejeitados ou consolidados.");
  }
  if (event.conflict_reason) {
    throw new Error("Registro em conflito com o servidor. Revise no sistema antes de reenviar.");
  }

  const queueItem = await db.sync_queue.where("entity_id").equals(localId).and((item) => item.entity_type === "caderno_event").first();

  await db.caderno_events.update(localId, {
    sync_status: "PENDING",
    last_sync_error: null,
    conflict_reason: null,
    updated_at: isoNow(),
  });

  if (queueItem) {
    await db.sync_queue.update(queueItem.id, {
      status: "PENDING",
      last_error: undefined,
      payload: {
        ...queueItem.payload,
        evidencias: (event.evidencias ?? []).map(toBackendEvidence),
        payload_operacional: {
          ...(event.payload_operacional ?? {}),
          evidencias: (event.evidencias ?? []).map(toBackendEvidence),
        },
      },
    });
    return;
  }

  await enqueueSync("CREATE", "caderno_event", localId, {
    ...event,
    evidencias: (event.evidencias ?? []).map(toBackendEvidence),
    payload_operacional: {
      ...(event.payload_operacional ?? {}),
      evidencias: (event.evidencias ?? []).map(toBackendEvidence),
    },
  } as unknown as OfflineQueuePayload);
}

export async function markOfflineCadernoEventSyncResult(
  localId: string,
  changes: Partial<Pick<CampoEventoOffline, "server_id" | "sync_status" | "sync_attempts" | "last_sync_error" | "synced_at" | "updated_at">>
): Promise<void> {
  await db.caderno_events.update(localId, {
    ...changes,
    updated_at: isoNow(),
  });
}

// ---------------------------------------------------------------------------
// Gerenciamento de evidências individuais
// ---------------------------------------------------------------------------

/**
 * Retorna evidências pendentes de upload de um evento local.
 * Inclui evidências com status LOCAL (após evento receber server_id), PENDENTE_UPLOAD e ERRO_UPLOAD.
 */
export async function getEvidenciasPendentesUpload(
  eventLocalId: string
): Promise<Array<CadernoEvidenciaOffline & { eventLocalId: string; serverId: string }>> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento?.server_id) return [];

  const pendentes = evento.evidencias.filter(
    (ev) =>
      ev.local_uri &&
      ev.upload_status !== "ENVIADA" &&
      ev.upload_status !== "ENVIANDO" &&
      (ev.upload_attempts ?? 0) < 5
  );

  return pendentes.map((ev) => ({
    ...ev,
    eventLocalId,
    serverId: evento.server_id!,
  }));
}

/**
 * Marca evidência como ENVIANDO (início do upload).
 */
export async function markEvidenciaUploading(
  eventLocalId: string,
  localEvidenceId: string
): Promise<void> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento) return;

  await db.caderno_events.update(eventLocalId, {
    evidencias: evento.evidencias.map((ev) =>
      ev.local_evidence_id === localEvidenceId
        ? { ...ev, upload_status: "ENVIANDO" as const }
        : ev
    ),
    updated_at: isoNow(),
  });
}

/**
 * Marca evidência como ENVIADA com IDs do servidor após upload bem-sucedido.
 */
export async function markEvidenciaUploaded(
  eventLocalId: string,
  localEvidenceId: string,
  serverFileId: string,
  serverUrl: string
): Promise<void> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento) return;

  await db.caderno_events.update(eventLocalId, {
    evidencias: evento.evidencias.map((ev) =>
      ev.local_evidence_id === localEvidenceId
        ? {
            ...ev,
            upload_status: "ENVIADA" as const,
            server_file_id: serverFileId,
            server_url: serverUrl,
            last_upload_error: null,
          }
        : ev
    ),
    updated_at: isoNow(),
  });
}

/**
 * Marca evidência com erro de upload e incrementa upload_attempts.
 */
export async function markEvidenciaUploadError(
  eventLocalId: string,
  localEvidenceId: string,
  error: string
): Promise<void> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento) return;

  await db.caderno_events.update(eventLocalId, {
    evidencias: evento.evidencias.map((ev) =>
      ev.local_evidence_id === localEvidenceId
        ? {
            ...ev,
            upload_status: "ERRO_UPLOAD" as const,
            upload_attempts: (ev.upload_attempts ?? 0) + 1,
            last_upload_error: error,
          }
        : ev
    ),
    updated_at: isoNow(),
  });
}

/**
 * Recoloca evidência na fila de upload após erro.
 * Limpa o erro e permite nova tentativa se abaixo do limite.
 */
export async function retryEvidenciaUpload(
  eventLocalId: string,
  localEvidenceId: string
): Promise<void> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento) return;

  const evidencia = evento.evidencias.find((ev) => ev.local_evidence_id === localEvidenceId);
  if (!evidencia) return;

  if (evidencia.upload_status === "ENVIADA") {
    throw new Error("Evidência já enviada. Retry não necessário.");
  }

  if ((evidencia.upload_attempts ?? 0) >= 5) {
    throw new Error("Limite de tentativas atingido. Crie um novo registro para reenviar.");
  }

  await db.caderno_events.update(eventLocalId, {
    evidencias: evento.evidencias.map((ev) =>
      ev.local_evidence_id === localEvidenceId
        ? {
            ...ev,
            upload_status: "PENDENTE_UPLOAD" as const,
            last_upload_error: null,
          }
        : ev
    ),
    updated_at: isoNow(),
  });
}

/**
 * Promove evidências de LOCAL para PENDENTE_UPLOAD quando o evento recebe server_id.
 * Chamado pelo push.ts após sync bem-sucedido.
 */
export async function promoverEvidenciasParaUpload(eventLocalId: string): Promise<void> {
  const evento = await db.caderno_events.get(eventLocalId);
  if (!evento?.server_id) return;

  const temPendentes = evento.evidencias.some(
    (ev) => ev.local_uri && ev.upload_status === "LOCAL"
  );
  if (!temPendentes) return;

  await db.caderno_events.update(eventLocalId, {
    evidencias: evento.evidencias.map((ev) =>
      ev.local_uri && ev.upload_status === "LOCAL"
        ? { ...ev, upload_status: "PENDENTE_UPLOAD" as const }
        : ev
    ),
    updated_at: isoNow(),
  });
}
