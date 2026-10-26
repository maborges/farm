/**
 * Catálogo Extensível de Produtos e Indicadores de Mercado Agropecuário
 *
 * Módulo puro desacoplado da apresentação visual e do banco de dados relacional.
 * Respeita a distinção entre classificações comerciais de mercado e classificações agronômicas/botânicas.
 * Homologado com dados auditados do DERAL/SEAB-PR e referências federais da CONAB.
 */

export type CategoriaMercado =
  | "GRAOS_CEREAIS"
  | "CAFE"
  | "PECUARIA"
  | "LEGUMINOSAS"
  | "FIBRAS"
  | "HORTIFRUTI"
  | "CANA_DERIVADOS"
  | "OUTROS"
  // Retrocompatibilidade com B4
  | "GRAOS_CEREAIS_OLEAGINOSAS"
  | "CAFE_CULTURAS_ESPECIFICAS"
  | "FIBRAS_OUTROS";

export interface MetadadosCategoria {
  id: CategoriaMercado;
  label: string;
  descricao: string;
}

export const CATEGORIAS_MERCADO: Record<CategoriaMercado, MetadadosCategoria> = {
  GRAOS_CEREAIS: {
    id: "GRAOS_CEREAIS",
    label: "Grãos e Cereais",
    descricao: "Soja, milho, arroz, trigo, aveia branca, cevada, canola e amendoim",
  },
  CAFE: {
    id: "CAFE",
    label: "Café",
    descricao: "Café beneficiado recebido pelo produtor",
  },
  PECUARIA: {
    id: "PECUARIA",
    label: "Pecuária",
    descricao: "Boi gordo, boi magro, vaca em pé, frango vivo, suíno, leite e ovos",
  },
  LEGUMINOSAS: {
    id: "LEGUMINOSAS",
    label: "Leguminosas",
    descricao: "Feijão de cor e feijão preto",
  },
  FIBRAS: {
    id: "FIBRAS",
    label: "Fibras",
    descricao: "Algodão em pluma e fibras têxteis",
  },
  HORTIFRUTI: {
    id: "HORTIFRUTI",
    label: "Hortifrúti",
    descricao: "Frutas, hortaliças e tubérculos de mesa",
  },
  CANA_DERIVADOS: {
    id: "CANA_DERIVADOS",
    label: "Cana e Derivados",
    descricao: "Cana-de-açúcar destinada ao processamento agroindustrial",
  },
  OUTROS: {
    id: "OUTROS",
    label: "Outros Produtos",
    descricao: "Mandioca industrial, erva-mate e culturas agropecuárias regionais",
  },
  // Retrocompatibilidade com código B4
  GRAOS_CEREAIS_OLEAGINOSAS: {
    id: "GRAOS_CEREAIS",
    label: "Grãos e Oleaginosas",
    descricao: "Soja, milho, arroz, trigo, feijão e cereais de grão",
  },
  CAFE_CULTURAS_ESPECIFICAS: {
    id: "CAFE",
    label: "Café e Culturas Específicas",
    descricao: "Café arábica, cana-de-açúcar e culturas perenes",
  },
  FIBRAS_OUTROS: {
    id: "FIBRAS",
    label: "Fibras e Outros",
    descricao: "Algodão em pluma e produtos agroindustriais",
  },
};

export const CATEGORIAS_ATIVAS_EXIBICAO: CategoriaMercado[] = [
  "GRAOS_CEREAIS",
  "CAFE",
  "PECUARIA",
  "LEGUMINOSAS",
  "FIBRAS",
  "CANA_DERIVADOS",
  "OUTROS",
];

export type TipoIndicador =
  | "FISICO_SPOT"
  | "FUTURO_BOLSA"
  | "REFERENCIA_INTERNACIONAL"
  | "ESTATISTICO_CONJUNTURA";

export type TipoFonteReferencia =
  | "PESQUISA_PRECO_FISICO"
  | "BOLSA_DERIVATIVOS"
  | "ORGAO_PUBLICO_FEDERAL"
  | "INSTITUTO_ESTADUAL";

export interface FonteReferencia {
  id: string;
  nome: string;
  entidade: string;
  url: string;
  tipoFonte: TipoFonteReferencia;
  abrangencia: string;
  descricaoAcesso: string;
}

export type EstadoDisponibilidade =
  | "HOMOLOGADO_ATIVO"
  | "REFERENCIA_INSTITUCIONAL"
  | "AGUARDANDO_HOMOLOGACAO"
  | "DISPONIVEL"
  | "DEFASADO"
  | "LINK_HOMOLOGADO";

export type SituacaoIntegracao =
  | "INTEGRADO"
  | "LINK_HOMOLOGADO"
  | "PENDENTE_CONTRATO"
  | "SOB_ANALISE";

export interface VariantePreco {
  varianteId: string;
  siglaFonte: string;
  fonteOficial: string;
  tipoPreco: string;
  pracaReferencia: string;
  unidade: string;
  moeda: string;
  valor: number | null;
  valorOriginal?: number | null;
  unidadeOriginal?: string | null;
  dataReferencia: string | null;
  dataPublicacao?: string | null;
  defasagemDiasAproximada?: number | null;
  documentoOficial: string | null;
  documentoHashSha256: string | null;
  registroOriginal: string | null;
  estadoDisponibilidade: "DISPONIVEL" | "DEFASADO" | "LINK_HOMOLOGADO";
  urlConsultaInstitucional: string;
  urlDocumentoDownload: string | null;
}

export interface ProdutoCatalogo {
  id: string;
  nome: string;
  categoriaMercado: CategoriaMercado;
  categoria?: CategoriaMercado;
  classificacao?: string;
  classificacaoAgronomica: string;
  descricao: string;
  tipoIndicador: TipoIndicador;
  pracaReferencia: string;
  unidade: string;
  moeda: "BRL" | "USD";
  fontesReferencia: FonteReferencia[];
  urlInstitucionalPrincipal: string;
  urlConsultaInstitucional?: string;
  urlDocumentoDownload?: string | null;
  fontePrincipalNome: string;
  siglaFonte?: string;
  estadoDisponibilidade: EstadoDisponibilidade;
  situacaoIntegracao: SituacaoIntegracao;
  destaque: boolean;
  valor?: number | null;
  dataReferencia?: string | null;
  dataPublicacao?: string | null;
  defasagemDiasAproximada?: number | null;
  documentoOficial?: string | null;
  documentoHashSha256?: string | null;
  registroOriginal?: string | null;
  variantes?: VariantePreco[];
}

export interface CatalogoMercadoResponse {
  sucesso: boolean;
  versao: string;
  dataConsultaIso: string;
  cacheAtualizadoEmIso?: string | null;
  estadoDisponibilidade: "NORMAL" | "DEFASADO" | "FONTE_INDISPONIVEL";
  avisoLegal: string;
  totalItens: number;
  itens: ProdutoCatalogo[];
}

const FONTE_DERAL_PADRAO: FonteReferencia = {
  id: "deral-pr",
  nome: "DERAL/SEAB-PR",
  entidade: "Departamento de Economia Rural do Paraná",
  url: "https://www.agricultura.pr.gov.br/deral/precos",
  tipoFonte: "INSTITUTO_ESTADUAL",
  abrangencia: "Paraná — Preço Médio Ponderado Estadual",
  descricaoAcesso: "Preço médio semanal recebido pelo produtor rural",
};

const FONTE_CONAB_PADRAO: FonteReferencia = {
  id: "conab-oficial",
  nome: "CONAB",
  entidade: "Companhia Nacional de Abastecimento",
  url: "https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios",
  tipoFonte: "ORGAO_PUBLICO_FEDERAL",
  abrangencia: "Séries históricas e safras nacionais",
  descricaoAcesso: "Preços médios mensais e levantamentos de safra",
};

/**
 * Catálogo Oficial de 22 Produtos Agropecuários com Fontes Auditadas
 */
export const PRODUTOS_CATALOGO: ProdutoCatalogo[] = [
  // 7 Itens Homologados B4 (Preservação Estrita)
  {
    id: "soja",
    nome: "Soja em Grão",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Leguminosa / Fabaceae (Glycine max)",
    descricao: "Principal oleaginosa brasileira de exportação, balizada pela paridade no porto e prêmios de exportação.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [
      FONTE_DERAL_PADRAO,
      {
        id: "cepea-soja",
        nome: "CEPEA/ESALQ",
        entidade: "Centro de Estudos Avançados em Economia Aplicada (USP/FEALQ)",
        url: "https://www.cepea.org.br/br/indicador/soja.aspx",
        tipoFonte: "PESQUISA_PRECO_FISICO",
        abrangencia: "Paranaguá (FOB) e Cooperativas do Paraná",
        descricaoAcesso: "Indicador diário oficial de mercado spot físico",
      },
      FONTE_CONAB_PADRAO,
    ],
  },
  {
    id: "milho",
    nome: "Milho Físico",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Poácea (Gramínea) / Cereal (Zea mays)",
    descricao: "Cereal base para alimentação animal e bioenergia, com forte liquidez nos mercados de safra e safrinha.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  {
    id: "boi-gordo",
    nome: "Boi Gordo",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Bovinocultura de Corte / Ruminante (Bos taurus / Bos indicus)",
    descricao: "Boi gordo terminado para abate, balizador da pecuária de corte e referência para a indústria frigorífica nacional.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Arroba (@ de 15 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  {
    id: "cafe-arabica",
    nome: "Café Beneficiado (Produtor)",
    categoriaMercado: "CAFE",
    classificacaoAgronomica: "Café beneficiado — classificação comercial DERAL",
    descricao: "Café beneficiado recebido pelo produtor, sem identificação de espécie na publicação de origem.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  {
    id: "trigo",
    nome: "Trigo em Grão",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Poácea (Gramínea) / Cereal de Inverno (Triticum aestivum)",
    descricao: "Cereal nobre de inverno cultivado prioritariamente na Região Sul para abastecimento da indústria moageira nacional.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  {
    id: "arroz",
    nome: "Arroz em Casca",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Poácea (Gramínea) / Cereal Irrigado (Oryza sativa)",
    descricao: "Arroz em casca irrigado recebido pelo produtor, alimento básico da dieta e balizador do complexo orizícola.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  {
    id: "feijao",
    nome: "Feijão de Cor",
    categoriaMercado: "LEGUMINOSAS",
    classificacaoAgronomica: "Leguminosa / Fabaceae (Phaseolus vulgaris)",
    descricao: "Feijão de cor recebido pelo produtor, sem indicação de cultivar na publicação de origem.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [FONTE_DERAL_PADRAO, FONTE_CONAB_PADRAO],
  },
  // 14 Novos Itens P1 (Expansão DERAL Auditada)
  {
    id: "amendoim",
    nome: "Amendoim em Casca",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Leguminosa / Fabaceae (Arachis hypogaea)",
    descricao: "Amendoim em casca comercializado pelo produtor rural, matéria-prima para confeitaria e indústria de óleos.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 25 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "feijao-preto",
    nome: "Feijão Preto",
    categoriaMercado: "LEGUMINOSAS",
    classificacaoAgronomica: "Leguminosa / Fabaceae (Phaseolus vulgaris)",
    descricao: "Feijão comum tipo preto, com alta preferência na Região Sul e Sudeste, negociado em sacas de 60 kg.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "aveia-branca",
    nome: "Aveia Branca",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Poácea (Gramínea) / Cereal de Inverno (Avena sativa)",
    descricao: "Cereal de inverno de dupla aptidão para grãos e forragem animal, cultivado nas lavouras do Sul.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "canola",
    nome: "Canola Grão",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Crucífera / Brassicaceae (Brassica napus)",
    descricao: "Oleaginosa de inverno rica em óleo vegetal nobre e matéria-prima para biocombustíveis.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "cevada",
    nome: "Cevada em Grão",
    categoriaMercado: "GRAOS_CEREAIS",
    classificacaoAgronomica: "Poácea (Gramínea) / Cereal (Hordeum vulgare)",
    descricao: "Cevada em grão recebida pelo produtor, conforme classificação comercial do DERAL.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Saca de 60 kg",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "cana-de-acucar",
    nome: "Cana-de-Açúcar para Indústria",
    categoriaMercado: "CANA_DERIVADOS",
    classificacaoAgronomica: "Poácea (Gramínea) / Semi-perene (Saccharum officinarum)",
    descricao: "Cana-de-açúcar destinada ao processamento agroindustrial de açúcar e etanol pelo setor sucroenergético.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Tonelada (1.000 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "erva-mate",
    nome: "Erva-Mate Folha Verde",
    categoriaMercado: "OUTROS",
    classificacaoAgronomica: "Aquifoliácea / Cultura Nativa Florestal (Ilex paraguariensis)",
    descricao: "Erva-mate folha verde entregue na indústria ervateira para beneficiamento de chimarrão e chás.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Arroba (@ de 15 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "mandioca-industrial",
    nome: "Mandioca Industrial",
    categoriaMercado: "OUTROS",
    classificacaoAgronomica: "Euforbiácea / Raiz Tuberosa (Manihot esculenta)",
    descricao: "Mandioca industrial destinada a fecularias e indústrias de farinha, cultura de grande expressão no Paraná.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Tonelada (1.000 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "boi-magro",
    nome: "Boi Magro p/ Engorda",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Bovinocultura de Corte / Categoria de Reposição",
    descricao: "Boi magro destinado à engorda intensiva e confinamento, indicador chave do custo de reposição pecuária.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Cabeça",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "frango-vivo",
    nome: "Frango Vivo",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Avicultura de Corte (Gallus gallus domesticus)",
    descricao: "Frango vivo no mercado independente da avicultura industrial, polo em que o Paraná lidera a produção brasileira.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Quilo (kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "leite",
    nome: "Leite (Produtor)",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Bovinocultura de Leite / Produto ao produtor",
    descricao: "Leite recebido pelo produtor, sem qualificação de refrigeração na publicação de origem.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Litro",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "ovo-grande",
    nome: "Ovo Tipo Grande",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Avicultura de Postura / Ovos Comerciais",
    descricao: "Ovo tipo grande comercializado em caixas com 30 dúzias (360 ovos), referência da postura comercial.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Caixa com 30 dúzias",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "suino",
    nome: "Suíno Vivo",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Suinocultura Industrial (Sus domesticus)",
    descricao: "Suíno vivo terminado para abate na indústria frigorífica, com preço médio pago ao produtor independente.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Quilo (kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  {
    id: "vaca-em-pe",
    nome: "Vaca em Pé (Abate)",
    categoriaMercado: "PECUARIA",
    classificacaoAgronomica: "Bovinocultura de Corte / Matrizes e Descarte",
    descricao: "Vaca em pé para abate imediato, indicador do mercado de descarte pecuário e consumo de carne de fêmeas.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Paraná — média semanal estadual",
    unidade: "Arroba (@ de 15 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.agricultura.pr.gov.br/deral/precos",
    urlConsultaInstitucional: "https://www.agricultura.pr.gov.br/deral/precos",
    urlDocumentoDownload: "https://www.agricultura.pr.gov.br/system/files/publico/Precos/prp.xls",
    fontePrincipalNome: "DERAL/SEAB-PR",
    siglaFonte: "DERAL/SEAB-PR",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: false,
    fontesReferencia: [FONTE_DERAL_PADRAO],
  },
  // 1 Item Cadastral com Link Homologado (sem cotação DERAL nesta fase)
  {
    id: "algodao",
    nome: "Algodão em Pluma",
    categoriaMercado: "FIBRAS",
    classificacaoAgronomica: "Malvácea (Gossypium hirsutum L.)",
    descricao: "Fibra têxtil de relevância global balizada pelo mercado spot e contratos de exportação.",
    tipoIndicador: "FISICO_SPOT",
    pracaReferencia: "Brasil — Referência Nacional",
    unidade: "Arroba (@ de 15 kg)",
    moeda: "BRL",
    urlInstitucionalPrincipal: "https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios",
    urlConsultaInstitucional: "https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios",
    urlDocumentoDownload: null,
    fontePrincipalNome: "CONAB/MAPA",
    siglaFonte: "CONAB/MAPA",
    estadoDisponibilidade: "REFERENCIA_INSTITUCIONAL",
    situacaoIntegracao: "LINK_HOMOLOGADO",
    destaque: true,
    fontesReferencia: [FONTE_CONAB_PADRAO],
  },
];

export interface FiltrosCatalogo {
  busca?: string;
  categoria?: CategoriaMercado | "TODAS";
}

function normalizarTexto(texto: string): string {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

/**
 * Filtra produtos do catálogo combinando busca textual e filtro de categoria.
 */
export function filtrarProdutos(
  produtos: ProdutoCatalogo[],
  filtros: FiltrosCatalogo
): ProdutoCatalogo[] {
  const buscaLimpa = filtros.busca ? normalizarTexto(filtros.busca) : "";
  const categoriaFiltro = filtros.categoria && filtros.categoria !== "TODAS" ? filtros.categoria : null;

  return produtos.filter((produto) => {
    // Normaliza categoria do produto caso seja uma das categorias legadas
    const catProd = produto.categoriaMercado;
    const catMeta = CATEGORIAS_MERCADO[catProd];
    const catIdNormalizada = catMeta ? catMeta.id : catProd;

    if (categoriaFiltro) {
      const filtroMeta = CATEGORIAS_MERCADO[categoriaFiltro];
      const filtroIdNormalizado = filtroMeta ? filtroMeta.id : categoriaFiltro;

      if (catIdNormalizada !== filtroIdNormalizado && catProd !== categoriaFiltro) {
        return false;
      }
    }

    if (!buscaLimpa) {
      return true;
    }

    const camposBusca = [
      produto.nome,
      produto.descricao,
      produto.classificacaoAgronomica,
      produto.pracaReferencia,
      produto.unidade,
      produto.fontePrincipalNome,
    ].map(normalizarTexto);

    return camposBusca.some((campo) => campo.includes(buscaLimpa));
  });
}

/**
 * Recupera um produto específico pelo seu identificador estável.
 */
export function obterProdutoPorId(
  id: string,
  produtos: ProdutoCatalogo[] = PRODUTOS_CATALOGO
): ProdutoCatalogo | undefined {
  return produtos.find((produto) => produto.id === id);
}

/**
 * Computa a contagem de produtos disponíveis por categoria de mercado.
 */
export function obterContagemPorCategoria(
  produtos: ProdutoCatalogo[] = PRODUTOS_CATALOGO
): Record<CategoriaMercado, number> {
  const contagem: Record<CategoriaMercado, number> = {
    GRAOS_CEREAIS: 0,
    CAFE: 0,
    PECUARIA: 0,
    LEGUMINOSAS: 0,
    FIBRAS: 0,
    HORTIFRUTI: 0,
    CANA_DERIVADOS: 0,
    OUTROS: 0,
    GRAOS_CEREAIS_OLEAGINOSAS: 0,
    CAFE_CULTURAS_ESPECIFICAS: 0,
    FIBRAS_OUTROS: 0,
  };

  for (const produto of produtos) {
    const cat = produto.categoriaMercado;
    if (cat in contagem) {
      contagem[cat] += 1;
    }
    // Mapeia para categoria unificada caso seja antiga
    const meta = CATEGORIAS_MERCADO[cat];
    if (meta && meta.id !== cat && meta.id in contagem) {
      contagem[meta.id] += 1;
    }
  }

  return contagem;
}

/**
 * Validador estrito de segurança de links externos institucionais.
 */
export function isUrlInstitucionalSegura(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") {
      return false;
    }
    const dominiosAutorizados = [
      "cepea.org.br",
      "cepea.esalq.usp.br",
      "b3.com.br",
      "gov.br",
      "conab.gov.br",
      "agricultura.pr.gov.br",
    ];
    return dominiosAutorizados.some(
      (dominio) => parsed.hostname === dominio || parsed.hostname.endsWith(`.${dominio}`)
    );
  } catch {
    return false;
  }
}

/**
 * Consulta o catálogo dinâmico de commodities via API pública.
 */
export async function fetchCatalogoMercado(
  location: Location | URL,
  signal?: AbortSignal
): Promise<CatalogoMercadoResponse | null> {
  try {
    const url = new URL("/api/v1/public/mercado/catalogo", location.origin);
    const resp = await fetch(url.toString(), {
      signal,
      headers: { Accept: "application/json" },
      cache: "default",
    });
    if (!resp.ok) return null;
    return (await resp.json()) as CatalogoMercadoResponse;
  } catch {
    return null;
  }
}
