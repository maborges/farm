/**
 * Modelos, validação em runtime, persistência offline e cliente HTTP
 * para a previsão meteorológica do DeepFarms Agro.
 */

import { agroApiUrl } from "@/lib/api-url";

export type TipoDadoClima = "OBSERVADO" | "PREVISTO" | "CALCULADO";
export type StatusOperacionalClima =
  | "NORMAL"
  | "DESATUALIZADO"
  | "INDISPONIVEL"
  | "PROVEDOR_NAO_CONFIGURADO";

export interface CondicaoAtualClima {
  temperaturaC: number | null;
  sensacaoTermicaC: number | null;
  umidadeRelativaPct: number | null;
  ventoKmH: number | null;
  ventoDirecaoGraus: number | null;
  ventoRajadasKmH: number | null;
  precipitacaoMm: number | null;
  probabilidadeChuvaPct: number | null;
  condicaoDescricao: string | null;
  condicaoIcone: string | null;
}

export interface PrevisaoHorariaItemClima {
  horaIso: string;
  temperaturaC: number | null;
  sensacaoTermicaC: number | null;
  umidadePct: number | null;
  ventoKmH: number | null;
  ventoDirecaoGraus: number | null;
  ventoRajadasKmH: number | null;
  precipitacaoMm: number | null;
  probabilidadeChuvaPct: number | null;
  condicaoDescricao: string | null;
  condicaoIcone: string | null;
}

export interface PrevisaoDiariaItemClima {
  dataIso: string;
  diaSemana: string;
  tempMinC: number | null;
  tempMaxC: number | null;
  precipitacaoMm: number | null;
  probabilidadeChuvaPct: number | null;
  ventoMaxKmH: number | null;
  condicaoDescricao: string | null;
  condicaoIcone: string | null;
}

export interface ClimaPrevisaoData {
  latitude: number;
  longitude: number;
  latitudeGrid: number;
  longitudeGrid: number;
  fusoHorario: string;
  provedor: string;
  licencaFonte: string;
  tipoDado: TipoDadoClima;
  dadosSinteticos: boolean;

  temperaturaAtualC: number | null;
  sensacaoTermicaC: number | null;
  umidadeRelativaPct: number | null;
  ventoVelocidadeKmH: number | null;
  ventoDirecaoGraus: number | null;
  ventoRajadasKmH: number | null;
  precipitacaoMm: number | null;
  probabilidadeChuvaPct: number | null;
  condicaoDescricao: string | null;
  condicaoIcone: string | null;

  condicoesAtuais?: CondicaoAtualClima | null;
  previsaoHoraria: PrevisaoHorariaItemClima[];
  previsaoDiaria: PrevisaoDiariaItemClima[];

  horarioReferenciaIso: string;
  obtidoEmIso: string;
  validoAteIso: string;
  emCache: boolean;
  desatualizado: boolean;
  statusOperacional: StatusOperacionalClima;
  avisoLegal: string;
}

export interface ClimaPrevisaoEnvelopeV1 {
  version: 1;
  dados: ClimaPrevisaoData;
  localidadeNome: string;
  salvoEmIso: string;
  validoAteIso: string;
}

export const PREVISAO_STORAGE_PREFIX = "deepfarms_agro_clima_previsao_v1:";
export const PREVISAO_MAX_CACHE_AGE_MS = 60 * 60 * 1000;

/**
 * Gera a chave única de armazenamento para coordenadas quantizadas no grid.
 */
export function getPrevisaoCacheKey(lat: number, lon: number): string {
  const latRounded = Math.round(lat * 20) / 20;
  const lonRounded = Math.round(lon * 20) / 20;
  return `${PREVISAO_STORAGE_PREFIX}${latRounded.toFixed(2)}_${lonRounded.toFixed(2)}`;
}

/**
 * Converte graus de direção do vento (0° a 360°) para a rosa dos ventos em português.
 */
export function formatarDirecaoVento(graus: number | null): string {
  if (graus === null || !Number.isFinite(graus)) return "—";
  const normalizado = ((graus % 360) + 360) % 360;
  const setores = [
    "N", "NNE", "NE", "ENE", "L", "ESE", "SE", "SSE",
    "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"
  ];
  const indice = Math.round(normalizado / 22.5) % 16;
  return `${Math.round(normalizado)}° (${setores[indice]})`;
}

/**
 * Formata um timestamp ISO para o formato de hora local (ex: "14:00").
 */
export function formatarHorario(isoString: string, fusoHorario: string = "America/Sao_Paulo"): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "—";
    return new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: fusoHorario,
      hour12: false,
    }).format(d);
  } catch {
    return "—";
  }
}

/**
 * Formata uma data ISO para o formato dia e mês (ex: "23/10").
 */
export function formatarDataDiaMes(isoString: string, fusoHorario: string = "America/Sao_Paulo"): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "—";
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      timeZone: fusoHorario,
    }).format(d);
  } catch {
    return "—";
  }
}

/**
 * Valida rigorosamente se um payload arbitrário é uma ClimaPrevisaoData legítima.
 */
export function parsePrevisaoResponse(raw: unknown): ClimaPrevisaoData | null {
  if (!raw || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;

  if (typeof obj.latitude !== "number" || !Number.isFinite(obj.latitude)) return null;
  if (typeof obj.longitude !== "number" || !Number.isFinite(obj.longitude)) return null;
  if (obj.latitude < -90 || obj.latitude > 90) return null;
  if (obj.longitude < -180 || obj.longitude > 180) return null;

  const fuso = typeof obj.fusoHorario === "string" && obj.fusoHorario ? obj.fusoHorario : "America/Sao_Paulo";
  const provedor = typeof obj.provedor === "string" ? obj.provedor : "DESCONHECIDO";
  const licenca = typeof obj.licencaFonte === "string" ? obj.licencaFonte : "Não informada";
  const tipoDado: TipoDadoClima = obj.tipoDado === "OBSERVADO" || obj.tipoDado === "CALCULADO" ? obj.tipoDado : "PREVISTO";
  const dadosSinteticos = Boolean(obj.dadosSinteticos);

  // Parsing da previsão horária
  const horaria: PrevisaoHorariaItemClima[] = Array.isArray(obj.previsaoHoraria)
    ? obj.previsaoHoraria
        .filter((it): it is Record<string, unknown> => typeof it === "object" && it !== null && typeof it.horaIso === "string")
        .map((it) => ({
          horaIso: String(it.horaIso),
          temperaturaC: typeof it.temperaturaC === "number" && Number.isFinite(it.temperaturaC) ? it.temperaturaC : null,
          sensacaoTermicaC: typeof it.sensacaoTermicaC === "number" && Number.isFinite(it.sensacaoTermicaC) ? it.sensacaoTermicaC : null,
          umidadePct: typeof it.umidadePct === "number" && Number.isFinite(it.umidadePct) ? Math.round(it.umidadePct) : null,
          ventoKmH: typeof it.ventoKmH === "number" && Number.isFinite(it.ventoKmH) ? it.ventoKmH : null,
          ventoDirecaoGraus: typeof it.ventoDirecaoGraus === "number" && Number.isFinite(it.ventoDirecaoGraus) ? Math.round(it.ventoDirecaoGraus) : null,
          ventoRajadasKmH: typeof it.ventoRajadasKmH === "number" && Number.isFinite(it.ventoRajadasKmH) ? it.ventoRajadasKmH : null,
          precipitacaoMm: typeof it.precipitacaoMm === "number" && Number.isFinite(it.precipitacaoMm) ? it.precipitacaoMm : null,
          probabilidadeChuvaPct: typeof it.probabilidadeChuvaPct === "number" && Number.isFinite(it.probabilidadeChuvaPct) ? Math.round(it.probabilidadeChuvaPct) : null,
          condicaoDescricao: typeof it.condicaoDescricao === "string" ? it.condicaoDescricao : null,
          condicaoIcone: typeof it.condicaoIcone === "string" ? it.condicaoIcone : null,
        }))
    : [];

  // Parsing da previsão diária
  const diaria: PrevisaoDiariaItemClima[] = Array.isArray(obj.previsaoDiaria)
    ? obj.previsaoDiaria
        .filter((it): it is Record<string, unknown> => typeof it === "object" && it !== null && typeof it.dataIso === "string")
        .map((it) => ({
          dataIso: String(it.dataIso),
          diaSemana: typeof it.diaSemana === "string" ? it.diaSemana : "",
          tempMinC: typeof it.tempMinC === "number" && Number.isFinite(it.tempMinC) ? it.tempMinC : null,
          tempMaxC: typeof it.tempMaxC === "number" && Number.isFinite(it.tempMaxC) ? it.tempMaxC : null,
          precipitacaoMm: typeof it.precipitacaoMm === "number" && Number.isFinite(it.precipitacaoMm) ? it.precipitacaoMm : null,
          probabilidadeChuvaPct: typeof it.probabilidadeChuvaPct === "number" && Number.isFinite(it.probabilidadeChuvaPct) ? Math.round(it.probabilidadeChuvaPct) : null,
          ventoMaxKmH: typeof it.ventoMaxKmH === "number" && Number.isFinite(it.ventoMaxKmH) ? it.ventoMaxKmH : null,
          condicaoDescricao: typeof it.condicaoDescricao === "string" ? it.condicaoDescricao : null,
          condicaoIcone: typeof it.condicaoIcone === "string" ? it.condicaoIcone : null,
        }))
    : [];

  // Parsing de condições atuais
  let condicoesAtuais: CondicaoAtualClima | null = null;
  if (obj.condicoesAtuais && typeof obj.condicoesAtuais === "object") {
    const c = obj.condicoesAtuais as Record<string, unknown>;
    condicoesAtuais = {
      temperaturaC: typeof c.temperaturaC === "number" && Number.isFinite(c.temperaturaC) ? c.temperaturaC : null,
      sensacaoTermicaC: typeof c.sensacaoTermicaC === "number" && Number.isFinite(c.sensacaoTermicaC) ? c.sensacaoTermicaC : null,
      umidadeRelativaPct: typeof c.umidadeRelativaPct === "number" && Number.isFinite(c.umidadeRelativaPct) ? Math.round(c.umidadeRelativaPct) : null,
      ventoKmH: typeof c.ventoKmH === "number" && Number.isFinite(c.ventoKmH) ? c.ventoKmH : null,
      ventoDirecaoGraus: typeof c.ventoDirecaoGraus === "number" && Number.isFinite(c.ventoDirecaoGraus) ? Math.round(c.ventoDirecaoGraus) : null,
      ventoRajadasKmH: typeof c.ventoRajadasKmH === "number" && Number.isFinite(c.ventoRajadasKmH) ? c.ventoRajadasKmH : null,
      precipitacaoMm: typeof c.precipitacaoMm === "number" && Number.isFinite(c.precipitacaoMm) ? c.precipitacaoMm : null,
      probabilidadeChuvaPct: typeof c.probabilidadeChuvaPct === "number" && Number.isFinite(c.probabilidadeChuvaPct) ? Math.round(c.probabilidadeChuvaPct) : null,
      condicaoDescricao: typeof c.condicaoDescricao === "string" ? c.condicaoDescricao : null,
      condicaoIcone: typeof c.condicaoIcone === "string" ? c.condicaoIcone : null,
    };
  }

  const tempAtual = typeof obj.temperaturaAtualC === "number" && Number.isFinite(obj.temperaturaAtualC)
    ? obj.temperaturaAtualC
    : condicoesAtuais?.temperaturaC ?? null;

  return {
    latitude: obj.latitude,
    longitude: obj.longitude,
    latitudeGrid: typeof obj.latitudeGrid === "number" ? obj.latitudeGrid : obj.latitude,
    longitudeGrid: typeof obj.longitudeGrid === "number" ? obj.longitudeGrid : obj.longitude,
    fusoHorario: fuso,
    provedor,
    licencaFonte: licenca,
    tipoDado,
    dadosSinteticos,

    temperaturaAtualC: tempAtual,
    sensacaoTermicaC: typeof obj.sensacaoTermicaC === "number" && Number.isFinite(obj.sensacaoTermicaC)
      ? obj.sensacaoTermicaC
      : condicoesAtuais?.sensacaoTermicaC ?? null,
    umidadeRelativaPct: typeof obj.umidadeRelativaPct === "number" && Number.isFinite(obj.umidadeRelativaPct)
      ? Math.round(obj.umidadeRelativaPct)
      : condicoesAtuais?.umidadeRelativaPct ?? null,
    ventoVelocidadeKmH: typeof obj.ventoVelocidadeKmH === "number" && Number.isFinite(obj.ventoVelocidadeKmH)
      ? obj.ventoVelocidadeKmH
      : condicoesAtuais?.ventoKmH ?? null,
    ventoDirecaoGraus: typeof obj.ventoDirecaoGraus === "number" && Number.isFinite(obj.ventoDirecaoGraus)
      ? Math.round(obj.ventoDirecaoGraus)
      : condicoesAtuais?.ventoDirecaoGraus ?? null,
    ventoRajadasKmH: typeof obj.ventoRajadasKmH === "number" && Number.isFinite(obj.ventoRajadasKmH)
      ? obj.ventoRajadasKmH
      : condicoesAtuais?.ventoRajadasKmH ?? null,
    precipitacaoMm: typeof obj.precipitacaoMm === "number" && Number.isFinite(obj.precipitacaoMm)
      ? obj.precipitacaoMm
      : condicoesAtuais?.precipitacaoMm ?? null,
    probabilidadeChuvaPct: typeof obj.probabilidadeChuvaPct === "number" && Number.isFinite(obj.probabilidadeChuvaPct)
      ? Math.round(obj.probabilidadeChuvaPct)
      : condicoesAtuais?.probabilidadeChuvaPct ?? null,
    condicaoDescricao: typeof obj.condicaoDescricao === "string"
      ? obj.condicaoDescricao
      : condicoesAtuais?.condicaoDescricao ?? null,
    condicaoIcone: typeof obj.condicaoIcone === "string"
      ? obj.condicaoIcone
      : condicoesAtuais?.condicaoIcone ?? null,

    condicoesAtuais,
    previsaoHoraria: horaria,
    previsaoDiaria: diaria,

    horarioReferenciaIso: typeof obj.horarioReferenciaIso === "string" ? obj.horarioReferenciaIso : new Date().toISOString(),
    obtidoEmIso: typeof obj.obtidoEmIso === "string" ? obj.obtidoEmIso : new Date().toISOString(),
    validoAteIso: typeof obj.validoAteIso === "string" ? obj.validoAteIso : new Date(Date.now() + 1800000).toISOString(),
    emCache: Boolean(obj.emCache),
    desatualizado: Boolean(obj.desatualizado),
    statusOperacional: (obj.statusOperacional as StatusOperacionalClima) ?? "NORMAL",
    avisoLegal: typeof obj.avisoLegal === "string"
      ? obj.avisoLegal
      : "Dados meteorológicos para planejamento operacional. Não substituem medições in-situ da propriedade.",
  };
}

/**
 * Valida rigorosamente se um valor salvo no localStorage é um envelope de previsão válido.
 */
export function parseSavedPrevisao(value: unknown): ClimaPrevisaoEnvelopeV1 | null {
  if (!value || typeof value !== "object") return null;
  const env = value as Record<string, unknown>;

  if (env.version !== 1) return null;
  if (typeof env.localidadeNome !== "string" || !env.localidadeNome) return null;
  if (typeof env.salvoEmIso !== "string" || isNaN(Date.parse(env.salvoEmIso))) return null;
  if (typeof env.validoAteIso !== "string" || isNaN(Date.parse(env.validoAteIso))) return null;

  const dados = parsePrevisaoResponse(env.dados);
  if (!dados) return null;

  return {
    version: 1,
    dados,
    localidadeNome: env.localidadeNome,
    salvoEmIso: env.salvoEmIso,
    validoAteIso: env.validoAteIso,
  };
}

/**
 * Salva a previsão no localStorage com envelope versionado.
 */
export function savePrevisao(
  storage: Storage,
  key: string,
  dados: ClimaPrevisaoData,
  localidadeNome: string
): void {
  try {
    const savedAt = Date.now();
    const providerExpiry = Date.parse(dados.validoAteIso);
    const expiry = Math.min(
      Number.isFinite(providerExpiry) ? providerExpiry : savedAt + PREVISAO_MAX_CACHE_AGE_MS,
      savedAt + PREVISAO_MAX_CACHE_AGE_MS
    );
    const envelope: ClimaPrevisaoEnvelopeV1 = {
      version: 1,
      dados,
      localidadeNome,
      salvoEmIso: new Date(savedAt).toISOString(),
      validoAteIso: new Date(expiry).toISOString(),
    };
    storage.setItem(key, JSON.stringify(envelope));
  } catch {
    // Falha silenciosa em caso de QuotaExceededError
  }
}

/**
 * Lê e valida a previsão salva no localStorage.
 */
export function readSavedPrevisao(
  storage: Storage,
  key: string,
  nowMs: number = Date.now()
): ClimaPrevisaoEnvelopeV1 | null {
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const validated = parseSavedPrevisao(parsed);
    if (!validated) {
      storage.removeItem(key);
      return null;
    }
    const savedAt = Date.parse(validated.salvoEmIso);
    const expiresAt = Math.min(
      Date.parse(validated.validoAteIso),
      savedAt + PREVISAO_MAX_CACHE_AGE_MS
    );
    if (!Number.isFinite(savedAt) || !Number.isFinite(expiresAt) || nowMs >= expiresAt || nowMs < savedAt) {
      storage.removeItem(key);
      return null;
    }
    return validated;
  } catch {
    return null;
  }
}

/**
 * Remove a previsão salva para a chave indicada.
 */
export function clearSavedPrevisao(storage: Storage, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // Falha silenciosa
  }
}

export type FetchPrevisaoStatus =
  | "SUCESSO"
  | "PROVEDOR_NAO_LICENCIADO"
  | "LIMITE_EXCEDIDO"
  | "ERRO_SERVIDOR"
  | "PARAMETRO_INVALIDO"
  | "OFFLINE";

export interface FetchPrevisaoSuccess {
  ok: true;
  status: "SUCESSO";
  httpStatus: 200;
  dados: ClimaPrevisaoData;
  emCache: boolean;
  desatualizado: boolean;
}

export interface FetchPrevisaoError {
  ok: false;
  status: "PROVEDOR_NAO_LICENCIADO" | "LIMITE_EXCEDIDO" | "ERRO_SERVIDOR" | "PARAMETRO_INVALIDO" | "OFFLINE";
  httpStatus?: number;
  mensagem: string;
  detalhe?: string;
}

export type FetchPrevisaoOutcome = FetchPrevisaoSuccess | FetchPrevisaoError;

/**
 * Consulta o endpoint público de previsão meteorológica.
 */
export async function fetchClimaPrevisao(
  lat: number,
  lon: number,
  signal?: AbortSignal
): Promise<FetchPrevisaoOutcome> {
  const url = agroApiUrl(`/api/v1/public/clima/previsao?lat=${lat}&lon=${lon}`);

  try {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    if (res.status === 429) {
      return {
        ok: false,
        status: "LIMITE_EXCEDIDO",
        httpStatus: 429,
        mensagem: "Limite de consultas de previsão meteorológica atingido. Aguarde um minuto.",
      };
    }

    if (res.status === 503) {
      let detalhe = "";
      try {
        const body = (await res.json()) as { detail?: string };
        detalhe = typeof body.detail === "string" ? body.detail : "";
      } catch {
        // Ignora
      }

      const lower = detalhe.toLowerCase();
      if (lower.includes("licenciad") || lower.includes("licença")) {
        return {
          ok: false,
          status: "PROVEDOR_NAO_LICENCIADO",
          httpStatus: 503,
          mensagem: "Provedor meteorológico não licenciado para produção.",
          detalhe,
        };
      }

      return {
        ok: false,
        status: "ERRO_SERVIDOR",
        httpStatus: 503,
        mensagem: "Serviço meteorológico temporariamente indisponível.",
        detalhe: detalhe || undefined,
      };
    }

    if (res.status === 400 || res.status === 422) {
      return {
        ok: false,
        status: "PARAMETRO_INVALIDO",
        httpStatus: res.status,
        mensagem: "Coordenadas geográficas inválidas para consulta meteorológica.",
      };
    }

    if (!res.ok) {
      return {
        ok: false,
        status: "ERRO_SERVIDOR",
        httpStatus: res.status,
        mensagem: "Serviço meteorológico temporariamente indisponível.",
      };
    }

    const json: unknown = await res.json();
    const parsed = parsePrevisaoResponse(json);
    if (!parsed) {
      return {
        ok: false,
        status: "ERRO_SERVIDOR",
        httpStatus: 200,
        mensagem: "Payload de previsão corrompido ou incompleto retornado pelo servidor.",
      };
    }

    return {
      ok: true,
      status: "SUCESSO",
      httpStatus: 200,
      dados: parsed,
      emCache: parsed.emCache,
      desatualizado: parsed.desatualizado,
    };
  } catch (err: unknown) {
    if (signal?.aborted) {
      throw err;
    }
    return {
      ok: false,
      status: "OFFLINE",
      mensagem: "Não foi possível conectar ao servidor. Verifique sua conexão à internet.",
    };
  }
}
