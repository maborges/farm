import { z } from "zod";

export const StatusDevolucaoEmbalagemSchema = z.enum(["PENDENTE", "DEVOLVIDO", "VENCIDO"]);

export const DevolucaoEmbalagemSchema = z.object({
  id: z.string().uuid(),
  item_recebimento_id: z.string().uuid(),
  produto_id: z.string().uuid(),
  quantidade_embalagens_compradas: z.number().int(),
  quantidade_embalagens_devolvidas: z.number().int(),
  data_compra: z.string(),
  prazo_limite: z.string(),
  destino_pessoa_id: z.string().uuid().nullable(),
  status: StatusDevolucaoEmbalagemSchema,
  comprovante_pdf_url: z.string().nullable(),
  observacoes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const RegistrarDevolucaoSchema = z.object({
  quantidade_embalagens: z.number().int().positive(),
  destino_pessoa_id: z.string().uuid().optional().nullable(),
  observacoes: z.string().max(2000).optional().nullable(),
});

export type StatusDevolucaoEmbalagem = z.infer<typeof StatusDevolucaoEmbalagemSchema>;
export type DevolucaoEmbalagem = z.infer<typeof DevolucaoEmbalagemSchema>;
export type RegistrarDevolucao = z.infer<typeof RegistrarDevolucaoSchema>;
