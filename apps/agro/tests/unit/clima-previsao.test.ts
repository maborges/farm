import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  clearSavedPrevisao,
  fetchClimaPrevisao,
  formatarDataDiaMes,
  formatarDirecaoVento,
  formatarHorario,
  getPrevisaoCacheKey,
  parsePrevisaoResponse,
  parseSavedPrevisao,
  PREVISAO_STORAGE_PREFIX,
  readSavedPrevisao,
  savePrevisao,
  type ClimaPrevisaoData,
} from "../../src/lib/clima/previsao";

describe("DEEPFARMS-AGRO-FREE-01F-CLIMA-01D — Previsão Meteorológica e Persistência", () => {
  let mockStorage: Record<string, string>;

  beforeEach(() => {
    mockStorage = {};
    const storageMock = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, val: string) => {
        mockStorage[key] = val;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
      clear: () => {
        mockStorage = {};
      },
      length: 0,
      key: () => null,
    };

    const windowMock = {
      localStorage: storageMock,
      location: { hostname: "localhost", protocol: "http:" },
    };

    vi.stubGlobal("window", windowMock);
    vi.stubGlobal("localStorage", storageMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // =========================================================================
  // 1. Funções Utilitárias e de Formatação
  // =========================================================================

  describe("getPrevisaoCacheKey", () => {
    it("quantiza latitude e longitude no grid de 0.05 e prefixa chave", () => {
      const key = getPrevisaoCacheKey(-23.5505, -46.6333);
      expect(key.startsWith(PREVISAO_STORAGE_PREFIX)).toBe(true);
      expect(key).toBe(`${PREVISAO_STORAGE_PREFIX}-23.55_-46.65`);
    });
  });

  describe("formatarDirecaoVento", () => {
    it("retorna travessão '—' para valores nulos ou inválidos", () => {
      expect(formatarDirecaoVento(null)).toBe("—");
      expect(formatarDirecaoVento(NaN)).toBe("—");
      expect(formatarDirecaoVento(Infinity)).toBe("—");
    });

    it("formata graus nos pontos cardeais e colaterais corretamente", () => {
      expect(formatarDirecaoVento(0)).toBe("0° (N)");
      expect(formatarDirecaoVento(360)).toBe("0° (N)");
      expect(formatarDirecaoVento(90)).toBe("90° (L)");
      expect(formatarDirecaoVento(180)).toBe("180° (S)");
      expect(formatarDirecaoVento(270)).toBe("270° (O)");
      expect(formatarDirecaoVento(45)).toBe("45° (NE)");
    });
  });

  describe("formatarHorario e formatarDataDiaMes", () => {
    it("formatarHorario formata timestamp respeitando fuso horário", () => {
      const iso = "2026-10-22T14:30:00Z";
      const formatado = formatarHorario(iso, "UTC");
      expect(formatado).toBe("14:30");
    });

    it("formatarHorario retorna '—' para strings inválidas", () => {
      expect(formatarHorario("invalid-iso")).toBe("—");
    });

    it("formatarDataDiaMes formata dia e mês respeitando fuso horário", () => {
      const iso = "2026-10-22T14:30:00Z";
      const formatado = formatarDataDiaMes(iso, "UTC");
      expect(formatado).toBe("22/10");
    });

    it("formatarDataDiaMes retorna '—' para datas corrompidas", () => {
      expect(formatarDataDiaMes("corrupted")).toBe("—");
    });
  });

  // =========================================================================
  // 2. Parser em Runtime de Previsão (parsePrevisaoResponse)
  // =========================================================================

  describe("parsePrevisaoResponse", () => {
    const validRaw = {
      latitude: -23.55,
      longitude: -46.63,
      latitudeGrid: -23.55,
      longitudeGrid: -46.65,
      fusoHorario: "America/Sao_Paulo",
      provedor: "TEST_FIXTURE",
      licencaFonte: "Uso de Testes",
      tipoDado: "PREVISTO",
      dadosSinteticos: true,
      temperaturaAtualC: 22.4,
      sensacaoTermicaC: 21.8,
      umidadeRelativaPct: 75,
      ventoVelocidadeKmH: 14.2,
      ventoDirecaoGraus: 180,
      ventoRajadasKmH: 22.0,
      precipitacaoMm: 0.0,
      probabilidadeChuvaPct: 10,
      condicaoDescricao: "Parcialmente nublado",
      condicaoIcone: "cloudsun",
      previsaoHoraria: [
        {
          horaIso: "2026-10-22T15:00:00-03:00",
          temperaturaC: 22.0,
          sensacaoTermicaC: 21.5,
          umidadePct: 76,
          ventoKmH: 13.5,
          ventoDirecaoGraus: 175,
          ventoRajadasKmH: 20.0,
          precipitacaoMm: 0.0,
          probabilidadeChuvaPct: 15,
          condicaoDescricao: "Parcialmente nublado",
          condicaoIcone: "cloudsun",
        },
      ],
      previsaoDiaria: [
        {
          dataIso: "2026-10-22",
          diaSemana: "qui",
          tempMinC: 17.0,
          tempMaxC: 25.0,
          precipitacaoMm: 1.2,
          probabilidadeChuvaPct: 30,
          ventoMaxKmH: 22.0,
          condicaoDescricao: "Chuva fraca",
          condicaoIcone: "cloudrain",
        },
      ],
      horarioReferenciaIso: "2026-10-22T14:00:00-03:00",
      obtidoEmIso: "2026-10-22T14:05:00-03:00",
      validoAteIso: "2026-10-22T15:05:00-03:00",
      emCache: false,
      desatualizado: false,
      statusOperacional: "NORMAL",
      avisoLegal: "Aviso legal de teste",
    };

    it("valida e converte payload íntegro", () => {
      const parsed = parsePrevisaoResponse(validRaw);
      expect(parsed).not.toBeNull();
      expect(parsed?.latitude).toBe(-23.55);
      expect(parsed?.temperaturaAtualC).toBe(22.4);
      expect(parsed?.dadosSinteticos).toBe(true);
      expect(parsed?.previsaoHoraria).toHaveLength(1);
      expect(parsed?.previsaoDiaria).toHaveLength(1);
    });

    it("rejeita coordenadas fora dos limites geográficos", () => {
      expect(parsePrevisaoResponse({ ...validRaw, latitude: 95 })).toBeNull();
      expect(parsePrevisaoResponse({ ...validRaw, latitude: -95 })).toBeNull();
      expect(parsePrevisaoResponse({ ...validRaw, longitude: 190 })).toBeNull();
      expect(parsePrevisaoResponse({ ...validRaw, longitude: -190 })).toBeNull();
      expect(parsePrevisaoResponse({ ...validRaw, latitude: "invalido" })).toBeNull();
    });

    it("tolera campos meteorológicos nulos sem falhar", () => {
      const rawComNulos = {
        latitude: -15.78,
        longitude: -47.92,
        temperaturaAtualC: null,
        sensacaoTermicaC: null,
        umidadeRelativaPct: null,
        ventoVelocidadeKmH: null,
        ventoDirecaoGraus: null,
        ventoRajadasKmH: null,
        precipitacaoMm: null,
        probabilidadeChuvaPct: null,
        condicaoDescricao: null,
        condicaoIcone: null,
        previsaoHoraria: [
          {
            horaIso: "2026-10-22T15:00:00-03:00",
            temperaturaC: null,
          },
        ],
        previsaoDiaria: [
          {
            dataIso: "2026-10-22",
            diaSemana: "qui",
            tempMinC: null,
            tempMaxC: null,
          },
        ],
      };

      const parsed = parsePrevisaoResponse(rawComNulos);
      expect(parsed).not.toBeNull();
      expect(parsed?.temperaturaAtualC).toBeNull();
      expect(parsed?.ventoRajadasKmH).toBeNull();
      expect(parsed?.previsaoHoraria[0].temperaturaC).toBeNull();
      expect(parsed?.previsaoDiaria[0].tempMinC).toBeNull();
    });

    it("rejeita inputs não objetos ou vazios", () => {
      expect(parsePrevisaoResponse(null)).toBeNull();
      expect(parsePrevisaoResponse(undefined)).toBeNull();
      expect(parsePrevisaoResponse("string")).toBeNull();
      expect(parsePrevisaoResponse(42)).toBeNull();
    });
  });

  // =========================================================================
  // 3. Envelope Versionado e Cache no localStorage
  // =========================================================================

  describe("parseSavedPrevisao e Operações de Cache", () => {
    const dadosExemplo: ClimaPrevisaoData = {
      latitude: -23.55,
      longitude: -46.63,
      latitudeGrid: -23.55,
      longitudeGrid: -46.65,
      fusoHorario: "America/Sao_Paulo",
      provedor: "TEST",
      licencaFonte: "Livre",
      tipoDado: "PREVISTO",
      dadosSinteticos: true,
      temperaturaAtualC: 20,
      sensacaoTermicaC: 20,
      umidadeRelativaPct: 70,
      ventoVelocidadeKmH: 10,
      ventoDirecaoGraus: 90,
      ventoRajadasKmH: 15,
      precipitacaoMm: 0,
      probabilidadeChuvaPct: 0,
      condicaoDescricao: "Céu limpo",
      condicaoIcone: "sun",
      previsaoHoraria: [],
      previsaoDiaria: [],
      horarioReferenciaIso: "2026-10-22T14:00:00Z",
      obtidoEmIso: "2026-10-22T14:00:00Z",
      validoAteIso: new Date(Date.now() + 3600000).toISOString(),
      emCache: false,
      desatualizado: false,
      statusOperacional: "NORMAL",
      avisoLegal: "Teste",
    };

    it("savePrevisao e readSavedPrevisao gravam e recuperam com versionamento", () => {
      const storage = window.localStorage;
      const key = getPrevisaoCacheKey(-23.55, -46.63);
      dadosExemplo.validoAteIso = new Date(Date.now() + 30 * 60 * 1000).toISOString();

      savePrevisao(storage, key, dadosExemplo, "São Paulo");
      const recuperado = readSavedPrevisao(storage, key);

      expect(recuperado).not.toBeNull();
      expect(recuperado?.version).toBe(1);
      expect(recuperado?.localidadeNome).toBe("São Paulo");
      expect(recuperado?.dados.temperaturaAtualC).toBe(20);
    });

    it("limita o cache offline combinado a 60 minutos e remove dados expirados", () => {
      const storage = window.localStorage;
      const key = "clima-expirado";
      const now = new Date("2026-10-26T12:00:00Z");
      vi.useFakeTimers();
      vi.setSystemTime(now);
      dadosExemplo.validoAteIso = "2026-10-26T14:00:00Z";

      savePrevisao(storage, key, dadosExemplo, "Local de teste");
      const raw = JSON.parse(storage.getItem(key) ?? "{}") as { validoAteIso: string };
      expect(Date.parse(raw.validoAteIso)).toBe(now.getTime() + 60 * 60 * 1000);
      expect(readSavedPrevisao(storage, key, now.getTime() + 60 * 60 * 1000)).toBeNull();
      expect(storage.getItem(key)).toBeNull();
      vi.useRealTimers();
    });

    it("readSavedPrevisao descarta e remove cache corrompido ou com versão incompatível", () => {
      const storage = window.localStorage;
      const key = "chave_invalida";

      storage.setItem(key, JSON.stringify({ version: 99, dados: {} }));
      const recuperado = readSavedPrevisao(storage, key);

      expect(recuperado).toBeNull();
      expect(storage.getItem(key)).toBeNull();
    });

    it("clearSavedPrevisao remove o item especificado", () => {
      const storage = window.localStorage;
      const key = "chave_para_limpar";

      storage.setItem(key, "dado");
      clearSavedPrevisao(storage, key);
      expect(storage.getItem(key)).toBeNull();
    });
  });

  // =========================================================================
  // 4. fetchClimaPrevisao: Cenários de Sucesso e Falha da API
  // =========================================================================

  describe("fetchClimaPrevisao", () => {
    it("processa HTTP 200 com payload válido com sucesso", async () => {
      const mockPayload = {
        latitude: -23.55,
        longitude: -46.63,
        fusoHorario: "America/Sao_Paulo",
        temperaturaAtualC: 25.5,
        previsaoHoraria: [],
        previsaoDiaria: [],
      };

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => mockPayload,
        })
      );

      const resultado = await fetchClimaPrevisao(-23.55, -46.63);
      expect(resultado.ok).toBe(true);
      if (resultado.ok) {
        expect(resultado.status).toBe("SUCESSO");
        expect(resultado.dados.temperaturaAtualC).toBe(25.5);
      }
    });

    it("trata HTTP 429 como LIMITE_EXCEDIDO", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 429,
        })
      );

      const resultado = await fetchClimaPrevisao(-23.55, -46.63);
      expect(resultado.ok).toBe(false);
      if (!resultado.ok) {
        expect(resultado.status).toBe("LIMITE_EXCEDIDO");
        expect(resultado.httpStatus).toBe(429);
      }
    });

    it("trata HTTP 503 com menção a licença como PROVEDOR_NAO_LICENCIADO", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Provedor Open-Meteo não licenciado para uso público em produção.",
          }),
        })
      );

      const resultado = await fetchClimaPrevisao(-23.55, -46.63);
      expect(resultado.ok).toBe(false);
      if (!resultado.ok) {
        expect(resultado.status).toBe("PROVEDOR_NAO_LICENCIADO");
        expect(resultado.httpStatus).toBe(503);
      }
    });

    it("trata HTTP 503 genérico como ERRO_SERVIDOR", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Serviço temporariamente indisponível para manutenção.",
          }),
        })
      );

      const resultado = await fetchClimaPrevisao(-23.55, -46.63);
      expect(resultado.ok).toBe(false);
      if (!resultado.ok) {
        expect(resultado.status).toBe("ERRO_SERVIDOR");
        expect(resultado.httpStatus).toBe(503);
      }
    });

    it("trata HTTP 400 ou 422 como PARAMETRO_INVALIDO", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 422,
        })
      );

      const resultado = await fetchClimaPrevisao(999, 999);
      expect(resultado.ok).toBe(false);
      if (!resultado.ok) {
        expect(resultado.status).toBe("PARAMETRO_INVALIDO");
        expect(resultado.httpStatus).toBe(422);
      }
    });

    it("trata falha de rede como OFFLINE", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
      );

      const resultado = await fetchClimaPrevisao(-23.55, -46.63);
      expect(resultado.ok).toBe(false);
      if (!resultado.ok) {
        expect(resultado.status).toBe("OFFLINE");
      }
    });

    it("repassa abort error quando cancelado por AbortController", async () => {
      const abortError = new DOMException("Aborted", "AbortError");
      const controller = new AbortController();
      controller.abort();

      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(abortError)
      );

      await expect(
        fetchClimaPrevisao(-23.55, -46.63, controller.signal)
      ).rejects.toThrow();
    });
  });
});
