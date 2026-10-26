/**
 * Modelos, validação e persistência da localidade selecionada no módulo Clima.
 */

import { agroApiUrl } from "@/lib/api-url";

export type TipoOrigemLocalidade = "GPS" | "CENTROIDE_IBGE";

export interface LocalidadeClima {
  codigoIbge?: number;
  nome: string;
  uf: string;
  estadoNome?: string;
  latitude: number;
  longitude: number;
  fusoHorario: string;
  tipoOrigem: TipoOrigemLocalidade;
  precisaoGpsMetros?: number;
  selecionadoEmIso: string;
}

export interface MunicipioBuscaItem {
  codigoIbge: number;
  nome: string;
  uf: string;
  estadoNome: string;
  latitude: number;
  longitude: number;
  fusoHorario: string;
  capital: boolean;
  tipoLocalidade: "CENTROIDE_MUNICIPAL";
}

export interface MunicipiosBuscaResponse {
  sucesso: boolean;
  total: number;
  limite: number;
  offset: number;
  fonte: string;
  versaoFonte: string;
  avisoMetodologico: string;
  itens: MunicipioBuscaItem[];
}

export interface LocalidadeStorageEnvelopeV1 {
  version: 1;
  localidade: LocalidadeClima;
}

export const LOCALIDADE_STORAGE_KEY = "deepfarms_agro_clima_localidade_v1";

/**
 * Valida rigorosamente se um valor arbitrário recuperado do localStorage
 * corresponde a uma LocalidadeClima legítima.
 */
export function parseSavedLocalidade(value: unknown): LocalidadeClima | null {
  if (!value || typeof value !== "object") return null;

  const envelope = value as Record<string, unknown>;
  if (envelope.version !== 1 || !envelope.localidade || typeof envelope.localidade !== "object") {
    return null;
  }

  const raw = envelope.localidade as Record<string, unknown>;

  if (typeof raw.nome !== "string" || raw.nome.trim().length === 0) return null;
  if (typeof raw.uf !== "string") return null;
  if (typeof raw.latitude !== "number" || !Number.isFinite(raw.latitude)) return null;
  if (raw.latitude < -90.0 || raw.latitude > 90.0) return null;
  if (typeof raw.longitude !== "number" || !Number.isFinite(raw.longitude)) return null;
  if (raw.longitude < -180.0 || raw.longitude > 180.0) return null;

  if (raw.tipoOrigem !== "GPS" && raw.tipoOrigem !== "CENTROIDE_IBGE") return null;

  const fuso = typeof raw.fusoHorario === "string" && raw.fusoHorario.length > 0
    ? raw.fusoHorario
    : "America/Sao_Paulo";

  const selecionadoEm = typeof raw.selecionadoEmIso === "string" && !isNaN(Date.parse(raw.selecionadoEmIso))
    ? raw.selecionadoEmIso
    : new Date().toISOString();

  return {
    codigoIbge: typeof raw.codigoIbge === "number" ? raw.codigoIbge : undefined,
    nome: raw.nome.trim(),
    uf: raw.uf.trim().toUpperCase(),
    estadoNome: typeof raw.estadoNome === "string" ? raw.estadoNome : undefined,
    latitude: raw.latitude,
    longitude: raw.longitude,
    fusoHorario: fuso,
    tipoOrigem: raw.tipoOrigem,
    precisaoGpsMetros: typeof raw.precisaoGpsMetros === "number" ? raw.precisaoGpsMetros : undefined,
    selecionadoEmIso: selecionadoEm,
  };
}

/**
 * Salva a localidade no localStorage com envelope versionado.
 */
export function saveLocalidade(storage: Storage, loc: LocalidadeClima): void {
  try {
    const envelope: LocalidadeStorageEnvelopeV1 = {
      version: 1,
      localidade: loc,
    };
    storage.setItem(LOCALIDADE_STORAGE_KEY, JSON.stringify(envelope));
  } catch {
    // Falha silenciosa em caso de QuotaExceededError ou Storage restrito
  }
}

/**
 * Lê e valida a localidade persistida no localStorage.
 */
export function readSavedLocalidade(storage: Storage): LocalidadeClima | null {
  try {
    const raw = storage.getItem(LOCALIDADE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    return parseSavedLocalidade(parsed);
  } catch {
    return null;
  }
}

/**
 * Remove a localidade salva do localStorage.
 */
export function clearSavedLocalidade(storage: Storage): void {
  try {
    storage.removeItem(LOCALIDADE_STORAGE_KEY);
  } catch {
    // Falha silenciosa
  }
}

export type FetchMunicipiosStatus =
  | "SUCESSO"
  | "NENHUM_ENCONTRADO"
  | "CATALOGO_INDISPONIVEL"
  | "ERRO_COMUNICACAO"
  | "PARAMETROS_INVALIDOS";

export interface FetchMunicipiosSuccess extends MunicipiosBuscaResponse {
  ok: true;
  status: "SUCESSO";
  httpStatus: 200;
}

export interface FetchMunicipiosEmpty {
  ok: true;
  status: "NENHUM_ENCONTRADO";
  httpStatus: 200;
  sucesso: true;
  total: 0;
  limite: number;
  offset: number;
  fonte: string;
  versaoFonte: string;
  avisoMetodologico: string;
  itens: MunicipioBuscaItem[];
  mensagem: string;
}

export interface FetchMunicipiosError {
  ok: false;
  status: "CATALOGO_INDISPONIVEL" | "ERRO_COMUNICACAO" | "PARAMETROS_INVALIDOS";
  httpStatus?: number;
  sucesso: false;
  total: 0;
  itens: MunicipioBuscaItem[];
  mensagem: string;
}

export type FetchMunicipiosResult =
  | FetchMunicipiosSuccess
  | FetchMunicipiosEmpty
  | FetchMunicipiosError;

/**
 * Consulta a API pública de municípios com tipagem discriminada de estados e erros.
 */
export async function fetchMunicipios(
  query?: string,
  uf?: string,
  signal?: AbortSignal
): Promise<FetchMunicipiosResult | null> {
  const params = new URLSearchParams();
  if (query && query.trim().length >= 2) {
    params.set("q", query.trim());
  }
  if (uf && uf.trim().length === 2 && uf.trim().toUpperCase() !== "TODAS") {
    params.set("uf", uf.trim().toUpperCase());
  }

  if (!params.has("q") && !params.has("uf")) {
    return null;
  }

  params.set("limit", "25");

  try {
    const url = agroApiUrl(`/api/v1/public/clima/municipios?${params.toString()}`);
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    if (res.status === 503) {
      return {
        ok: false,
        sucesso: false,
        status: "CATALOGO_INDISPONIVEL",
        httpStatus: 503,
        total: 0,
        itens: [],
        mensagem: "Catálogo oficial de municípios temporariamente indisponível no servidor.",
      };
    }

    if (res.status === 400 || res.status === 422) {
      return {
        ok: false,
        sucesso: false,
        status: "PARAMETROS_INVALIDOS",
        httpStatus: res.status,
        total: 0,
        itens: [],
        mensagem: "Critérios de busca inválidos. Verifique o nome digitado ou o estado selecionado.",
      };
    }

    if (!res.ok) {
      return {
        ok: false,
        sucesso: false,
        status: "ERRO_COMUNICACAO",
        httpStatus: res.status,
        total: 0,
        itens: [],
        mensagem: `Falha na comunicação com o serviço de municípios (HTTP ${res.status}).`,
      };
    }

    const data = (await res.json()) as MunicipiosBuscaResponse;
    if (data && data.sucesso && Array.isArray(data.itens)) {
      if (data.itens.length === 0) {
        return {
          ok: true,
          status: "NENHUM_ENCONTRADO",
          httpStatus: 200,
          sucesso: true,
          total: 0,
          limite: data.limite ?? 25,
          offset: data.offset ?? 0,
          fonte: data.fonte ?? "",
          versaoFonte: data.versaoFonte ?? "",
          avisoMetodologico: data.avisoMetodologico ?? "",
          itens: [],
          mensagem: "Nenhum município encontrado para os critérios informados.",
        };
      }

      return {
        ...data,
        ok: true,
        status: "SUCESSO",
        httpStatus: 200,
      };
    }

    return {
      ok: false,
      sucesso: false,
      status: "ERRO_COMUNICACAO",
      httpStatus: 200,
      total: 0,
      itens: [],
      mensagem: "Resposta inválida recebida do serviço de municípios.",
    };
  } catch (err: unknown) {
    if (signal?.aborted) {
      throw err;
    }
    return {
      ok: false,
      sucesso: false,
      status: "ERRO_COMUNICACAO",
      total: 0,
      itens: [],
      mensagem: "Não foi possível conectar ao servidor. Verifique sua conexão de rede.",
    };
  }
}

