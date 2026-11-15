/**
 * Constantes de Módulos da DeepFarms (Frontend)
 * DEVE estar sincronizado com services/api/core/constants.py
 */

export const Modulos = {
  // ==================== NÚCLEO (Obrigatório) ====================
  CORE: "CORE",

  // ==================== BLOCO IMÓVEIS RURAIS ====================
  IMOVEIS_CADASTRO: "IMOVEIS_CADASTRO",        // Cadastro de Imóveis Rurais + Documentos Legais
  IMOVEIS_ARRENDAMENTOS: "IMOVEIS_ARRENDAMENTOS",  // Arrendamentos e Parcerias Rurais
  IMOVEIS_AVALIACAO: "IMOVEIS_AVALIACAO",      // Avaliação Patrimonial (Enterprise)

  // ==================== BLOCO AGRÍCOLA ====================
  AGRICOLA_PLANEJAMENTO: "A1_PLANEJAMENTO",      // Planejamento de Safra e Orçamento
  AGRICOLA_CAMPO: "A2_CAMPO",                    // Caderno de Campo (OS, Apontamentos)
  AGRICOLA_DEFENSIVOS: "A3_DEFENSIVOS",          // Defensivos e Receituário
  AGRICOLA_PRECISAO: "A4_PRECISAO",              // Agricultura de Precisão (NDVI, IoT)
  AGRICOLA_COLHEITA: "A5_COLHEITA",              // Colheita e Romaneio
  AGRICOLA_CLIMATICO: "A6_CLIMATICO",            // Estação e Previsão Agrícola
  AGRICOLA_INTELIGENCIA: "A7_INTELIGENCIA",      // Inteligência Climática Agrícola

  // ==================== BLOCO PECUÁRIA ====================
  PECUARIA_REBANHO: "P1_REBANHO",                // Rastreio inicial do rebanho
  PECUARIA_GENETICA: "P2_GENETICA",              // Genética Reprodutiva
  PECUARIA_CONFINAMENTO: "P3_CONFINAMENTO",      // Feedlot Control
  PECUARIA_LEITE: "P4_LEITE",                    // Pecuária Leiteira
  PECUARIA_CLIMATICO: "P5_CLIMATICO",            // Estação e Previsão Pecuária
  PECUARIA_INTELIGENCIA: "P6_INTELIGENCIA",      // Inteligência Climática Pecuária

  // ==================== BLOCO FINANCEIRO ====================
  FINANCEIRO_TESOURARIA: "F1_TESOURARIA",        // Tesouraria Básica
  FINANCEIRO_CUSTOS_ABC: "F2_CUSTOS_ABC",        // Custos ABC / Rateio
  FINANCEIRO_FISCAL: "F3_FISCAL",                // SPED, NF-e, Conformidade
  FINANCEIRO_HEDGING: "F4_HEDGING",              // Hedging, Futuros, Barter

  // ==================== BLOCO OPERACIONAL ====================
  OPERACIONAL_FROTA: "O1_FROTA",                 // Controle de Maquinários
  OPERACIONAL_ESTOQUE: "O2_ESTOQUE",             // Estoque Multi-armazéns
  OPERACIONAL_COMPRAS: "O3_COMPRAS",             // Supply e Compras
  OPERACIONAL_BALANCA: "O4_BALANCA",             // Balança de Pesagem (carga e animais)

  // ==================== BLOCO RH ====================
  RH_REMUNERACAO: "RH1_REMUNERACAO",             // Remuneração Temporários
  RH_SEGURANCA: "RH2_SEGURANCA",                 // EPC, EPIs, SESMT

  // ==================== BLOCO MEIO AMBIENTE ====================
  AMBIENTAL_COMPLIANCE: "AM1_COMPLIANCE",        // CAR, Outorgas
  AMBIENTAL_CARBONO: "AM2_CARBONO",              // Pegada de Carbono, MRV

  // ==================== EXTENSÕES ENTERPRISE ====================
  EXTENSAO_IA_COPILOT: "EXT_IA",                 // IA Agrônoma / ML
  EXTENSAO_IOT_SENSORES: "EXT_IOT",              // Sensórica Direta
  EXTENSAO_ERP_BRIDGE: "EXT_ERP",                // Bridge SAP/Datasul
} as const;

export type ModuloId = (typeof Modulos)[keyof typeof Modulos];

/** Compatibilidade de leitura para contratos antigos já emitidos. */
export const ModuleIdAliases: Readonly<Record<string, ModuloId>> = {
  IA_COPILOT: Modulos.EXTENSAO_IA_COPILOT,
};

export function normalizeModuleId(moduleId: string): ModuloId | string {
  return ModuleIdAliases[moduleId] ?? moduleId;
}

/**
 * Metadados dos módulos para exibição no frontend
 */
export const ModuloMetadata: Record<
  string,
  {
    nome: string;
    descricao: string;
    categoria: string;
    icone?: string;
    cor?: string;
    precoMensal?: number;
  }
> = {
  // CORE
  [Modulos.CORE]: {
    nome: "Núcleo da plataforma",
    descricao: "Produtores, mapas, permissões e operação offline",
    categoria: "CORE",
    cor: "bg-slate-500",
  },

  // IMÓVEIS RURAIS
  [Modulos.IMOVEIS_CADASTRO]: {
    nome: "Cadastro de Imóveis Rurais",
    descricao: "Gestão de NIRF, CAR, CCIR, documentos legais",
    categoria: "IMOVEIS",
    icone: "🏡",
    cor: "bg-teal-500",
    precoMensal: 99,
  },
  [Modulos.IMOVEIS_ARRENDAMENTOS]: {
    nome: "Arrendamentos e Parcerias",
    descricao: "Contratos de arrendamento, parcerias rurais",
    categoria: "IMOVEIS",
    icone: "📜",
    cor: "bg-teal-600",
    precoMensal: 149,
  },
  [Modulos.IMOVEIS_AVALIACAO]: {
    nome: "Avaliação Patrimonial",
    descricao: "Laudo de avaliação, valor de mercado",
    categoria: "IMOVEIS",
    icone: "💎",
    cor: "bg-teal-700",
    precoMensal: 199,
  },

  // AGRÍCOLA
  [Modulos.AGRICOLA_PLANEJAMENTO]: {
    nome: "Planejamento de Safra",
    descricao: "Gestão de ciclos, orçado vs realizado",
    categoria: "AGRICOLA",
    icone: "📊",
    cor: "bg-green-500",
    precoMensal: 199,
  },
  [Modulos.AGRICOLA_CAMPO]: {
    nome: "Caderno de Campo",
    descricao: "Ordens de Serviço, apontamentos, scouting",
    categoria: "AGRICOLA",
    icone: "📝",
    cor: "bg-green-600",
    precoMensal: 299,
  },
  [Modulos.AGRICOLA_DEFENSIVOS]: {
    nome: "Defensivos e Receituário",
    descricao: "Controle fitossanitário, período de carência",
    categoria: "AGRICOLA",
    icone: "🛡️",
    cor: "bg-green-700",
    precoMensal: 149,
  },
  [Modulos.AGRICOLA_PRECISAO]: {
    nome: "Agricultura de Precisão",
    descricao: "NDVI, NDRE, prescrições VRA, IoT",
    categoria: "AGRICOLA",
    icone: "🛰️",
    cor: "bg-green-800",
    precoMensal: 499,
  },
  [Modulos.AGRICOLA_COLHEITA]: {
    nome: "Colheita e Romaneio",
    descricao: "Romaneio dinâmico, balanças, despacho",
    categoria: "AGRICOLA",
    icone: "🚜",
    cor: "bg-green-900",
    precoMensal: 249,
  },
  [Modulos.AGRICOLA_CLIMATICO]: {
    nome: "Clima Agrícola",
    descricao: "Previsão do tempo, histórico de chuva e temperatura",
    categoria: "AGRICOLA",
    icone: "⛅",
    cor: "bg-blue-400",
    precoMensal: 99,
  },
  [Modulos.AGRICOLA_INTELIGENCIA]: {
    nome: "Inteligência Climática Agrícola",
    descricao: "Graus-dia, modelos fitossanitários, favorabilidade",
    categoria: "AGRICOLA",
    icone: "🧠",
    cor: "bg-blue-600",
    precoMensal: 199,
  },

  // PECUÁRIA
  [Modulos.PECUARIA_REBANHO]: {
    nome: "Controle de Rebanho",
    descricao: "Rastreio individual, GMD, pesagens",
    categoria: "PECUARIA",
    icone: "🐄",
    cor: "bg-amber-500",
    precoMensal: 249,
  },
  [Modulos.PECUARIA_GENETICA]: {
    nome: "Genética Reprodutiva",
    descricao: "IATF, diagnóstico prenhez, genealogia",
    categoria: "PECUARIA",
    icone: "🧬",
    cor: "bg-amber-600",
    precoMensal: 349,
  },
  [Modulos.PECUARIA_CONFINAMENTO]: {
    nome: "Feedlot Control",
    descricao: "Fábrica de ração, TMR, cochos",
    categoria: "PECUARIA",
    icone: "🏭",
    cor: "bg-amber-700",
    precoMensal: 399,
  },
  [Modulos.PECUARIA_LEITE]: {
    nome: "Pecuária Leiteira",
    descricao: "Controle leiteiro, CCS, CBT",
    categoria: "PECUARIA",
    icone: "🥛",
    cor: "bg-amber-800",
    precoMensal: 299,
  },
  [Modulos.PECUARIA_CLIMATICO]: {
    nome: "Clima Pecuário",
    descricao: "Previsão do tempo, umidade e ventos para gado",
    categoria: "PECUARIA",
    icone: "⛅",
    cor: "bg-orange-400",
    precoMensal: 99,
  },
  [Modulos.PECUARIA_INTELIGENCIA]: {
    nome: "Inteligência Climática Pecuária",
    descricao: "ITH, estresse térmico, alerta zoossanitário",
    categoria: "PECUARIA",
    icone: "🌡️",
    cor: "bg-orange-600",
    precoMensal: 199,
  },

  // FINANCEIRO
  [Modulos.FINANCEIRO_TESOURARIA]: {
    nome: "Tesouraria",
    descricao: "DFC, contas a pagar/receber",
    categoria: "FINANCEIRO",
    icone: "💰",
    cor: "bg-blue-500",
    precoMensal: 199,
  },
  [Modulos.FINANCEIRO_CUSTOS_ABC]: {
    nome: "Custos ABC",
    descricao: "Rateio de custos, centro de custos",
    categoria: "FINANCEIRO",
    icone: "📈",
    cor: "bg-blue-600",
    precoMensal: 299,
  },
  [Modulos.FINANCEIRO_FISCAL]: {
    nome: "Fiscal e Compliance",
    descricao: "LCDPR, NF-e, MDFe, SPED",
    categoria: "FINANCEIRO",
    icone: "📋",
    cor: "bg-blue-700",
    precoMensal: 449,
  },
  [Modulos.FINANCEIRO_HEDGING]: {
    nome: "Hedging e Futuros",
    descricao: "Proteção B3, barter, contratos",
    categoria: "FINANCEIRO",
    icone: "📊",
    cor: "bg-blue-800",
    precoMensal: 599,
  },

  // OPERACIONAL
  [Modulos.OPERACIONAL_FROTA]: {
    nome: "Controle de Frota",
    descricao: "Manutenções, horímetro, combustível",
    categoria: "OPERACIONAL",
    icone: "🚜",
    cor: "bg-purple-500",
    precoMensal: 179,
  },
  [Modulos.OPERACIONAL_ESTOQUE]: {
    nome: "Estoque Multi-armazéns",
    descricao: "Movimentações, validade, inventário",
    categoria: "OPERACIONAL",
    icone: "📦",
    cor: "bg-purple-600",
    precoMensal: 199,
  },
  [Modulos.OPERACIONAL_COMPRAS]: {
    nome: "Supply e Compras",
    descricao: "Solicitações, cotações, PO",
    categoria: "OPERACIONAL",
    icone: "🛒",
    cor: "bg-purple-700",
    precoMensal: 249,
  },
  [Modulos.OPERACIONAL_BALANCA]: {
    nome: "Balança de Pesagem",
    descricao: "Integração de pesagens de carga e animais com a Plataforma Pondaxis",
    categoria: "OPERACIONAL",
    icone: "⚖️",
    cor: "bg-cyan-600",
    precoMensal: 249,
  },

  // RH
  [Modulos.RH_REMUNERACAO]: {
    nome: "Remuneração Rural",
    descricao: "Diárias, empreitadas, produção",
    categoria: "RH",
    icone: "👷",
    cor: "bg-orange-500",
    precoMensal: 199,
  },
  [Modulos.RH_SEGURANCA]: {
    nome: "Segurança do Trabalho",
    descricao: "EPC, EPIs, PPP, PCMSO, NR-31",
    categoria: "RH",
    icone: "🦺",
    cor: "bg-orange-600",
    precoMensal: 149,
  },

  // AMBIENTAL
  [Modulos.AMBIENTAL_COMPLIANCE]: {
    nome: "Compliance Ambiental",
    descricao: "CAR, CCIR, outorgas hídricas",
    categoria: "AMBIENTAL",
    icone: "🌳",
    cor: "bg-emerald-500",
    precoMensal: 299,
  },
  [Modulos.AMBIENTAL_CARBONO]: {
    nome: "Gestão de Carbono",
    descricao: "MRV, pegada de carbono, créditos",
    categoria: "AMBIENTAL",
    icone: "🌍",
    cor: "bg-emerald-600",
    precoMensal: 499,
  },

  // EXTENSÕES
  [Modulos.EXTENSAO_IA_COPILOT]: {
    nome: "IA Copilot Agrônoma",
    descricao: "LLM treinado, alertas preditivos",
    categoria: "EXTENSAO",
    icone: "🤖",
    cor: "bg-pink-500",
    precoMensal: 799,
  },
  [Modulos.EXTENSAO_IOT_SENSORES]: {
    nome: "Integração IoT",
    descricao: "John Deere, balanças, sensores",
    categoria: "EXTENSAO",
    icone: "📡",
    cor: "bg-pink-600",
    precoMensal: 599,
  },
  [Modulos.EXTENSAO_ERP_BRIDGE]: {
    nome: "Bridge ERP Corporativo",
    descricao: "SAP, Datasul, Open Banking",
    categoria: "EXTENSAO",
    icone: "🔗",
    cor: "bg-pink-700",
    precoMensal: 1299,
  },
};

/**
 * Agrupa módulos por categoria para exibição
 */
export const ModulosPorCategoria = {
  IMOVEIS: [
    Modulos.IMOVEIS_CADASTRO,
    Modulos.IMOVEIS_ARRENDAMENTOS,
    Modulos.IMOVEIS_AVALIACAO,
  ],
  AGRICOLA: [
    Modulos.AGRICOLA_PLANEJAMENTO,
    Modulos.AGRICOLA_CAMPO,
    Modulos.AGRICOLA_DEFENSIVOS,
    Modulos.AGRICOLA_PRECISAO,
    Modulos.AGRICOLA_COLHEITA,
    Modulos.AGRICOLA_CLIMATICO,
    Modulos.AGRICOLA_INTELIGENCIA,
  ],
  PECUARIA: [
    Modulos.PECUARIA_REBANHO,
    Modulos.PECUARIA_GENETICA,
    Modulos.PECUARIA_CONFINAMENTO,
    Modulos.PECUARIA_LEITE,
    Modulos.PECUARIA_CLIMATICO,
    Modulos.PECUARIA_INTELIGENCIA,
  ],
  FINANCEIRO: [
    Modulos.FINANCEIRO_TESOURARIA,
    Modulos.FINANCEIRO_CUSTOS_ABC,
    Modulos.FINANCEIRO_FISCAL,
    Modulos.FINANCEIRO_HEDGING,
  ],
  OPERACIONAL: [
    Modulos.OPERACIONAL_FROTA,
    Modulos.OPERACIONAL_ESTOQUE,
    Modulos.OPERACIONAL_COMPRAS,
    Modulos.OPERACIONAL_BALANCA,
  ],
  RH: [Modulos.RH_REMUNERACAO, Modulos.RH_SEGURANCA],
  AMBIENTAL: [Modulos.AMBIENTAL_COMPLIANCE, Modulos.AMBIENTAL_CARBONO],
  EXTENSAO: [
    Modulos.EXTENSAO_IA_COPILOT,
    Modulos.EXTENSAO_IOT_SENSORES,
    Modulos.EXTENSAO_ERP_BRIDGE,
  ],
};
