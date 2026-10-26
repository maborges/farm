import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  _resetMoedaStoreForTesting,
  getMoedaSnapshot,
  getServerMoedaSnapshot,
  mudarMoeda,
  subscribeMoeda,
} from "../../src/lib/mercado/moeda-store";
import type { PtaxPublicaV1 } from "../../src/lib/mercado/ptax";

describe("DEEPFARMS-AGRO-FREE-01E2F-B6B — Store Reativa de Moedas (moeda-store)", () => {
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
    vi.stubGlobal("navigator", { onLine: false }); // Testes determinísticos offline para validar sincronização

    _resetMoedaStoreForTesting();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("retorna o snapshot padrão para SSR", () => {
    const serverSnap = getServerMoedaSnapshot();
    expect(serverSnap.currency).toBe("USD");
    expect(serverSnap.quote).toBeNull();
    expect(serverSnap.loading).toBe(false);
  });

  it("atualiza moeda e notifica subscribers ao mudar de moeda", async () => {
    let notified = false;
    const unsubscribe = subscribeMoeda(() => {
      notified = true;
    });

    await mudarMoeda("EUR");

    const snapshot = getMoedaSnapshot();
    expect(snapshot.currency).toBe("EUR");
    expect(mockStorage["deepfarms_agro_mercado_moeda_v1"]).toBe("EUR");
    expect(notified).toBe(true);

    unsubscribe();
  });

  it("recupera cotação em cache instantaneamente para a nova moeda", async () => {
    const mockQuoteEur: PtaxPublicaV1 = {
      sucesso: true,
      versao: "1.0",
      indicador: "CAMBIO_PTAX",
      moeda: "EUR",
      moedaReferencia: "BRL",
      cotacaoCompra: 6.12,
      cotacaoVenda: 6.1245,
      dataCotacao: "2024-10-15",
      dataHoraBoletimIso: "2024-10-15T13:00:00.000-03:00",
      tipoBoletim: "Fechamento PTAX",
      fonteOficial: "Banco Central do Brasil (BCB)",
      dataConsultaIso: "2026-10-21T18:00:00.000Z",
      cacheAtualizadoEmIso: "2026-10-21T18:00:00.000Z",
      estadoDisponibilidade: "NORMAL",
      estadoCotacao: "ULTIMO_FECHAMENTO_OFICIAL",
      estaDesatualizado: false,
      avisoLegal: "Aviso",
    };

    // Preenche cache prévio do Euro
    mockStorage["deepfarms_agro_mercado_cotacao_v1:EUR"] = JSON.stringify({
      currency: "EUR",
      quote: mockQuoteEur,
    });

    await mudarMoeda("EUR");

    const snapshot = getMoedaSnapshot();
    expect(snapshot.currency).toBe("EUR");
    expect(snapshot.quote).not.toBeNull();
    expect(snapshot.quote?.cotacaoVenda).toBe(6.1245);
    expect(snapshot.quote?.moeda).toBe("EUR");
  });

  it("não re-emite notificação se a alteração for redundante", async () => {
    await mudarMoeda("USD");

    let count = 0;
    const unsubscribe = subscribeMoeda(() => {
      count++;
    });

    // Muda para o mesmo USD sem nova cotação
    await mudarMoeda("USD");
    expect(count).toBe(0);

    unsubscribe();
  });
});
