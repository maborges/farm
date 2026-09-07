/**
 * Constantes de Tier de Plano do AgroSaaS (Frontend)
 * DEVE estar sincronizado com services/api/core/constants.py — classe PlanTier
 *
 * O tier governa a PROFUNDIDADE de funcionalidades financeiras em todos os módulos.
 * O add-on de módulo controla SE o módulo está ativo.
 *
 * check_acesso(feature) = modulo_ativo(ADD_ON) AND tier_suficiente(TIER)
 */

import type { PlanTierId } from "@/types/global";

export const PlanTier = {
  BASICO: "BASICO",
  PROFISSIONAL: "PROFISSIONAL",
  ENTERPRISE: "ENTERPRISE",
  PREMIUM: "ENTERPRISE",
} as const;

export function normalizePlanTier(tier: PlanTierId | null | undefined): Exclude<PlanTierId, "PREMIUM"> | null {
  if (!tier) return null;
  return tier === "PREMIUM" ? "ENTERPRISE" : tier;
}

const TIER_LEVELS: Record<PlanTierId, number> = {
  BASICO: 1,
  PROFISSIONAL: 2,
  ENTERPRISE: 3,
  PREMIUM: 3,
};

/**
 * Retorna true se o tier atual atende ao mínimo exigido.
 * Espelha a lógica de PlanTier.__ge__ do backend.
 *
 * @example
 * tierAtLeast("PROFISSIONAL", "BASICO")     // true
 * tierAtLeast("BASICO", "PROFISSIONAL")     // false
 * tierAtLeast(null, "BASICO")               // false
 */
export function tierAtLeast(
  current: PlanTierId | null | undefined,
  minimum: PlanTierId
): boolean {
  const normalizedCurrent = normalizePlanTier(current);
  const normalizedMinimum = normalizePlanTier(minimum);
  if (!normalizedCurrent || !normalizedMinimum) return false;
  return TIER_LEVELS[normalizedCurrent] >= TIER_LEVELS[normalizedMinimum];
}

const ENTERPRISE_METADATA = {
  label: "Enterprise",
  descricao: "IA preditiva, benchmarking de mercado, integrações avançadas",
  cor: "bg-amber-100",
  corTexto: "text-amber-700",
};

export const PlanTierCommercialNames: Record<PlanTierId, string> = {
  BASICO: "Planejamento",
  PROFISSIONAL: "Profissional",
  ENTERPRISE: "Enterprise",
  PREMIUM: "Enterprise",
};

export const PlanTierMetadata: Record<
  PlanTierId,
  { label: string; descricao: string; cor: string; corTexto: string }
> = {
  BASICO: {
    label: "Planejamento",
    descricao: "Lançamentos simples, Livro Caixa, Fluxo de Caixa básico (30d)",
    cor: "bg-slate-100",
    corTexto: "text-slate-700",
  },
  PROFISSIONAL: {
    label: "Profissional",
    descricao: "Rateio automático, conciliação bancária, cenários de fluxo",
    cor: "bg-blue-100",
    corTexto: "text-blue-700",
  },
  ENTERPRISE: ENTERPRISE_METADATA,
  PREMIUM: ENTERPRISE_METADATA,
};

export function getCommercialPlanName(tier: PlanTierId | null | undefined): string | null {
  const normalizedTier = normalizePlanTier(tier);
  if (!normalizedTier) return null;
  return PlanTierCommercialNames[normalizedTier];
}

/**
 * Mapeamento comercial de módulos e submódulos do AgroSaaS.
 */
export const MODULE_LABELS: Record<string, string> = {
    // Core & Base
    CORE: "Gestão Base",
    
    // Imóveis
    IMOVEIS_CADASTRO: "Cadastro de Imóveis",
    IMOVEIS_ARRENDAMENTOS: "Gestão de Arrendamentos",
    IMOVEIS_AVALIACAO: "Avaliação de Terras",
    
    // Agrícola (A)
    A1_PLANEJAMENTO: "Planejamento Agrícola",
    A2_CAMPO: "Operações do Campo",
    A3_DEFENSIVOS: "Gestão de Defensivos",
    A4_PRECISAO: "Agricultura de Precisão",
    A5_COLHEITA: "Controle de Colheita",
    A1: "Módulo Agrícola",
    A2: "NDVI e Satélite",
    
    // Pecuária (P)
    P1_REBANHO: "Gestão de Rebanho",
    P2_GENETICA: "Melhoramento Genético",
    P3_CONFINAMENTO: "Confinamento e Dieta",
    P4_LEITE: "Produção de Leite",
    P1: "Pecuária (Rebanho)",
    
    // Financeiro (F)
    F1_TESOURARIA: "Tesouraria e Caixa",
    F2_CUSTOS_ABC: "Custos por Atividade (ABC)",
    F3_FISCAL: "Gestão Fiscal e Tributária",
    F4_HEDGING: "Gestão de Risco (Hedging)",
    F1: "Financeiro Completo",
    
    // Operacional & Frota (O)
    O1_FROTA: "Gestão de Frota",
    O2_ESTOQUE: "Controle de Estoque",
    O3_COMPRAS: "Gestão de Compras",
    O4_BALANCA: "Balança de Pesagem",
    O1: "Operacional (Frota)",
    
    // RH & Pessoas
    RH1_REMUNERACAO: "Gestão de Remuneração",
    RH2_SEGURANCA: "Segurança do Trabalho",
    
    // Sustentabilidade & Ambiental (AM)
    AM1_COMPLIANCE: "Compliance Ambiental",
    AM2_CARBONO: "Créditos de Carbono",
    
    // Extensões
    EXT_IA: "Copiloto IA Premium",
    EXT_IOT: "Integração IoT/Sensores",
    EXT_ERP: "Conectividade ERP",
};

/**
 * Retorna o nome amigável do módulo ou submódulo.
 * Se não houver mapeamento, formata o código bruto.
 */
export function getModuleName(code: string | null | undefined): string {
    if (!code) return "";
    if (MODULE_LABELS[code]) return MODULE_LABELS[code];
    
    return code
        .toLowerCase()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
