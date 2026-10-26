import { describe, expect, it, beforeEach } from "vitest";
import {
  formatarDataReferencia,
  formatarValorMacro,
  markMacroUnavailable,
  macroApiUrl,
  parseIndicadoresMacro,
  readSavedMacro,
  saveMacro,
  type IndicadorMacroItem,
  type IndicadoresMacroResponse,
} from "@/lib/mercado/macro";

const SAMPLE_PAYLOAD: IndicadoresMacroResponse = {
  sucesso: true,
  versao: "1.0",
  dataConsultaIso: "2026-10-19T20:00:00.000Z",
  cacheAtualizadoEmIso: "2026-10-19T19:50:00.000Z",
  estadoDisponibilidade: "NORMAL",
  estaDesatualizado: false,
  avisoLegal: "Aviso legal de teste",
  itens: [
    {
      id: "SELIC_META",
      nomeOficial: "Taxa de juros - Meta Selic definida pelo Copom",
      codigoSerieBcb: 432,
      valor: 13.75,
      unidade: "% a.a.",
      periodicidade: "DIARIA",
      dataReferencia: "2026-11-04",
      dataConsultaIso: "2026-10-19T20:00:00.000Z",
      fonteOficial: "Banco Central do Brasil (BCB)",
      estadoDisponibilidade: "NORMAL",
      estaDesatualizado: false,
      avisoLegal: "Aviso legal",
    },
    {
      id: "IPCA_MENSAL",
      nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA)",
      codigoSerieBcb: 433,
      valor: 0.82,
      unidade: "% a.m.",
      periodicidade: "MENSAL",
      dataReferencia: "2026-09-01",
      dataConsultaIso: "2026-10-19T20:00:00.000Z",
      fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
      estadoDisponibilidade: "NORMAL",
      estaDesatualizado: false,
      avisoLegal: "Aviso legal",
    },
    {
      id: "IPCA_12M",
      nomeOficial: "Índice nacional de preços ao consumidor-amplo (IPCA) - em 12 meses",
      codigoSerieBcb: 13522,
      valor: 4.58,
      unidade: "% em 12 meses",
      periodicidade: "MENSAL",
      dataReferencia: "2026-09-01",
      dataConsultaIso: "2026-10-19T20:00:00.000Z",
      fonteOficial: "IBGE / Banco Central do Brasil (BCB)",
      estadoDisponibilidade: "NORMAL",
      estaDesatualizado: false,
      avisoLegal: "Aviso legal",
    },
    {
      id: "EURO_PTAX",
      nomeOficial: "Taxa de câmbio - Euro / Real - comercial (fechamento PTAX)",
      codigoSerieBcb: 21619,
      valor: 5.6682,
      valorCompra: 5.6665,
      valorVenda: 5.6682,
      unidade: "BRL",
      periodicidade: "DIARIA",
      dataReferencia: "2026-10-19",
      dataConsultaIso: "2026-10-19T20:00:00.000Z",
      fonteOficial: "Banco Central do Brasil (BCB)",
      estadoDisponibilidade: "NORMAL",
      estaDesatualizado: false,
      avisoLegal: "Aviso legal",
    },
  ],
};

class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(key: string): string | null { return this.store.get(key) ?? null; }
  key(index: number): string | null { return Array.from(this.store.keys())[index] ?? null; }
  removeItem(key: string): void { this.store.delete(key); }
  setItem(key: string, value: string): void { this.store.set(key, value); }
}

describe("Módulo Macro — Parsing e Formatação", () => {
  it("deve validar e parsear payload completo da API", () => {
    const parsed = parseIndicadoresMacro(SAMPLE_PAYLOAD);
    expect(parsed).not.toBeNull();
    expect(parsed?.sucesso).toBe(true);
    expect(parsed?.itens).toHaveLength(4);

    const selic = parsed?.itens.find((i) => i.id === "SELIC_META");
    expect(selic?.valor).toBe(13.75);
    expect(selic?.unidade).toBe("% a.a.");
    expect(selic?.codigoSerieBcb).toBe(432);
  });

  it("deve rejeitar payload inválido ou malformado", () => {
    expect(parseIndicadoresMacro(null)).toBeNull();
    expect(parseIndicadoresMacro({})).toBeNull();
    expect(parseIndicadoresMacro({ versao: "2.0", itens: [] })).toBeNull();
    expect(parseIndicadoresMacro({ sucesso: true, versao: "1.0", itens: "invalido" })).toBeNull();
  });

  it("deve formatar valores com percentuais e moedas corretamente em pt-BR", () => {
    const selic: IndicadorMacroItem = SAMPLE_PAYLOAD.itens[0];
    expect(formatarValorMacro(selic)).toBe("13,75%");

    const ipcaM: IndicadorMacroItem = SAMPLE_PAYLOAD.itens[1];
    expect(formatarValorMacro(ipcaM)).toBe("+0,82%");

    const ipca12m: IndicadorMacroItem = SAMPLE_PAYLOAD.itens[2];
    expect(formatarValorMacro(ipca12m)).toBe("4,58%");

    const euro: IndicadorMacroItem = SAMPLE_PAYLOAD.itens[3];
    // R$ 5,6682 (com espaço sem quebra padrão Intl pt-BR)
    const formattedEuro = formatarValorMacro(euro);
    expect(formattedEuro).toContain("5,6682");
    expect(formattedEuro).toContain("R$");
  });

  it("deve formatar datas de referência diárias e mensais", () => {
    expect(formatarDataReferencia("2026-11-04", "DIARIA")).toBe("04/11/2026");
    expect(formatarDataReferencia("2026-09-01", "MENSAL")).toBe("Setembro/2026");
    expect(formatarDataReferencia("2026-10-19", "DIARIA")).toBe("19/10/2026");
  });

  it("deve persistir e carregar dados válidos do localStorage", () => {
    const storage = new MemoryStorage();
    const saved = saveMacro(storage, SAMPLE_PAYLOAD);
    expect(saved).toBe(true);

    const loaded = readSavedMacro(storage);
    expect(loaded).not.toBeNull();
    expect(loaded?.itens).toHaveLength(4);
    expect(loaded?.itens[0].valor).toBe(13.75);
  });

  it("marca os valores salvos como indisponíveis quando a atualização falha", () => {
    const stale = markMacroUnavailable(SAMPLE_PAYLOAD);
    expect(stale.estaDesatualizado).toBe(true);
    expect(stale.estadoDisponibilidade).toBe("FONTE_INDISPONIVEL");
    expect(stale.itens.every((item) => item.estaDesatualizado)).toBe(true);
    expect(stale.itens.every((item) => item.estadoDisponibilidade === "FONTE_INDISPONIVEL")).toBe(true);
  });

  it("deve limpar localStorage se os dados estiverem corrompidos", () => {
    const storage = new MemoryStorage();
    storage.setItem("deepfarms_agro_mercado_macro_v1", "corrompido-json{");

    const loaded = readSavedMacro(storage);
    expect(loaded).toBeNull();
    expect(storage.getItem("deepfarms_agro_mercado_macro_v1")).toBeNull();
  });

  it("deve resolver URL correta da API para ambiente local e produção", () => {
    const localUrl = macroApiUrl({ hostname: "localhost", protocol: "http:" });
    expect(localUrl).toBe("/api/v1/public/mercado/indicadores-macro");

    const prodUrl = macroApiUrl({ hostname: "agro.deepfarms.com.br", protocol: "https:" });
    expect(prodUrl).toBe("/api/v1/public/mercado/indicadores-macro");
  });
});
