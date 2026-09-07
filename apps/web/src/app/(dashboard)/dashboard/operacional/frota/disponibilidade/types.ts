export type StatusOperacional =
  | "DISPONIVEL"
  | "EM_USO"
  | "EM_MANUTENCAO"
  | "BLOQUEADO"
  | "CHECKLIST_PENDENTE"
  | "NAO_CONFORME"
  | "DOCUMENTO_VENCIDO";

export interface DisponibilidadeResumo {
  disponiveis: number;
  em_uso: number;
  em_manutencao: number;
  bloqueados: number;
  checklist_pendente: number;
  nao_conformes: number;
  documentos_vencidos: number;
}

export interface OsAberta {
  os_id: string;
  numero_os: string;
  tipo: string;
  status: string;
  data_abertura: string;
}

export interface DocumentoVencido {
  id: string;
  tipo: string;
  descricao: string | null;
  numero: string | null;
  data_vencimento: string | null;
}

export interface DisponibilidadeItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  status_operacional: StatusOperacional;
  ultimo_checklist_em: string | null;
  checklist_pendente: boolean;
  nao_conforme: boolean;
  bloqueado_manual: boolean;
  motivo_status: string | null;
  motivo_bloqueio_manual: string | null;
  os_aberta: OsAberta | null;
  documentos_vencidos: DocumentoVencido[];
  manutencao_preventiva_vencida: boolean;
}

export interface DisponibilidadeResponse {
  resumo: DisponibilidadeResumo;
  equipamentos: DisponibilidadeItem[];
}

export interface BloqueioResponse {
  equipamento_id: string;
  equipamento_nome: string;
  bloqueado_operacional: boolean;
  mensagem: string;
}
