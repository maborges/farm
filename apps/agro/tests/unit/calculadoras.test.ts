import { describe, it, expect } from "vitest";
import {
  converterSacasKgToneladas,
  converterAreaRural,
  calcularFreteAgricola,
  calcularCustoEquilibrio,
  converterUnidadeGeral,
  FATORES_AREA_M2,
  CATALOGO_UNIDADES,
} from "../../src/lib/calculadoras/core";
import {
  parseNumeroPtBr,
  formatarNumero,
  formatarMoeda,
  formatarPercentual,
  formatarMoedaOuNaoCalculavel,
  formatarNumeroOuNaoCalculavel,
  formatarPercentualOuNaoCalculavel,
  detectarEntradaAmbiguaPtBr,
  MENSAGEM_NAO_CALCULAVEL,
} from "../../src/lib/calculadoras/format";

describe("1. Calculadora de Sacas, Quilogramas e Toneladas", () => {
  it("converte sacas para kg e toneladas com saca padrão de 60 kg", () => {
    const res = converterSacasKgToneladas({
      valor: 100,
      unidadeOrigem: "SACAS",
      kgPorSaca: 60,
    });
    expect(res.quilogramas).toBe(6000);
    expect(res.toneladas).toBe(6);
    expect(res.sacas).toBe(100);
    expect(res.kgPorSaca).toBe(60);
  });

  it("converte quilogramas para sacas e toneladas", () => {
    const res = converterSacasKgToneladas({
      valor: 12000,
      unidadeOrigem: "QUILOGRAMAS",
      kgPorSaca: 60,
    });
    expect(res.sacas).toBe(200);
    expect(res.toneladas).toBe(12);
    expect(res.quilogramas).toBe(12000);
  });

  it("converte toneladas para sacas e quilogramas", () => {
    const res = converterSacasKgToneladas({
      valor: 30,
      unidadeOrigem: "TONELADAS",
      kgPorSaca: 60,
    });
    expect(res.quilogramas).toBe(30000);
    expect(res.sacas).toBe(500);
    expect(res.toneladas).toBe(30);
  });

  it("suporta massa configurável por saca (ex: café ou milho com 50 kg ou saca especial)", () => {
    const res = converterSacasKgToneladas({
      valor: 10,
      unidadeOrigem: "SACAS",
      kgPorSaca: 50,
    });
    expect(res.quilogramas).toBe(500);
    expect(res.toneladas).toBe(0.5);
    expect(res.sacas).toBe(10);
    expect(res.kgPorSaca).toBe(50);
  });

  it("realiza conversão de ida e volta (roundtrip) sem perda de precisão", () => {
    const valorOriginal = 345.678;
    const paraKg = converterSacasKgToneladas({
      valor: valorOriginal,
      unidadeOrigem: "SACAS",
      kgPorSaca: 60,
    });
    const deVolta = converterSacasKgToneladas({
      valor: paraKg.quilogramas,
      unidadeOrigem: "QUILOGRAMAS",
      kgPorSaca: 60,
    });
    expect(deVolta.sacas).toBeCloseTo(valorOriginal, 8);
  });

  it("trata valor zero corretamente", () => {
    const res = converterSacasKgToneladas({
      valor: 0,
      unidadeOrigem: "SACAS",
      kgPorSaca: 60,
    });
    expect(res.sacas).toBe(0);
    expect(res.quilogramas).toBe(0);
    expect(res.toneladas).toBe(0);
  });

  it("rejeita valores negativos e kg/saca nulo ou menor igual a zero", () => {
    expect(() =>
      converterSacasKgToneladas({
        valor: -10,
        unidadeOrigem: "SACAS",
      })
    ).toThrow("O valor de massa não pode ser negativo");

    expect(() =>
      converterSacasKgToneladas({
        valor: 10,
        unidadeOrigem: "SACAS",
        kgPorSaca: 0,
      })
    ).toThrow("A massa por saca deve ser um valor numérico positivo");

    expect(() =>
      converterSacasKgToneladas({
        valor: 10,
        unidadeOrigem: "SACAS",
        kgPorSaca: -5,
      })
    ).toThrow("A massa por saca deve ser um valor numérico positivo");
  });
});

describe("2. Calculadora de Conversão de Áreas Rurais e Fatores de Alqueire", () => {
  it("converte 1 hectare para 10.000 m²", () => {
    const res = converterAreaRural({
      valor: 1,
      unidadeOrigem: "HECTARES",
    });
    expect(res.metrosQuadrados).toBe(10000);
    expect(res.hectares).toBe(1);
    expect(res.alqueiresPaulistas).toBeCloseTo(10000 / 24200, 6);
  });

  it("converte alqueire paulista com fator exato de 24.200 m² (2,42 ha)", () => {
    const res = converterAreaRural({
      valor: 1,
      unidadeOrigem: "ALQUEIRE_PAULISTA",
    });
    expect(res.metrosQuadrados).toBe(24200);
    expect(res.hectares).toBe(2.42);
    expect(res.alqueiresPaulistas).toBe(1);
  });

  it("converte alqueire mineiro/goiano com fator exato de 48.400 m² (4,84 ha)", () => {
    const res = converterAreaRural({
      valor: 1,
      unidadeOrigem: "ALQUEIRE_MINEIRO",
    });
    expect(res.metrosQuadrados).toBe(48400);
    expect(res.hectares).toBe(4.84);
    expect(res.alqueiresMineiros).toBe(1);
    expect(res.alqueiresPaulistas).toBe(2); // 48.400 / 24.200 = 2 exatos
  });

  it("converte alqueire do Norte com fator geométrico exato de 75x75 braças = 27.225 m² (2,7225 ha)", () => {
    const res = converterAreaRural({
      valor: 1,
      unidadeOrigem: "ALQUEIRE_NORTE",
    });
    expect(res.metrosQuadrados).toBe(27225);
    expect(res.hectares).toBe(2.7225);
    expect(res.alqueiresNorte).toBe(1);
  });

  it("converte alqueire baiano / pequeno com fator geométrico de 50x50 braças = 12.100 m² (1,21 ha)", () => {
    const res = converterAreaRural({
      valor: 1,
      unidadeOrigem: "ALQUEIRE_BAIANO",
    });
    expect(res.metrosQuadrados).toBe(12100);
    expect(res.hectares).toBe(1.21);
    expect(res.alqueiresBaianos).toBe(1);
    expect(res.alqueiresMineiros).toBe(0.25); // 12.100 / 48.400 = 0.25 exatos
  });

  it("executa ida e volta perfeita entre m² e todos os alqueires regionais", () => {
    const areaM2 = 242000;
    const res = converterAreaRural({
      valor: areaM2,
      unidadeOrigem: "METROS_QUADRADOS",
    });
    expect(res.alqueiresPaulistas).toBe(10); // 242.000 / 24.200 = 10
    expect(res.alqueiresMineiros).toBe(5); // 242.000 / 48.400 = 5
    expect(res.hectares).toBe(24.2);

    // Volta Alqueire Paulista
    const voltaPaulista = converterAreaRural({
      valor: res.alqueiresPaulistas,
      unidadeOrigem: "ALQUEIRE_PAULISTA",
    });
    expect(voltaPaulista.metrosQuadrados).toBe(areaM2);

    // Volta Alqueire Mineiro
    const voltaMineiro = converterAreaRural({
      valor: res.alqueiresMineiros,
      unidadeOrigem: "ALQUEIRE_MINEIRO",
    });
    expect(voltaMineiro.metrosQuadrados).toBe(areaM2);

    // Volta Alqueire Norte
    const voltaNorte = converterAreaRural({
      valor: res.alqueiresNorte,
      unidadeOrigem: "ALQUEIRE_NORTE",
    });
    expect(voltaNorte.metrosQuadrados).toBeCloseTo(areaM2, 4);

    // Volta Alqueire Baiano
    const voltaBaiano = converterAreaRural({
      valor: res.alqueiresBaianos,
      unidadeOrigem: "ALQUEIRE_BAIANO",
    });
    expect(voltaBaiano.metrosQuadrados).toBeCloseTo(areaM2, 4);
  });

  it("retorna zero para valor zero", () => {
    const res = converterAreaRural({
      valor: 0,
      unidadeOrigem: "HECTARES",
    });
    expect(res.metrosQuadrados).toBe(0);
    expect(res.hectares).toBe(0);
  });

  it("rejeita áreas negativas", () => {
    expect(() =>
      converterAreaRural({
        valor: -5,
        unidadeOrigem: "HECTARES",
      })
    ).toThrow("O valor de área não pode ser negativo");
  });
});

describe("3. Calculadora de Estimativa de Frete Agrícola", () => {
  it("calcula frete por tonelada com quantidade em toneladas", () => {
    const res = calcularFreteAgricola({
      quantidade: 32, // 32 toneladas
      unidadeQuantidade: "TONELADAS",
      valorTarifa: 150, // R$ 150 por tonelada
      tipoTarifa: "POR_TONELADA",
      custosAdicionais: 200, // Pedágio/seguro
      kgPorSaca: 60,
    });

    expect(res.massaToneladas).toBe(32);
    expect(res.massaKg).toBe(32000);
    expect(res.totalSacas).toBeCloseTo(32000 / 60, 4);
    expect(res.freteBase).toBe(4800); // 32 * 150
    expect(res.custosAdicionais).toBe(200);
    expect(res.totalFrete).toBe(5000);
    expect(res.custoEfetivoPorTonelada).toBe(5000 / 32); // 156.25
    expect(res.custoEfetivoPorSaca).toBeCloseTo(5000 / (32000 / 60), 4);
  });

  it("calcula frete por saca com quantidade informada em sacas", () => {
    const res = calcularFreteAgricola({
      quantidade: 500, // 500 sacas
      unidadeQuantidade: "SACAS",
      valorTarifa: 12, // R$ 12 por saca
      tipoTarifa: "POR_SACA",
      custosAdicionais: 0,
      kgPorSaca: 60,
    });

    expect(res.totalSacas).toBe(500);
    expect(res.massaKg).toBe(30000);
    expect(res.massaToneladas).toBe(30);
    expect(res.freteBase).toBe(6000);
    expect(res.totalFrete).toBe(6000);
    expect(res.custoEfetivoPorSaca).toBe(12);
    expect(res.custoEfetivoPorTonelada).toBe(200); // 6000 / 30
  });

  it("calcula corretamente quando a tarifa é por tonelada mas a carga foi informada em sacas", () => {
    const res = calcularFreteAgricola({
      quantidade: 1000, // 1000 sacas de 60kg = 60 toneladas
      unidadeQuantidade: "SACAS",
      valorTarifa: 100, // R$ 100 por tonelada
      tipoTarifa: "POR_TONELADA",
      kgPorSaca: 60,
    });

    expect(res.massaToneladas).toBe(60);
    expect(res.freteBase).toBe(6000);
    expect(res.totalFrete).toBe(6000);
    expect(res.custoEfetivoPorSaca).toBe(6); // 6000 / 1000
  });

  it("rejeita quantidade <= 0 ou tarifa <= 0", () => {
    expect(() =>
      calcularFreteAgricola({
        quantidade: 0,
        unidadeQuantidade: "TONELADAS",
        valorTarifa: 100,
        tipoTarifa: "POR_TONELADA",
      })
    ).toThrow("A quantidade transportada deve ser maior que zero");

    expect(() =>
      calcularFreteAgricola({
        quantidade: 10,
        unidadeQuantidade: "TONELADAS",
        valorTarifa: 0,
        tipoTarifa: "POR_TONELADA",
      })
    ).toThrow("O valor da tarifa de frete deve ser maior que zero");
  });
});

describe("4. Calculadora de Custo por Hectare e Ponto de Equilíbrio (Correções Matemáticas)", () => {
  it("calcula custo/ha, receita bruta, margem e ponto de equilíbrio com valores normais", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 100,
      custoTotal: 400000, // R$ 4.000 / ha
      produtividadeEsperadaPorHa: 60, // 60 sacas/ha
      precoVendaUnitario: 100, // R$ 100 / saca
    });

    expect(res.custoPorHectare).toBe(4000);
    expect(res.producaoTotalEsperada).toBe(6000); // 100 ha * 60 sacas
    expect(res.custoPorUnidadeProduzida).toBeCloseTo(400000 / 6000, 4); // ~66.67
    expect(res.receitaBrutaEstimada).toBe(600000); // 6000 * 100
    expect(res.resultadoEstimado).toBe(200000); // 600.000 - 400.000
    expect(res.margemLucroPct).toBeCloseTo((200000 / 600000) * 100, 2); // 33.33%
    expect(res.precoDeEquilibrio).toBeCloseTo(400000 / 6000, 4); // R$ 66.67
    expect(res.produtividadeDeEquilibrioPorHa).toBe(40); // 4000 / 100
    expect(res.producaoTotalDeEquilibrio).toBe(4000); // 400.000 / 100
  });

  it("CENÁRIO 1: Produção total zero com custo positivo -> custo unitário e preço de equilíbrio são null", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 20,
      custoTotal: 50000,
      produtividadeEsperadaPorHa: 0, // Produção esperada = 0
      precoVendaUnitario: 80,
    });

    expect(res.producaoTotalEsperada).toBe(0);
    expect(res.custoPorHectare).toBe(2500); // 50.000 / 20
    expect(res.custoPorUnidadeProduzida).toBeNull(); // Não pode ser 0! Deve ser null
    expect(res.precoDeEquilibrio).toBeNull(); // Não pode ser 0! Deve ser null
    expect(res.receitaBrutaEstimada).toBe(0);
    expect(res.resultadoEstimado).toBe(-50000);
    expect(res.margemLucroPct).toBeNull(); // Receita zero -> não calculável
    expect(res.produtividadeDeEquilibrioPorHa).toBe(2500 / 80); // 31.25 sc/ha
  });

  it("CENÁRIO 2: Produção total zero com custo zero -> custo unitário e preço de equilíbrio são null", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 10,
      custoTotal: 0,
      produtividadeEsperadaPorHa: 0,
      precoVendaUnitario: 100,
    });

    expect(res.producaoTotalEsperada).toBe(0);
    expect(res.custoPorUnidadeProduzida).toBeNull();
    expect(res.precoDeEquilibrio).toBeNull();
    expect(res.margemLucroPct).toBeNull();
  });

  it("CENÁRIO 3: Preço de venda zero com custo positivo -> produtividade e produção de equilíbrio são null", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 50,
      custoTotal: 100000,
      produtividadeEsperadaPorHa: 70,
      precoVendaUnitario: 0, // Preço zero
    });

    expect(res.custoPorHectare).toBe(2000);
    expect(res.receitaBrutaEstimada).toBe(0);
    expect(res.resultadoEstimado).toBe(-100000);
    expect(res.margemLucroPct).toBeNull();
    expect(res.produtividadeDeEquilibrioPorHa).toBeNull(); // Não calculável com preço zero
    expect(res.producaoTotalDeEquilibrio).toBeNull(); // Não calculável com preço zero
  });

  it("CENÁRIO 4: Receita bruta zero -> margem percentual sobre receita é null", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 10,
      custoTotal: 20000,
      produtividadeEsperadaPorHa: 0,
      precoVendaUnitario: 0,
    });

    expect(res.receitaBrutaEstimada).toBe(0);
    expect(res.margemLucroPct).toBeNull();
  });

  it("CENÁRIO 5: Custo total zero com produção positiva -> custo unitário e preço de equilíbrio são zero", () => {
    const res = calcularCustoEquilibrio({
      areaHectares: 10,
      custoTotal: 0,
      produtividadeEsperadaPorHa: 50,
      precoVendaUnitario: 90,
    });

    expect(res.producaoTotalEsperada).toBe(500);
    expect(res.custoPorHectare).toBe(0);
    expect(res.custoPorUnidadeProduzida).toBe(0); // 0 / 500 = 0
    expect(res.precoDeEquilibrio).toBe(0); // 0 / 500 = 0
    expect(res.receitaBrutaEstimada).toBe(45000);
    expect(res.resultadoEstimado).toBe(45000);
    expect(res.margemLucroPct).toBe(100);
  });

  it("rejeita área <= 0 ou custos negativos", () => {
    expect(() =>
      calcularCustoEquilibrio({
        areaHectares: 0,
        custoTotal: 1000,
        produtividadeEsperadaPorHa: 10,
        precoVendaUnitario: 10,
      })
    ).toThrow("A área cultivada em hectares deve ser maior que zero");

    expect(() =>
      calcularCustoEquilibrio({
        areaHectares: 10,
        custoTotal: -50,
        produtividadeEsperadaPorHa: 10,
        precoVendaUnitario: 10,
      })
    ).toThrow("O custo total não pode ser negativo");
  });
});

describe("5. Conversor Geral de Unidades", () => {
  it("converte grandezas de Massa (kg -> g, kg -> tonelada, kg -> @)", () => {
    expect(converterUnidadeGeral(1, "KG", "G")).toBe(1000);
    expect(converterUnidadeGeral(1000, "KG", "TONELADA")).toBe(1);
    expect(converterUnidadeGeral(15, "KG", "ARROBA")).toBe(1);
    expect(converterUnidadeGeral(2, "ARROBA", "KG")).toBe(30);
  });

  it("converte grandezas de Área (m² -> ha, km² -> ha)", () => {
    expect(converterUnidadeGeral(10000, "M2", "HECTARE")).toBe(1);
    expect(converterUnidadeGeral(1, "KM2", "HECTARE")).toBe(100);
    expect(converterUnidadeGeral(5, "HECTARE", "M2")).toBe(50000);
  });

  it("converte grandezas de Volume (L -> mL, m³ -> L)", () => {
    expect(converterUnidadeGeral(1, "LITRO", "MILILITRO")).toBe(1000);
    expect(converterUnidadeGeral(1, "METRO_CUBICO", "LITRO")).toBe(1000);
    expect(converterUnidadeGeral(2500, "MILILITRO", "LITRO")).toBe(2.5);
  });

  it("converte grandezas de Comprimento (m -> km, cm -> m)", () => {
    expect(converterUnidadeGeral(1000, "METRO", "QUILOMETRO")).toBe(1);
    expect(converterUnidadeGeral(150, "CENTIMETRO", "METRO")).toBe(1.5);
    expect(converterUnidadeGeral(5, "QUILOMETRO", "METRO")).toBe(5000);
  });

  it("barreira de segurança: impede conversão entre grandezas incompatíveis", () => {
    expect(() => converterUnidadeGeral(10, "HECTARE", "LITRO")).toThrow(
      /Não é permitido converter area.*para volume/i
    );
    expect(() => converterUnidadeGeral(50, "KG", "METRO")).toThrow(
      /Não é permitido converter massa.*para comprimento/i
    );
    expect(() => converterUnidadeGeral(1, "M2", "TONELADA")).toThrow(
      /Não é permitido converter area.*para massa/i
    );
  });

  it("retorna o mesmo valor quando unidade de origem e destino forem iguais", () => {
    expect(converterUnidadeGeral(42.5, "HECTARE", "HECTARE")).toBe(42.5);
  });
});

describe("6. Parser Numérico pt-BR, Ambiguidade e Formatação Segura", () => {
  it("CENÁRIO 8: Trata entrada numérica ambígua (1.234) e decimais com vírgula (1,234)", () => {
    // 1.234 com ponto e 3 dígitos -> convenção brasileira de milhar
    expect(parseNumeroPtBr("1.234")).toBe(1234);
    // 1,234 com vírgula e 3 dígitos -> decimal brasileiro
    expect(parseNumeroPtBr("1,234")).toBe(1.234);

    // Detecção explícita de ambiguidade para aviso ao usuário
    const avisoMilhar = detectarEntradaAmbiguaPtBr("1.234");
    expect(avisoMilhar).toContain("1.234");
    expect(avisoMilhar).toContain("separador de milhar");

    // 1,234 com vírgula não é ambíguo
    expect(detectarEntradaAmbiguaPtBr("1,234")).toBeNull();
    // 1250.50 com 2 dígitos não é ambíguo (claramente decimal)
    expect(detectarEntradaAmbiguaPtBr("1250.50")).toBeNull();
  });

  it("faz parse de números com padrão brasileiro (vírgula decimal e pontos de milhar)", () => {
    expect(parseNumeroPtBr("1.250,50")).toBe(1250.5);
    expect(parseNumeroPtBr("1250,50")).toBe(1250.5);
    expect(parseNumeroPtBr("0,75")).toBe(0.75);
    expect(parseNumeroPtBr("1,25")).toBe(1.25);
    expect(parseNumeroPtBr("100")).toBe(100);
  });

  it("faz parse de números decimais com ponto (fallback internacional inequívoco)", () => {
    expect(parseNumeroPtBr("1250.50")).toBe(1250.5); // 2 dígitos após ponto -> decimal
    expect(parseNumeroPtBr("0.25")).toBe(0.25);
    expect(parseNumeroPtBr("1.5")).toBe(1.5); // 1 dígito após ponto -> decimal
  });

  it("faz parse de múltiplos separadores de milhar", () => {
    expect(parseNumeroPtBr("1.250.000")).toBe(1250000);
    expect(parseNumeroPtBr("1.234.567")).toBe(1234567);
  });

  it("CENÁRIO 10: Valores muito grandes, NaN, Infinity e entradas inválidas retornam null", () => {
    expect(parseNumeroPtBr("")).toBeNull();
    expect(parseNumeroPtBr("   ")).toBeNull();
    expect(parseNumeroPtBr(null)).toBeNull();
    expect(parseNumeroPtBr(undefined)).toBeNull();
    expect(parseNumeroPtBr("abc")).toBeNull();
    expect(parseNumeroPtBr("-")).toBeNull();
    expect(parseNumeroPtBr("1,2,3")).toBeNull();
    expect(parseNumeroPtBr(NaN)).toBeNull();
    expect(parseNumeroPtBr(Infinity)).toBeNull();
    expect(parseNumeroPtBr(-Infinity)).toBeNull();
    // Valor que excede MAX_SAFE_INTEGER
    expect(parseNumeroPtBr("99999999999999999999999")).toBeNull();
  });

  it("CENÁRIO 9: Valores monetários fracionários e mensagens de valor não calculável", () => {
    expect(formatarNumero(1250.5, 2)).toBe("1.250,5");
    expect(formatarPercentual(25.4, 1)).toBe("25,4%");
    expect(formatarMoeda(1250.75)).toContain("1.250,75");

    // Teste da mensagem padronizada 'Não calculável com os valores informados.'
    expect(formatarMoedaOuNaoCalculavel(null)).toBe(MENSAGEM_NAO_CALCULAVEL);
    expect(formatarMoedaOuNaoCalculavel(undefined)).toBe(MENSAGEM_NAO_CALCULAVEL);
    expect(formatarNumeroOuNaoCalculavel(null)).toBe(MENSAGEM_NAO_CALCULAVEL);
    expect(formatarPercentualOuNaoCalculavel(null)).toBe(MENSAGEM_NAO_CALCULAVEL);
  });
});
