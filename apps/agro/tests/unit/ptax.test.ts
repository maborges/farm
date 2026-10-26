import { describe, it, expect, beforeEach } from "vitest";
import {
  parsePtax,
  readSavedPtax,
  savePtax,
  formatPtax,
  formatDateBr,
  formatTimeBr,
  formatSyncBr,
  ptaxApiUrl,
  bcbPtaxUrl,
  parseBcbPtax,
  parseBcbPtaxIntraday,
  type PtaxPublicaV1,
} from "../../src/lib/mercado/ptax";

const VALID_PTAX_PAYLOAD: PtaxPublicaV1 = {
  sucesso: true,
  versao: "1.0",
  indicador: "DOLAR_PTAX",
  moeda: "USD",
  moedaReferencia: "BRL",
  cotacaoCompra: 5.6372,
  cotacaoVenda: 5.6378,
  dataCotacao: "2024-10-15",
  dataHoraBoletimIso: "2024-10-15T13:06:27.393-03:00",
  tipoBoletim: "Fechamento PTAX",
  fonteOficial: "Banco Central do Brasil (BCB)",
  dataConsultaIso: "2026-10-16T21:40:00.000Z",
  cacheAtualizadoEmIso: "2026-10-16T21:30:00.000Z",
  estadoDisponibilidade: "NORMAL",
  estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
  estaDesatualizado: false,
  avisoLegal:
    "A PTAX é uma taxa de referência publicada pelo Banco Central do Brasil. Não representa cotação de câmbio em tempo real.",
};

describe("Módulo PTAX Frontend — Parsing, Validação e Formatação", () => {
  it("valida payload oficial com sucesso", () => {
    const parsed = parsePtax(VALID_PTAX_PAYLOAD);
    expect(parsed).not.toBeNull();
    expect(parsed?.cotacaoCompra).toBe(5.6372);
    expect(parsed?.cotacaoVenda).toBe(5.6378);
    expect(parsed?.dataCotacao).toBe("2024-10-15");
    expect(parsed?.estadoDisponibilidade).toBe("NORMAL");
    expect(parsed?.estaDesatualizado).toBe(false);
  });

  it("rejeita payloads inválidos ou com valores negativos/infinitos", () => {
    expect(parsePtax(null)).toBeNull();
    expect(parsePtax({})).toBeNull();
    expect(parsePtax({ ...VALID_PTAX_PAYLOAD, cotacaoCompra: -1 })).toBeNull();
    expect(parsePtax({ ...VALID_PTAX_PAYLOAD, cotacaoCompra: Number.NaN })).toBeNull();
    expect(parsePtax({ ...VALID_PTAX_PAYLOAD, cotacaoVenda: 5.0 })).toBeNull(); // compra > venda
    expect(parsePtax({ ...VALID_PTAX_PAYLOAD, versao: "2.0" })).toBeNull();
    expect(parsePtax({ ...VALID_PTAX_PAYLOAD, moeda: "EUR" })).toBeNull();
  });

  it("formata valor cambial da PTAX com 4 a 5 casas decimais", () => {
    const formatado = formatPtax(5.6372);
    // Deve conter R$ e o valor com vírgula decimal
    expect(formatado).toContain("5,6372");
    expect(formatado).toContain("R$");
  });

  it("formata data e horário oficial no fuso de São Paulo", () => {
    expect(formatDateBr("2024-10-15")).toBe("15/10/2024");
    const hora = formatTimeBr("2024-10-15T13:06:27.393-03:00");
    expect(hora).toBe("13:06");
  });

  it("constrói URL de API apropriada conforme hostname", () => {
    expect(ptaxApiUrl({ hostname: "localhost", protocol: "http:" })).toBe(
      "/api/v1/public/mercado/ptax"
    );
    expect(ptaxApiUrl({ hostname: "127.0.0.1", protocol: "http:" })).toBe(
      "/api/v1/public/mercado/ptax"
    );
    expect(ptaxApiUrl({ hostname: "192.168.0.2", protocol: "http:" })).toBe(
      "/api/v1/public/mercado/ptax"
    );
    expect(ptaxApiUrl({ hostname: "agro.deepfarms.com.br", protocol: "https:" })).toBe(
      "/api/v1/public/mercado/ptax"
    );
  });

  it("constrói e normaliza o fallback oficial do BCB", () => {
    expect(bcbPtaxUrl(new Date("2026-10-17T15:00:00.000Z"))).toContain(
      "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
    );
    const quote = parseBcbPtax({
      value: [{
        cotacaoCompra: 5.082,
        cotacaoVenda: 5.0826,
        dataHoraCotacao: "2026-10-16 13:04:14.548156",
      }],
    }, new Date("2026-10-17T15:00:00.000Z"));

    expect(quote?.cotacaoCompra).toBe(5.082);
    expect(quote?.dataCotacao).toBe("2026-10-16");
    expect(quote?.dataHoraBoletimIso).toBe("2026-10-16T13:04:14.548-03:00");
  });

  it("rejeita o fallback do BCB sem fechamento válido", () => {
    expect(parseBcbPtax({ value: [] }, new Date())).toBeNull();
    expect(parseBcbPtax({ value: [{ cotacaoCompra: 5.1, cotacaoVenda: 5.0 }] }, new Date())).toBeNull();
  });

  it("rejeita boletins BCB futuros ou com mais de sete dias", () => {
    const now = new Date("2026-10-17T15:00:00.000Z");
    expect(parseBcbPtax({ value: [{ cotacaoCompra: 5.1, cotacaoVenda: 5.2, dataHoraCotacao: "2026-10-09 12:00:00" }] }, now)).toBeNull();
    expect(parseBcbPtax({ value: [{ cotacaoCompra: 5.1, cotacaoVenda: 5.2, dataHoraCotacao: "2026-10-18 12:00:00" }] }, now)).toBeNull();
  });

  it("normaliza os boletins intradiários oficiais do BCB", () => {
    const series = parseBcbPtaxIntraday({
      value: [
        { cotacaoCompra: 5.06, cotacaoVenda: 5.061, dataHoraCotacao: "2026-10-15 10:03:45.504865", tipoBoletim: "Abertura" },
        { cotacaoCompra: 5.0515, cotacaoVenda: 5.0521, dataHoraCotacao: "2026-10-15 13:05:33.305854", tipoBoletim: "Fechamento PTAX" },
      ],
    });

    expect(series).toHaveLength(2);
    expect(series[0]?.hora).toBe("10:03");
    expect(series[1]?.tipoBoletim).toBe("Fechamento PTAX");
  });
});

describe("Persistência Offline Local (localStorage)", () => {
  let mockStorage: Record<string, string>;
  let storageAdapter: Pick<Storage, "getItem" | "setItem" | "removeItem">;

  beforeEach(() => {
    mockStorage = {};
    storageAdapter = {
      getItem: (key: string) => mockStorage[key] ?? null,
      setItem: (key: string, value: string) => {
        mockStorage[key] = value;
      },
      removeItem: (key: string) => {
        delete mockStorage[key];
      },
    };
  });

  it("salva e recupera cotação válida do storage", () => {
    const saved = savePtax(storageAdapter, VALID_PTAX_PAYLOAD);
    expect(saved).toBe(true);

    const retrieved = readSavedPtax(storageAdapter);
    expect(retrieved).not.toBeNull();
    expect(retrieved?.cotacaoCompra).toBe(5.6372);
    expect(retrieved?.cotacaoVenda).toBe(5.6378);
    expect(retrieved?.dataCotacao).toBe("2024-10-15");
  });

  it("limpa storage e retorna null se os dados salvos estiverem corrompidos", () => {
    storageAdapter.setItem("deepfarms_agro_mercado_ptax_v1", "{ invalid json");
    const retrieved = readSavedPtax(storageAdapter);
    expect(retrieved).toBeNull();
  });

  it("não armazena nem vaza dados confidenciais ou tokens no storage", () => {
    savePtax(storageAdapter, VALID_PTAX_PAYLOAD);
    const raw = storageAdapter.getItem("deepfarms_agro_mercado_ptax_v1");
    expect(raw).not.toBeNull();
    expect(raw).not.toContain("token");
    expect(raw).not.toContain("tenant");
    expect(raw).not.toContain("secret");
  });
});
