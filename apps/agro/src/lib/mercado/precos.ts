import { agroApiUrl } from "@/lib/api-url";

/**
 * Módulo de parsing, armazenamento offline e formatação de preços públicos de commodities (DERAL e CONAB).
 */

export interface PrecoPublicoItem {
  id: string;
  commodityNome: string;
  classificacao: string;
  valor: number;
  moeda: string;
  unidade: string;
  pracaReferencia: string;
  fonteOficial: string;
  siglaFonte: string;
  linkOficial: string;
  urlConsultaInstitucional?: string;
  urlDocumentoDownload?: string | null;
  tipoPreco: "PRECO_MEDIO_RECEBIDO_PRODUTOR" | "PRECO_MEDIO_ATACADO" | "REFERENCIA_OFICIAL_GOVERNAMENTAL" | string;
  periodicidade: "SEMANAL" | "MENSAL" | "DIARIA" | string;
  dataReferencia: string; // YYYY-MM-DD
  dataConsultaIso: string;
  defasagemDiasAproximada: number;
  indicacaoTemporal: string;
  avisoLegal: string;
  documentoOficial: string;
  documentoHashSha256: string;
  dataPublicacao: string | null;
  registroOriginal: string;
  valorOriginal: number;
  unidadeOriginal: string;
  transformacaoAplicada: string;
}

export interface PrecosPublicosResponse {
  sucesso: boolean;
  versao: "1.0";
  dataConsultaIso: string;
  cacheAtualizadoEmIso: string | null;
  estadoDisponibilidade: "NORMAL" | "DEFASADO" | "FONTE_INDISPONIVEL" | string;
  avisoLegal: string;
  totalItens?: number;
  itens: PrecoPublicoItem[];
}

const STORAGE_KEY = "deepfarms_agro_mercado_precos_v4";
const LEGACY_STORAGE_KEY = "deepfarms_agro_mercado_precos_v1";

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isoTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

export function parsePrecoItem(value: unknown): PrecoPublicoItem | null {
  if (!record(value)) return null;

  const id = typeof value.id === "string" ? value.id.trim() : "";
  const commodityNome = typeof value.commodityNome === "string" ? value.commodityNome.trim() : "";
  const classificacao = typeof value.classificacao === "string" ? value.classificacao.trim() : "";
  const valor = Number(value.valor);
  const moeda = typeof value.moeda === "string" ? value.moeda.trim() : "BRL";
  const unidade = typeof value.unidade === "string" ? value.unidade.trim() : "";
  const pracaReferencia = typeof value.pracaReferencia === "string" ? value.pracaReferencia.trim() : "";
  const fonteOficial = typeof value.fonteOficial === "string" ? value.fonteOficial.trim() : "";
  const siglaFonte = typeof value.siglaFonte === "string" ? value.siglaFonte.trim() : "";
  const linkOficial = typeof value.linkOficial === "string" ? value.linkOficial.trim() : "";
  const tipoPreco = typeof value.tipoPreco === "string" ? value.tipoPreco.trim() : "PRECO_MEDIO_RECEBIDO_PRODUTOR";
  const periodicidade = typeof value.periodicidade === "string" ? value.periodicidade.trim() : "SEMANAL";
  const dataReferencia = typeof value.dataReferencia === "string" ? value.dataReferencia.trim() : "";
  const dataConsultaIso = typeof value.dataConsultaIso === "string" ? value.dataConsultaIso.trim() : "";
  const defasagemDiasAproximada = Number(value.defasagemDiasAproximada ?? 0);
  const indicacaoTemporal = typeof value.indicacaoTemporal === "string" ? value.indicacaoTemporal.trim() : "Semanal — Preço Médio Produtor";
  const avisoLegal = typeof value.avisoLegal === "string" ? value.avisoLegal.trim() : "";
  const documentoOficial = typeof value.documentoOficial === "string" ? value.documentoOficial.trim() : "";
  const documentoHashSha256 = typeof value.documentoHashSha256 === "string" ? value.documentoHashSha256.trim() : "";
  const dataPublicacao = typeof value.dataPublicacao === "string" ? value.dataPublicacao.trim() : null;
  const registroOriginal = typeof value.registroOriginal === "string" ? value.registroOriginal.trim() : "";
  const valorOriginal = Number(value.valorOriginal);
  const unidadeOriginal = typeof value.unidadeOriginal === "string" ? value.unidadeOriginal.trim() : "";
  const transformacaoAplicada = typeof value.transformacaoAplicada === "string" ? value.transformacaoAplicada.trim() : "";

  // 1. Formato canônico de slug do ID
  if (!id || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
    return null;
  }

  // 2. Valores numéricos positivos, finitos e não-NaN
  if (!Number.isFinite(valor) || Number.isNaN(valor) || valor <= 0) {
    return null;
  }
  if (!Number.isFinite(valorOriginal) || Number.isNaN(valorOriginal) || valorOriginal <= 0) {
    return null;
  }

  // 3. Unidades válidas não vazias
  if (!unidade || !unidadeOriginal) {
    return null;
  }

  // 4. Metadados cadastrais e proveniência obrigatória
  if (
    !commodityNome ||
    !pracaReferencia ||
    !siglaFonte ||
    !documentoOficial.startsWith("https://") ||
    !/^[0-9a-f]{64}$/.test(documentoHashSha256) ||
    !/^Rav!X\d+$/.test(registroOriginal) ||
    !transformacaoAplicada ||
    !/^\d{4}-\d{2}-\d{2}$/.test(dataReferencia) ||
    !isoTimestamp(dataConsultaIso) ||
    (dataPublicacao !== null && !/^\d{4}-\d{2}-\d{2}$/.test(dataPublicacao))
  ) {
    return null;
  }

  const urlConsultaInstitucional = typeof value.urlConsultaInstitucional === "string" ? value.urlConsultaInstitucional : linkOficial;
  const urlDocumentoDownload = typeof value.urlDocumentoDownload === "string" ? value.urlDocumentoDownload : documentoOficial;

  return {
    id,
    commodityNome,
    classificacao,
    valor,
    moeda,
    unidade,
    pracaReferencia,
    fonteOficial,
    siglaFonte,
    linkOficial,
    urlConsultaInstitucional,
    urlDocumentoDownload,
    tipoPreco,
    periodicidade,
    dataReferencia,
    dataConsultaIso,
    defasagemDiasAproximada,
    indicacaoTemporal,
    avisoLegal,
    documentoOficial,
    documentoHashSha256,
    dataPublicacao,
    registroOriginal,
    valorOriginal,
    unidadeOriginal,
    transformacaoAplicada,
  };
}

export function parsePrecosResponse(value: unknown): PrecosPublicosResponse | null {
  if (!record(value) || value.versao !== "1.0" || !Array.isArray(value.itens)) {
    return null;
  }

  // Tratamento de fonte indisponível sem itens
  if (value.estadoDisponibilidade === "FONTE_INDISPONIVEL") {
    return {
      sucesso: Boolean(value.sucesso),
      versao: "1.0",
      dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
      cacheAtualizadoEmIso: isoTimestamp(value.cacheAtualizadoEmIso) ? value.cacheAtualizadoEmIso : null,
      estadoDisponibilidade: "FONTE_INDISPONIVEL",
      avisoLegal: String(value.avisoLegal ?? ""),
      totalItens: 0,
      itens: [],
    };
  }

  // 1. Integridade do payload completo: cada item DEVE ser estruturalmente válido
  const itensValidos: PrecoPublicoItem[] = [];
  for (const item of value.itens) {
    const parsedItem = parsePrecoItem(item);
    if (!parsedItem) {
      // Rejeita resposta corrompida ou truncada
      return null;
    }
    itensValidos.push(parsedItem);
  }

  // Não aceita payload com sucesso contendo lista vazia
  if (itensValidos.length === 0) {
    return null;
  }

  // 2. Unicidade rigorosa de IDs
  const ids = new Set<string>();
  for (const item of itensValidos) {
    if (ids.has(item.id)) {
      return null; // ID duplicado
    }
    ids.add(item.id);
  }

  // 3. Consistência de lote e ausência de contaminação entre períodos
  const primeiroHash = itensValidos[0].documentoHashSha256;
  const primeiraDataRef = itensValidos[0].dataReferencia;
  for (let i = 1; i < itensValidos.length; i++) {
    if (itensValidos[i].documentoHashSha256 !== primeiroHash) {
      return null; // Contaminação de hashes divergentes no mesmo lote
    }
    if (itensValidos[i].dataReferencia !== primeiraDataRef) {
      return null; // Contaminação de datas de apuração distintas no mesmo lote
    }
  }

  // 4. Consistência entre metadados e registros (validação anti-truncamento)
  if (typeof value.totalItens === "number" && value.totalItens !== itensValidos.length) {
    return null; // Metadado totalItens indica resposta truncada
  }
  if (typeof value.quantidadeEsperada === "number" && value.quantidadeEsperada !== itensValidos.length) {
    return null; // Metadado quantidadeEsperada indica resposta truncada
  }

  return {
    sucesso: Boolean(value.sucesso),
    versao: "1.0",
    dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
    cacheAtualizadoEmIso: isoTimestamp(value.cacheAtualizadoEmIso) ? value.cacheAtualizadoEmIso : null,
    estadoDisponibilidade: String(value.estadoDisponibilidade ?? "NORMAL"),
    avisoLegal: String(value.avisoLegal ?? ""),
    totalItens: itensValidos.length,
    itens: itensValidos,
  };
}

export function readSavedPrecos(storage: Pick<Storage, "getItem" | "removeItem">): PrecosPublicosResponse | null {
  try {
    storage.removeItem(LEGACY_STORAGE_KEY);
    storage.removeItem("deepfarms_agro_mercado_precos_v2");
    storage.removeItem("deepfarms_agro_mercado_precos_v3");
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const envelope: unknown = JSON.parse(raw);
    const parsed = record(envelope) && envelope.version === 4 ? parsePrecosResponse(envelope.dados) : null;
    if (!parsed) storage.removeItem(STORAGE_KEY);
    return parsed;
  } catch {
    return null;
  }
}

export function savePrecos(storage: Pick<Storage, "setItem">, value: unknown): boolean {
  const parsed = parsePrecosResponse(value);
  if (!parsed || !parsed.sucesso) return false;
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify({ version: 4, dados: parsed }));
    return true;
  } catch {
    return false;
  }
}

export interface BrowserLocation {
  hostname: string;
  protocol: string;
}

export function precosApiUrl(location: BrowserLocation): string {
  void location;
  return agroApiUrl("/api/v1/public/mercado/precos");
}

export async function fetchPrecosPublicos(
  location: BrowserLocation,
  signal?: AbortSignal
): Promise<PrecosPublicosResponse | null> {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), 15000);
  const abort = () => timeout.abort();
  signal?.addEventListener("abort", abort, { once: true });
  try {
  const response = await fetch(precosApiUrl(location), {
    credentials: "omit",
    cache: "no-store",
    signal: timeout.signal,
  });
  if (!response.ok) throw new Error(`Serviço de preços indisponível (HTTP ${response.status})`);
  const parsed = parsePrecosResponse(await response.json());
  if (!parsed) throw new Error("Resposta de preços públicos inválida");
  return parsed;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

export function formatarPrecoPublico(valor: number, moeda = "BRL"): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: moeda,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valor);
}

export function formatarDataPreco(dataIso: string): string {
  const [year, month, day] = dataIso.split("-");
  return `${day}/${month}/${year}`;
}

/**
 * Converte um valor monetário em BRL para a moeda estrangeira de destino com base na cotação PTAX Venda.
 * Fórmula: valorConvertido = valorBRL / cotacaoVenda
 * Rejeita valores não numéricos, nulos, infinitos ou taxas <= 0.
 */
export function converterBrlParaMoeda(
  valorBrl: number,
  cotacaoVenda: number | null | undefined
): number | null {
  if (
    typeof valorBrl !== "number" ||
    !Number.isFinite(valorBrl) ||
    valorBrl < 0 ||
    typeof cotacaoVenda !== "number" ||
    !Number.isFinite(cotacaoVenda) ||
    cotacaoVenda <= 0
  ) {
    return null;
  }
  const convertido = valorBrl / cotacaoVenda;
  if (!Number.isFinite(convertido) || convertido < 0) {
    return null;
  }
  return convertido;
}

/**
 * Formata um valor numérico em moeda internacional no padrão pt-BR.
 * Aplica convenção cambial: JPY e CLP com 0 decimais, demais com 2 decimais.
 */
export function formatarPrecoMoeda(valor: number, moeda: string): string {
  const fracoes = moeda === "JPY" || moeda === "CLP" ? 0 : 2;
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: moeda,
    minimumFractionDigits: fracoes,
    maximumFractionDigits: fracoes,
  }).format(valor);
}
