/**
 * Unidades de medida para o domínio rural do AgroSaaS.
 * Cobre: área, peso, volume, concentração e contagem.
 */

export const UNIDADES_AREA = ["ha", "alq", "m2", "acre"] as const;
export type UnidadeArea = (typeof UNIDADES_AREA)[number];

export const UNIDADES_PESO = ["kg", "t", "sc", "@", "g"] as const;
export type UnidadePeso = (typeof UNIDADES_PESO)[number];

export const UNIDADES_VOLUME = ["L", "mL", "m3", "cc"] as const;
export type UnidadeVolume = (typeof UNIDADES_VOLUME)[number];

export const UNIDADES_CONCENTRACAO = [
  "kg/ha",
  "L/ha",
  "sc/ha",
  "g/ha",
  "mL/ha",
  "t/ha",
  "%",
  "ppm",
] as const;
export type UnidadeConcentracao = (typeof UNIDADES_CONCENTRACAO)[number];

export const UNIDADES_INSUMO = [
  "kg",
  "t",
  "L",
  "mL",
  "sc",
  "un",
  "cx",
  "g",
] as const;
export type UnidadeInsumo = (typeof UNIDADES_INSUMO)[number];

/**
 * Símbolos para apresentação conforme ISO 80000 / SI.
 *
 * Os identificadores de persistência (por exemplo, `m2`, `m3` e `cc`) são
 * mantidos por compatibilidade com a API. Nunca os use diretamente na UI.
 */
export const UNIDADE_SIMBOLO: Record<string, string> = {
  m2: "m²",
  m3: "m³",
  cc: "cm³",
};

/** Retorna o símbolo de apresentação da unidade sem alterar seu código interno. */
export function formatUnidadeSimbolo(unidade: string): string {
  return UNIDADE_SIMBOLO[unidade] ?? unidade;
}

export const UNIDADE_LABEL: Record<string, string> = {
  ha: "Hectare (ha)",
  alq: "Alqueire",
  m2: "Metro quadrado (m²)",
  acre: "Acre",
  kg: "Quilograma (kg)",
  t: "Tonelada (t)",
  sc: "Saca (sc)",
  "@": "Arroba (@)",
  g: "Grama (g)",
  L: "Litro (L)",
  mL: "Mililitro (mL)",
  m3: "Metro cúbico (m³)",
  cc: "Centímetro cúbico (cm³)",
  "kg/ha": "Quilograma por hectare (kg ha⁻¹)",
  "L/ha": "Litro por hectare (L ha⁻¹)",
  "sc/ha": "Saca por hectare (sc ha⁻¹)",
  "g/ha": "Grama por hectare (g ha⁻¹)",
  "mL/ha": "Mililitro por hectare (mL ha⁻¹)",
  "t/ha": "Tonelada por hectare (t ha⁻¹)",
  "%": "Porcentagem (%)",
  ppm: "Partes por milhão (ppm)",
  un: "Unidade (un)",
  cx: "Caixa (cx)",
};

/** Tipos de operação agrícola */
export const TIPOS_OPERACAO_AGRICOLA = [
  "PREPARO_SOLO",
  "PLANTIO",
  "ADUBACAO",
  "PULVERIZACAO",
  "IRRIGACAO",
  "COLHEITA",
  "TRANSPORTE",
  "MANUTENCAO",
  "MONITORAMENTO",
  "OUTRO",
] as const;

export type TipoOperacaoAgricola = (typeof TIPOS_OPERACAO_AGRICOLA)[number];

export const TIPO_OPERACAO_LABEL: Record<TipoOperacaoAgricola, string> = {
  PREPARO_SOLO: "Preparo de Solo",
  PLANTIO: "Plantio",
  ADUBACAO: "Adubação",
  PULVERIZACAO: "Pulverização",
  IRRIGACAO: "Irrigação",
  COLHEITA: "Colheita",
  TRANSPORTE: "Transporte",
  MANUTENCAO: "Manutenção",
  MONITORAMENTO: "Monitoramento",
  OUTRO: "Outro",
};
