import { agroApiUrl } from "@/lib/api-url";

/**
 * Módulo de parsing, armazenamento offline e formatação de estatísticas oficiais IBGE/SIDRA.
 * Atende às pesquisas PAM, PPM e LSPA em níveis Brasil, UF e Município.
 */

export type TipoProdutoIbge = "LAVOURA" | "REBANHO" | "PRODUCAO_ANIMAL";
export type NivelTerritorialIbge = "BRASIL" | "UF" | "MUNICIPIO";
export type FontePesquisaIbge = "PAM" | "PPM" | "LSPA";
export type PeriodicidadeIbge = "ANUAL" | "MENSAL";

export interface ProdutoCatalogoIbge {
  id: string;
  nome: string;
  tipo: TipoProdutoIbge;
  pesquisa: string;
  indicadores: string[];
  suportaLspa: boolean;
}

export interface UfIbge {
  codigo: string;
  sigla: string;
  nome: string;
}

export interface CatalogoIbgeResponse {
  sucesso: boolean;
  versao: "1.0";
  fonteOficial: string;
  dataConsultaIso: string;
  anoMinimo: number;
  produtos: ProdutoCatalogoIbge[];
  ufs: UfIbge[];
}

export interface MunicipioIbge {
  codigo: string;
  nome: string;
}

export interface MunicipiosIbgeResponse {
  sucesso: boolean;
  versao: "1.0";
  fonteOficial: string;
  dataConsultaIso: string;
  cacheAtualizadoEmIso: string | null;
  estadoDisponibilidade: string;
  estaDesatualizado: boolean;
  uf: string;
  itens: MunicipioIbge[];
}

export interface PontoSerieIbge {
  periodo: string;
  valor: number | null;
  simboloIbge: string | null;
}

export interface IndicadorIbge {
  id: string;
  nomeOficial: string;
  codigoVariavelSidra: number;
  recorte: string | null;
  unidade: string;
  pontos: PontoSerieIbge[];
  ultimoPeriodo: string | null;
  ultimoValor: number | null;
}

export interface LocalidadeIbge {
  nivel: NivelTerritorialIbge;
  codigo: string;
  nome: string;
}

export interface ProdutoIbge {
  id: string;
  nome: string;
  tipo: TipoProdutoIbge;
}

export interface EstatisticasIbgeResponse {
  sucesso: boolean;
  versao: "1.0";
  fonteOficial: string;
  dataConsultaIso: string;
  cacheAtualizadoEmIso: string | null;
  estadoDisponibilidade: "NORMAL" | "DEFASADO" | "SEM_DADOS" | "FONTE_INDISPONIVEL" | "INDISPONIVEL" | string;
  estaDesatualizado: boolean;
  avisoLegal: string;
  pesquisa: string;
  fontePesquisa: FontePesquisaIbge;
  tabelaSidra: number;
  urlTabela: string;
  periodicidade: PeriodicidadeIbge;
  produto: ProdutoIbge;
  localidade: LocalidadeIbge;
  periodoSolicitado: string;
  ultimoPeriodoDisponivel: string | null;
  dataAtualizacaoFonte: string | null;
  avisoDefasagem: string | null;
  indicadores: IndicadorIbge[];
}

export interface ConsultaIbgeParams {
  produto: string;
  nivel?: NivelTerritorialIbge;
  uf?: string;
  municipio?: string;
  anos?: number;
  fonte?: "PAM" | "LSPA";
}

const STORAGE_PREFIX = "deepfarms_agro_mercado_ibge_v1_";
const CATALOGO_STORAGE_KEY = "deepfarms_agro_mercado_ibge_cat_v1";

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isoTimestamp(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

export function parsePontoSerie(value: unknown): PontoSerieIbge | null {
  if (!record(value)) return null;
  const periodo = String(value.periodo ?? "");
  if (!periodo) return null;
  const valor = typeof value.valor === "number" && Number.isFinite(value.valor) ? value.valor : null;
  const simboloIbge = value.simboloIbge ? String(value.simboloIbge) : null;
  return { periodo, valor, simboloIbge };
}

export function parseIndicador(value: unknown): IndicadorIbge | null {
  if (!record(value) || !Array.isArray(value.pontos)) return null;
  const id = String(value.id ?? "");
  const nomeOficial = String(value.nomeOficial ?? "");
  const codigoVariavelSidra = Number(value.codigoVariavelSidra);
  const recorte = value.recorte ? String(value.recorte) : null;
  const unidade = String(value.unidade ?? "");
  if (!id || !nomeOficial || !Number.isFinite(codigoVariavelSidra)) return null;

  const pontos = value.pontos.map(parsePontoSerie).filter((p): p is PontoSerieIbge => p !== null);
  const ultimoPeriodo = value.ultimoPeriodo ? String(value.ultimoPeriodo) : null;
  const ultimoValor = typeof value.ultimoValor === "number" && Number.isFinite(value.ultimoValor) ? value.ultimoValor : null;

  return {
    id,
    nomeOficial,
    codigoVariavelSidra,
    recorte,
    unidade,
    pontos,
    ultimoPeriodo,
    ultimoValor,
  };
}

export function parseEstatisticasIbge(value: unknown): EstatisticasIbgeResponse | null {
  if (!record(value) || value.versao !== "1.0" || !Array.isArray(value.indicadores)) {
    return null;
  }

  const produtoRaw = record(value.produto) ? value.produto : null;
  const localidadeRaw = record(value.localidade) ? value.localidade : null;
  if (!produtoRaw || !localidadeRaw) return null;

  const produto: ProdutoIbge = {
    id: String(produtoRaw.id ?? ""),
    nome: String(produtoRaw.nome ?? ""),
    tipo: (produtoRaw.tipo as TipoProdutoIbge) || "LAVOURA",
  };

  const localidade: LocalidadeIbge = {
    nivel: (localidadeRaw.nivel as NivelTerritorialIbge) || "BRASIL",
    codigo: String(localidadeRaw.codigo ?? "1"),
    nome: String(localidadeRaw.nome ?? ""),
  };

  const indicadores = value.indicadores.map(parseIndicador).filter((i): i is IndicadorIbge => i !== null);

  return {
    sucesso: Boolean(value.sucesso),
    versao: "1.0",
    fonteOficial: String(value.fonteOficial ?? ""),
    dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
    cacheAtualizadoEmIso: isoTimestamp(value.cacheAtualizadoEmIso) ? value.cacheAtualizadoEmIso : null,
    estadoDisponibilidade: String(value.estadoDisponibilidade ?? "NORMAL"),
    estaDesatualizado: Boolean(value.estaDesatualizado),
    avisoLegal: String(value.avisoLegal ?? ""),
    pesquisa: String(value.pesquisa ?? ""),
    fontePesquisa: (value.fontePesquisa as FontePesquisaIbge) || "PAM",
    tabelaSidra: Number(value.tabelaSidra) || 0,
    urlTabela: String(value.urlTabela ?? ""),
    periodicidade: (value.periodicidade as PeriodicidadeIbge) || "ANUAL",
    produto,
    localidade,
    periodoSolicitado: String(value.periodoSolicitado ?? ""),
    ultimoPeriodoDisponivel: value.ultimoPeriodoDisponivel ? String(value.ultimoPeriodoDisponivel) : null,
    dataAtualizacaoFonte: value.dataAtualizacaoFonte ? String(value.dataAtualizacaoFonte) : null,
    avisoDefasagem: value.avisoDefasagem ? String(value.avisoDefasagem) : null,
    indicadores,
  };
}

export function markIbgeUnavailable(value: EstatisticasIbgeResponse): EstatisticasIbgeResponse {
  return {
    ...value,
    estadoDisponibilidade: "FONTE_INDISPONIVEL",
    estaDesatualizado: true,
    avisoDefasagem: "Fonte indisponível; exibindo a última estatística salva, que pode estar desatualizada.",
  };
}

export function parseCatalogoIbge(value: unknown): CatalogoIbgeResponse | null {
  if (!record(value) || value.versao !== "1.0" || !Array.isArray(value.produtos) || !Array.isArray(value.ufs)) {
    return null;
  }

  const produtos: ProdutoCatalogoIbge[] = value.produtos
    .filter(record)
    .map((p) => ({
      id: String(p.id ?? ""),
      nome: String(p.nome ?? ""),
      tipo: (p.tipo as TipoProdutoIbge) || "LAVOURA",
      pesquisa: String(p.pesquisa ?? ""),
      indicadores: Array.isArray(p.indicadores) ? p.indicadores.map(String) : [],
      suportaLspa: Boolean(p.suportaLspa),
    }))
    .filter((p) => p.id && p.nome);

  const ufs: UfIbge[] = value.ufs
    .filter(record)
    .map((u) => ({
      codigo: String(u.codigo ?? ""),
      sigla: String(u.sigla ?? ""),
      nome: String(u.nome ?? ""),
    }))
    .filter((u) => u.codigo && u.sigla);

  return {
    sucesso: Boolean(value.sucesso),
    versao: "1.0",
    fonteOficial: String(value.fonteOficial ?? ""),
    dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
    anoMinimo: Number(value.anoMinimo) || 1974,
    produtos,
    ufs,
  };
}

export function parseMunicipiosIbge(value: unknown): MunicipiosIbgeResponse | null {
  if (!record(value) || value.versao !== "1.0" || !Array.isArray(value.itens)) {
    return null;
  }

  const itens: MunicipioIbge[] = value.itens
    .filter(record)
    .map((m) => ({
      codigo: String(m.codigo ?? ""),
      nome: String(m.nome ?? ""),
    }))
    .filter((m) => m.codigo && m.nome);

  return {
    sucesso: Boolean(value.sucesso),
    versao: "1.0",
    fonteOficial: String(value.fonteOficial ?? ""),
    dataConsultaIso: isoTimestamp(value.dataConsultaIso) ? value.dataConsultaIso : new Date().toISOString(),
    cacheAtualizadoEmIso: isoTimestamp(value.cacheAtualizadoEmIso) ? value.cacheAtualizadoEmIso : null,
    estadoDisponibilidade: String(value.estadoDisponibilidade ?? "NORMAL"),
    estaDesatualizado: Boolean(value.estaDesatualizado),
    uf: String(value.uf ?? ""),
    itens,
  };
}

export interface BrowserLocation {
  hostname: string;
  protocol: string;
}

export function ibgeApiBaseUrl(location: BrowserLocation): string {
  void location;
  return agroApiUrl("/api/v1/public/mercado/ibge");
}

export function gerarQueryKey(params: ConsultaIbgeParams): string {
  const nivel = params.nivel ?? "BRASIL";
  const territorial = nivel === "BRASIL" ? "BR" : nivel === "UF" ? `UF_${params.uf ?? ""}` : `MUN_${params.municipio ?? ""}`;
  const fonte = params.fonte ? `_${params.fonte}` : "";
  return `${params.produto}_${territorial}${fonte}`;
}

export function readSavedIbge(
  storage: Pick<Storage, "getItem" | "removeItem">,
  queryKey: string
): EstatisticasIbgeResponse | null {
  try {
    const raw = storage.getItem(STORAGE_PREFIX + queryKey);
    if (!raw) return null;
    const envelope: unknown = JSON.parse(raw);
    const parsed = record(envelope) && envelope.version === 1 ? parseEstatisticasIbge(envelope.dados) : null;
    if (!parsed) storage.removeItem(STORAGE_PREFIX + queryKey);
    return parsed;
  } catch {
    return null;
  }
}

export function saveIbge(
  storage: Pick<Storage, "setItem">,
  queryKey: string,
  value: EstatisticasIbgeResponse
): boolean {
  try {
    storage.setItem(STORAGE_PREFIX + queryKey, JSON.stringify({ version: 1, dados: value }));
    return true;
  } catch {
    return false;
  }
}

export function readSavedCatalogo(storage: Pick<Storage, "getItem" | "removeItem">): CatalogoIbgeResponse | null {
  try {
    const raw = storage.getItem(CATALOGO_STORAGE_KEY);
    if (!raw) return null;
    const envelope: unknown = JSON.parse(raw);
    const parsed = record(envelope) && envelope.version === 1 ? parseCatalogoIbge(envelope.dados) : null;
    if (!parsed) storage.removeItem(CATALOGO_STORAGE_KEY);
    return parsed;
  } catch {
    return null;
  }
}

export function saveCatalogo(storage: Pick<Storage, "setItem">, value: CatalogoIbgeResponse): boolean {
  try {
    storage.setItem(CATALOGO_STORAGE_KEY, JSON.stringify({ version: 1, dados: value }));
    return true;
  } catch {
    return false;
  }
}

export async function fetchIbgeCatalogo(
  location: BrowserLocation,
  signal?: AbortSignal
): Promise<CatalogoIbgeResponse | null> {
  const base = ibgeApiBaseUrl(location);
  const response = await fetch(`${base}/catalogo`, {
    credentials: "omit",
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Catálogo IBGE indisponível (HTTP ${response.status})`);
  }
  const payload: unknown = await response.json();
  const parsed = parseCatalogoIbge(payload);
  if (!parsed) {
    throw new Error("Resposta de catálogo IBGE inválida");
  }
  return parsed;
}

export async function fetchIbgeMunicipios(
  location: BrowserLocation,
  uf: string,
  signal?: AbortSignal
): Promise<MunicipiosIbgeResponse | null> {
  const base = ibgeApiBaseUrl(location);
  const response = await fetch(`${base}/municipios/${encodeURIComponent(uf)}`, {
    credentials: "omit",
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Municípios da UF ${uf} indisponíveis (HTTP ${response.status})`);
  }
  const payload: unknown = await response.json();
  const parsed = parseMunicipiosIbge(payload);
  if (!parsed) {
    throw new Error("Resposta de municípios IBGE inválida");
  }
  return parsed;
}

export async function fetchIbgeEstatisticas(
  location: BrowserLocation,
  params: ConsultaIbgeParams,
  signal?: AbortSignal
): Promise<EstatisticasIbgeResponse | null> {
  const base = ibgeApiBaseUrl(location);
  const query = new URLSearchParams({ produto: params.produto, nivel: params.nivel ?? "BRASIL" });
  if (params.uf) query.set("uf", params.uf);
  if (params.municipio) query.set("municipio", params.municipio);
  if (params.anos) query.set("anos", String(params.anos));
  if (params.fonte) query.set("fonte", params.fonte);

  const response = await fetch(`${base}/estatisticas?${query.toString()}`, {
    credentials: "omit",
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Estatísticas IBGE indisponíveis (HTTP ${response.status})`);
  }
  const payload: unknown = await response.json();
  const parsed = parseEstatisticasIbge(payload);
  if (!parsed) {
    throw new Error("Resposta de estatísticas IBGE inválida");
  }
  return parsed;
}

/**
 * Formata o valor numérico com precisão e separadores no padrão pt-BR.
 */
export function formatarValorIbge(valor: number | null, unidade: string): string {
  if (valor === null || !Number.isFinite(valor)) {
    return "Dado inibido / s/ dado";
  }

  const fracDigits = valor % 1 === 0 ? 0 : 2;
  const numFormatado = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: fracDigits,
    maximumFractionDigits: 2,
  }).format(valor);

  if (!unidade) return numFormatado;
  return `${numFormatado} ${unidade}`;
}

const MESES_PT_BR = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

/**
 * Formata o período de apuração (ex: '2024' ou '2024-08' -> 'Agosto/2024').
 */
export function formatarPeriodoIbge(periodo: string | null, periodicidade: PeriodicidadeIbge): string {
  if (!periodo) return "Não informado";
  if (periodicidade === "MENSAL" && periodo.includes("-")) {
    const [year, monthStr] = periodo.split("-");
    const month = parseInt(monthStr, 10);
    if (month >= 1 && month <= 12) {
      return `${MESES_PT_BR[month - 1]}/${year}`;
    }
  }
  return periodo;
}
