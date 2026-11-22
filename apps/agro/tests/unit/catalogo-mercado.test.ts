import { describe, it, expect } from "vitest";
import {
  CATEGORIAS_MERCADO,
  PRODUTOS_CATALOGO,
  filtrarProdutos,
  obterProdutoPorId,
  obterContagemPorCategoria,
  isUrlInstitucionalSegura,
  type CategoriaMercado,
} from "../../src/lib/mercado/catalogo";

describe("Catálogo Extensível de Mercado Agropecuário — Modelo e Regras", () => {
  describe("Integridade do Catálogo de Produtos Oficiais", () => {
    it("contém todos os 22 produtos homologados com dados cadastrais completos", () => {
      expect(PRODUTOS_CATALOGO.length).toBe(22);

      const idsOriginaisB4 = [
        "soja",
        "milho",
        "boi-gordo",
        "cafe-arabica",
        "trigo",
        "arroz",
        "algodao",
        "feijao",
      ];

      const idsNovosP1 = [
        "amendoim",
        "feijao-preto",
        "aveia-branca",
        "canola",
        "cevada",
        "cana-de-acucar",
        "erva-mate",
        "mandioca-industrial",
        "boi-magro",
        "frango-vivo",
        "leite",
        "ovo-grande",
        "suino",
        "vaca-em-pe",
      ];

      const idsNoCatalogo = PRODUTOS_CATALOGO.map((p) => p.id);
      for (const id of idsOriginaisB4) {
        expect(idsNoCatalogo).toContain(id);
      }
      for (const id of idsNovosP1) {
        expect(idsNoCatalogo).toContain(id);
      }
    });

    it("assegura que todo produto pertence a uma categoria de mercado válida", () => {
      const categoriasValidas = Object.keys(CATEGORIAS_MERCADO);

      for (const produto of PRODUTOS_CATALOGO) {
        expect(categoriasValidas).toContain(produto.categoriaMercado);
        expect(produto.nome.trim().length).toBeGreaterThan(0);
        expect(produto.unidade.trim().length).toBeGreaterThan(0);
        expect(produto.pracaReferencia.trim().length).toBeGreaterThan(0);
      }
    });

    it("mantém estrita separação entre categoria de mercado e classificação agronômica", () => {
      for (const produto of PRODUTOS_CATALOGO) {
        expect(produto.classificacaoAgronomica).toBeDefined();
        expect(produto.classificacaoAgronomica.length).toBeGreaterThan(5);
        expect(produto.classificacaoAgronomica).not.toBe(produto.categoriaMercado);
      }

      // Verificações botânicas específicas
      const soja = obterProdutoPorId("soja");
      expect(soja?.classificacaoAgronomica).toContain("Fabaceae");

      const milho = obterProdutoPorId("milho");
      expect(milho?.classificacaoAgronomica).toContain("Poácea");

      const cafe = obterProdutoPorId("cafe-arabica");
      expect(cafe?.classificacaoAgronomica).toContain("Rubiaceae");

      for (const produto of PRODUTOS_CATALOGO) {
        expect(produto.classificacaoAgronomica).not.toContain("DERAL");
        expect(produto.descricao).not.toContain("DERAL");
      }

      const boi = obterProdutoPorId("boi-gordo");
      expect(boi?.classificacaoAgronomica).toContain("Bovinocultura de Corte");

      const cana = obterProdutoPorId("cana-de-acucar");
      expect(cana?.classificacaoAgronomica).toContain("Poácea");

      const mandioca = obterProdutoPorId("mandioca-industrial");
      expect(mandioca?.classificacaoAgronomica).toContain("Euforbiácea");

      const erva = obterProdutoPorId("erva-mate");
      expect(erva?.classificacaoAgronomica).toContain("Aquifoliácea");
    });

    it("garante que nenhum produto possui cotações simuladas ou fictícias", () => {
      for (const produto of PRODUTOS_CATALOGO) {
        expect(produto.estadoDisponibilidade).toBe("REFERENCIA_INSTITUCIONAL");
        expect(produto.situacaoIntegracao).toBe("LINK_HOMOLOGADO");
        expect("cotacao" in produto).toBe(false);
      }
    });

    it("valida que todas as URLs institucionais principais são seguras e de entidades homologadas", () => {
      for (const produto of PRODUTOS_CATALOGO) {
        expect(isUrlInstitucionalSegura(produto.urlInstitucionalPrincipal)).toBe(true);

        for (const fonte of produto.fontesReferencia) {
          expect(isUrlInstitucionalSegura(fonte.url)).toBe(true);
        }
      }
    });
  });

  describe("Filtragem e Busca do Catálogo", () => {
    it("retorna todos os produtos quando os filtros são vazios", () => {
      const todos = filtrarProdutos(PRODUTOS_CATALOGO, {});
      expect(todos.length).toBe(PRODUTOS_CATALOGO.length);

      const todasCategorias = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "TODAS" });
      expect(todasCategorias.length).toBe(PRODUTOS_CATALOGO.length);
    });

    it("filtra corretamente pelas novas categorias de mercado da auditoria", () => {
      const graos = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "GRAOS_CEREAIS" });
      expect(graos.length).toBe(8); // soja, milho, trigo, arroz, amendoim, aveia-branca, cevada, canola

      const pecuaria = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "PECUARIA" });
      expect(pecuaria.length).toBe(7); // boi-gordo, boi-magro, vaca-em-pe, frango-vivo, leite, ovo-grande, suino

      const leguminosas = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "LEGUMINOSAS" });
      expect(leguminosas.length).toBe(2); // feijao, feijao-preto

      const cafe = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "CAFE" });
      expect(cafe.length).toBe(1);
      expect(cafe[0].id).toBe("cafe-arabica");

      const cana = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "CANA_DERIVADOS" });
      expect(cana.length).toBe(1);
      expect(cana[0].id).toBe("cana-de-acucar");

      const outros = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "OUTROS" });
      expect(outros.length).toBe(2); // mandioca-industrial, erva-mate

      const fibras = filtrarProdutos(PRODUTOS_CATALOGO, { categoria: "FIBRAS" });
      expect(fibras.length).toBe(1);
      expect(fibras[0].id).toBe("algodao");
    });

    it("busca por nome de forma insensível a maiúsculas e acentuação", () => {
      const resultadoSemAcento = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "feijao" });
      expect(resultadoSemAcento.some((p) => p.id === "feijao")).toBe(true);

      const resultadoComAcento = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "Feijão" });
      expect(resultadoComAcento.some((p) => p.id === "feijao")).toBe(true);

      const resultadoCafe = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "BENEFICIADO" });
      expect(resultadoCafe.some((p) => p.id === "cafe-arabica")).toBe(true);

      const resultadoLeite = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "leite" });
      expect(resultadoLeite.some((p) => p.id === "leite")).toBe(true);
    });

    it("busca por praça de referência e classificação botânica", () => {
      const porPraca = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "Paraná" });
      expect(porPraca.length).toBeGreaterThan(15);

      const porBotanica = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "Zea mays" });
      expect(porBotanica.some((p) => p.id === "milho")).toBe(true);

      const porCana = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "Saccharum" });
      expect(porCana.some((p) => p.id === "cana-de-acucar")).toBe(true);
    });

    it("combina busca por texto e categoria simultaneamente", () => {
      const resultado = filtrarProdutos(PRODUTOS_CATALOGO, {
        categoria: "GRAOS_CEREAIS",
        busca: "trigo",
      });
      expect(resultado.length).toBe(1);
      expect(resultado[0].id).toBe("trigo");

      // Produto existe mas em outra categoria -> deve retornar vazio
      const resultadoIncompativel = filtrarProdutos(PRODUTOS_CATALOGO, {
        categoria: "PECUARIA",
        busca: "trigo",
      });
      expect(resultadoIncompativel.length).toBe(0);
    });

    it("retorna array vazio quando nenhum produto satisfaz a busca", () => {
      const resultado = filtrarProdutos(PRODUTOS_CATALOGO, { busca: "produto_inexistente_xyz" });
      expect(resultado).toEqual([]);
    });
  });

  describe("Recuperação por ID e Contagem", () => {
    it("obterProdutoPorId recupera produto com sucesso ou retorna undefined", () => {
      const boi = obterProdutoPorId("boi-gordo");
      expect(boi).toBeDefined();
      expect(boi?.nome).toBe("Boi Gordo");

      const leite = obterProdutoPorId("leite");
      expect(leite).toBeDefined();
      expect(leite?.nome).toBe("Leite (Produtor)");

      const inexistente = obterProdutoPorId("cacau");
      expect(inexistente).toBeUndefined();
    });

    it("obterContagemPorCategoria calcula o número exato de produtos em cada categoria", () => {
      const contagem = obterContagemPorCategoria(PRODUTOS_CATALOGO);

      expect(contagem.GRAOS_CEREAIS).toBe(8);
      expect(contagem.PECUARIA).toBe(7);
      expect(contagem.LEGUMINOSAS).toBe(2);
      expect(contagem.CAFE).toBe(1);
      expect(contagem.CANA_DERIVADOS).toBe(1);
      expect(contagem.OUTROS).toBe(2);
      expect(contagem.FIBRAS).toBe(1);

      // Soma das categorias principais cobre os 22 produtos
      const soma =
        contagem.GRAOS_CEREAIS +
        contagem.PECUARIA +
        contagem.LEGUMINOSAS +
        contagem.CAFE +
        contagem.CANA_DERIVADOS +
        contagem.OUTROS +
        contagem.FIBRAS;
      expect(soma).toBe(22);
    });
  });

  describe("Segurança de Links Institucionais (isUrlInstitucionalSegura)", () => {
    it("aceita domínios governamentais e de pesquisa credenciados via HTTPS", () => {
      expect(isUrlInstitucionalSegura("https://www.cepea.org.br/br/indicador/soja.aspx")).toBe(true);
      expect(isUrlInstitucionalSegura("https://cepea.esalq.usp.br/indicador/milho")).toBe(true);
      expect(isUrlInstitucionalSegura("https://www.b3.com.br/pt_br/produtos-e-servicos/")).toBe(true);
      expect(isUrlInstitucionalSegura("https://www.gov.br/conab/pt-br/")).toBe(true);
      expect(isUrlInstitucionalSegura("https://portal.conab.gov.br/indicador")).toBe(true);
      expect(isUrlInstitucionalSegura("https://www.agricultura.pr.gov.br/deral/precos")).toBe(true);
    });

    it("rejeita protocolos inseguros (HTTP simples)", () => {
      expect(isUrlInstitucionalSegura("http://www.cepea.org.br/br/indicador/soja.aspx")).toBe(false);
      expect(isUrlInstitucionalSegura("http://www.gov.br/conab")).toBe(false);
      expect(isUrlInstitucionalSegura("http://www.agricultura.pr.gov.br/deral")).toBe(false);
    });

    it("rejeita domínios não autorizados ou tentativas de spoofing", () => {
      expect(isUrlInstitucionalSegura("https://fake-cepea.com/soja")).toBe(false);
      expect(isUrlInstitucionalSegura("https://b3.com.br.malicious-site.com/invest")).toBe(false);
      expect(isUrlInstitucionalSegura("https://noticiasagricolas.com.br")).toBe(false);
      expect(isUrlInstitucionalSegura("https://alphavantage.co/query")).toBe(false);
    });

    it("retorna false graciosamente para strings inválidas", () => {
      expect(isUrlInstitucionalSegura("")).toBe(false);
      expect(isUrlInstitucionalSegura("not-a-valid-url")).toBe(false);
      expect(isUrlInstitucionalSegura("javascript:alert(1)")).toBe(false);
    });
  });
});
