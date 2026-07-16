// packages/zod-schemas/src/fazenda-schemas.ts
// Schemas de validação para UnidadeProdutiva (ex-Fazenda)

import { z } from "zod";

export const createUnidadeProdutivaBaseSchema = z.object({
    nome: z.string().min(2, "Nome deve ter pelo menos 2 caracteres").max(150, "Nome muito longo"),
    tipo_propriedade: z.enum(["fazenda", "sitio", "chacara", "arrendamento", "parceria"]).default("fazenda"),
    cpf_cnpj: z.string().max(18, "CPF/CNPJ inválido").optional().or(z.literal("")),
    inscricao_estadual: z.string().max(50).optional().or(z.literal("")),
    grupo_id: z.string().uuid("Grupo inválido").optional().nullable().or(z.literal("")),
    area_total_ha: z.coerce.number().gt(0, "Área deve ser maior que zero").optional().or(z.literal(0)),
    area_app_ha: z.coerce.number().gte(0).optional().or(z.literal(0)),
    area_rl_ha: z.coerce.number().gte(0).optional().or(z.literal(0)),
    coordenadas_sede: z.string().max(100, "Coordenadas inválidas").optional().or(z.literal("")),
    geometria: z.any().optional().nullable(),
    ativo: z.boolean().default(true),
    cep: z.string().max(9).optional().or(z.literal("")),
    logradouro: z.string().max(255).optional().or(z.literal("")),
    numero: z.string().max(20, "Número muito longo").optional().or(z.literal("")),
    complemento: z.string().max(100, "Complemento muito longo").optional().or(z.literal("")),
    bairro: z.string().max(100).optional().or(z.literal("")),
    municipio: z.string().max(100).optional().or(z.literal("")),
    uf: z.string().max(2).optional().or(z.literal("")),
    ibge_municipio_codigo: z.string().max(7).optional().or(z.literal("")),
});

export const createImovelRuralBaseSchema = z.object({
    codigo_car: z.string().max(80).optional().or(z.literal("")),
    nirf: z.string().max(20).optional().or(z.literal("")),
    ccir: z.string().max(30).optional().or(z.literal("")),
    sigef_codigo: z.string().max(50).optional().or(z.literal("")),
    numero_matricula: z.string().max(100).optional().or(z.literal("")),
});

export const createCadastroCompletoSchema = createUnidadeProdutivaBaseSchema.merge(createImovelRuralBaseSchema).extend({
    // Permite que o frontend passe IDs conhecidos durante edição para não perder a referência
    propriedade_id: z.string().uuid().optional(),
    imovel_rural_id: z.string().uuid().optional(),
    propriedade_imovel_id: z.string().uuid().optional(),
});
export const updateCadastroCompletoSchema = createCadastroCompletoSchema.partial();

export type CreateCadastroCompletoInput = z.infer<typeof createCadastroCompletoSchema>;
export type UpdateCadastroCompletoInput = z.infer<typeof updateCadastroCompletoSchema>;

// Aliases temporários mantidos para retrocompatibilidade do formulário atual durante a transição
export const createUnidadeProdutivaSchema = createCadastroCompletoSchema;
export const updateUnidadeProdutivaSchema = updateCadastroCompletoSchema;
export type CreateUnidadeProdutivaInput = z.infer<typeof createUnidadeProdutivaSchema>;
export type UpdateUnidadeProdutivaInput = z.infer<typeof updateUnidadeProdutivaSchema>;

export const createFazendaSchema = createUnidadeProdutivaSchema;
export const updateFazendaSchema = updateUnidadeProdutivaSchema;
export type CreateFazendaInput = CreateUnidadeProdutivaInput;
export type UpdateFazendaInput = UpdateUnidadeProdutivaInput;
