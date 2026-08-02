import { z } from "zod";

export const SAFRA_FASES = [
  "PLANEJAMENTO",
  "PLANEJADA",
  "PREPARO_SOLO",
  "PLANTIO",
  "DESENVOLVIMENTO",
  "COLHEITA",
  "POS_COLHEITA",
  "ENCERRADA",
] as const;
export const SafraFaseSchema = z.enum(SAFRA_FASES);
export type SafraFase = z.infer<typeof SafraFaseSchema>;

export const PhaseTemplateCreateSchema = z.object({
  cultura: z.string().max(50).nullable().optional(),
  fase: SafraFaseSchema,
  titulo: z.string().min(2, "Título deve ter pelo menos 2 caracteres").max(200),
  descricao: z.string().nullable().optional(),
  ativo: z.boolean().optional().default(true),
});
export type PhaseTemplateCreate = z.infer<typeof PhaseTemplateCreateSchema>;

export const PhaseTemplateUpdateSchema = PhaseTemplateCreateSchema.partial();
export type PhaseTemplateUpdate = z.infer<typeof PhaseTemplateUpdateSchema>;

export const OperationTemplateCreateSchema = z.object({
  cultura: z.string().max(50).nullable().optional(),
  fase: SafraFaseSchema.nullable().optional(),
  titulo: z.string().min(2, "Título deve ter pelo menos 2 caracteres").max(200),
  descricao: z.string().nullable().optional(),
  ativo: z.boolean().optional().default(true),
});
export type OperationTemplateCreate = z.infer<typeof OperationTemplateCreateSchema>;

export const OperationTemplateUpdateSchema = OperationTemplateCreateSchema.partial();
export type OperationTemplateUpdate = z.infer<typeof OperationTemplateUpdateSchema>;

export const OperationTemplateItemCreateSchema = z.object({
  tipo: z.string().min(1, "Tipo é obrigatório").max(30),
  titulo: z.string().min(2, "Título deve ter pelo menos 2 caracteres").max(200),
  descricao: z.string().nullable().optional(),
  dose_sugerida: z.number().nonnegative("A dose não pode ser negativa").nullable().optional(),
  unidade: z.string().max(20).nullable().optional(),
  unidade_medida_id: z.string().uuid().nullable().optional(),
  can_generate_task: z.boolean().optional().default(true),
  ordem: z.number().int().nonnegative().optional().default(0),
  dependency_ids: z.array(z.string().uuid()).optional().default([]),
});
export type OperationTemplateItemCreate = z.infer<typeof OperationTemplateItemCreateSchema>;

export const OperationTemplateItemUpdateSchema = OperationTemplateItemCreateSchema.partial();
export type OperationTemplateItemUpdate = z.infer<typeof OperationTemplateItemUpdateSchema>;
