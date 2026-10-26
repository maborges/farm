import { agroApiUrl } from "@/lib/api-url";

export type EstadoDisponibilidadePtax = "NORMAL" | "FONTE_INDISPONIVEL" | "OFFLINE" | "INDISPONIVEL";
export type EstadoCotacaoPtax = "ULTIMO_FECHAMENTO_OFICIAL" | "ULTIMO_FECHAMENTO_CONHECIDO" | "SEM_COTACAO";

export interface PtaxPublicaV1 {
  sucesso: boolean;
  versao: "1.0";
  indicador: string;
  moeda: string;
  moedaReferencia: "BRL";
  cotacaoCompra: number | null;
  cotacaoVenda: number | null;
  dataCotacao: string | null;
  dataHoraBoletimIso: string | null;
  tipoBoletim: string | null;
  fonteOficial: "Banco Central do Brasil (BCB)";
  dataConsultaIso: string;
  cacheAtualizadoEmIso: string | null;
  estadoDisponibilidade: EstadoDisponibilidadePtax;
  estadoCotacao: EstadoCotacaoPtax;
  estaDesatualizado: boolean;
  avisoLegal: string;
}

export interface PtaxIntradayPoint {
  hora: string;
  compra: number;
  venda: number;
  tipoBoletim: string;
}

const STORAGE_KEY = "deepfarms_agro_mercado_ptax_v1";
const SELECTED_CURRENCY_KEY = "deepfarms_agro_mercado_moeda_v1";
const CURRENCY_QUOTE_KEY = "deepfarms_agro_mercado_cotacao_v1";
const AVISO = "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.";
const BCB_PERIOD_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)";

export const CURRENCIES = [
  { code: "USD", name: "Dólar americano", symbol: "US$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "Libra esterlina", symbol: "£" },
  { code: "JPY", name: "Iene japonês", symbol: "¥" },
  { code: "CAD", name: "Dólar canadense", symbol: "CA$" },
  { code: "CHF", name: "Franco suíço", symbol: "CHF" },
  { code: "AUD", name: "Dólar australiano", symbol: "A$" },
  { code: "CNY", name: "Yuan chinês", symbol: "¥" },
  { code: "ARS", name: "Peso argentino", symbol: "AR$" },
  { code: "CLP", name: "Peso chileno", symbol: "CLP$" },
  { code: "ZAR", name: "Rand sul-africano", symbol: "R" },
] as const;

export type CurrencyCode = (typeof CURRENCIES)[number]["code"];

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isoTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

export function parsePtax(value: unknown): PtaxPublicaV1 | null {
  if (!record(value) || value.versao !== "1.0" || !["DOLAR_PTAX", "CAMBIO_PTAX"].includes(String(value.indicador)) ||
      (value.indicador === "DOLAR_PTAX" && value.moeda !== "USD") ||
      typeof value.moeda !== "string" || !/^[A-Z]{3}$/.test(value.moeda) || value.moedaReferencia !== "BRL" || value.sucesso !== true ||
      value.fonteOficial !== "Banco Central do Brasil (BCB)" ||
      typeof value.tipoBoletim !== "string" ||
      typeof value.cotacaoCompra !== "number" || !Number.isFinite(value.cotacaoCompra) || value.cotacaoCompra <= 0 ||
      typeof value.cotacaoVenda !== "number" || !Number.isFinite(value.cotacaoVenda) || value.cotacaoVenda < value.cotacaoCompra ||
      typeof value.dataCotacao !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value.dataCotacao) ||
      !isoTimestamp(value.dataHoraBoletimIso) || !isoTimestamp(value.dataConsultaIso) ||
      !isoTimestamp(value.cacheAtualizadoEmIso) ||
      !["NORMAL", "FONTE_INDISPONIVEL"].includes(String(value.estadoDisponibilidade)) ||
      !["ULTIMO_FECHAMENTO_OFICIAL", "ULTIMO_FECHAMENTO_CONHECIDO"].includes(String(value.estadoCotacao)) ||
      typeof value.estaDesatualizado !== "boolean") {
    return null;
  }
  return {
    sucesso: true, versao: "1.0", indicador: value.indicador as string, moeda: value.moeda, moedaReferencia: "BRL",
    cotacaoCompra: value.cotacaoCompra, cotacaoVenda: value.cotacaoVenda,
    dataCotacao: value.dataCotacao, dataHoraBoletimIso: value.dataHoraBoletimIso,
    tipoBoletim: value.tipoBoletim, fonteOficial: "Banco Central do Brasil (BCB)",
    dataConsultaIso: value.dataConsultaIso, cacheAtualizadoEmIso: value.cacheAtualizadoEmIso,
    estadoDisponibilidade: value.estadoDisponibilidade as EstadoDisponibilidadePtax,
    estadoCotacao: value.estadoCotacao as EstadoCotacaoPtax,
    estaDesatualizado: value.estaDesatualizado, avisoLegal: AVISO,
  };
}

function currencyStorageKey(currency: CurrencyCode): string {
  return `${CURRENCY_QUOTE_KEY}:${currency}`;
}

export function readSavedCurrency(storage: Pick<Storage, "getItem">): CurrencyCode {
  try {
    const saved = storage.getItem(SELECTED_CURRENCY_KEY);
    return CURRENCIES.find((currency) => currency.code === saved)?.code ?? "USD";
  } catch {
    return "USD";
  }
}

export function saveSelectedCurrency(storage: Pick<Storage, "setItem">, currency: CurrencyCode): void {
  try { storage.setItem(SELECTED_CURRENCY_KEY, currency); } catch { /* armazenamento bloqueado */ }
}

export function readSavedCurrencyQuote(
  storage: Pick<Storage, "getItem" | "removeItem">,
  currency: CurrencyCode,
): PtaxPublicaV1 | null {
  try {
    const raw = storage.getItem(currencyStorageKey(currency));
    if (raw) {
      const value: unknown = JSON.parse(raw);
      if (record(value) && value.currency === currency && record(value.quote)) {
        const quote = parsePtax(value.quote);
        if (!quote || quote.moeda !== currency) storage.removeItem(currencyStorageKey(currency));
        return quote?.moeda === currency ? quote : null;
      }
    }
    if (currency === "USD") {
      return readSavedPtax(storage);
    }
    return null;
  } catch {
    try { storage.removeItem(currencyStorageKey(currency)); } catch { /* armazenamento bloqueado */ }
    if (currency === "USD") {
      return readSavedPtax(storage);
    }
    return null;
  }
}

export function saveCurrencyQuote(
  storage: Pick<Storage, "setItem">,
  currency: CurrencyCode,
  quote: PtaxPublicaV1,
): boolean {
  if (quote.moeda !== currency || !parsePtax(quote)) return false;
  try {
    storage.setItem(currencyStorageKey(currency), JSON.stringify({ currency, quote }));
    return true;
  } catch {
    return false;
  }
}

export function readSavedPtax(storage: Pick<Storage, "getItem" | "removeItem">): PtaxPublicaV1 | null {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const envelope: unknown = JSON.parse(raw);
    const quote = record(envelope) && envelope.version === 1 ? parsePtax(envelope.quote) : null;
    if (!quote) storage.removeItem(STORAGE_KEY);
    return quote;
  } catch {
    try { storage.removeItem(STORAGE_KEY); } catch { /* armazenamento bloqueado */ }
    return null;
  }
}

export function savePtax(storage: Pick<Storage, "setItem">, value: unknown): boolean {
  const quote = parsePtax(value);
  if (!quote) return false;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, quote }));
    return true;
  } catch {
    return false;
  }
}

export interface BrowserLocation {
  hostname: string;
  protocol: string;
}

export function ptaxApiUrl(location: BrowserLocation): string {
  void location;
  return agroApiUrl("/api/v1/public/mercado/ptax");
}

function bcbDate(value: Date): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(value);
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value;
  return `${part("month")}-${part("day")}-${part("year")}`;
}

export function bcbPtaxUrl(now: Date): string {
  const end = bcbDate(now);
  const start = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);
  return `${BCB_PERIOD_URL}?@dataInicial='${bcbDate(start)}'&@dataFinalCotacao='${end}'&$top=1&$orderby=dataHoraCotacao%20desc&$format=json`;
}

export function bcbCurrencyUrl(currency: CurrencyCode, now: Date): string {
  const base = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/" +
    "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)";
  const end = bcbDate(now);
  const start = bcbDate(new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000));
  return `${base}?@moeda='${currency}'&@dataInicial='${start}'&@dataFinalCotacao='${end}'&$top=1&$orderby=dataHoraCotacao%20desc&$format=json`;
}

export function parseBcbCurrency(value: unknown, currency: CurrencyCode, now: Date): PtaxPublicaV1 | null {
  if (!record(value) || !Array.isArray(value.value) || value.value.length !== 1 || !record(value.value[0])) return null;
  const row = value.value[0];
  const bulletin = bcbTimestamp(row.dataHoraCotacao);
  const buy = row.cotacaoCompra;
  const sell = row.cotacaoVenda;
  if (!bulletin || !isRecentBcbBulletin(bulletin, now) || typeof buy !== "number" || typeof sell !== "number" || !Number.isFinite(buy) || !Number.isFinite(sell) || buy <= 0 || sell < buy) return null;
  return {
    sucesso: true, versao: "1.0", indicador: "CAMBIO_PTAX", moeda: currency, moedaReferencia: "BRL",
    cotacaoCompra: buy, cotacaoVenda: sell, dataCotacao: bulletin.slice(0, 10),
    dataHoraBoletimIso: bulletin, tipoBoletim: typeof row.tipoBoletim === "string" ? row.tipoBoletim : "Fechamento PTAX",
    fonteOficial: "Banco Central do Brasil (BCB)", dataConsultaIso: now.toISOString(),
    cacheAtualizadoEmIso: now.toISOString(), estadoDisponibilidade: "NORMAL",
    estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL", estaDesatualizado: false, avisoLegal: AVISO,
  };
}

export async function fetchCurrencyQuote(
  currency: CurrencyCode,
  location: BrowserLocation,
  signal?: AbortSignal,
): Promise<PtaxPublicaV1 | null> {
  if (currency === "USD") return fetchPtax(location, signal);
  const now = new Date();
  const response = await fetch(bcbCurrencyUrl(currency, now), { credentials: "omit", cache: "no-store", signal });
  if (!response.ok) throw new Error("Serviço PTAX indisponível");
  const quote = parseBcbCurrency(await response.json() as unknown, currency, now);
  if (!quote) throw new Error("Resposta PTAX inválida");
  return quote;
}

function bcbTimestamp(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = value.match(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?$/);
  if (!match) return null;
  const milliseconds = (match[3] ?? "").slice(0, 3).padEnd(3, "0");
  return `${match[1]}T${match[2]}.${milliseconds}-03:00`;
}

function isRecentBcbBulletin(timestamp: string, now: Date): boolean {
  const ageMs = now.getTime() - Date.parse(timestamp);
  return ageMs >= -5 * 60 * 1000 && ageMs <= 7 * 24 * 60 * 60 * 1000;
}

export function parseBcbPtax(value: unknown, now: Date): PtaxPublicaV1 | null {
  if (!record(value) || !Array.isArray(value.value) || value.value.length !== 1 || !record(value.value[0])) return null;
  const row = value.value[0];
  const bulletin = bcbTimestamp(row.dataHoraCotacao);
  const compra = row.cotacaoCompra;
  const venda = row.cotacaoVenda;
  if (!bulletin || !isRecentBcbBulletin(bulletin, now) || typeof compra !== "number" || typeof venda !== "number") return null;
  return parsePtax({
    sucesso: true, versao: "1.0", indicador: "DOLAR_PTAX", moeda: "USD", moedaReferencia: "BRL",
    cotacaoCompra: compra, cotacaoVenda: venda, dataCotacao: bulletin.slice(0, 10),
    dataHoraBoletimIso: bulletin, tipoBoletim: "Fechamento PTAX",
    fonteOficial: "Banco Central do Brasil (BCB)", dataConsultaIso: now.toISOString(),
    cacheAtualizadoEmIso: now.toISOString(), estadoDisponibilidade: "NORMAL",
    estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL", estaDesatualizado: false, avisoLegal: AVISO,
  });
}

export function parseBcbPtaxIntraday(value: unknown): PtaxIntradayPoint[] {
  if (!record(value) || !Array.isArray(value.value)) return [];
  return value.value.flatMap((row) => {
    if (!record(row) || typeof row.cotacaoCompra !== "number" || typeof row.cotacaoVenda !== "number") return [];
    const timestamp = bcbTimestamp(row.dataHoraCotacao);
    if (!timestamp || !Number.isFinite(row.cotacaoCompra) || !Number.isFinite(row.cotacaoVenda) || row.cotacaoCompra > row.cotacaoVenda) return [];
    return [{
      hora: timestamp.slice(11, 16), compra: row.cotacaoCompra, venda: row.cotacaoVenda,
      tipoBoletim: typeof row.tipoBoletim === "string" ? row.tipoBoletim : "Boletim PTAX",
    }];
  });
}

export function bcbIntradayUrl(dataCotacao: string, currency: CurrencyCode = "USD"): string {
  return "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/" +
    `CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)?@moeda='${currency}'&@dataCotacao='${dataCotacao.slice(5, 7)}-${dataCotacao.slice(8, 10)}-${dataCotacao.slice(0, 4)}'&$format=json`;
}

export async function fetchPtaxIntraday(dataCotacao: string, signal?: AbortSignal, currency: CurrencyCode = "USD"): Promise<PtaxIntradayPoint[]> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dataCotacao)) return [];
  const response = await fetch(bcbIntradayUrl(dataCotacao, currency), { credentials: "omit", cache: "no-store", signal });
  if (!response.ok) return [];
  return parseBcbPtaxIntraday(await response.json() as unknown);
}

export async function fetchPtax(location: BrowserLocation, signal?: AbortSignal): Promise<PtaxPublicaV1 | null> {
  try {
    const response = await fetch(ptaxApiUrl(location), { credentials: "omit", cache: "no-store", signal });
    if (!response.ok) throw new Error("Serviço PTAX indisponível");
    const quote = parsePtax(await response.json() as unknown);
    if (!quote) throw new Error("Resposta PTAX inválida");
    return quote;
  } catch (apiError) {
    const now = new Date();
    const response = await fetch(bcbPtaxUrl(now), { credentials: "omit", cache: "no-store", signal });
    if (!response.ok) throw apiError;
    const quote = parseBcbPtax(await response.json() as unknown, now);
    if (!quote) throw apiError;
    return quote;
  }
}

export function formatPtax(value: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 4, maximumFractionDigits: 5 }).format(value);
}

export function formatCurrencyRate(value: number, currency: CurrencyCode): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency", currency: "BRL", minimumFractionDigits: 4, maximumFractionDigits: 5,
  }).format(value) + ` / ${currency}`;
}

export function formatDateBr(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export function formatTimeBr(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
}

export function formatSyncBr(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}
