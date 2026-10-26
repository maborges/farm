import { agroApiUrl } from "@/lib/api-url";

/**
 * Módulo de parsing, armazenamento offline e formatação de indicadores macroeconômicos do BCB.
 */

export interface IndicadorMacroItem {
  id: "SELIC_META" | "IPCA_MENSAL" | "IPCA_12M" | "EURO_PTAX" | string;
  nomeOficial: string;
  codigoSerieBcb: number;
  valor: number;
  valorCompra?: number | null;
  valorVenda?: number | null;
  unidade: string;
  periodicidade: "DIARIA" | "MENSAL" | string;
  dataReferencia: string; // YYYY-MM-DD
  dataConsultaIso: string;
  fonteOficial: string;
  estadoDisponibilidade: "NORMAL" | "DEFASADO" | "FONTE_INDISPONIVEL" | "INDISPONIVEL" | string;
  estaDesatualizado: boolean;
  avisoLegal: string;
}

export interface IndicadoresMacroResponse {
  sucesso: boolean;
  versao: "1.0";
  dataConsultaIso: string;
  cacheAtualizadoEmIso: string | null;
  estadoDisponibilidade: "NORMAL" | "DEFASADO" | "FONTE_INDISPONIVEL" | "INDISPONIVEL" | string;
  estaDesatualizado: boolean;
  avisoLegal: string;
  itens: IndicadorMacroItem[];
}

const STORAGE_KEY = "deepfarms_agro_mercado_macro_v1";

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isoTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

export function parseIndicadorItem(value: unknown): IndicadorMacroItem | null {
  if (!record(value)) return null;

  const id = String(value.id);
  const nomeOficial = String(value.nomeOficial ?? "");
  const codigoSerieBcb = Number(value.codigoSerieBcb);
  const valor = Number(value.valor);
  const unidade = String(value.unidade ?? "");
  const periodicidade = String(value.periodicidade ?? "");
  const dataReferencia = String(value.dataReferencia ?? "");
  const dataConsultaIso = String(value.dataConsultaIso ?? "");
  const fonteOficial = String(value.fonteOficial ?? "");
  const estadoDisponibilidade = String(value.estadoDisponibilidade ?? "NORMAL");
  const estaDesatualizado = Boolean(value.estaDesatualizado);
  const avisoLegal = String(value.avisoLegal ?? "");

  if (
    !id ||
    !nomeOficial ||
    !Number.isFinite(codigoSerieBcb) ||
    !Number.isFinite(valor) ||
    !unidade ||
    !/^\d{4}-\d{2}-\d{2}$/.test(dataReferencia) ||
    !isoTimestamp(dataConsultaIso)
  ) {
    return null;
  }

  const valorCompra = typeof value.valorCompra === "number" && Number.isFinite(value.valorCompra) ? value.valorCompra : null;
  const valorVenda = typeof value.valorVenda === "number" && Number.isFinite(value.valorVenda) ? value.valorVenda : null;

  return {
    id,
    nomeOficial,
    codigoSerieBcb,
    valor,
    valorCompra,
    valorVenda,
    unidade,
    periodicidade,
    dataReferencia,
    dataConsultaIso,
    fonteOficial,
    estadoDisponibilidade,
    estaDesatualizado,
    avisoLegal,
  };
}

export function parseIndicadoresMacro(value: unknown): IndicadoresMacroResponse | null {
  if (!record(value) || value.versao !== "1.0" || !Array.isArray(value.itens)) {
    return null;
  }

  const itensValidos = value.itens
    .map(parseIndicadorItem)
    .filter((item): item is IndicadorMacroItem => item !== null);

  if (value.sucesso === true && itensValidos.length === 0) {
    return null;
  }

  return {
    sucesso: Boolean(value.sucesso),
    versao: "1.0",
    dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
    cacheAtualizadoEmIso: isoTimestamp(value.cacheAtualizadoEmIso) ? value.cacheAtualizadoEmIso : null,
    estadoDisponibilidade: String(value.estadoDisponibilidade ?? "NORMAL"),
    estaDesatualizado: Boolean(value.estaDesatualizado),
    avisoLegal: String(value.avisoLegal ?? ""),
    itens: itensValidos,
  };
}

export function markMacroUnavailable(value: IndicadoresMacroResponse): IndicadoresMacroResponse {
  return {
    ...value,
    estadoDisponibilidade: "FONTE_INDISPONIVEL",
    estaDesatualizado: true,
    itens: value.itens.map((item) => ({
      ...item,
      estadoDisponibilidade: "FONTE_INDISPONIVEL",
      estaDesatualizado: true,
    })),
  };
}

export function readSavedMacro(storage: Pick<Storage, "getItem" | "removeItem">): IndicadoresMacroResponse | null {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const envelope: unknown = JSON.parse(raw);
    const parsed = record(envelope) && envelope.version === 1 ? parseIndicadoresMacro(envelope.dados) : null;
    if (!parsed) storage.removeItem(STORAGE_KEY);
    return parsed;
  } catch {
    try {
      storage.removeItem(STORAGE_KEY);
    } catch {
      /* storage inacessível */
    }
    return null;
  }
}

export function saveMacro(storage: Pick<Storage, "setItem">, value: unknown): boolean {
  const parsed = parseIndicadoresMacro(value);
  if (!parsed || !parsed.sucesso) return false;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, dados: parsed }));
    return true;
  } catch {
    return false;
  }
}

export interface BrowserLocation {
  hostname: string;
  protocol: string;
}

export function macroApiUrl(location: BrowserLocation): string {
  void location;
  return agroApiUrl("/api/v1/public/mercado/indicadores-macro");
}

export async function fetchIndicadoresMacro(
  location: BrowserLocation,
  signal?: AbortSignal
): Promise<IndicadoresMacroResponse | null> {
  const response = await fetch(macroApiUrl(location), {
    credentials: "omit",
    cache: "no-store",
    signal,
  });

  if (!response.ok) {
    throw new Error(`Serviço de indicadores macroeconômicos indisponível (HTTP ${response.status})`);
  }

  const payload: unknown = await response.json();
  const parsed = parseIndicadoresMacro(payload);
  if (!parsed) {
    throw new Error("Resposta de indicadores macroeconômicos inválida");
  }

  return parsed;
}

/**
 * Formata o valor numérico de acordo com a unidade da série
 */
export function formatarValorMacro(indicador: IndicadorMacroItem): string {
  if (indicador.unidade === "BRL") {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    }).format(indicador.valor);
  }

  if (indicador.unidade.includes("%")) {
    const prefixo = indicador.id === "IPCA_MENSAL" && indicador.valor > 0 ? "+" : "";
    const formatado = new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(indicador.valor);
    return `${prefixo}${formatado}%`;
  }

  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(indicador.valor);
}

const MESES_PT_BR = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

/**
 * Formata a data de referência respeitando a periodicidade do indicador
 */
export function formatarDataReferencia(dataIso: string, periodicidade: string): string {
  const [yearStr, monthStr, dayStr] = dataIso.split("-");
  const year = parseInt(yearStr, 10);
  const month = parseInt(monthStr, 10);

  if (periodicidade === "MENSAL" && month >= 1 && month <= 12) {
    return `${MESES_PT_BR[month - 1]}/${year}`;
  }

  return `${dayStr}/${monthStr}/${year}`;
}
