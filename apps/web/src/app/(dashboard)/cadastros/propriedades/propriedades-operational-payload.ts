import type { CreateCadastroCompletoInput, UpdateCadastroCompletoInput } from "@farm/zod-schemas";

type TipoPropriedade = "fazenda" | "sitio" | "chacara" | "arrendamento" | "parceria";

export interface OperationalCadastroPayloadInput {
  id?: string;
  nome: string;
  tipo_propriedade: TipoPropriedade;
  cpf_cnpj?: string | null;
  inscricao_estadual?: string | null;
  area_total_ha?: number;
  area_app_ha?: number;
  area_rl_ha?: number;
  cep?: string | null;
  logradouro?: string | null;
  numero?: string | null;
  complemento?: string | null;
  bairro?: string | null;
  municipio?: string | null;
  uf?: string | null;
  ibge_municipio_codigo?: string | null;
  coordenadas_sede?: string | null;
  geometria?: GeoJSON.Geometry | null;
  ativo: boolean;
}

function toNullableText(value?: string | null) {
  const normalized = value?.trim() ?? "";
  return normalized.length > 0 ? normalized : null;
}

function toOptionalPositive(value?: number) {
  return typeof value === "number" && value > 0 ? value : undefined;
}

export function buildOperationalCadastroPayload(
  input: OperationalCadastroPayloadInput,
): CreateCadastroCompletoInput | UpdateCadastroCompletoInput {
  return {
    unidade_produtiva: {
      ...(input.id ? { id: input.id } : {}),
      nome: input.nome,
      tipo_propriedade: input.tipo_propriedade,
      cpf_cnpj: toNullableText(input.cpf_cnpj),
      inscricao_estadual: toNullableText(input.inscricao_estadual),
      area_total_ha: toOptionalPositive(input.area_total_ha),
      area_app_ha: toOptionalPositive(input.area_app_ha),
      area_rl_ha: toOptionalPositive(input.area_rl_ha),
      cep: toNullableText(input.cep),
      logradouro: toNullableText(input.logradouro),
      numero: toNullableText(input.numero),
      complemento: toNullableText(input.complemento),
      bairro: toNullableText(input.bairro),
      municipio: toNullableText(input.municipio),
      uf: toNullableText(input.uf),
      ibge_municipio_codigo: toNullableText(input.ibge_municipio_codigo),
      coordenadas_sede: toNullableText(input.coordenadas_sede) ?? undefined,
      geometria: input.id && input.geometria === null ? null : (input.geometria ?? undefined),
      ativo: input.ativo,
    },
  };
}
