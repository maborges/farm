"use client";

import type { SessionClearNotice } from "@/lib/stores/session-store";

const REASON_LABEL: Record<SessionClearNotice["reason"], string> = {
  DEVICE_REVOKED: "O dispositivo foi revogado pelo administrador.",
  SESSION_INVALID: "A sessão local não era mais válida.",
  TENANT_CHANGED: "Este dispositivo foi ativado para outra organização.",
  USER_CHANGED: "Este dispositivo foi ativado para outro usuário.",
  MANUAL_LOGOUT: "Você saiu da sessão anterior.",
};

export function CampoSessionClearNotice({ notice }: { notice: SessionClearNotice }) {
  const { summary } = notice;

  return (
    <div className="mb-4 rounded-[20px] border border-amber-200/80 bg-amber-50/92 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
      <p className="font-medium">Dados locais pendentes foram removidos</p>
      <p className="mt-1 text-xs leading-4">
        {REASON_LABEL[notice.reason]} Havia registros ainda não sincronizados neste dispositivo
        e eles foram apagados para proteger o isolamento entre organizações.
      </p>
      <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs">
        {summary.syncQueue > 0 && <li>{summary.syncQueue} item(ns) na fila de sincronização</li>}
        {summary.tasks > 0 && <li>{summary.tasks} tarefa(s) local(is) não sincronizada(s)</li>}
        {summary.cadernoEvents > 0 && <li>{summary.cadernoEvents} evento(s) de caderno pendente(s)</li>}
        {summary.cadernoDrafts > 0 && <li>{summary.cadernoDrafts} rascunho(s) não salvo(s)</li>}
      </ul>
      <p className="mt-2 text-xs leading-4">
        Se precisar recuperar essa operação, contate o administrador ou o suporte.
      </p>
    </div>
  );
}
