/**
 * Definição dos Pacotes Comerciais — AgroSaaS
 *
 * Cada pacote combina:
 *  - Um **tier** (BASICO, PROFISSIONAL, ENTERPRISE) que governa a profundidade
 *    de funcionalidades financeiras em todos os módulos (ex: rateio, conciliação, IA).
 *  - Um conjunto de **módulos** que determina quais blocos estão ativos.
 *
 * Regras de composição:
 *  1. CORE é obrigatório em todos os pacotes.
 *  2. Dependências de módulo DEVEM estar incluídas (ex: DEFENSIVOS → CAMPO).
 *  3. Módulos EXTENSAO são exclusivos do pacote EMPRESA (ENTERPRISE).
 *  4. O tier do plano é derivado do nome do pacote.
 *
 * Sincronizar com services/api/core/constants.py (ModuloMetadata.CATALOGO).
 */

import { Modulos, ModuloMetadata } from "./modulos";

// ─── Tipos ───────────────────────────────────────────────────────────────────

export type PacoteId = "BASICO" | "PROFISSIONAL" | "EMPRESA";

export interface PacoteDefinicao {
  /** ID único do pacote (mesmo valor do tier) */
  id: PacoteId;
  /** Nome comercial exibido ao usuário */
  nome: string;
  /** Descrição curta para marketing */
  descricao: string;
  /** Tier que governa profundidade financeira */
  tier: "BASICO" | "PROFISSIONAL" | "ENTERPRISE" | "PREMIUM";
  /** Módulos incluídos (IDs) */
  modulos: string[];
  /** Preço mensal sugerido (R$) */
  precoMensal: number;
  /** Preço anual sugerido (R$) */
  precoAnual: number;
  /** Limite de usuários */
  limiteUsuarios: number;
  /** Limite de hectares (null = ilimitado) */
  limiteHectares: number | null;
  /** Destaque comercial (badge) */
  destaque?: string;
}

// ─── Definição dos Pacotes ───────────────────────────────────────────────────

export const PACOTES: Record<PacoteId, PacoteDefinicao> = {
  // ═══════════════════════════════════════════════════════════════════════════
  // BÁSICO — Para pequenos e médios produtores que estão começando a digitalizar
  // ═══════════════════════════════════════════════════════════════════════════
  BASICO: {
    id: "BASICO",
    nome: "Planejamento",
    descricao:
      "Controle essencial da propriedade: cadastro de imóveis, planejamento de safra, " +
      "caderno de campo, rebanho básico, tesouraria e frota. Ideal para quem quer sair " +
      "do caderno de papel e ter visibilidade das operações.",
    tier: "BASICO",
    modulos: [
      // ── Núcleo ──
      Modulos.CORE,

      // ── Imóveis Rurais ──
      Modulos.IMOVEIS_CADASTRO,

      // ── Agrícola (essenciais) ──
      Modulos.AGRICOLA_PLANEJAMENTO,
      Modulos.AGRICOLA_CAMPO,

      // ── Pecuária (básico) ──
      Modulos.PECUARIA_REBANHO,

      // ── Financeiro (tesouraria básica) ──
      Modulos.FINANCEIRO_TESOURARIA,

      // ── Operacional (frota + estoque) ──
      Modulos.OPERACIONAL_FROTA,
      Modulos.OPERACIONAL_ESTOQUE,

      // ── RH (remuneração) ──
      Modulos.RH_REMUNERACAO,

      // ── Ambiental (compliance básico) ──
      Modulos.AMBIENTAL_COMPLIANCE,
    ],
    precoMensal: 497,
    precoAnual: 4970, // ~2 meses grátis
    limiteUsuarios: 5,
    limiteHectares: 500,
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // PROFISSIONAL — Para propriedades em crescimento que precisam de controle
  //                 financeiro detalhado e operações avançadas
  // ═══════════════════════════════════════════════════════════════════════════
  PROFISSIONAL: {
    id: "PROFISSIONAL",
    nome: "Profissional",
    descricao:
      "Tudo do Planejamento + defensivos, colheita, genética, custos ABC, fiscal, compras, " +
      "segurança do trabalho e gestão de carbono. Para quem quer controle total de " +
      "custos por safra/talhão e compliance fiscal.",
    tier: "PROFISSIONAL",
    modulos: [
      // ── Tudo do Planejamento ──
      Modulos.CORE,
      Modulos.IMOVEIS_CADASTRO,
      Modulos.AGRICOLA_PLANEJAMENTO,
      Modulos.AGRICOLA_CAMPO,
      Modulos.PECUARIA_REBANHO,
      Modulos.FINANCEIRO_TESOURARIA,
      Modulos.OPERACIONAL_FROTA,
      Modulos.OPERACIONAL_ESTOQUE,
      Modulos.RH_REMUNERACAO,
      Modulos.AMBIENTAL_COMPLIANCE,

      // ── Agrícola avançado ──
      Modulos.AGRICOLA_DEFENSIVOS,    // requer CAMPO ✓
      Modulos.AGRICOLA_COLHEITA,      // requer PLANEJAMENTO ✓

      // ── Pecuária avançada ──
      Modulos.PECUARIA_GENETICA,       // requer REBANHO ✓
      Modulos.PECUARIA_CONFINAMENTO,   // requer REBANHO ✓
      Modulos.PECUARIA_LEITE,          // requer REBANHO ✓

      // ── Financeiro avançado ──
      Modulos.FINANCEIRO_CUSTOS_ABC,  // requer TESOURARIA ✓
      Modulos.FINANCEIRO_FISCAL,       // requer TESOURARIA ✓

      // ── Operacional completo ──
      Modulos.OPERACIONAL_COMPRAS,     // requer ESTOQUE ✓
      Modulos.OPERACIONAL_BALANCA,     // integração TARA

      // ── RH completo ──
      Modulos.RH_SEGURANCA,

      // ── Ambiental avançado ──
      Modulos.AMBIENTAL_CARBONO,

      // ── Imóveis avançado ──
      Modulos.IMOVEIS_ARRENDAMENTOS,  // requer CADASTRO ✓
    ],
    precoMensal: 1497,
    precoAnual: 14970, // ~2 meses grátis
    limiteUsuarios: 15,
    limiteHectares: 2000,
    destaque: "Mais popular",
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // EMPRESA (ENTERPRISE) — Para grandes propriedades e grupos rurais que precisam
  //                     de IA, IoT, integrações ERP e controle patrimonial
  // ═══════════════════════════════════════════════════════════════════════════
  EMPRESA: {
    id: "EMPRESA",
    nome: "Enterprise",
    descricao:
      "Tudo do Profissional + agricultura de precisão (NDVI/IoT), pecuária leiteira " +
      "avançada, hedging e futuros, avaliação patrimonial, IA Copilot Agrônoma, " +
      "integração IoT com maquinário e bridge ERP corporativo. Sem limites.",
    tier: "ENTERPRISE",
    modulos: [
      // ── Tudo do Profissional ──
      Modulos.CORE,
      Modulos.IMOVEIS_CADASTRO,
      Modulos.IMOVEIS_ARRENDAMENTOS,
      Modulos.AGRICOLA_PLANEJAMENTO,
      Modulos.AGRICOLA_CAMPO,
      Modulos.AGRICOLA_DEFENSIVOS,
      Modulos.AGRICOLA_COLHEITA,
      Modulos.PECUARIA_REBANHO,
      Modulos.PECUARIA_GENETICA,
      Modulos.PECUARIA_CONFINAMENTO,
      Modulos.PECUARIA_LEITE,
      Modulos.FINANCEIRO_TESOURARIA,
      Modulos.FINANCEIRO_CUSTOS_ABC,
      Modulos.FINANCEIRO_FISCAL,
      Modulos.OPERACIONAL_FROTA,
      Modulos.OPERACIONAL_ESTOQUE,
      Modulos.OPERACIONAL_COMPRAS,
      Modulos.OPERACIONAL_BALANCA,
      Modulos.RH_REMUNERACAO,
      Modulos.RH_SEGURANCA,
      Modulos.AMBIENTAL_COMPLIANCE,
      Modulos.AMBIENTAL_CARBONO,

      // ── Agrícola de precisão ──
      Modulos.AGRICOLA_PRECISAO,

      // ── Financeiro enterprise ──
      Modulos.FINANCEIRO_HEDGING,

      // ── Imóveis enterprise ──
      Modulos.IMOVEIS_AVALIACAO,

      // ── Extensões exclusivas ──
      Modulos.EXTENSAO_IA_COPILOT,
      Modulos.EXTENSAO_IOT_SENSORES,
      Modulos.EXTENSAO_ERP_BRIDGE,
    ],
    precoMensal: 4997,
    precoAnual: 49970, // ~2 meses grátis
    limiteUsuarios: 999, // ilimitado na prática
    limiteHectares: null, // ilimitado
    destaque: "Mais completo",
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Retorna a definição de um pacote pelo ID */
export function getPacote(id: PacoteId): PacoteDefinicao {
  return PACOTES[id];
}

/** Retorna todos os pacotes em ordem comercial */
export function getPacotes(): PacoteDefinicao[] {
  return (["BASICO", "PROFISSIONAL", "EMPRESA"] as PacoteId[]).map(
    (id) => PACOTES[id]
  );
}

/** Verifica se um módulo está incluído em um pacote */
export function moduloIncluso(moduloId: string, pacoteId: PacoteId): boolean {
  return PACOTES[pacoteId].modulos.includes(moduloId);
}

/** Retorna os módulos que estão no Profissional mas NÃO estão no Planejamento */
export function modulosUpgradeDePara(de: PacoteId, para: PacoteId): string[] {
  const modulosDe = new Set(PACOTES[de].modulos);
  return PACOTES[para].modulos.filter((m) => !modulosDe.has(m));
}

/** Calcula o preço avulso dos módulos de um pacote (para mostrar economia) */
export function calcularPrecoAvulso(modulos: string[]): number {
  return modulos.reduce((total, modId) => {
    const info = (ModuloMetadata as Record<string, Record<string, unknown>>)[modId];
    return total + ((info?.precoMensal as number) ?? 0);
  }, 0);
}

/** Retorna a economia percentual do pacote vs preço avulso */
export function economiaPacote(pacoteId: PacoteId): number {
  const pacote = PACOTES[pacoteId];
  const precoAvulso = calcularPrecoAvulso(pacote.modulos);
  if (precoAvulso === 0) return 0;
  return Math.round(((precoAvulso - pacote.precoMensal) / precoAvulso) * 100);
}

// ─── Resumo Comercial (para documentação) ────────────────────────────────────
//
// ┌────────────────┬──────────┬───────────────┬─────────┬──────────┬──────────┐
// │ Pacote         │ Tier     │ Módulos       │ Usuários│ ha       │ R$/mês   │
// ├────────────────┼──────────┼───────────────┼─────────┼──────────┼──────────┤
// │ Planejamento   │ BASICO   │ 10 módulos    │    5    │   500    │   497    │
// │ Profissional   │ PROFISS. │ 19 módulos    │   15    │  2.000   │  1.497   │
// │ Enterprise     │ ENTERPRISE │ 26 módulos  │ ilimit. │ ilimit.  │  4.997   │
// └────────────────┴──────────┴───────────────┴─────────┴──────────┴──────────┘
//
// Módulos por pacote:
//
// BÁSICO (10):
//   ✅ CORE                        — Núcleo AgroSaaS
//   ✅ IMOVEIS_CADASTRO            — Cadastro de Imóveis Rurais
//   ✅ AGRICOLA_PLANEJAMENTO       — Planejamento de Safra
//   ✅ AGRICOLA_CAMPO              — Caderno de Campo
//   ✅ PECUARIA_REBANHO            — Controle de Rebanho
//   ✅ FINANCEIRO_TESOURARIA       — Tesouraria
//   ✅ OPERACIONAL_FROTA           — Controle de Frota
//   ✅ OPERACIONAL_ESTOQUE         — Estoque Multi-armazéns
//   ✅ RH_REMUNERACAO              — Remuneração Rural
//   ✅ AMBIENTAL_COMPLIANCE        — Compliance Ambiental
//
// PROFISSIONAL (+9 = 19):
//   ✅ AGRICOLA_DEFENSIVOS         — Defensivos e Receituário
//   ✅ AGRICOLA_COLHEITA           — Colheita e Romaneio
//   ✅ PECUARIA_GENETICA           — Genética Reprodutiva
//   ✅ PECUARIA_CONFINAMENTO       — Feedlot Control
//   ✅ PECUARIA_LEITE              — Pecuária Leiteira
//   ✅ FINANCEIRO_CUSTOS_ABC       — Custos ABC
//   ✅ FINANCEIRO_FISCAL           — Fiscal e Compliance
//   ✅ OPERACIONAL_COMPRAS         — Supply e Compras
//   ✅ RH_SEGURANCA                — Segurança do Trabalho
//   ✅ AMBIENTAL_CARBONO           — Gestão de Carbono
//   ✅ IMOVEIS_ARRENDAMENTOS       — Arrendamentos e Parcerias
//
// EMPRESA (+7 = 26):
//   ✅ AGRICOLA_PRECISAO           — Agricultura de Precisão (NDVI/IoT)
//   ✅ FINANCEIRO_HEDGING          — Hedging e Futuros
//   ✅ IMOVEIS_AVALIACAO           — Avaliação Patrimonial
//   ✅ EXTENSAO_IA_COPILOT         — IA Copilot Agrônoma
//   ✅ EXTENSAO_IOT_SENSORES       — Integração IoT
//   ✅ EXTENSAO_ERP_BRIDGE         — Bridge ERP Corporativo
