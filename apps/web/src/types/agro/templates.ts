export interface PhaseTemplate {
  id: string;
  tenant_id?: string;
  cultura?: string;
  fase: string;
  titulo: string;
  descricao?: string;
  ativo: boolean;
  is_system_default: boolean;
}

export interface PhaseTemplateChecklistItem {
  id: string;
  titulo: string;
  descricao?: string;
  obrigatorio: boolean;
  ordem: number;
  ativo: boolean;
  tipo_resultado: "TAREFA_CAMPO" | "SOLICITACAO_ESTOQUE" | "MANUAL";
  produto_id_padrao?: string | null;
  quantidade_minima?: number | null;
}

export interface PhaseTemplateTask {
  id: string;
  tipo: string;
  titulo: string;
  descricao?: string;
  criticidade: 'BAIXA' | 'MEDIA' | 'ALTA' | 'URGENTE';
  ordem: number;
}

export interface PhaseTemplateDetail extends PhaseTemplate {
  checklist_items: PhaseTemplateChecklistItem[];
  tasks: PhaseTemplateTask[];
}

export interface OperationTemplate {
  id: string;
  tenant_id?: string;
  cultura?: string;
  fase?: string;
  titulo: string;
  descricao?: string;
  ativo: boolean;
  is_system_default: boolean;
}

export interface OperationTemplateItem {
  id: string;
  operation_template_id: string;
  tipo: string;
  titulo: string;
  descricao?: string;
  dose_sugerida?: number;
  unidade?: string;
  unidade_medida_id?: string | null;
  can_generate_task: boolean;
  ordem: number;
}

export interface OperationTemplateDetail extends OperationTemplate {
  items: OperationTemplateItem[];
}
