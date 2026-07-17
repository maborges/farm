// Schemas de validação para UnidadeProdutiva e cadastro completo em blocos.

import { z } from "zod";

export const createUnidadeProdutivaBaseSchema = z.object({
    nome: z.string().min(2, "Nome deve ter pelo menos 2 caracteres").max(150, "Nome muito longo"),
    tipo_propriedade: z.enum(["fazenda", "sitio", "chacara", "arrendamento", "parceria"]).default("fazenda"),
    cpf_cnpj: z.string().max(18, "CPF/CNPJ inválido").optional().nullable().or(z.literal("")),
    inscricao_estadual: z.string().max(50).optional().nullable().or(z.literal("")),
    area_total_ha: z.coerce.number().gt(0, "Área deve ser maior que zero").optional().or(z.literal(0)),
    area_app_ha: z.coerce.number().gte(0).optional().or(z.literal(0)),
    area_rl_ha: z.coerce.number().gte(0).optional().or(z.literal(0)),
    coordenadas_sede: z.string().max(100, "Coordenadas inválidas").optional().nullable().or(z.literal("")),
    geometria: z.any().optional().nullable(),
    ativo: z.boolean().default(true),
    cep: z.string().max(9).optional().nullable().or(z.literal("")),
    logradouro: z.string().max(255).optional().nullable().or(z.literal("")),
    numero: z.string().max(20, "Número muito longo").optional().nullable().or(z.literal("")),
    complemento: z.string().max(100, "Complemento muito longo").optional().nullable().or(z.literal("")),
    bairro: z.string().max(100).optional().nullable().or(z.literal("")),
    municipio: z.string().max(100).optional().nullable().or(z.literal("")),
    uf: z.string().max(2).optional().nullable().or(z.literal("")),
    ibge_municipio_codigo: z.string().max(7).optional().nullable().or(z.literal("")),
});

export const createPropriedadeCadastroSchema = z.object({
    id: z.string().uuid().optional(),
    nome: z.string().min(2, "Nome deve ter pelo menos 2 caracteres").max(200).optional(),
    cpf_cnpj: z.string().max(18).optional().nullable(),
    inscricao_estadual: z.string().max(50).optional().nullable(),
    ie_isento: z.boolean().optional().nullable(),
    email: z.string().max(200).optional().nullable(),
    telefone: z.string().max(30).optional().nullable(),
    nome_fantasia: z.string().max(200).optional().nullable(),
    regime_tributario: z.string().max(30).optional().nullable(),
    cor: z.string().max(7).optional().nullable(),
    icone: z.string().max(50).optional().nullable(),
    ordem: z.number().int().optional().nullable(),
    ativo: z.boolean().optional().nullable(),
    observacoes: z.string().optional().nullable(),
});

export const createExploracaoRuralCadastroSchema = z.object({
    id: z.string().uuid().optional(),
    natureza: z.string().optional().nullable(),
    data_inicio: z.coerce.date().optional().nullable(),
    data_fim: z.coerce.date().optional().nullable(),
    numero_contrato: z.string().max(100).optional().nullable(),
    valor_anual: z.coerce.number().gt(0).optional().nullable(),
    percentual_producao: z.coerce.number().gt(0).lte(100).optional().nullable(),
    area_explorada_ha: z.coerce.number().gt(0).optional().nullable(),
    observacoes: z.string().optional().nullable(),
});

export const createImovelRuralCadastroSchema = z.object({
    id: z.string().uuid().optional(),
    nome: z.string().max(255).optional().nullable(),
    municipio: z.string().max(100).optional().nullable(),
    uf: z.string().min(2).max(2).optional().nullable(),
    area_total_ha: z.coerce.number().gt(0).optional().nullable(),
    nirf: z.string().max(20).optional().nullable(),
    car_numero: z.string().max(50).optional().nullable(),
    codigo_car: z.string().max(50).optional().nullable(),
    ccir_numero: z.string().max(50).optional().nullable(),
    ccir: z.string().max(50).optional().nullable(),
    cartorio_id: z.string().uuid().optional().nullable(),
    numero_matricula: z.string().max(100).optional().nullable(),
    motivo_alteracao_area: z.string().optional().nullable(),
    tipo: z.string().optional().nullable(),
    observacao: z.string().optional().nullable(),
});

export const createPropriedadeImovelCadastroSchema = z.object({
    id: z.string().uuid().optional(),
    tipo_vinculo: z.enum(["PRINCIPAL", "SECUNDARIO"]).optional().nullable(),
    ativo: z.boolean().optional().nullable(),
    data_inicio: z.coerce.date().optional().nullable(),
    data_fim: z.coerce.date().optional().nullable(),
    origem_documental: z.string().min(1).optional().nullable(),
    observacoes: z.string().optional().nullable(),
    area_vinculada: z.coerce.number().optional().nullable(),
    percentual_vinculado: z.coerce.number().optional().nullable(),
    vinculo_principal: z.boolean().optional().nullable(),
    origem_referencia: z.string().optional().nullable(),
    status_documental: z.string().optional().nullable(),
});

export const createCadastroCompletoSchema = z.object({
    unidade_produtiva: createUnidadeProdutivaBaseSchema,
    propriedade: createPropriedadeCadastroSchema.optional().nullable(),
    exploracao_rural: createExploracaoRuralCadastroSchema.optional().nullable(),
    imovel_rural: createImovelRuralCadastroSchema.optional().nullable(),
    propriedade_imovel: createPropriedadeImovelCadastroSchema.optional().nullable(),
});

export const updateCadastroCompletoSchema = createCadastroCompletoSchema.partial();

export type CreateCadastroCompletoInput = z.infer<typeof createCadastroCompletoSchema>;
export type UpdateCadastroCompletoInput = z.infer<typeof updateCadastroCompletoSchema>;

export const createUnidadeProdutivaSchema = createUnidadeProdutivaBaseSchema;
export const updateUnidadeProdutivaSchema = createUnidadeProdutivaBaseSchema.partial();
export type CreateUnidadeProdutivaInput = z.infer<typeof createUnidadeProdutivaSchema>;
export type UpdateUnidadeProdutivaInput = z.infer<typeof updateUnidadeProdutivaSchema>;

export const createFazendaSchema = createUnidadeProdutivaSchema;
export const updateFazendaSchema = updateUnidadeProdutivaSchema;
export type CreateFazendaInput = CreateUnidadeProdutivaInput;
export type UpdateFazendaInput = UpdateUnidadeProdutivaInput;
