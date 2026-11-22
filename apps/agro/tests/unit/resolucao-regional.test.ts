import { describe, it, expect } from "vitest";
import { PRODUTOS_CATALOGO, obterProdutoPorId } from "../../src/lib/mercado/catalogo";
import type { PrecoPublicoItem } from "../../src/lib/mercado/precos";
import {
  UFS_MERCADO_BRASIL,
  filtrarProdutosPorFonte,
  isUfValida,
  obterNomeUf,
  resolverExibicaoCardMercado,
  type CotacaoRegiaoApiItem,
} from "../../src/lib/mercado/resolucao-regional";

function criarPrecoDeralMock(overrides: Partial<PrecoPublicoItem> = {}): PrecoPublicoItem {
  return {
    id: "soja",
    commodityNome: "Soja em Grão",
    classificacao: "Grão",
    valor: 134.98,
    moeda: "BRL",
    unidade: "Saca de 60 kg",
    pracaReferencia: "Paraná — média semanal estadual",
    fonteOficial: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    linkOficial: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    tipoPreco: "PRECO_MEDIO_RECEBIDO_PRODUTOR",
    periodicidade: "SEMANAL",
    dataReferencia: "2026-11-13",
    dataConsultaIso: "2026-11-20T12:00:00Z",
    defasagemDiasAproximada: 7,
    indicacaoTemporal: "Semanal — Preço Médio Produtor",
    avisoLegal: "Dado oficial.",
    documentoOficial: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    documentoHashSha256: "e25b3b14" + "0".repeat(56),
    dataPublicacao: "2026-11-13",
    registroOriginal: "Rav!X12",
    valorOriginal: 134.98,
    unidadeOriginal: "Saca de 60 kg",
    transformacaoAplicada: "Sem conversão",
    valorSemanaAnterior: 133.5,
    variacaoSemanalAbsoluta: 1.48,
    variacaoSemanalPct: 1.11,
    valorMinimoRegional: 128.0,
    pracaMinimoRegional: "Cascavel",
    valorMaximoRegional: 141.5,
    pracaMaximoRegional: "Paranaguá",
    pracasRegionais: [
      { praca: "Cascavel", valor: 128.0, valorOriginal: 128.0, registroOriginal: "Rav!C12" },
      { praca: "Maringá", valor: 133.2, valorOriginal: 133.2, registroOriginal: "Rav!E12" },
    ],
    ...overrides,
  };
}

function criarRegiaoMultiMock(
  id: string,
  uf: string,
  ibgeValor: number | null
): CotacaoRegiaoApiItem {
  const fontes = [];
  if (ibgeValor !== null) {
    fontes.push({
      fonte_id: `ibge-pam-${uf.toLowerCase()}-uf`,
      sigla_fonte: "IBGE/SIDRA (PAM)",
      nome_fonte: `IBGE/SIDRA — Valor Médio Regional (${obterNomeUf(uf)})`,
      tipo_fonte: "ESTATISTICO_OFICIAL",
      uf,
      praca: `${obterNomeUf(uf)} (Média Regional PAM/IBGE)`,
      valor: ibgeValor,
      unidade: "Saca de 60 kg",
      periodicidade: "ANUAL",
      data_referencia: "2024",
      url_consulta: "https://sidra.ibge.gov.br/tabela/5457",
      registro_origem: "SIDRA!T5457(V215/V214)",
    });
  }
  return {
    id,
    nome: id,
    unidade: "Saca de 60 kg",
    uf_consulta: uf,
    fontes,
    resumo: {
      total_fontes_catalogo: fontes.length,
      fontes_com_preco_ativo: fontes.length,
      valor_minimo: ibgeValor,
      fonte_minima: ibgeValor !== null ? "IBGE/SIDRA (PAM)" : null,
      valor_medio: ibgeValor,
      valor_maximo: ibgeValor,
      fonte_maxima: ibgeValor !== null ? "IBGE/SIDRA (PAM)" : null,
      dispersao_pct: 0,
      valor_recomendado_regiao: ibgeValor,
      fonte_recomendada_regiao: ibgeValor !== null ? "IBGE/SIDRA (PAM)" : null,
    },
  };
}

describe("Resolução Regional e Multi-Fonte de Mercado (apps/agro)", () => {
  it("disponibiliza todas as 27 UFs brasileiras com validação consistente", () => {
    expect(UFS_MERCADO_BRASIL).toHaveLength(27);
    expect(isUfValida("PR")).toBe(true);
    expect(isUfValida("MT")).toBe(true);
    expect(isUfValida("AC")).toBe(true);
    expect(isUfValida("TO")).toBe(true);
    expect(isUfValida("XX")).toBe(false);
    expect(obterNomeUf("MT")).toBe("Mato Grosso");
  });

  it("em PR + TODAS + Média Estadual exibe DERAL em destaque sem duplicar DERAL-PR em outras fontes", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: criarRegiaoMultiMock("soja", "PR", 122.4),
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque).not.toBeNull();
    expect(exibicao.destaque?.familia).toBe("DERAL");
    expect(exibicao.destaque?.ehHistoricoAnual).toBe(false);
    expect(exibicao.destaque?.valor).toBe(134.98);
    expect(exibicao.mostrarFaixaPr).toBe(true);
    expect(exibicao.urlDownloadXls).toContain("prp.xls");
    expect(exibicao.outrasFontes.some((f) => f.familia === "DERAL")).toBe(false);
    expect(exibicao.outrasFontes.some((f) => f.familia === "IBGE" && f.valor === 122.4)).toBe(true);
    expect(exibicao.outrasFontes.some((f) => f.familia === "CEPEA")).toBe(true);
    expect(exibicao.outrasFontes.some((f) => f.familia === "CONAB")).toBe(true);
    expect(exibicao.ctaPrincipal.rotulo).toContain("DERAL");
  });

  it("em PR com núcleo regional selecionado atualiza valor, origem e etiqueta sem duplicar DERAL", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: null,
      ufAtiva: "PR",
      pracaAtiva: "Cascavel",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque?.valor).toBe(128.0);
    expect(exibicao.destaque?.origem).toBe("Rav!C12");
    expect(exibicao.regiaoLabel).toBe("Cascavel/PR (Núcleo DERAL)");
    expect(exibicao.pracaRegionalSelecionada?.praca).toBe("Cascavel");
    expect(exibicao.avisoPracaIndisponivel).toBe(false);
    expect(exibicao.outrasFontes.some((f) => f.familia === "DERAL")).toBe(false);
  });

  it("em PR quando núcleo selecionado não existe no produto sinaliza avisoPracaIndisponivel", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: null,
      ufAtiva: "PR",
      pracaAtiva: "Londrina",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque?.valor).toBe(134.98);
    expect(exibicao.avisoPracaIndisponivel).toBe(true);
    expect(exibicao.pracaRegionalSelecionada).toBeNull();
  });

  it("em MT + TODAS com IBGE/PAM disponível promove IBGE no destaque, oculta Faixa PR e mantém DERAL como ref. do PR", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: criarRegiaoMultiMock("soja", "MT", 118.45),
      ufAtiva: "MT",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque?.familia).toBe("IBGE");
    expect(exibicao.destaque?.ehHistoricoAnual).toBe(true);
    expect(exibicao.badgeCabecalho).toEqual({
      texto: "Histórico Anual IBGE",
      variant: "warning",
    });
    expect(exibicao.destaque?.valor).toBe(118.45);
    expect(exibicao.destaque?.origem).toBe("SIDRA!T5457(V215/V214)");
    expect(exibicao.destaque?.dataLabel).toContain("2024");
    expect(exibicao.mostrarFaixaPr).toBe(false);
    expect(exibicao.urlDownloadXls).toBeNull();
    expect(exibicao.ctaPrincipal.href).toContain("sidra.ibge.gov.br");
    expect(exibicao.regiaoLabel).toContain("Mato Grosso");
    const deralComparativo = exibicao.outrasFontes.find((f) => f.familia === "DERAL");
    expect(deralComparativo).toBeDefined();
    expect(deralComparativo?.detalhe).toContain("PR");
    expect(exibicao.outrasFontes.some((f) => f.familia === "IBGE")).toBe(false);
  });

  it("em MT + TODAS para Boi Gordo (sem PAM/IBGE) NÃO exibe DERAL no bloco principal e explicita ausência para MT", () => {
    const boi = obterProdutoPorId("boi-gordo")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: boi,
      precoDeral: criarPrecoDeralMock({
        id: "boi-gordo",
        commodityNome: "Boi Gordo",
        unidade: "Arroba (@ de 15 kg)",
        valor: 389.33,
        valorOriginal: 389.33,
        registroOriginal: "Rav!X49",
      }),
      regiaoMultiItem: criarRegiaoMultiMock("boi-gordo", "MT", null),
      ufAtiva: "MT",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque).toBeNull();
    expect(exibicao.badgeCabecalho.texto).toBe("Referência externa (PR)");
    expect(exibicao.motivoIndisponivel).toContain("Mato Grosso");
    expect(exibicao.mostrarFaixaPr).toBe(false);
    expect(exibicao.urlDownloadXls).toBeNull();
    expect(exibicao.outrasFontes.some((f) => f.familia === "DERAL" && f.valor === 389.33)).toBe(true);
    expect(exibicao.outrasFontes.some((f) => f.familia === "CEPEA")).toBe(true);
    expect(exibicao.ctaPrincipal.rotulo).toContain("CEPEA");
  });

  it("em PR + Fonte = IBGE para Soja promove IBGE/PAM sem mostrar DERAL nem Faixa PR", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: criarRegiaoMultiMock("soja", "PR", 122.4),
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "IBGE",
    });

    expect(exibicao.destaque?.familia).toBe("IBGE");
    expect(exibicao.destaque?.ehHistoricoAnual).toBe(true);
    expect(exibicao.badgeCabecalho.texto).toBe("Histórico Anual IBGE");
    expect(exibicao.destaque?.valor).toBe(122.4);
    expect(exibicao.mostrarFaixaPr).toBe(false);
    expect(exibicao.urlDownloadXls).toBeNull();
    expect(exibicao.outrasFontes).toHaveLength(0);
    expect(exibicao.ctaPrincipal.rotulo).toContain("IBGE");
  });

  it("em PR + Fonte = IBGE para Boi Gordo explica ausência de série na PAM/IBGE", () => {
    const boi = obterProdutoPorId("boi-gordo")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: boi,
      precoDeral: criarPrecoDeralMock({ id: "boi-gordo", valor: 389.33, valorOriginal: 389.33 }),
      regiaoMultiItem: criarRegiaoMultiMock("boi-gordo", "PR", null),
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "IBGE",
    });

    expect(exibicao.destaque).toBeNull();
    expect(exibicao.motivoIndisponivel).toContain("IBGE/PAM");
    expect(exibicao.outrasFontes).toHaveLength(0);
    expect(exibicao.mostrarFaixaPr).toBe(false);
  });

  it("quando Fonte = CONAB ou CEPEA entra em consulta direta da fonte e oculta DERAL/Faixa PR", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicaoCepea = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock(),
      regiaoMultiItem: criarRegiaoMultiMock("soja", "PR", 122.4),
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "CEPEA",
    });

    expect(exibicaoCepea.destaque).toBeNull();
    expect(exibicaoCepea.modoConsultaDireta).toBe(true);
    expect(exibicaoCepea.mostrarFaixaPr).toBe(false);
    expect(exibicaoCepea.urlDownloadXls).toBeNull();
    expect(exibicaoCepea.outrasFontes).toHaveLength(0);
    expect(exibicaoCepea.ctaPrincipal.rotulo).toContain("CEPEA");
    expect(exibicaoCepea.ctaPrincipal.href).toContain("cepea.org.br");
  });

  it("mantém contrato para item sem DERAL nem IBGE no PR (ex.: algodão)", () => {
    const algodao = obterProdutoPorId("algodao")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: algodao,
      precoDeral: undefined,
      regiaoMultiItem: null,
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque).toBeNull();
    expect(exibicao.badgeCabecalho.texto).toBe("Preço indisponível");
    expect(exibicao.ctaPrincipal.rotulo).toContain("CONAB/MAPA");
  });

  it("preserva contrato de fixture sintética (FIXTURE) sem regressão de E2E", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock({
        siglaFonte: "FIXTURE",
        fonteOficial: "Fixture DeepFarms",
        linkOficial: "https://example.invalid/fixture",
        urlConsultaInstitucional: "https://example.invalid/fixture",
        urlDocumentoDownload: null,
        valorMinimoRegional: null,
        valorMaximoRegional: null,
        pracasRegionais: [],
      }),
      regiaoMultiItem: null,
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.destaque?.sigla).toBe("FIXTURE");
    expect(exibicao.destaque?.ehHistoricoAnual).toBe(false);
    expect(exibicao.badgeCabecalho.texto).toBe("Preço Público Real");
    expect(exibicao.ctaPrincipal.rotulo).toContain("FIXTURE");
    expect(exibicao.ctaPrincipal.href).toBe("https://example.invalid/fixture");
  });

  it("descarta URLs inseguras vindas da API usando fallback institucional HTTPS", () => {
    const soja = obterProdutoPorId("soja")!;
    const exibicao = resolverExibicaoCardMercado({
      produto: soja,
      precoDeral: criarPrecoDeralMock({
        urlConsultaInstitucional: "javascript:alert(1)",
        linkOficial: "http://evil.example.com/phish",
      }),
      regiaoMultiItem: null,
      ufAtiva: "PR",
      pracaAtiva: "MEDIA_ESTADUAL",
      fonteAtiva: "TODAS",
    });

    expect(exibicao.ctaPrincipal.href.startsWith("https://")).toBe(true);
    expect(exibicao.ctaPrincipal.href).toContain("agricultura.pr.gov.br");
  });

  it("filtra produtos por fonte respeitando o catálogo enriquecido com CEPEA e CONAB", () => {
    const comCepea = filtrarProdutosPorFonte(PRODUTOS_CATALOGO, "CEPEA");
    expect(comCepea.some((p) => p.id === "soja")).toBe(true);
    expect(comCepea.some((p) => p.id === "boi-gordo")).toBe(true);
    expect(comCepea.some((p) => p.id === "algodao")).toBe(true);

    const comConab = filtrarProdutosPorFonte(PRODUTOS_CATALOGO, "CONAB");
    expect(comConab.length).toBe(PRODUTOS_CATALOGO.length);
  });
});
