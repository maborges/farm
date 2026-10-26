import { describe, expect, it, beforeEach } from "vitest";
import {
  formatarPeriodoIbge,
  formatarValorIbge,
  gerarQueryKey,
  ibgeApiBaseUrl,
  markIbgeUnavailable,
  parseCatalogoIbge,
  parseEstatisticasIbge,
  parseMunicipiosIbge,
  readSavedCatalogo,
  readSavedIbge,
  saveCatalogo,
  saveIbge,
  type CatalogoIbgeResponse,
  type EstatisticasIbgeResponse,
  type MunicipiosIbgeResponse,
} from "@/lib/mercado/ibge";

const SAMPLE_ESTATISTICAS: EstatisticasIbgeResponse = {
  sucesso: true,
  versao: "1.0",
  fonteOficial: "Instituto Brasileiro de Geografia e Estatística (IBGE) — SIDRA",
  dataConsultaIso: "2026-10-19T20:00:00.000Z",
  cacheAtualizadoEmIso: "2026-10-19T19:50:00.000Z",
  estadoDisponibilidade: "NORMAL",
  estaDesatualizado: false,
  avisoLegal: "Estatística oficial de produção.",
  pesquisa: "Produção Agrícola Municipal (PAM)",
  fontePesquisa: "PAM",
  tabelaSidra: 5457,
  urlTabela: "https://sidra.ibge.gov.br/tabela/5457",
  periodicidade: "ANUAL",
  produto: {
    id: "soja",
    nome: "Soja (em grão)",
    tipo: "LAVOURA",
  },
  localidade: {
    nivel: "BRASIL",
    codigo: "1",
    nome: "Brasil",
  },
  periodoSolicitado: "2024",
  ultimoPeriodoDisponivel: "2024",
  dataAtualizacaoFonte: "2024-10-15",
  avisoDefasagem: null,
  indicadores: [
    {
      id: "PRODUCAO",
      nomeOficial: "Quantidade produzida",
      codigoVariavelSidra: 214,
      recorte: null,
      unidade: "Toneladas",
      pontos: [{ periodo: "2024", valor: 150000000, simboloIbge: null }],
      ultimoPeriodo: "2024",
      ultimoValor: 150000000,
    },
    {
      id: "AREA_COLHIDA",
      nomeOficial: "Área colhida",
      codigoVariavelSidra: 216,
      recorte: null,
      unidade: "Hectares",
      pontos: [{ periodo: "2024", valor: 45000000, simboloIbge: null }],
      ultimoPeriodo: "2024",
      ultimoValor: 45000000,
    },
    {
      id: "RENDIMENTO_MEDIO",
      nomeOficial: "Rendimento médio da produção",
      codigoVariavelSidra: 112,
      recorte: null,
      unidade: "Quilogramas por Hectare",
      pontos: [{ periodo: "2024", valor: null, simboloIbge: "..." }],
      ultimoPeriodo: "2024",
      ultimoValor: null,
    },
  ],
};

const SAMPLE_CATALOGO: CatalogoIbgeResponse = {
  sucesso: true,
  versao: "1.0",
  fonteOficial: "Instituto Brasileiro de Geografia e Estatística (IBGE) — SIDRA",
  dataConsultaIso: "2026-10-19T20:00:00.000Z",
  anoMinimo: 1974,
  produtos: [
    {
      id: "soja",
      nome: "Soja (em grão)",
      tipo: "LAVOURA",
      pesquisa: "PAM",
      indicadores: ["Quantidade produzida", "Área colhida"],
      suportaLspa: true,
    },
  ],
  ufs: [
    { codigo: "51", sigla: "MT", nome: "Mato Grosso" },
    { codigo: "35", sigla: "SP", nome: "São Paulo" },
  ],
};

const SAMPLE_MUNICIPIOS: MunicipiosIbgeResponse = {
  sucesso: true,
  versao: "1.0",
  fonteOficial: "IBGE",
  dataConsultaIso: "2026-10-19T20:00:00.000Z",
  cacheAtualizadoEmIso: "2026-10-19T20:00:00.000Z",
  estadoDisponibilidade: "NORMAL",
  estaDesatualizado: false,
  uf: "35",
  itens: [
    { codigo: "3550308", nome: "São Paulo" },
    { codigo: "3509502", nome: "Campinas" },
  ],
};

class MockStorage implements Storage {
  private store: Record<string, string> = {};

  get length(): number {
    return Object.keys(this.store).length;
  }

  clear(): void {
    this.store = {};
  }

  getItem(key: string): string | null {
    return this.store[key] ?? null;
  }

  key(index: number): string | null {
    return Object.keys(this.store)[index] ?? null;
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  setItem(key: string, value: string): void {
    this.store[key] = value;
  }
}

describe("Módulo de Estatísticas Oficiais IBGE/SIDRA", () => {
  let storage: MockStorage;

  beforeEach(() => {
    storage = new MockStorage();
  });

  it("1. Deve fazer o parsing correto de estatísticas válidas", () => {
    const parsed = parseEstatisticasIbge(SAMPLE_ESTATISTICAS);
    expect(parsed).not.toBeNull();
    expect(parsed?.sucesso).toBe(true);
    expect(parsed?.produto.id).toBe("soja");
    expect(parsed?.indicadores.length).toBe(3);
    expect(parsed?.indicadores[0].ultimoValor).toBe(150000000);
    expect(parsed?.indicadores[2].ultimoValor).toBeNull();
  });

  it("2. Deve rejeitar payloads malformados ou incompletos", () => {
    expect(parseEstatisticasIbge(null)).toBeNull();
    expect(parseEstatisticasIbge({})).toBeNull();
    expect(parseEstatisticasIbge({ ...SAMPLE_ESTATISTICAS, versao: "2.0" })).toBeNull();
    expect(parseEstatisticasIbge({ ...SAMPLE_ESTATISTICAS, indicadores: "invalid" })).toBeNull();
  });

  it("3. Deve fazer o parsing correto de catálogo e municípios", () => {
    const cat = parseCatalogoIbge(SAMPLE_CATALOGO);
    expect(cat).not.toBeNull();
    expect(cat?.produtos.length).toBe(1);
    expect(cat?.ufs.length).toBe(2);

    const mun = parseMunicipiosIbge(SAMPLE_MUNICIPIOS);
    expect(mun).not.toBeNull();
    expect(mun?.itens.length).toBe(2);
  });

  it("4. Deve salvar e recuperar estatísticas do localStorage", () => {
    const qKey = gerarQueryKey({ produto: "soja", nivel: "BRASIL" });
    expect(qKey).toBe("soja_BR");

    const saved = saveIbge(storage, qKey, SAMPLE_ESTATISTICAS);
    expect(saved).toBe(true);

    const retrieved = readSavedIbge(storage, qKey);
    expect(retrieved).not.toBeNull();
    expect(retrieved?.produto.id).toBe("soja");
  });

  it("marca estatística salva como desatualizada se a fonte falha", () => {
    const stale = markIbgeUnavailable(SAMPLE_ESTATISTICAS);
    expect(stale.estadoDisponibilidade).toBe("FONTE_INDISPONIVEL");
    expect(stale.estaDesatualizado).toBe(true);
    expect(stale.avisoDefasagem).toContain("pode estar desatualizada");
  });

  it("5. Deve salvar e recuperar catálogo do localStorage", () => {
    const saved = saveCatalogo(storage, SAMPLE_CATALOGO);
    expect(saved).toBe(true);

    const retrieved = readSavedCatalogo(storage);
    expect(retrieved).not.toBeNull();
    expect(retrieved?.produtos[0].id).toBe("soja");
  });

  it("6. Deve gerar a URL base correta da API", () => {
    const localUrl = ibgeApiBaseUrl({ hostname: "localhost", protocol: "http:" });
    expect(localUrl).toBe("/api/v1/public/mercado/ibge");

    const prodUrl = ibgeApiBaseUrl({ hostname: "agro.deepfarms.com.br", protocol: "https:" });
    expect(prodUrl).toBe("/api/v1/public/mercado/ibge");
  });

  it("7. Deve formatar valores numéricos com precisão pt-BR", () => {
    expect(formatarValorIbge(150000000, "Toneladas")).toBe("150.000.000 Toneladas");
    expect(formatarValorIbge(3250.75, "kg/ha")).toBe("3.250,75 kg/ha");
    expect(formatarValorIbge(null, "Toneladas")).toBe("Dado inibido / s/ dado");
  });

  it("8. Deve formatar períodos anual e mensal", () => {
    expect(formatarPeriodoIbge("2024", "ANUAL")).toBe("2024");
    expect(formatarPeriodoIbge("2024-08", "MENSAL")).toBe("Agosto/2024");
    expect(formatarPeriodoIbge(null, "ANUAL")).toBe("Não informado");
  });
});
