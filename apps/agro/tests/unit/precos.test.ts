import { describe, expect, it, beforeEach, vi } from "vitest";
import {
  formatarDataPreco,
  formatarPrecoPublico,
  parsePrecoItem,
  parsePrecosResponse,
  precosApiUrl,
  readSavedPrecos,
  savePrecos,
  fetchPrecosPublicos,
  type PrecoPublicoItem,
  type PrecosPublicosResponse,
} from "@/lib/mercado/precos";

const SAMPLE_ITEM: PrecoPublicoItem = {
  id: "soja",
  commodityNome: "Soja em Grão",
  classificacao: "Padrão Exportação (Preço Médio Recebido pelo Produtor)",
  valor: 134.98,
  moeda: "BRL",
  unidade: "Saca de 60 kg",
  pracaReferencia: "Paraná (Média Estadual - DERAL/SEAB-PR)",
  fonteOficial: "Departamento de Economia Rural / SEAB-PR",
  siglaFonte: "DERAL/SEAB-PR",
  linkOficial: "https://www.agricultura.pr.gov.br/Deral",
  tipoPreco: "PRECO_MEDIO_RECEBIDO_PRODUTOR",
  periodicidade: "SEMANAL",
  dataReferencia: "2026-10-16",
  dataConsultaIso: "2026-10-21T10:00:00.000Z",
  defasagemDiasAproximada: 5,
  indicacaoTemporal: "Semanal — Preço Médio Produtor",
  avisoLegal: "Aviso legal de teste",
  documentoOficial: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
  documentoHashSha256: "65582dc4c47c8993415dc71ee9af6ed69651b7279d65ab31f4316a1bc787dde1",
  dataPublicacao: "2026-10-16",
  registroOriginal: "Rav!X12",
  valorOriginal: 134.9794,
  unidadeOriginal: "60 kg",
  transformacaoAplicada: "Arredondamento decimal HALF_UP para 2 casas",
};

const IDS_HOMOLOGADOS_21 = [
  "arroz", "cafe-arabica", "feijao", "milho", "soja", "trigo", "boi-gordo",
  "amendoim", "feijao-preto", "aveia-branca", "canola", "cevada", "cana-de-acucar",
  "erva-mate", "mandioca-industrial", "boi-magro", "frango-vivo", "leite",
  "ovo-grande", "suino", "vaca-em-pe",
];

function criarPayloadFixture(ids: string[], totalItens?: number): PrecosPublicosResponse {
  return {
    sucesso: true,
    versao: "1.0",
    dataConsultaIso: "2026-10-21T10:00:00.000Z",
    cacheAtualizadoEmIso: "2026-10-21T09:30:00.000Z",
    estadoDisponibilidade: "NORMAL",
    avisoLegal: "Aviso legal de teste",
    totalItens: totalItens ?? ids.length,
    itens: ids.map((id, index) => ({
      ...SAMPLE_ITEM,
      id,
      commodityNome: `Commodity ${id}`,
      registroOriginal: `Rav!X${index + 5}`,
    })),
  };
}

class MemoryStorage implements Storage {
  private map = new Map<string, string>();
  get length(): number {
    return this.map.size;
  }
  clear(): void {
    this.map.clear();
  }
  getItem(key: string): string | null {
    return this.map.get(key) ?? null;
  }
  key(index: number): string | null {
    return Array.from(this.map.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.map.delete(key);
  }
  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }
}

describe("Preços Públicos Agropecuários - Client Library", () => {
  let storage: MemoryStorage;

  beforeEach(() => {
    storage = new MemoryStorage();
    vi.restoreAllMocks();
  });

  describe("parsePrecoItem", () => {
    it("deve parsear item com sucesso quando todos os campos obrigatórios são fornecidos", () => {
      const item = parsePrecoItem(SAMPLE_ITEM);
      expect(item).not.toBeNull();
      expect(item?.id).toBe("soja");
      expect(item?.valor).toBe(134.98);
      expect(item?.moeda).toBe("BRL");
      expect(item?.unidade).toBe("Saca de 60 kg");
      expect(item?.siglaFonte).toBe("DERAL/SEAB-PR");
      expect(item?.dataReferencia).toBe("2026-10-16");
    });

    it("deve rejeitar item com valor nulo, negativo, zero ou não numérico", () => {
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valor: -10 })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valor: 0 })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valor: Number.NaN })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valor: Number.POSITIVE_INFINITY })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valor: "abc" })).toBeNull();
    });

    it("deve rejeitar item com valorOriginal inválido", () => {
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valorOriginal: 0 })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valorOriginal: -5.5 })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, valorOriginal: Number.NaN })).toBeNull();
    });

    it("deve rejeitar item com formato de data inválido", () => {
      expect(parsePrecoItem({ ...SAMPLE_ITEM, dataReferencia: "16/10/2026" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, dataReferencia: "invalido" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, dataConsultaIso: "data-invalida" })).toBeNull();
    });

    it("deve rejeitar item com unidade vazia ou praça de referência ausente", () => {
      expect(parsePrecoItem({ ...SAMPLE_ITEM, unidade: "" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, unidadeOriginal: "" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, pracaReferencia: "" })).toBeNull();
    });

    it("deve rejeitar item com formato de ID não slug ou documento não HTTPS", () => {
      expect(parsePrecoItem({ ...SAMPLE_ITEM, id: "Soja Invalida!" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, documentoOficial: "http://inseguro.pr.gov.br/prp.xls" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, documentoHashSha256: "curto" })).toBeNull();
      expect(parsePrecoItem({ ...SAMPLE_ITEM, registroOriginal: "A1" })).toBeNull();
    });

    it("deve preservar variação semanal MSA, faixa mín/máx e núcleos regionais quando presentes", () => {
      const enriquecido = parsePrecoItem({
        ...SAMPLE_ITEM,
        valorSemanaAnterior: 134.14,
        variacaoSemanalAbsoluta: 0.84,
        variacaoSemanalPct: 0.62,
        valorMinimoRegional: 131.82,
        pracaMinimoRegional: "Londrina",
        valorMaximoRegional: 141.5,
        pracaMaximoRegional: "Guarapuava",
        pracasRegionais: [
          { praca: "Cascavel", valor: 132.98, valorOriginal: 132.98, registroOriginal: "Rav!F12" },
          { praca: "Londrina", valor: 131.82, valorOriginal: 131.82, registroOriginal: "Rav!O12" },
        ],
      });
      expect(enriquecido).not.toBeNull();
      expect(enriquecido?.valorSemanaAnterior).toBe(134.14);
      expect(enriquecido?.variacaoSemanalPct).toBe(0.62);
      expect(enriquecido?.pracaMinimoRegional).toBe("Londrina");
      expect(enriquecido?.pracaMaximoRegional).toBe("Guarapuava");
      expect(enriquecido?.pracasRegionais).toHaveLength(2);
      expect(enriquecido?.pracasRegionais?.[0]?.praca).toBe("Cascavel");
    });
  });

  describe("parsePrecosResponse - Validação Resiliente e Desacoplada", () => {
    it("cenário 1: valida com sucesso snapshot atual com 21 preços", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      const res = parsePrecosResponse(payload);
      expect(res).not.toBeNull();
      expect(res?.sucesso).toBe(true);
      expect(res?.versao).toBe("1.0");
      expect(res?.totalItens).toBe(21);
      expect(res?.itens).toHaveLength(21);
      expect(res?.itens.some((item) => item.id === "soja")).toBe(true);
    });

    it("cenário 2: valida com sucesso atualização legítima com 20 preços (fixture sintética)", () => {
      const ids20 = IDS_HOMOLOGADOS_21.slice(0, 20);
      const payload = criarPayloadFixture(ids20);
      const res = parsePrecosResponse(payload);
      expect(res).not.toBeNull();
      expect(res?.totalItens).toBe(20);
      expect(res?.itens).toHaveLength(20);
    });

    it("cenário 3: valida com sucesso atualização legítima com 22 preços (fixture sintética)", () => {
      const ids22 = [...IDS_HOMOLOGADOS_21, "sorgo-grao"];
      const payload = criarPayloadFixture(ids22);
      const res = parsePrecosResponse(payload);
      expect(res).not.toBeNull();
      expect(res?.totalItens).toBe(22);
      expect(res?.itens).toHaveLength(22);
      expect(res?.itens.some((item) => item.id === "sorgo-grao")).toBe(true);
    });

    it("cenário 4: rejeita resposta truncada onde totalItens diverge da quantidade recebida", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21.slice(0, 15), 21); // diz ter 21, mas só envia 15
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 5: rejeita resposta truncada onde um item interno falha no schema", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      // Corrompe o 3º item com valor negativo
      payload.itens[2].valor = -99;
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 6: rejeita payload com IDs duplicados", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      payload.itens[1].id = payload.itens[0].id; // duplica o primeiro ID
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 7: rejeita payload vazio quando sucesso=true e estado normal", () => {
      const payload = {
        ...criarPayloadFixture([]),
        itens: [],
      };
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 8: rejeita contaminação entre períodos de referência no mesmo lote", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      // Um item com data de referência de outra semana
      payload.itens[5].dataReferencia = "2026-10-09";
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 9: rejeita contaminação de hashes de documento divergentes no mesmo lote", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      payload.itens[3].documentoHashSha256 = "0000000000000000000000000000000000000000000000000000000000000000";
      expect(parsePrecosResponse(payload)).toBeNull();
    });

    it("cenário 10: aceita estado FONTE_INDISPONIVEL com lista vazia", () => {
      const payload = {
        sucesso: true,
        versao: "1.0",
        dataConsultaIso: "2026-10-21T10:00:00.000Z",
        cacheAtualizadoEmIso: null,
        estadoDisponibilidade: "FONTE_INDISPONIVEL",
        avisoLegal: "Aviso",
        itens: [],
      };
      const res = parsePrecosResponse(payload);
      expect(res).not.toBeNull();
      expect(res?.estadoDisponibilidade).toBe("FONTE_INDISPONIVEL");
      expect(res?.itens).toHaveLength(0);
    });
  });

  describe("Armazenamento Offline e Tolerância a Falhas", () => {
    it("salva snapshot válido e recupera preservando todos os itens", () => {
      const payload = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      const salvo = savePrecos(storage, payload);
      expect(salvo).toBe(true);

      const recuperado = readSavedPrecos(storage);
      expect(recuperado).not.toBeNull();
      expect(recuperado?.itens).toHaveLength(21);
      expect(recuperado?.itens[0]?.valor).toBe(134.98);
    });

    it("preserva o último snapshot válido íntegro se uma atualização subsequente falhar ou vier truncada", () => {
      // 1. Grava snapshot válido inicial
      const validoInicial = criarPayloadFixture(IDS_HOMOLOGADOS_21);
      expect(savePrecos(storage, validoInicial)).toBe(true);

      // 2. Tenta salvar payload truncado ou corrompido
      const payloadTruncado = criarPayloadFixture(IDS_HOMOLOGADOS_21.slice(0, 10), 21);
      const tentouSalvar = savePrecos(storage, payloadTruncado);
      expect(tentouSalvar).toBe(false);

      // 3. O storage continua contendo o snapshot inicial íntegro
      const preservado = readSavedPrecos(storage);
      expect(preservado).not.toBeNull();
      expect(preservado?.itens).toHaveLength(21);
      expect(preservado?.itens.some((i) => i.id === "vaca-em-pe")).toBe(true);
    });

    it("limpa storage se o payload salvo estiver com versão anterior e migra com segurança", () => {
      storage.setItem("deepfarms_agro_mercado_precos_v1", JSON.stringify({ old: true }));
      storage.setItem("deepfarms_agro_mercado_precos_v2", JSON.stringify({ old: true }));
      storage.setItem("deepfarms_agro_mercado_precos_v3", JSON.stringify({ old: true }));

      // Ao ler o storage, purga chaves obsoletas
      expect(readSavedPrecos(storage)).toBeNull();
      expect(storage.getItem("deepfarms_agro_mercado_precos_v1")).toBeNull();
      expect(storage.getItem("deepfarms_agro_mercado_precos_v2")).toBeNull();
      expect(storage.getItem("deepfarms_agro_mercado_precos_v3")).toBeNull();
    });

    it("fetchPrecosPublicos trata falha de rede lançando erro sem corromper storage", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network failure"));
      const loc = { hostname: "localhost", protocol: "http:" };

      await expect(fetchPrecosPublicos(loc)).rejects.toThrow("Network failure");
    });

    it("fetchPrecosPublicos trata resposta HTTP 500 lançando erro sem corromper storage", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      } as unknown as Response);
      const loc = { hostname: "localhost", protocol: "http:" };

      await expect(fetchPrecosPublicos(loc)).rejects.toThrow("Serviço de preços indisponível (HTTP 500)");
    });
  });

  describe("precosApiUrl", () => {
    it("deve usar mesma origem em ambiente local", () => {
      const url = precosApiUrl({ hostname: "localhost", protocol: "http:" });
      expect(url).toBe("/api/v1/public/mercado/precos");
    });

    it("deve usar mesma origem em produção", () => {
      const url = precosApiUrl({ hostname: "agro.deepfarms.com.br", protocol: "https:" });
      expect(url).toBe("/api/v1/public/mercado/precos");
    });
  });

  describe("Formatação", () => {
    it("deve formatar valores monetários em padrão BRL", () => {
      const formatado = formatarPrecoPublico(124.8);
      expect(formatado.replace(/\s+/g, " ")).toMatch(/R\$\s*124,80/);
    });

    it("deve formatar datas ISO (YYYY-MM-DD) para DD/MM/YYYY", () => {
      expect(formatarDataPreco("2026-10-16")).toBe("16/10/2026");
      expect(formatarDataPreco("2026-05-01")).toBe("01/05/2026");
    });
  });
});
