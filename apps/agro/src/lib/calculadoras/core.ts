/**
 * Camada Matemática Pura para Calculadoras Agrícolas do DeepFarms Agro.
 *
 * Funções determinísticas e livres de efeitos colaterais.
 * Nenhuma dependência de React, DOM, APIs ou armazenamento.
 */

// ── 1. CALCULADORA DE SACAS, QUILOGRAMAS E TONELADAS ──────────────────────────

export type UnidadeMassaAgricola = "SACAS" | "QUILOGRAMAS" | "TONELADAS";

export interface ConversaoMassaInput {
  valor: number;
  unidadeOrigem: UnidadeMassaAgricola;
  kgPorSaca?: number; // Padrão: 60 kg (grãos) ou configurável (ex: 50 kg café/feijão)
}

export interface ConversaoMassaResultado {
  sacas: number;
  quilogramas: number;
  toneladas: number;
  kgPorSaca: number;
}

export function converterSacasKgToneladas(input: ConversaoMassaInput): ConversaoMassaResultado {
  const { valor, unidadeOrigem, kgPorSaca = 60 } = input;

  if (kgPorSaca <= 0 || !Number.isFinite(kgPorSaca)) {
    throw new Error("A massa por saca deve ser um valor numérico positivo maior que zero.");
  }

  if (valor < 0 || !Number.isFinite(valor)) {
    throw new Error("O valor de massa não pode ser negativo ou inválido.");
  }

  if (valor === 0) {
    return { sacas: 0, quilogramas: 0, toneladas: 0, kgPorSaca };
  }

  let quilogramas = 0;

  switch (unidadeOrigem) {
    case "SACAS":
      quilogramas = valor * kgPorSaca;
      break;
    case "QUILOGRAMAS":
      quilogramas = valor;
      break;
    case "TONELADAS":
      quilogramas = valor * 1000;
      break;
    default:
      throw new Error(`Unidade de origem desconhecida: ${unidadeOrigem as string}`);
  }

  const sacas = quilogramas / kgPorSaca;
  const toneladas = quilogramas / 1000;

  return {
    sacas,
    quilogramas,
    toneladas,
    kgPorSaca,
  };
}

// ── 2. CALCULADORA DE CONVERSÃO DE ÁREAS RURAIS ───────────────────────────────

export type UnidadeAreaRural =
  | "METROS_QUADRADOS"
  | "HECTARES"
  | "ALQUEIRE_PAULISTA"
  | "ALQUEIRE_MINEIRO"
  | "ALQUEIRE_NORTE"
  | "ALQUEIRE_BAIANO";

/**
 * Fatores de conversão para Metros Quadrados (m²).
 * Fontes oficiais / Legislação agrária e cartografia tradicional brasileira (IBGE / INCRA):
 *
 * 1 braça linear = 2,20 metros (10 palmos de 0,22 m).
 * 1 braça quadrada = 2,20 m × 2,20 m = 4,84 m².
 *
 * - Hectare: 10.000 m² (Sistema Internacional - SI / Inmetro).
 * - Alqueire Paulista: 5.000 braças quadradas = 5.000 × 4,84 m² = 24.200 m² (2,42 ha).
 * - Alqueire Mineiro / Goiano: 10.000 braças quadradas (quadrado de 100×100 braças de lado = 220 m × 220 m) = 48.400 m² (4,84 ha).
 * - Alqueire do Norte: 5.625 braças quadradas (quadrado de 75×75 braças de lado = 165 m × 165 m) = 27.225 m² (2,7225 ha).
 *   Padrão dominante na Amazônia Legal e estados do Norte (PA, TO, RO, AC, AM).
 * - Alqueire Baiano / do Norte Pequeno: 2.500 braças quadradas (quadrado de 50×50 braças de lado = 110 m × 110 m) = 12.100 m² (1,21 ha).
 *   Utilizado na Bahia e áreas do Maranhão e Piauí.
 */
export const FATORES_AREA_M2: Record<UnidadeAreaRural, number> = {
  METROS_QUADRADOS: 1,
  HECTARES: 10000,
  ALQUEIRE_PAULISTA: 24200,
  ALQUEIRE_MINEIRO: 48400,
  ALQUEIRE_NORTE: 27225,
  ALQUEIRE_BAIANO: 12100,
};

export interface ConversaoAreaInput {
  valor: number;
  unidadeOrigem: UnidadeAreaRural;
}

export interface ConversaoAreaResultado {
  metrosQuadrados: number;
  hectares: number;
  alqueiresPaulistas: number;
  alqueiresMineiros: number;
  alqueiresNorte: number;
  alqueiresBaianos: number;
  unidadeOrigem: UnidadeAreaRural;
}

export function converterAreaRural(input: ConversaoAreaInput): ConversaoAreaResultado {
  const { valor, unidadeOrigem } = input;

  if (valor < 0 || !Number.isFinite(valor)) {
    throw new Error("O valor de área não pode ser negativo ou inválido.");
  }

  const fator = FATORES_AREA_M2[unidadeOrigem];
  if (!fator) {
    throw new Error(`Unidade de área desconhecida: ${unidadeOrigem as string}`);
  }

  if (valor === 0) {
    return {
      metrosQuadrados: 0,
      hectares: 0,
      alqueiresPaulistas: 0,
      alqueiresMineiros: 0,
      alqueiresNorte: 0,
      alqueiresBaianos: 0,
      unidadeOrigem,
    };
  }

  const metrosQuadrados = valor * fator;

  return {
    metrosQuadrados,
    hectares: metrosQuadrados / FATORES_AREA_M2.HECTARES,
    alqueiresPaulistas: metrosQuadrados / FATORES_AREA_M2.ALQUEIRE_PAULISTA,
    alqueiresMineiros: metrosQuadrados / FATORES_AREA_M2.ALQUEIRE_MINEIRO,
    alqueiresNorte: metrosQuadrados / FATORES_AREA_M2.ALQUEIRE_NORTE,
    alqueiresBaianos: metrosQuadrados / FATORES_AREA_M2.ALQUEIRE_BAIANO,
    unidadeOrigem,
  };
}

// ── 3. ESTIMATIVA DE FRETE AGRÍCOLA ───────────────────────────────────────────

export type TipoTarifaFrete = "POR_TONELADA" | "POR_SACA";

export interface FreteAgricolaInput {
  quantidade: number;
  unidadeQuantidade: UnidadeMassaAgricola;
  valorTarifa: number;
  tipoTarifa: TipoTarifaFrete;
  kgPorSaca?: number; // Padrão: 60 kg
  custosAdicionais?: number; // Pedágio, taxas, seguro, etc.
}

export interface FreteAgricolaResultado {
  massaToneladas: number;
  totalSacas: number;
  massaKg: number;
  freteBase: number;
  custosAdicionais: number;
  totalFrete: number;
  custoEfetivoPorTonelada: number;
  custoEfetivoPorSaca: number;
}

export function calcularFreteAgricola(input: FreteAgricolaInput): FreteAgricolaResultado {
  const {
    quantidade,
    unidadeQuantidade,
    valorTarifa,
    tipoTarifa,
    kgPorSaca = 60,
    custosAdicionais = 0,
  } = input;

  if (quantidade <= 0 || !Number.isFinite(quantidade)) {
    throw new Error("A quantidade transportada deve ser maior que zero.");
  }

  if (valorTarifa <= 0 || !Number.isFinite(valorTarifa)) {
    throw new Error("O valor da tarifa de frete deve ser maior que zero.");
  }

  if (custosAdicionais < 0 || !Number.isFinite(custosAdicionais)) {
    throw new Error("Custos adicionais não podem ser negativos.");
  }

  if (kgPorSaca <= 0 || !Number.isFinite(kgPorSaca)) {
    throw new Error("A massa por saca deve ser maior que zero.");
  }

  // Normalização de massa sem arredondamento intermediário
  let massaKg = 0;
  switch (unidadeQuantidade) {
    case "TONELADAS":
      massaKg = quantidade * 1000;
      break;
    case "SACAS":
      massaKg = quantidade * kgPorSaca;
      break;
    case "QUILOGRAMAS":
      massaKg = quantidade;
      break;
    default:
      throw new Error(`Unidade de quantidade desconhecida: ${unidadeQuantidade as string}`);
  }

  const massaToneladas = massaKg / 1000;
  const totalSacas = massaKg / kgPorSaca;

  // Cálculo do frete base
  let freteBase = 0;
  if (tipoTarifa === "POR_TONELADA") {
    freteBase = massaToneladas * valorTarifa;
  } else if (tipoTarifa === "POR_SACA") {
    freteBase = totalSacas * valorTarifa;
  } else {
    throw new Error(`Tipo de tarifa inválido: ${tipoTarifa as string}`);
  }

  const totalFrete = freteBase + custosAdicionais;
  const custoEfetivoPorTonelada = totalFrete / massaToneladas;
  const custoEfetivoPorSaca = totalFrete / totalSacas;

  return {
    massaToneladas,
    totalSacas,
    massaKg,
    freteBase,
    custosAdicionais,
    totalFrete,
    custoEfetivoPorTonelada,
    custoEfetivoPorSaca,
  };
}

// ── 4. CUSTO POR HECTARE E PONTO DE EQUILÍBRIO ────────────────────────────────

export type UnidadeProdutividade = "SACAS_HA" | "TONELADAS_HA" | "KG_HA";

export interface CustoEquilibrioInput {
  areaHectares: number;
  custoTotal: number;
  produtividadeEsperadaPorHa: number;
  precoVendaUnitario: number;
  unidadeProdutividade?: UnidadeProdutividade;
}

export interface CustoEquilibrioResultado {
  areaHectares: number;
  custoTotal: number;
  custoPorHectare: number;
  producaoTotalEsperada: number;
  custoPorUnidadeProduzida: number | null; // null quando a produção total for zero
  receitaBrutaEstimada: number;
  resultadoEstimado: number;
  margemLucroPct: number | null; // null quando a receita bruta for zero
  precoDeEquilibrio: number | null; // null quando a produção total for zero
  produtividadeDeEquilibrioPorHa: number | null; // null quando preço de venda for zero (com custo > 0)
  producaoTotalDeEquilibrio: number | null; // null quando preço de venda for zero
}

export function calcularCustoEquilibrio(input: CustoEquilibrioInput): CustoEquilibrioResultado {
  const {
    areaHectares,
    custoTotal,
    produtividadeEsperadaPorHa,
    precoVendaUnitario,
  } = input;

  if (areaHectares <= 0 || !Number.isFinite(areaHectares)) {
    throw new Error("A área cultivada em hectares deve ser maior que zero.");
  }

  if (custoTotal < 0 || !Number.isFinite(custoTotal)) {
    throw new Error("O custo total não pode ser negativo.");
  }

  if (produtividadeEsperadaPorHa < 0 || !Number.isFinite(produtividadeEsperadaPorHa)) {
    throw new Error("A produtividade esperada não pode ser negativa.");
  }

  if (precoVendaUnitario < 0 || !Number.isFinite(precoVendaUnitario)) {
    throw new Error("O preço de venda estimado não pode ser negativo.");
  }

  const custoPorHectare = custoTotal / areaHectares;
  const producaoTotalEsperada = areaHectares * produtividadeEsperadaPorHa;

  // Se a produção total for zero, custo unitário e preço de equilíbrio são não calculáveis (null)
  // Se a produção for positiva e custo for zero, custo unitário e preço de equilíbrio são 0.
  let custoPorUnidadeProduzida: number | null = null;
  let precoDeEquilibrio: number | null = null;

  if (producaoTotalEsperada > 0) {
    custoPorUnidadeProduzida = custoTotal / producaoTotalEsperada;
    precoDeEquilibrio = custoTotal / producaoTotalEsperada;
  }

  const receitaBrutaEstimada = producaoTotalEsperada * precoVendaUnitario;
  const resultadoEstimado = receitaBrutaEstimada - custoTotal;

  // Margem sobre receita: só é calculável se receita bruta for maior que zero
  const margemLucroPct =
    receitaBrutaEstimada > 0 ? (resultadoEstimado / receitaBrutaEstimada) * 100 : null;

  // Produtividade de equilíbrio: só é calculável se o preço de venda for maior que zero
  let produtividadeDeEquilibrioPorHa: number | null = null;
  let producaoTotalDeEquilibrio: number | null = null;

  if (precoVendaUnitario > 0) {
    produtividadeDeEquilibrioPorHa = custoPorHectare / precoVendaUnitario;
    producaoTotalDeEquilibrio = custoTotal / precoVendaUnitario;
  }

  return {
    areaHectares,
    custoTotal,
    custoPorHectare,
    producaoTotalEsperada,
    custoPorUnidadeProduzida,
    receitaBrutaEstimada,
    resultadoEstimado,
    margemLucroPct,
    precoDeEquilibrio,
    produtividadeDeEquilibrioPorHa,
    producaoTotalDeEquilibrio,
  };
}

// ── 5. CONVERSOR GERAL DE UNIDADES ────────────────────────────────────────────

export type CategoriaGrandeza = "MASSA" | "AREA" | "VOLUME" | "COMPRIMENTO";

export interface UnidadeMedidaDef {
  codigo: string;
  nome: string;
  simbolo: string;
  grandeza: CategoriaGrandeza;
  fatorParaBase: number; // Multiplicador relativo à unidade base do SI
}

export const CATALOGO_UNIDADES: Record<string, UnidadeMedidaDef> = {
  // MASSA (Base: Quilograma - kg)
  KG: { codigo: "KG", nome: "Quilograma", simbolo: "kg", grandeza: "MASSA", fatorParaBase: 1 },
  G: { codigo: "G", nome: "Grama", simbolo: "g", grandeza: "MASSA", fatorParaBase: 0.001 },
  TONELADA: { codigo: "TONELADA", nome: "Tonelada Métrica", simbolo: "t", grandeza: "MASSA", fatorParaBase: 1000 },
  ARROBA: { codigo: "ARROBA", nome: "Arroba Agrícola", simbolo: "@", grandeza: "MASSA", fatorParaBase: 15 },

  // ÁREA (Base: Metro Quadrado - m²)
  M2: { codigo: "M2", nome: "Metro Quadrado", simbolo: "m²", grandeza: "AREA", fatorParaBase: 1 },
  HECTARE: { codigo: "HECTARE", nome: "Hectare", simbolo: "ha", grandeza: "AREA", fatorParaBase: 10000 },
  KM2: { codigo: "KM2", nome: "Quilômetro Quadrado", simbolo: "km²", grandeza: "AREA", fatorParaBase: 1000000 },

  // VOLUME (Base: Litro - L)
  LITRO: { codigo: "LITRO", nome: "Litro", simbolo: "L", grandeza: "VOLUME", fatorParaBase: 1 },
  MILILITRO: { codigo: "MILILITRO", nome: "Mililitro", simbolo: "mL", grandeza: "VOLUME", fatorParaBase: 0.001 },
  METRO_CUBICO: { codigo: "METRO_CUBICO", nome: "Metro Cúbico", simbolo: "m³", grandeza: "VOLUME", fatorParaBase: 1000 },

  // COMPRIMENTO (Base: Metro - m)
  METRO: { codigo: "METRO", nome: "Metro", simbolo: "m", grandeza: "COMPRIMENTO", fatorParaBase: 1 },
  QUILOMETRO: { codigo: "QUILOMETRO", nome: "Quilômetro", simbolo: "km", grandeza: "COMPRIMENTO", fatorParaBase: 1000 },
  CENTIMETRO: { codigo: "CENTIMETRO", nome: "Centímetro", simbolo: "cm", grandeza: "COMPRIMENTO", fatorParaBase: 0.01 },
};

export function converterUnidadeGeral(valor: number, codigoDe: string, codigoPara: string): number {
  if (valor < 0 || !Number.isFinite(valor)) {
    throw new Error("O valor a converter não pode ser negativo ou inválido.");
  }

  const unidadeDe = CATALOGO_UNIDADES[codigoDe];
  const unidadePara = CATALOGO_UNIDADES[codigoPara];

  if (!unidadeDe) {
    throw new Error(`Unidade de origem '${codigoDe}' não reconhecida.`);
  }

  if (!unidadePara) {
    throw new Error(`Unidade de destino '${codigoPara}' não reconhecida.`);
  }

  // Barreira estrita de incompatibilidade entre grandezas físicas
  if (unidadeDe.grandeza !== unidadePara.grandeza) {
    throw new Error(
      `Conversão inválida: grandezas incompatíveis. Não é permitido converter ${unidadeDe.grandeza.toLowerCase()} (${unidadeDe.nome}) diretamente para ${unidadePara.grandeza.toLowerCase()} (${unidadePara.nome}).`
    );
  }

  if (codigoDe === codigoPara) {
    return valor;
  }

  // Conversão normalizada via base SI sem arredondamento prematuro
  const valorNaBase = valor * unidadeDe.fatorParaBase;
  return valorNaBase / unidadePara.fatorParaBase;
}
