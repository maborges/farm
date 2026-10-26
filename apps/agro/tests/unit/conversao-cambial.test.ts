import { describe, it, expect } from "vitest";
import {
  converterBrlParaMoeda,
  formatarPrecoMoeda,
} from "../../src/lib/mercado/precos";
import { CURRENCIES, type CurrencyCode } from "../../src/lib/mercado/ptax";

describe("DEEPFARMS-AGRO-FREE-01E2F-B6B — Conversão Cambial Pura e Formatação", () => {
  // Amostra de taxas PTAX Venda oficiais registradas pelo BCB
  const TAXAS_PTAX_BCB: Record<CurrencyCode, number> = {
    USD: 5.6378,
    EUR: 6.1245,
    GBP: 7.3456,
    JPY: 0.03793,
    CAD: 4.1234,
    CHF: 6.5432,
    AUD: 3.7891,
    CNY: 0.7912,
    ARS: 0.0057,
    CLP: 0.0059,
    ZAR: 0.3214,
  };

  it("converte BRL para USD com precisão matemática", () => {
    // Soja DERAL: R$ 123,03 / saca 60 kg com USD a 5.6378
    const resultado = converterBrlParaMoeda(123.03, TAXAS_PTAX_BCB.USD);
    expect(resultado).not.toBeNull();
    // 123.03 / 5.6378 = 21.82234...
    expect(resultado).toBeCloseTo(21.8223, 3);
  });

  it("converte BRL para todas as 11 moedas suportadas pelo BCB", () => {
    const precoBrl = 134.98; // Valor de teste representativo de commodity
    for (const item of CURRENCIES) {
      const taxa = TAXAS_PTAX_BCB[item.code];
      const resultado = converterBrlParaMoeda(precoBrl, taxa);
      expect(resultado).not.toBeNull();
      expect(resultado).toBeGreaterThan(0);
      expect(resultado).toBe(precoBrl / taxa);
    }
  });

  it("rejeita taxas nulas, indefinidas, zero ou negativas", () => {
    expect(converterBrlParaMoeda(100, null)).toBeNull();
    expect(converterBrlParaMoeda(100, undefined)).toBeNull();
    expect(converterBrlParaMoeda(100, 0)).toBeNull();
    expect(converterBrlParaMoeda(100, -5.63)).toBeNull();
    expect(converterBrlParaMoeda(100, Number.NaN)).toBeNull();
    expect(converterBrlParaMoeda(100, Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("rejeita valores em BRL negativos ou inválidos", () => {
    expect(converterBrlParaMoeda(-10, 5.6378)).toBeNull();
    expect(converterBrlParaMoeda(Number.NaN, 5.6378)).toBeNull();
    expect(converterBrlParaMoeda(Number.POSITIVE_INFINITY, 5.6378)).toBeNull();
  });

  it("retorna 0 quando o valor em BRL for 0", () => {
    expect(converterBrlParaMoeda(0, 5.6378)).toBe(0);
  });

  it("formata moedas decimais com 2 casas e pontuação pt-BR", () => {
    const formatadoUsd = formatarPrecoMoeda(21.8223, "USD");
    expect(formatadoUsd).toContain("21,82");
    expect(formatadoUsd).toContain("US$");

    const formatadoEur = formatarPrecoMoeda(20.155, "EUR");
    expect(formatadoEur).toContain("20,16");
    expect(formatadoEur).toContain("€");
  });

  it("formata JPY e CLP com 0 casas decimais conforme convenção cambial", () => {
    // 123.03 / 0.03793 ≈ 3243.606
    const convertidoJpy = converterBrlParaMoeda(123.03, TAXAS_PTAX_BCB.JPY)!;
    const formatadoJpy = formatarPrecoMoeda(convertidoJpy, "JPY");
    expect(formatadoJpy).not.toContain(",00");
    expect(formatadoJpy).toMatch(/3\.244/);

    // 123.03 / 0.0059 ≈ 20852.54
    const convertidoClp = converterBrlParaMoeda(123.03, TAXAS_PTAX_BCB.CLP)!;
    const formatadoClp = formatarPrecoMoeda(convertidoClp, "CLP");
    expect(formatadoClp).not.toContain(",00");
    expect(formatadoClp).toMatch(/20\.853/);
  });
});
