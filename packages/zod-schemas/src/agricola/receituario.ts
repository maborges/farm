import { z } from "zod";

export const StatusReceituarioSchema = z.enum(["RASCUNHO", "EMITIDO", "VENCIDO", "CANCELADO"]);

export const ReceituarioItemCreateSchema = z.object({
  produto_id: z.string().uuid(),
  dose: z.number().positive(),
  unidade_dose: z.string().min(1),
  cultura: z.string().optional().nullable(),
  praga_alvo: z.string().optional().nullable(),
});

export const ReceituarioItemSchema = ReceituarioItemCreateSchema.extend({
  id: z.string().uuid(),
  carencia_dias: z.number().int().optional().nullable(),
});

export const ReceituarioAgronomicoCreateSchema = z.object({
  numero: z.string().max(50).optional().nullable(),
  agronomo_pessoa_id: z.string().uuid(),
  unidade_produtiva_id: z.string().uuid(),
  safra_id: z.string().uuid().optional().nullable(),
  talhao_id: z.string().uuid().optional().nullable(),
  operacao_agricola_id: z.string().uuid().optional().nullable(),
  cultura: z.string().optional().nullable(),
  praga_alvo: z.string().optional().nullable(),
  data_emissao: z.string().date(),
  validade_dias: z.number().int().positive().default(90),
  observacoes: z.string().max(2000).optional().nullable(),
  itens: z.array(ReceituarioItemCreateSchema).min(1),
});

export const ReceituarioAgronomicoUpdateSchema = z.object({
  cultura: z.string().optional().nullable(),
  praga_alvo: z.string().optional().nullable(),
  observacoes: z.string().max(2000).optional().nullable(),
  itens: z.array(ReceituarioItemCreateSchema).optional().nullable(),
});

export const ReceituarioAgronomicoSchema = z.object({
  id: z.string().uuid(),
  numero: z.string().nullable(),
  agronomo_pessoa_id: z.string().uuid(),
  crea_numero: z.string(),
  crea_uf: z.string(),
  unidade_produtiva_id: z.string().uuid(),
  safra_id: z.string().uuid().nullable(),
  talhao_id: z.string().uuid().nullable(),
  operacao_agricola_id: z.string().uuid().nullable(),
  cultura: z.string().nullable(),
  praga_alvo: z.string().nullable(),
  data_emissao: z.string(),
  data_validade: z.string(),
  status: StatusReceituarioSchema,
  arquivo_pdf_url: z.string().nullable(),
  observacoes: z.string().nullable(),
  motivo_cancelamento: z.string().nullable(),
  itens: z.array(ReceituarioItemSchema).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

export type StatusReceituario = z.infer<typeof StatusReceituarioSchema>;
export type ReceituarioItem = z.infer<typeof ReceituarioItemSchema>;
export type ReceituarioItemCreate = z.infer<typeof ReceituarioItemCreateSchema>;
export type ReceituarioAgronomico = z.infer<typeof ReceituarioAgronomicoSchema>;
export type ReceituarioAgronomicoCreate = z.infer<typeof ReceituarioAgronomicoCreateSchema>;
export type ReceituarioAgronomicoUpdate = z.infer<typeof ReceituarioAgronomicoUpdateSchema>;
