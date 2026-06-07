/**
 * evidence-upload.ts — Upload resiliente de evidências offline para o caderno de campo.
 *
 * Responsabilidades:
 * - Buscar todos os eventos sincronizados com evidências pendentes
 * - Para cada evidência: converter base64 para Blob e fazer POST multipart
 * - Atualizar estado local (markEvidenciaUploaded / markEvidenciaUploadError)
 * - Não bloqueia se uma evidência falhar — processa as demais
 */

import { db, type LocalSession } from "@/lib/db";
import {
  markEvidenciaUploading,
  markEvidenciaUploaded,
  markEvidenciaUploadError,
} from "@/lib/caderno-offline";

const API_BASE = "/api/v1";
const MAX_UPLOAD_ATTEMPTS = 5;

interface EvidenciaUploadResult {
  local_evidence_id: string;
  server_file_id: string;
  server_url: string;
  status: "UPLOADED" | "ALREADY_EXISTS";
}

/**
 * Converte um data URL base64 para Blob tipado.
 * Suporta "data:image/jpeg;base64,..." e "data:image/png;base64,..."
 */
function dataUrlToBlob(dataUrl: string): Blob {
  const parts = dataUrl.split(",");
  const mimeMatch = parts[0].match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
  const binary = atob(parts[1]);
  const byteArray = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    byteArray[i] = binary.charCodeAt(i);
  }
  return new Blob([byteArray], { type: mime });
}

/**
 * Faz o upload de uma evidência individual para o servidor.
 * Idempotente — o servidor retorna ALREADY_EXISTS se já foi enviada.
 */
async function uploadSingleEvidencia(
  session: LocalSession,
  serverId: string,
  localEvidenceId: string,
  localUri: string,
  options: {
    nomeArquivo?: string;
    mimeType?: string;
    tamanho?: number;
    capturedAt?: string;
    latitude?: number;
    longitude?: number;
  }
): Promise<EvidenciaUploadResult> {
  const blob = dataUrlToBlob(localUri);
  const filename = options.nomeArquivo ?? `${localEvidenceId}.jpg`;
  const effectiveMime = options.mimeType ?? blob.type ?? "image/jpeg";

  const form = new FormData();
  form.append("file", blob, filename);
  form.append("local_evidence_id", localEvidenceId);
  form.append("device_id", session.device_id);
  if (options.capturedAt) form.append("captured_at", options.capturedAt);
  if (options.latitude != null) form.append("latitude", String(options.latitude));
  if (options.longitude != null) form.append("longitude", String(options.longitude));
  form.append("mime_type", effectiveMime);
  if (options.tamanho != null) form.append("size_bytes", String(options.tamanho));

  const res = await fetch(`${API_BASE}/agricola/caderno/entradas/${serverId}/evidencias`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.device_token}`,
    },
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<EvidenciaUploadResult>;
}

/**
 * Processa o upload de todas as evidências pendentes de todos os eventos sincronizados.
 *
 * Ordem: eventos ordenados por created_at (FIFO), evidências por índice.
 * Uma falha em uma evidência não bloqueia as demais.
 *
 * @param session Sessão local do dispositivo
 */
export async function uploadEvidenciasPendentes(session: LocalSession): Promise<void> {
  // Busca eventos que já têm server_id (sincronizados) e têm evidências com blob local
  const eventosSync = await db.caderno_events
    .where("sync_status")
    .equals("SYNCED")
    .sortBy("created_at");

  const eventosComPendentes = eventosSync.filter(
    (ev) =>
      ev.server_id &&
      ev.evidencias.some(
        (e) =>
          e.local_uri &&
          e.upload_status !== "ENVIADA" &&
          e.upload_status !== "ENVIANDO" &&
          (e.upload_attempts ?? 0) < MAX_UPLOAD_ATTEMPTS
      )
  );

  if (eventosComPendentes.length === 0) return;

  for (const evento of eventosComPendentes) {
    const serverId = evento.server_id!;
    const pendentes = evento.evidencias.filter(
      (e) =>
        e.local_uri &&
        e.upload_status !== "ENVIADA" &&
        e.upload_status !== "ENVIANDO" &&
        (e.upload_attempts ?? 0) < MAX_UPLOAD_ATTEMPTS
    );

    for (const evidencia of pendentes) {
      const localEvidenceId = evidencia.local_evidence_id;

      try {
        await markEvidenciaUploading(evento.local_id, localEvidenceId);

        const result = await uploadSingleEvidencia(
          session,
          serverId,
          localEvidenceId,
          evidencia.local_uri!,
          {
            nomeArquivo: evidencia.nome_arquivo,
            mimeType: evidencia.mime_type,
            tamanho: evidencia.tamanho,
            capturedAt: evidencia.captured_at ?? evidencia.data_captura,
            latitude: evidencia.latitude,
            longitude: evidencia.longitude,
          }
        );

        await markEvidenciaUploaded(
          evento.local_id,
          localEvidenceId,
          result.server_file_id,
          result.server_url
        );
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Erro desconhecido no upload";
        await markEvidenciaUploadError(evento.local_id, localEvidenceId, errorMessage);
        // Continua com as próximas evidências — não propaga o erro
      }
    }
  }
}
