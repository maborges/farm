import { apiFetch } from "@/lib/api";
import {
  PhaseTemplate, PhaseTemplateDetail,
  OperationTemplate, OperationTemplateDetail,
  OperationTemplateItem,
} from "@/types/agro/templates";

export interface PhaseTemplatePayload {
  cultura?: string | null;
  fase: string;
  titulo: string;
  descricao?: string | null;
  ativo?: boolean;
}

export interface OperationTemplatePayload {
  cultura?: string | null;
  fase?: string | null;
  titulo: string;
  descricao?: string | null;
  ativo?: boolean;
}

export interface PhaseTemplateChecklistItemPayload {
  titulo: string;
  descricao?: string | null;
  obrigatorio?: boolean;
  ordem?: number;
  ativo?: boolean;
  tipo_resultado?: "TAREFA_CAMPO" | "SOLICITACAO_ESTOQUE" | "MANUAL";
  produto_id_padrao?: string | null;
  quantidade_minima?: number | null;
}

export interface PhaseTemplateTaskPayload {
  tipo: string;
  titulo: string;
  descricao?: string | null;
  criticidade?: string;
  ordem?: number;
}

export interface OperationTemplateItemPayload {
  tipo: string;
  titulo: string;
  descricao?: string | null;
  dose_sugerida?: number | null;
  unidade?: string | null;
  unidade_medida_id?: string | null;
  can_generate_task?: boolean;
  ordem?: number;
  dependency_ids?: string[];
}

export const templateService = {
  // Phase Templates
  listPhaseTemplates: (cultura?: string, fase?: string) => {
    const params = new URLSearchParams();
    if (cultura) params.append("cultura", cultura);
    if (fase) params.append("fase", fase);
    return apiFetch<PhaseTemplate[]>(`/templates/phase?${params.toString()}`);
  },

  getPhaseTemplate: (id: string) =>
    apiFetch<PhaseTemplateDetail>(`/templates/phase/${id}`),

  createPhaseTemplate: (dados: PhaseTemplatePayload) =>
    apiFetch<PhaseTemplate>(`/templates/phase`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  updatePhaseTemplate: (id: string, dados: Partial<PhaseTemplatePayload>) =>
    apiFetch<PhaseTemplate>(`/templates/phase/${id}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    }),

  deletePhaseTemplate: (id: string) =>
    apiFetch(`/templates/phase/${id}`, { method: "DELETE" }),

  applyPhaseTemplate: (safraId: string, phaseTemplateId: string) =>
    apiFetch(`/templates/apply/phase`, {
      method: "POST",
      body: JSON.stringify({ safra_id: safraId, phase_template_id: phaseTemplateId }),
    }),

  duplicatePhaseTemplate: (id: string) =>
    apiFetch<PhaseTemplate>(`/templates/phase/${id}/duplicate`, {
      method: "POST",
    }),

  createPhaseChecklistItem: (templateId: string, dados: PhaseTemplateChecklistItemPayload) =>
    apiFetch(`/templates/phase/${templateId}/checklist-items`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  updatePhaseChecklistItem: (templateId: string, itemId: string, dados: Partial<PhaseTemplateChecklistItemPayload>) =>
    apiFetch(`/templates/phase/${templateId}/checklist-items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    }),

  deletePhaseChecklistItem: (templateId: string, itemId: string) =>
    apiFetch(`/templates/phase/${templateId}/checklist-items/${itemId}`, { method: "DELETE" }),

  createPhaseTask: (templateId: string, dados: PhaseTemplateTaskPayload) =>
    apiFetch(`/templates/phase/${templateId}/tasks`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  updatePhaseTask: (templateId: string, taskId: string, dados: Partial<PhaseTemplateTaskPayload>) =>
    apiFetch(`/templates/phase/${templateId}/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    }),

  deletePhaseTask: (templateId: string, taskId: string) =>
    apiFetch(`/templates/phase/${templateId}/tasks/${taskId}`, { method: "DELETE" }),

  // Operation Templates
  listOperationTemplates: (cultura?: string, fase?: string) => {
    const params = new URLSearchParams();
    if (cultura) params.append("cultura", cultura);
    if (fase) params.append("fase", fase);
    return apiFetch<OperationTemplate[]>(`/templates/operations?${params.toString()}`);
  },

  getOperationTemplate: (id: string) =>
    apiFetch<OperationTemplateDetail>(`/templates/operations/${id}`),

  createOperationTemplate: (dados: OperationTemplatePayload) =>
    apiFetch<OperationTemplate>(`/templates/operations`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  updateOperationTemplate: (id: string, dados: Partial<OperationTemplatePayload>) =>
    apiFetch<OperationTemplate>(`/templates/operations/${id}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    }),

  deleteOperationTemplate: (id: string) =>
    apiFetch(`/templates/operations/${id}`, { method: "DELETE" }),

  duplicateOperationTemplate: (id: string) =>
    apiFetch<OperationTemplate>(`/templates/operations/${id}/duplicate`, {
      method: "POST",
    }),

  createOperationTemplateItem: (templateId: string, dados: OperationTemplateItemPayload) =>
    apiFetch<OperationTemplateItem>(`/templates/operations/${templateId}/items`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  updateOperationTemplateItem: (templateId: string, itemId: string, dados: Partial<OperationTemplateItemPayload>) =>
    apiFetch<OperationTemplateItem>(`/templates/operations/${templateId}/items/${itemId}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    }),

  deleteOperationTemplateItem: (templateId: string, itemId: string) =>
    apiFetch(`/templates/operations/${templateId}/items/${itemId}`, { method: "DELETE" }),

  applyOperationTemplate: (safraId: string, operationTemplateId: string, talhaoIds: string[]) =>
    apiFetch(`/templates/apply/operations`, {
      method: "POST",
      body: JSON.stringify({
        safra_id: safraId,
        operation_template_id: operationTemplateId,
        talhao_ids: talhaoIds
      }),
    }),
};
