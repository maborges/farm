export type WizardStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "PAUSED"
  | "BLOCKED"
  | "READY_FOR_GO_LIVE"
  | "GO_LIVE"
  | "STABILIZATION"
  | "COMPLETED"
  | "CANCELLED";

export type WizardStageStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "SKIPPED"
  | "BLOCKED";

export type WizardChecklistStatus =
  | "PENDENTE"
  | "ATENDIDO"
  | "DISPENSADO"
  | "FALHOU";

export type WizardChecklistSeverity = "INFO" | "ATENCAO" | "CRITICO";

export type WizardPendenciaSeverity = "BAIXA" | "MEDIA" | "ALTA" | "CRITICA";

export type WizardPendenciaStatus =
  | "ABERTA"
  | "EM_TRATAMENTO"
  | "RESOLVIDA"
  | "DESCARTADA";

export interface WizardResumo {
  implantacao_id: string;
  status: WizardStatus;
  etapa_atual: string;
  percentual_progresso: number;
  checklist_minimo_percentual: number;
  modo_implantacao: string;
  origem: string;
  unidade_produtiva_id: string | null;
  escopo_modulos: Record<string, unknown> | null;
  diagnostico_inicial_snapshot: Record<string, unknown> | null;
  pendencias_criticas_abertas: number;
  checklist_minimo_satisfeito: boolean;
  elegivel_para_pronto_go_live: boolean;
  elegivel_para_go_live: boolean;
  motivos_bloqueio: string[];
  itens_checklist_faltantes: Array<{
    codigo_item: string;
    descricao: string;
    acao_recomendada: string | null;
    acao_label: string | null;
    acao_link: string | null;
    obrigatorio: boolean;
    status: string;
    severidade: WizardChecklistSeverity;
  }>;
  pendencias_criticas: Array<{
    id: string;
    titulo: string;
    descricao: string;
    status: WizardPendenciaStatus;
    severidade: WizardPendenciaSeverity;
  }>;
}

export interface WizardEtapa {
  id: string;
  implantacao_id: string;
  codigo_etapa: string;
  nome: string;
  status: WizardStageStatus;
  obrigatoria: boolean;
  ordem: number;
  percentual_peso: number;
  started_at: string | null;
  completed_at: string | null;
  skipped_at: string | null;
  blocked_at: string | null;
  dados_snapshot: Record<string, unknown> | null;
  observacoes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WizardChecklistItem {
  id: string;
  implantacao_id: string;
  etapa_id: string | null;
  codigo_item: string;
  descricao: string;
  acao_recomendada: string | null;
  acao_label: string | null;
  acao_link: string | null;
  obrigatorio: boolean;
  status: WizardChecklistStatus;
  severidade: WizardChecklistSeverity;
  evidencia_tipo: string;
  evidencia_ref_id: string | null;
  checked_by_usuario_id: string | null;
  checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WizardChecklist {
  implantacao_id: string;
  checklist_minimo_satisfeito: boolean;
  pendencias_criticas_abertas: number;
  itens: WizardChecklistItem[];
}

export interface WizardPendencia {
  id: string;
  implantacao_id: string;
  etapa_id: string | null;
  tipo: string;
  severidade: WizardPendenciaSeverity;
  status: WizardPendenciaStatus;
  titulo: string;
  descricao: string;
  responsavel_usuario_id: string | null;
  due_date: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WizardIniciarPayload {
  unidade_produtiva_id?: string | null;
  modo_implantacao?: string;
  origem?: string;
  escopo_modulos?: Record<string, unknown> | null;
  diagnostico_inicial_snapshot?: Record<string, unknown> | null;
}

export interface WizardActionPayload {
  motivo?: string | null;
  payload_snapshot?: Record<string, unknown> | null;
}
