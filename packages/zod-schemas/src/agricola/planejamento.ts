import { z } from "zod";

export const CategoriaOrcamentoSchema = z.enum([
  "SEMENTE", "FERTILIZANTE", "DEFENSIVO",
  "COMBUSTIVEL", "MAO_DE_OBRA", "SERVICO", "SEGURO", "OUTROS"
], { message: "Categoria de orçamento inválida" });

export type CategoriaOrcamento = z.infer<typeof CategoriaOrcamentoSchema>;

export const OrigemItemOrcamentoSchema = z.enum(
  ["PRODUTO", "MAQUINA", "PESSOA", "SERVICO", "MANUAL"],
  { message: "Origem de item de orçamento inválida" }
);

export type OrigemItemOrcamento = z.infer<typeof OrigemItemOrcamentoSchema>;

export const ItemOrcamentoCreateSchema = z
  .object({
    cultivo_id: z.string().uuid().nullable().optional(),
    categoria: CategoriaOrcamentoSchema,
    descricao: z.string().min(2, "A descrição deve ter pelo menos 2 caracteres").max(200, "A descrição suporta até 200 caracteres"),
    quantidade: z.number().nonnegative("A quantidade não pode ser negativa"),
    unidade: z.string().min(1, "A unidade é obrigatória").max(20),
    origem_tipo: OrigemItemOrcamentoSchema.default("MANUAL"),
    origem_id: z.string().uuid().nullable().optional(),
    custo_unitario: z.number().nonnegative("O custo unitário não pode ser negativo").nullable().optional(),
    custo_unitario_ajustado: z.number().nonnegative("O ajuste não pode ser negativo").nullable().optional(),
    ordem: z.number().int().nonnegative().optional().default(0),
    observacoes: z.string().nullable().optional(),
  })
  .refine(
    (data) => data.origem_tipo !== "MANUAL" || data.custo_unitario != null,
    { message: "Informe o custo unitário para itens de origem manual", path: ["custo_unitario"] }
  )
  .refine(
    (data) => data.origem_tipo === "MANUAL" || data.origem_id != null,
    { message: "Selecione o registro de origem (produto, máquina ou pessoa)", path: ["origem_id"] }
  );

export type ItemOrcamentoCreate = z.infer<typeof ItemOrcamentoCreateSchema>;

export const ItemOrcamentoUpdateSchema = z.object({
  cultivo_id: z.string().uuid().nullable().optional(),
  categoria: CategoriaOrcamentoSchema.nullable().optional(),
  descricao: z.string().min(2, "A descrição deve ter pelo menos 2 caracteres").max(200).nullable().optional(),
  quantidade: z.number().positive("A quantidade deve ser maior que 0").nullable().optional(),
  unidade: z.string().min(1).max(20).nullable().optional(),
  custo_unitario: z.number().positive("O custo unitário deve ser maior que 0").nullable().optional(),
  custo_unitario_ajustado: z.number().positive("O ajuste deve ser maior que 0").nullable().optional(),
  ordem: z.number().int().nonnegative().nullable().optional(),
  observacoes: z.string().nullable().optional(),
});

export type ItemOrcamentoUpdate = z.infer<typeof ItemOrcamentoUpdateSchema>;
