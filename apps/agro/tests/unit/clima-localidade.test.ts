import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  clearSavedLocalidade,
  fetchMunicipios,
  LOCALIDADE_STORAGE_KEY,
  parseSavedLocalidade,
  readSavedLocalidade,
  saveLocalidade,
  type LocalidadeClima,
} from "../../src/lib/clima/localidade";
import {
  _resetLocalidadeStoreForTesting,
  clearLocalidade,
  getLocalidadeSnapshot,
  getServerLocalidadeSnapshot,
  setLocalidade,
  subscribeLocalidade,
} from "../../src/lib/clima/localidade-store";

describe("DEEPFARMS-AGRO-FREE-01F-CLIMA-01C — Validação e Persistência de Localidade", () => {
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
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      location: { hostname: "localhost", protocol: "http:" },
    };

    vi.stubGlobal("window", windowMock);
    vi.stubGlobal("localStorage", storageMock);

    _resetLocalidadeStoreForTesting();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parseSavedLocalidade: valida corretamente payload versionado íntegro", () => {
    const raw = {
      version: 1,
      localidade: {
        codigoIbge: 4106902,
        nome: "Curitiba",
        uf: "PR",
        estadoNome: "Paraná",
        latitude: -25.4195,
        longitude: -49.2646,
        fusoHorario: "America/Sao_Paulo",
        tipoOrigem: "CENTROIDE_IBGE",
        selecionadoEmIso: "2026-10-22T14:00:00.000Z",
      },
    };

    const parsed = parseSavedLocalidade(raw);
    expect(parsed).not.toBeNull();
    expect(parsed?.codigoIbge).toBe(4106902);
    expect(parsed?.nome).toBe("Curitiba");
    expect(parsed?.uf).toBe("PR");
    expect(parsed?.latitude).toBe(-25.4195);
    expect(parsed?.longitude).toBe(-49.2646);
    expect(parsed?.tipoOrigem).toBe("CENTROIDE_IBGE");
  });

  it("parseSavedLocalidade: valida payload de GPS com precisão estimada", () => {
    const raw = {
      version: 1,
      localidade: {
        nome: "Localização Atual (GPS)",
        uf: "",
        latitude: -23.5505,
        longitude: -46.6333,
        fusoHorario: "America/Sao_Paulo",
        tipoOrigem: "GPS",
        precisaoGpsMetros: 12,
        selecionadoEmIso: "2026-10-22T14:00:00.000Z",
      },
    };

    const parsed = parseSavedLocalidade(raw);
    expect(parsed).not.toBeNull();
    expect(parsed?.tipoOrigem).toBe("GPS");
    expect(parsed?.precisaoGpsMetros).toBe(12);
    expect(parsed?.codigoIbge).toBeUndefined();
  });

  it("parseSavedLocalidade: rejeita payload corrompido, versão incompatível ou fora dos limites", () => {
    expect(parseSavedLocalidade(null)).toBeNull();
    expect(parseSavedLocalidade("invalido")).toBeNull();
    expect(parseSavedLocalidade({ version: 2, localidade: {} })).toBeNull();

    // Latitude inválida (> 90)
    expect(
      parseSavedLocalidade({
        version: 1,
        localidade: {
          nome: "Invalido",
          uf: "SP",
          latitude: 95.0,
          longitude: -46.0,
          tipoOrigem: "CENTROIDE_IBGE",
        },
      })
    ).toBeNull();

    // Longitude inválida (< -180)
    expect(
      parseSavedLocalidade({
        version: 1,
        localidade: {
          nome: "Invalido",
          uf: "SP",
          latitude: -23.0,
          longitude: -185.0,
          tipoOrigem: "CENTROIDE_IBGE",
        },
      })
    ).toBeNull();

    // tipoOrigem desconhecido
    expect(
      parseSavedLocalidade({
        version: 1,
        localidade: {
          nome: "Invalido",
          uf: "SP",
          latitude: -23.0,
          longitude: -46.0,
          tipoOrigem: "PROVEDOR_TERCEIRO",
        },
      })
    ).toBeNull();
  });

  it("salva, lê e remove do localStorage de forma resiliente", () => {
    const loc: LocalidadeClima = {
      codigoIbge: 3550308,
      nome: "São Paulo",
      uf: "SP",
      latitude: -23.5505,
      longitude: -46.6333,
      fusoHorario: "America/Sao_Paulo",
      tipoOrigem: "CENTROIDE_IBGE",
      selecionadoEmIso: new Date().toISOString(),
    };

    saveLocalidade(window.localStorage, loc);
    expect(mockStorage[LOCALIDADE_STORAGE_KEY]).toBeDefined();

    const read = readSavedLocalidade(window.localStorage);
    expect(read).not.toBeNull();
    expect(read?.codigoIbge).toBe(3550308);
    expect(read?.nome).toBe("São Paulo");

    clearSavedLocalidade(window.localStorage);
    expect(readSavedLocalidade(window.localStorage)).toBeNull();
  });

  it("localidade-store: mantém isolamento SSR e notifica mudanças para subscribers", () => {
    const ssrState = getServerLocalidadeSnapshot();
    expect(ssrState.localidade).toBeNull();
    expect(ssrState.isLoaded).toBe(false);

    let notifications = 0;
    const unsubscribe = subscribeLocalidade(() => {
      notifications++;
    });

    const novaLoc: LocalidadeClima = {
      codigoIbge: 5208707,
      nome: "Goiânia",
      uf: "GO",
      latitude: -16.6869,
      longitude: -49.2648,
      fusoHorario: "America/Sao_Paulo",
      tipoOrigem: "CENTROIDE_IBGE",
      selecionadoEmIso: new Date().toISOString(),
    };

    setLocalidade(novaLoc);

    const snap1 = getLocalidadeSnapshot();
    expect(snap1.localidade?.nome).toBe("Goiânia");
    expect(snap1.localidade?.uf).toBe("GO");
    expect(notifications).toBe(1);

    clearLocalidade();
    const snap2 = getLocalidadeSnapshot();
    expect(snap2.localidade).toBeNull();
    expect(notifications).toBe(2);

    unsubscribe();
  });

  it("fetchMunicipios: retorna null quando parâmetros são insuficientes", async () => {
    expect(await fetchMunicipios()).toBeNull();
    expect(await fetchMunicipios("a")).toBeNull();
    expect(await fetchMunicipios("", "X")).toBeNull();
  });

  it("fetchMunicipios: executa chamada fetch e decodifica resposta com sucesso", async () => {
    const mockResponse = {
      sucesso: true,
      total: 1,
      limite: 25,
      offset: 0,
      fonte: "IBGE",
      versaoFonte: "2024.1",
      avisoMetodologico: "Centroides oficiais",
      itens: [
        {
          codigoIbge: 4106902,
          nome: "Curitiba",
          uf: "PR",
          estadoNome: "Paraná",
          latitude: -25.4195,
          longitude: -49.2646,
          fusoHorario: "America/Sao_Paulo",
          capital: true,
          tipoLocalidade: "CENTROIDE_MUNICIPAL",
        },
      ],
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    });
    vi.stubGlobal("fetch", fetchMock);

    const resultado = await fetchMunicipios("Curitiba", "PR");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(resultado).not.toBeNull();
    expect(resultado?.itens[0].nome).toBe("Curitiba");
    expect(resultado?.itens[0].uf).toBe("PR");
  });
});
