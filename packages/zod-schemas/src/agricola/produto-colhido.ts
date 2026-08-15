import { z } from "zod";

export const ProdutoColhidoSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  safra_id: z.string().uuid(),
  talhao_id: z.string().uuid(),
  romaneio_id: z.string().uuid().nullable(),
  commodity_id: z.string().uuid(),
  classificacao_id: z.string().uuid().nullable(),
  qualidade_laudo_id: z.string().uuid().nullable(),
  qualidade_status: z.string().nullable(),
  quantidade: z.number(),
  unidade: z.string(),
  peso_liquido_kg: z.number(),
  peso_desconto_qualidade_kg: z.number(),
  peso_liquido_comercial_kg: z.number().nullable(),
  custo_unitario_producao: z.number().nullable().optional(),
  umidade_pct: z.number().nullable(),
  impureza_pct: z.number().nullable(),
  avariados_pct: z.number().nullable(),
  ardidos_pct: z.number().nullable(),
  quebrados_pct: z.number().nullable(),
  destino: z.string().nullable(),
  armazem_id: z.string().uuid().nullable(),
  data_entrada: z.string(),
  data_saida_prevista: z.string().nullable(),
  nf_origem: z.string().nullable(),
  observacoes: z.string().nullable(),
  status: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const ProdutoColhidoCustoAlocacaoSchema = z.object({
  id: z.string().uuid(),
  produto_colhido_id: z.string().uuid(),
  cost_allocation_id: z.string().uuid(),
  valor_atribuido: z.number(),
  percentual_atribuido: z.number(),
  origem_calculo: z.enum(["AUTOMATICO", "MANUAL"]),
  justificativa: z.string().nullable().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export const ProdutoColhidoCustoResumoSchema = z.object({
  itens: z.array(ProdutoColhidoCustoAlocacaoSchema),
  total: z.number(),
});

export const ProdutoColhidoCustoOverrideInputSchema = z.object({
  cost_allocation_id: z.string().uuid(),
  valor_atribuido: z.number(),
  justificativa: z.string().min(1, "Justificativa obrigatória"),
});

export type ProdutoColhido = z.infer<typeof ProdutoColhidoSchema>;
export type ProdutoColhidoCustoAlocacao = z.infer<typeof ProdutoColhidoCustoAlocacaoSchema>;
export type ProdutoColhidoCustoResumo = z.infer<typeof ProdutoColhidoCustoResumoSchema>;
export type ProdutoColhidoCustoOverrideInput = z.infer<typeof ProdutoColhidoCustoOverrideInputSchema>;
