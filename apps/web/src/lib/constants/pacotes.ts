/**
 * Definição Oficial dos Pacotes Comerciais — DeepFarms (Política All-In)
 *
 * Política Comercial Vigente:
 *  1. 100% dos módulos liberados em TODOS os pacotes (tier ENTERPRISE).
 *  2. O valor varia pela soma do tamanho produtivo das propriedades (Hectares Equivalentes - HEq,
 *     isentando APP e Reserva Legal e não duplicando consórcio/safrinha) e pela quantidade
 *     de acessos simultâneos na Web.
 *  3. O uso no aplicativo Campo (offline-first) é 100% isento e não consome acesso simultâneo.
 *  4. No ciclo Anual: 2 meses grátis no pacote base + 20% de desconto nas licenças adicionais.
 */

import { Modulos, ModuloMetadata } from "./modulos";

export type PacoteId =
  | "FAMILIAR"
  | "PEQUENO_PRODUTOR"
  | "MEDIO_PRODUTOR"
  | "GRANDE_PRODUTOR"
  | "GRUPO"
  | "BASICO"
  | "PROFISSIONAL"
  | "EMPRESA";

export interface FaixaUsuarioAdicional {
  faixaInicio: number;
  faixaFim: number | null;
  precoMensal: number;
  precoAnual: number;
  precoMensalEquivalenteAnual: number;
}

export interface PacoteDefinicao {
  id: PacoteId;
  nome: string;
  descricao: string;
  descricaoMarketing: string;
  tier: "BASICO" | "PROFISSIONAL" | "ENTERPRISE" | "PREMIUM";
  modulos: string[];
  precoMensal: number;
  precoAnual: number;
  usuariosInclusos: number;
  limiteUsuarios: number;
  maxFazendas: number;
  limiteHectares: number | null;
  faixasAdicionais: FaixaUsuarioAdicional[];
  destaque?: string;
}

export interface ExtensaoContratadaAParte {
  id: string;
  nome: string;
  descricaoCurta: string;
  precoMensal: number;
  precoAnual: number;
  precoMensalEquivalenteAnual: number;
  ativo?: boolean;
}

/** Status de ativação do catálogo retornado por GET /billing/modules/catalog. */
export interface CatalogoModulosStatus {
  modulos_ativos: string[];
  modulos_inativos: string[];
  extensoes: Array<{
    id: string;
    nome: string;
    descricao: string;
    preco_mensal: number;
    preco_anual: number;
    preco_mensal_equivalente_anual: number;
    ativo: boolean;
  }>;
}

/**
 * Remove dos pacotes os módulos marcados como inativos no Backoffice.
 * O módulo CORE é sempre mantido.
 */
export function filtrarModulosAtivos(modulos: string[], modulosInativos: string[]): string[] {
  const inativos = new Set(modulosInativos);
  return modulos.filter((modulo) => modulo === Modulos.CORE || !inativos.has(modulo));
}

/**
 * Mescla as extensões locais (IoT/ERP) com o status ativo e preços vindos do backend.
 * Sem resposta do backend, as extensões permanecem com os valores padrão.
 */
export function mesclarStatusExtensoes(
  catalogo: CatalogoModulosStatus | undefined
): ExtensaoContratadaAParte[] {
  return EXTENSOES_CONTRATADAS_A_PARTE.map((extensao) => {
    const remota = catalogo?.extensoes?.find((item) => item.id === extensao.id);
    if (!remota) {
      return extensao;
    }
    return {
      ...extensao,
      nome: remota.nome || extensao.nome,
      precoMensal: typeof remota.preco_mensal === "number" ? remota.preco_mensal : extensao.precoMensal,
      precoAnual: typeof remota.preco_anual === "number" ? remota.preco_anual : extensao.precoAnual,
      precoMensalEquivalenteAnual:
        typeof remota.preco_mensal_equivalente_anual === "number"
          ? remota.preco_mensal_equivalente_anual
          : extensao.precoMensalEquivalenteAnual,
      ativo: remota.ativo !== false,
    };
  });
}

export const EXTENSOES_CONTRATADAS_A_PARTE: ExtensaoContratadaAParte[] = [
  {
    id: Modulos.EXTENSAO_IOT_SENSORES,
    nome: "Integração IoT",
    descricaoCurta: "Telemetria de máquinas, estações meteorológicas e sensores de umidade.",
    precoMensal: 599,
    precoAnual: 5750.4,
    precoMensalEquivalenteAnual: 479.2,
  },
  {
    id: Modulos.EXTENSAO_ERP_BRIDGE,
    nome: "Bridge ERP Corporativo",
    descricaoCurta: "Conector bidirecional com SAP, TOTVS Protheus, Senior e Sankhya.",
    precoMensal: 1299,
    precoAnual: 12470.4,
    precoMensalEquivalenteAnual: 1039.2,
  },
];

export const TODOS_MODULOS: string[] = [
  Modulos.CORE,
  Modulos.IMOVEIS_CADASTRO,
  Modulos.IMOVEIS_ARRENDAMENTOS,
  Modulos.IMOVEIS_AVALIACAO,
  Modulos.AGRICOLA_PLANEJAMENTO,
  Modulos.AGRICOLA_CAMPO,
  Modulos.AGRICOLA_DEFENSIVOS,
  Modulos.AGRICOLA_PRECISAO,
  Modulos.AGRICOLA_COLHEITA,
  Modulos.PECUARIA_REBANHO,
  Modulos.PECUARIA_GENETICA,
  Modulos.PECUARIA_CONFINAMENTO,
  Modulos.PECUARIA_LEITE,
  Modulos.FINANCEIRO_TESOURARIA,
  Modulos.FINANCEIRO_CUSTOS_ABC,
  Modulos.FINANCEIRO_FISCAL,
  Modulos.FINANCEIRO_HEDGING,
  Modulos.OPERACIONAL_FROTA,
  Modulos.OPERACIONAL_ESTOQUE,
  Modulos.OPERACIONAL_COMPRAS,
  Modulos.OPERACIONAL_BALANCA,
  Modulos.RH_REMUNERACAO,
  Modulos.RH_SEGURANCA,
  Modulos.AMBIENTAL_COMPLIANCE,
  Modulos.AMBIENTAL_CARBONO,
  Modulos.EXTENSAO_IA_COPILOT,
];

export const PACOTES_OFICIAIS_ORDEM: PacoteId[] = [
  "FAMILIAR",
  "PEQUENO_PRODUTOR",
  "MEDIO_PRODUTOR",
  "GRANDE_PRODUTOR",
  "GRUPO",
];

export const PACOTES: Record<PacoteId, PacoteDefinicao> = {
  FAMILIAR: {
    id: "FAMILIAR",
    nome: "Familiar",
    descricao:
      "100% dos módulos liberados (Agrícola, Pecuária, Financeiro, Fiscal, Estoque, Frota, RH, Ambiental e IA; extensões IoT e ERP contratadas à parte). Ideal para agricultura familiar e sítios até 100 ha equivalentes (ou 25 ha Café/HF; até 150 cabeças).",
    descricaoMarketing:
      "1 propriedade • Até 100 ha • 1 acesso simultâneo incluso (máx. 3) • App Campo livre",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 197,
    precoAnual: 1970,
    usuariosInclusos: 1,
    limiteUsuarios: 3,
    maxFazendas: 1,
    limiteHectares: 100,
    faixasAdicionais: [
      {
        faixaInicio: 1,
        faixaFim: 2,
        precoMensal: 89,
        precoAnual: 854.4,
        precoMensalEquivalenteAnual: 71.2,
      },
    ],
  },
  PEQUENO_PRODUTOR: {
    id: "PEQUENO_PRODUTOR",
    nome: "Pequeno Produtor",
    descricao:
      "100% dos módulos liberados para propriedades em crescimento até 500 ha equivalentes (ou 120 ha Café/HF; até 600 cabeças). Inclui 2 acessos simultâneos na Web e uso livre no aplicativo Campo.",
    descricaoMarketing:
      "Até 2 propriedades • Até 500 ha • 2 acessos simultâneos inclusos (máx. 6) • App Campo livre",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 497,
    precoAnual: 4970,
    usuariosInclusos: 2,
    limiteUsuarios: 6,
    maxFazendas: 2,
    limiteHectares: 500,
    faixasAdicionais: [
      {
        faixaInicio: 1,
        faixaFim: 2,
        precoMensal: 99,
        precoAnual: 950.4,
        precoMensalEquivalenteAnual: 79.2,
      },
      {
        faixaInicio: 3,
        faixaFim: 4,
        precoMensal: 85,
        precoAnual: 816.0,
        precoMensalEquivalenteAnual: 68.0,
      },
    ],
  },
  MEDIO_PRODUTOR: {
    id: "MEDIO_PRODUTOR",
    nome: "Médio Produtor",
    descricao:
      "100% dos módulos liberados para fazendas estruturadas até 2.000 ha equivalentes (ou 500 ha Café/HF; até 2.500 cabeças). Inclui 5 acessos simultâneos na Web e uso livre no aplicativo Campo.",
    descricaoMarketing:
      "Até 5 propriedades • Até 2.000 ha • 5 acessos simultâneos inclusos (máx. 15) • App Campo livre",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 1197,
    precoAnual: 11970,
    usuariosInclusos: 5,
    limiteUsuarios: 15,
    maxFazendas: 5,
    limiteHectares: 2000,
    destaque: "Mais popular",
    faixasAdicionais: [
      {
        faixaInicio: 1,
        faixaFim: 5,
        precoMensal: 110,
        precoAnual: 1056.0,
        precoMensalEquivalenteAnual: 88.0,
      },
      {
        faixaInicio: 6,
        faixaFim: 10,
        precoMensal: 90,
        precoAnual: 864.0,
        precoMensalEquivalenteAnual: 72.0,
      },
    ],
  },
  GRANDE_PRODUTOR: {
    id: "GRANDE_PRODUTOR",
    nome: "Grande Produtor",
    descricao:
      "100% dos módulos liberados para operações de alta escala até 6.000 ha equivalentes (ou 1.500 ha Café/HF; até 8.000 cabeças). Inclui 10 acessos simultâneos na Web e uso livre no aplicativo Campo.",
    descricaoMarketing:
      "Até 10 propriedades • Até 6.000 ha • 10 acessos simultâneos inclusos (máx. 30) • App Campo livre",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 2497,
    precoAnual: 24970,
    usuariosInclusos: 10,
    limiteUsuarios: 30,
    maxFazendas: 10,
    limiteHectares: 6000,
    faixasAdicionais: [
      {
        faixaInicio: 1,
        faixaFim: 10,
        precoMensal: 120,
        precoAnual: 1152.0,
        precoMensalEquivalenteAnual: 96.0,
      },
      {
        faixaInicio: 11,
        faixaFim: 20,
        precoMensal: 95,
        precoAnual: 912.0,
        precoMensalEquivalenteAnual: 76.0,
      },
    ],
  },
  GRUPO: {
    id: "GRUPO",
    nome: "Grupo",
    descricao:
      "100% dos módulos liberados para holdings, grupos agrícolas, usinas e cooperativas sem limite de área ou propriedades. Inclui 20 acessos simultâneos na Web, expansão ilimitada e uso livre no aplicativo Campo.",
    descricaoMarketing:
      "Propriedades e Hectares ilimitados • 20 acessos simultâneos inclusos (expansão ilimitada) • App Campo livre",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 4997,
    precoAnual: 49970,
    usuariosInclusos: 20,
    limiteUsuarios: 999,
    maxFazendas: -1,
    limiteHectares: null,
    destaque: "Sem limites",
    faixasAdicionais: [
      {
        faixaInicio: 1,
        faixaFim: 15,
        precoMensal: 110,
        precoAnual: 1056.0,
        precoMensalEquivalenteAnual: 88.0,
      },
      {
        faixaInicio: 16,
        faixaFim: 30,
        precoMensal: 90,
        precoAnual: 864.0,
        precoMensalEquivalenteAnual: 72.0,
      },
      {
        faixaInicio: 31,
        faixaFim: null,
        precoMensal: 75,
        precoAnual: 720.0,
        precoMensalEquivalenteAnual: 60.0,
      },
    ],
  },
  // Aliases legados mantidos para compatibilidade retroativa
  BASICO: {
    id: "BASICO",
    nome: "Pequeno Produtor",
    descricao: "100% dos módulos liberados para propriedades até 500 ha equivalentes.",
    descricaoMarketing: "Até 2 propriedades • Até 500 ha • 2 acessos simultâneos inclusos",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 497,
    precoAnual: 4970,
    usuariosInclusos: 2,
    limiteUsuarios: 6,
    maxFazendas: 2,
    limiteHectares: 500,
    faixasAdicionais: [
      { faixaInicio: 1, faixaFim: 2, precoMensal: 99, precoAnual: 950.4, precoMensalEquivalenteAnual: 79.2 },
      { faixaInicio: 3, faixaFim: 4, precoMensal: 85, precoAnual: 816.0, precoMensalEquivalenteAnual: 68.0 },
    ],
  },
  PROFISSIONAL: {
    id: "PROFISSIONAL",
    nome: "Médio Produtor",
    descricao: "100% dos módulos liberados para fazendas até 2.000 ha equivalentes.",
    descricaoMarketing: "Até 5 propriedades • Até 2.000 ha • 5 acessos simultâneos inclusos",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 1197,
    precoAnual: 11970,
    usuariosInclusos: 5,
    limiteUsuarios: 15,
    maxFazendas: 5,
    limiteHectares: 2000,
    destaque: "Mais popular",
    faixasAdicionais: [
      { faixaInicio: 1, faixaFim: 5, precoMensal: 110, precoAnual: 1056.0, precoMensalEquivalenteAnual: 88.0 },
      { faixaInicio: 6, faixaFim: 10, precoMensal: 90, precoAnual: 864.0, precoMensalEquivalenteAnual: 72.0 },
    ],
  },
  EMPRESA: {
    id: "EMPRESA",
    nome: "Grupo",
    descricao: "100% dos módulos liberados sem limite de área ou propriedades.",
    descricaoMarketing: "Propriedades e Hectares ilimitados • 20 acessos simultâneos inclusos",
    tier: "ENTERPRISE",
    modulos: TODOS_MODULOS,
    precoMensal: 4997,
    precoAnual: 49970,
    usuariosInclusos: 20,
    limiteUsuarios: 999,
    maxFazendas: -1,
    limiteHectares: null,
    destaque: "Sem limites",
    faixasAdicionais: [
      { faixaInicio: 1, faixaFim: 15, precoMensal: 110, precoAnual: 1056.0, precoMensalEquivalenteAnual: 88.0 },
      { faixaInicio: 16, faixaFim: 30, precoMensal: 90, precoAnual: 864.0, precoMensalEquivalenteAnual: 72.0 },
      { faixaInicio: 31, faixaFim: null, precoMensal: 75, precoAnual: 720.0, precoMensalEquivalenteAnual: 60.0 },
    ],
  },
};

export const FATORES_VOCACAO_HEQ: Record<string, { label: string; fator: number; descricao: string }> = {
  PASTAGEM: {
    label: "Pecuária Extensiva / Pastagem / Silvicultura (0.5x)",
    fator: 0.5,
    descricao: "1 ha físico consome apenas 0,5 ha equivalente do pacote.",
  },
  GRAOS: {
    label: "Grãos / Culturas Anuais / Cana / Safra + Safrinha (1.0x)",
    fator: 1.0,
    descricao: "1 ha físico = 1,0 ha equivalente (Safrinha e Consórcio não duplicam área).",
  },
  CAFE_PERENES: {
    label: "Café / Fruticultura / Citros / Algodão (2.5x)",
    fator: 2.5,
    descricao: "Alta densidade operacional (1 ha físico = 2,5 ha equivalentes).",
  },
  HORTIFRUTI: {
    label: "Hortifrúti / Olericultura / Cultivo Protegido (4.0x)",
    fator: 4.0,
    descricao: "Ciclos curtos intensivos e rastreabilidade lote a lote (1 ha = 4,0 HEq).",
  },
};

export function getPacote(id: PacoteId): PacoteDefinicao {
  return PACOTES[id];
}

export function getPacotes(): PacoteDefinicao[] {
  return PACOTES_OFICIAIS_ORDEM.map((id) => PACOTES[id]);
}

export const PACOTES_COMERCIAIS_LISTA: PacoteDefinicao[] = getPacotes();

export function obterPacotePorNome(nome: string | null | undefined): PacoteDefinicao | undefined {
  if (!nome) return undefined;
  const norm = nome
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  const oficial = getPacotes().find(
    (p) =>
      p.nome
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "") === norm
  );
  if (oficial) return oficial;

  if (norm.includes("familiar")) return PACOTES.FAMILIAR;
  if (norm.includes("pequeno") || norm.includes("basico")) return PACOTES.PEQUENO_PRODUTOR;
  if (norm.includes("medio") || norm.includes("profissional")) return PACOTES.MEDIO_PRODUTOR;
  if (norm.includes("grande")) return PACOTES.GRANDE_PRODUTOR;
  if (norm.includes("grupo") || norm.includes("empresa") || norm.includes("enterprise")) return PACOTES.GRUPO;
  return undefined;
}

export function calcularOrcamentoLocal(
  pacote: PacoteDefinicao,
  quantidadeUsuarios: number,
  ciclo: "MENSAL" | "ANUAL",
  extensoesSelecionadas: string[] = [],
  extensoesDisponiveis: ExtensaoContratadaAParte[] = EXTENSOES_CONTRATADAS_A_PARTE
): {
  valorPacoteBase: number;
  valorUsuariosAdicionais: number;
  valorExtensoes: number;
  extensoesSelecionadas: string[];
  valorTotal: number;
  equivalenteMensal: number;
  usuariosInclusos: number;
  usuariosAdicionais: number;
  economiaAnualTotal: number;
} {
  const usuariosEfetivos = Math.max(pacote.usuariosInclusos, quantidadeUsuarios);
  const usuariosAdicionais = Math.max(0, usuariosEfetivos - pacote.usuariosInclusos);

  const baseMensal = pacote.precoMensal;
  const baseAnual = pacote.precoAnual;

  let adicionaisMensal = 0;
  let adicionaisAnual = 0;
  let restantes = usuariosAdicionais;

  for (const faixa of pacote.faixasAdicionais) {
    if (restantes <= 0) break;
    const capacidadeFaixa =
      faixa.faixaFim === null ? restantes : Math.max(0, faixa.faixaFim - faixa.faixaInicio + 1);
    const qtdNaFaixa = Math.min(restantes, capacidadeFaixa);
    if (qtdNaFaixa > 0) {
      adicionaisMensal += qtdNaFaixa * faixa.precoMensal;
      adicionaisAnual += qtdNaFaixa * faixa.precoAnual;
      restantes -= qtdNaFaixa;
    }
  }

  let extensoesMensal = 0;
  let extensoesAnual = 0;
  const extensoesValidas: string[] = [];

  for (const extId of extensoesSelecionadas) {
    const ext = extensoesDisponiveis.find((item) => item.id === extId);
    if (ext && ext.ativo !== false && !extensoesValidas.includes(ext.id)) {
      extensoesValidas.push(ext.id);
      extensoesMensal += ext.precoMensal;
      extensoesAnual += ext.precoAnual;
    }
  }

  const totalMensal = baseMensal + adicionaisMensal + extensoesMensal;
  const totalAnual = baseAnual + adicionaisAnual + extensoesAnual;
  const economiaAnualTotal = totalMensal * 12 - totalAnual;

  if (ciclo === "ANUAL") {
    return {
      valorPacoteBase: baseAnual,
      valorUsuariosAdicionais: adicionaisAnual,
      valorExtensoes: extensoesAnual,
      extensoesSelecionadas: extensoesValidas,
      valorTotal: totalAnual,
      equivalenteMensal: totalAnual / 12,
      usuariosInclusos: pacote.usuariosInclusos,
      usuariosAdicionais,
      economiaAnualTotal,
    };
  }

  return {
    valorPacoteBase: baseMensal,
    valorUsuariosAdicionais: adicionaisMensal,
    valorExtensoes: extensoesMensal,
    extensoesSelecionadas: extensoesValidas,
    valorTotal: totalMensal,
    equivalenteMensal: totalMensal,
    usuariosInclusos: pacote.usuariosInclusos,
    usuariosAdicionais,
    economiaAnualTotal,
  };
}

export function moduloIncluso(moduloId: string, pacoteId: PacoteId): boolean {
  return PACOTES[pacoteId].modulos.includes(moduloId);
}

export function modulosUpgradeDePara(de: PacoteId, para: PacoteId): string[] {
  const modulosDe = new Set(PACOTES[de].modulos);
  return PACOTES[para].modulos.filter((m) => !modulosDe.has(m));
}

export function calcularPrecoAvulso(modulos: string[]): number {
  return modulos.reduce((total, modId) => {
    const info = (ModuloMetadata as Record<string, Record<string, unknown>>)[modId];
    return total + ((info?.precoMensal as number) ?? 0);
  }, 0);
}

export function economiaPacote(pacoteId: PacoteId): number {
  const pacote = PACOTES[pacoteId];
  const precoAvulso = calcularPrecoAvulso(pacote.modulos);
  if (precoAvulso === 0) return 0;
  return Math.round(((precoAvulso - pacote.precoMensal) / precoAvulso) * 100);
}
