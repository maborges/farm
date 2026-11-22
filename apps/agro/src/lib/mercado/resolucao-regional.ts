import { formatarDataPreco, type PrecoPublicoItem, type PracaRegionalDeralItem } from "./precos";
import { isUrlInstitucionalSegura, type FonteReferencia, type ProdutoCatalogo } from "./catalogo";

export type FonteFiltroMercado = "TODAS" | "DERAL" | "IBGE" | "CEPEA" | "CONAB" | "B3";
export type FamiliaFonteMercado = "DERAL" | "IBGE" | "CEPEA" | "CONAB" | "B3" | "FIXTURE" | "OUTRA";

export interface UfBrasilItem {
  sigla: string;
  nome: string;
  codigoIbge: string;
}

export interface FonteRegiaoApiItem {
  fonte_id: string;
  sigla_fonte: string;
  nome_fonte: string;
  tipo_fonte: string;
  uf: string;
  praca: string;
  valor: number | null;
  unidade: string;
  periodicidade: string;
  data_referencia?: string | null;
  variacao_pct?: number | null;
  url_consulta: string;
  registro_origem?: string | null;
}

export interface ResumoMultiFonteApi {
  total_fontes_catalogo: number;
  fontes_com_preco_ativo: number;
  valor_minimo: number | null;
  fonte_minima: string | null;
  valor_medio: number | null;
  valor_maximo: number | null;
  fonte_maxima: string | null;
  dispersao_pct: number | null;
  valor_recomendado_regiao: number | null;
  fonte_recomendada_regiao: string | null;
}

export interface CotacaoRegiaoApiItem {
  id: string;
  nome: string;
  unidade: string;
  uf_consulta: string;
  fontes: FonteRegiaoApiItem[];
  resumo: ResumoMultiFonteApi;
}

export interface DestaqueCotacaoCard {
  familia: FamiliaFonteMercado;
  sigla: string;
  valor: number;
  moeda: string;
  unidade: string;
  indicacaoTemporal: string;
  dataLabel: string;
  dataReferencia: string;
  origem: string;
  documentoHashSha256: string | null;
  variacaoSemanalPct?: number;
  valorSemanaAnterior?: number;
  urlConsulta: string;
  ehHistoricoAnual: boolean;
}

export interface FonteComparativaCard {
  chave: string;
  familia: FamiliaFonteMercado;
  sigla: string;
  detalhe: string;
  valor: number | null;
  moeda: string;
  urlConsulta: string;
}

export interface ExibicaoCardMercado {
  destaque: DestaqueCotacaoCard | null;
  badgeCabecalho: { texto: string; variant: "success" | "warning" | "info" | "outline" };
  mostrarFaixaPr: boolean;
  pracaRegionalSelecionada: PracaRegionalDeralItem | null;
  avisoPracaIndisponivel: boolean;
  regiaoLabel: string;
  motivoIndisponivel: string;
  subtituloIndisponivel: string;
  outrasFontes: FonteComparativaCard[];
  ctaPrincipal: { rotulo: string; href: string; ariaLabel: string };
  urlDownloadXls: string | null;
  naturezaPreco: string;
  modoConsultaDireta: boolean;
}

export interface EntradaResolucaoCard {
  produto: ProdutoCatalogo;
  precoDeral?: PrecoPublicoItem;
  regiaoMultiItem: CotacaoRegiaoApiItem | null;
  ufAtiva: string;
  pracaAtiva: string;
  fonteAtiva: FonteFiltroMercado | string;
}

export const UFS_MERCADO_BRASIL: readonly UfBrasilItem[] = [
  { sigla: "AC", nome: "Acre", codigoIbge: "12" },
  { sigla: "AL", nome: "Alagoas", codigoIbge: "27" },
  { sigla: "AP", nome: "Amapá", codigoIbge: "16" },
  { sigla: "AM", nome: "Amazonas", codigoIbge: "13" },
  { sigla: "BA", nome: "Bahia", codigoIbge: "29" },
  { sigla: "CE", nome: "Ceará", codigoIbge: "23" },
  { sigla: "DF", nome: "Distrito Federal", codigoIbge: "53" },
  { sigla: "ES", nome: "Espírito Santo", codigoIbge: "32" },
  { sigla: "GO", nome: "Goiás", codigoIbge: "52" },
  { sigla: "MA", nome: "Maranhão", codigoIbge: "21" },
  { sigla: "MT", nome: "Mato Grosso", codigoIbge: "51" },
  { sigla: "MS", nome: "Mato Grosso do Sul", codigoIbge: "50" },
  { sigla: "MG", nome: "Minas Gerais", codigoIbge: "31" },
  { sigla: "PA", nome: "Pará", codigoIbge: "15" },
  { sigla: "PB", nome: "Paraíba", codigoIbge: "25" },
  { sigla: "PR", nome: "Paraná", codigoIbge: "41" },
  { sigla: "PE", nome: "Pernambuco", codigoIbge: "26" },
  { sigla: "PI", nome: "Piauí", codigoIbge: "22" },
  { sigla: "RJ", nome: "Rio de Janeiro", codigoIbge: "33" },
  { sigla: "RN", nome: "Rio Grande do Norte", codigoIbge: "24" },
  { sigla: "RS", nome: "Rio Grande do Sul", codigoIbge: "43" },
  { sigla: "RO", nome: "Rondônia", codigoIbge: "11" },
  { sigla: "RR", nome: "Roraima", codigoIbge: "14" },
  { sigla: "SC", nome: "Santa Catarina", codigoIbge: "42" },
  { sigla: "SP", nome: "São Paulo", codigoIbge: "35" },
  { sigla: "SE", nome: "Sergipe", codigoIbge: "28" },
  { sigla: "TO", nome: "Tocantins", codigoIbge: "17" },
] as const;

const UF_POR_SIGLA = new Map(UFS_MERCADO_BRASIL.map((u) => [u.sigla, u]));
const URL_DERAL_PADRAO = "https://www.agricultura.pr.gov.br/deral/precos";
const URL_SIDRA_PADRAO = "https://sidra.ibge.gov.br/tabela/5457";
const URL_CONAB_PADRAO = "https://www.gov.br/conab/pt-br/assuntos/informacoes-agropecuarias/precos-agropecuarios";
const URL_B3_PADRAO = "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/cotacoes/agro/";

/**
 * Verifica se a sigla informada corresponde a uma das 27 UFs brasileiras.
 */
export function isUfValida(sigla: string | null | undefined): boolean {
  if (!sigla) return false;
  return UF_POR_SIGLA.has(sigla.trim().toUpperCase());
}

/**
 * Retorna o nome completo da UF a partir da sigla oficial.
 */
export function obterNomeUf(sigla: string | null | undefined): string {
  const normalizada = String(sigla ?? "PR").trim().toUpperCase();
  return UF_POR_SIGLA.get(normalizada)?.nome ?? normalizada;
}

/**
 * Valida URLs externas contra a allow-list institucional (ou domínio de fixture HTTPS em testes).
 */
export function sanitizarUrlExternaSegura(
  url: string | null | undefined,
  fallback: string,
  permitirFixture = false
): string {
  if (!url || typeof url !== "string") return fallback;
  if (isUrlInstitucionalSegura(url)) return url;
  if (permitirFixture) {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "https:" && parsed.hostname === "example.invalid") {
        return url;
      }
    } catch {
      return fallback;
    }
  }
  return fallback;
}

/**
 * Normaliza a família de uma fonte de dados a partir da sigla ou identificador.
 */
export function identificarFamiliaFonte(siglaOuId: string): FamiliaFonteMercado {
  const texto = siglaOuId.toUpperCase();
  if (texto.includes("FIXTURE")) return "FIXTURE";
  if (texto.includes("DERAL")) return "DERAL";
  if (texto.includes("IBGE") || texto.includes("SIDRA")) return "IBGE";
  if (texto.includes("CEPEA")) return "CEPEA";
  if (texto.includes("CONAB")) return "CONAB";
  if (texto.includes("B3")) return "B3";
  return "OUTRA";
}

function normalizarFonteFiltro(fonte: string): FonteFiltroMercado {
  const up = fonte.trim().toUpperCase();
  if (up === "DERAL" || up === "IBGE" || up === "CEPEA" || up === "CONAB" || up === "B3") {
    return up;
  }
  return "TODAS";
}

/**
 * Filtra os produtos do catálogo de acordo com a fonte selecionada.
 */
export function filtrarProdutosPorFonte(
  produtos: ProdutoCatalogo[],
  fonteAtiva: string
): ProdutoCatalogo[] {
  const filtro = normalizarFonteFiltro(fonteAtiva);
  if (filtro === "TODAS" || filtro === "DERAL" || filtro === "IBGE") {
    return produtos;
  }
  const termo = filtro.toLowerCase();
  return produtos.filter((p) =>
    p.fontesReferencia.some(
      (f) => f.nome.toLowerCase().includes(termo) || f.id.toLowerCase().includes(termo)
    )
  );
}

function resolverPracaDeral(
  precoDeral: PrecoPublicoItem | undefined,
  ufAtiva: string,
  pracaAtiva: string
): { selecionada: PracaRegionalDeralItem | null; indisponivel: boolean } {
  if (!precoDeral || ufAtiva !== "PR" || pracaAtiva === "MEDIA_ESTADUAL") {
    return { selecionada: null, indisponivel: false };
  }
  const match = (precoDeral.pracasRegionais ?? []).find((p) => p.praca === pracaAtiva) ?? null;
  return { selecionada: match, indisponivel: match === null };
}

function construirDestaqueDeral(
  produto: ProdutoCatalogo,
  precoDeral: PrecoPublicoItem,
  pracaSelecionada: PracaRegionalDeralItem | null
): DestaqueCotacaoCard {
  const familia = identificarFamiliaFonte(precoDeral.siglaFonte);
  const urlBruta = precoDeral.urlConsultaInstitucional || precoDeral.linkOficial || produto.urlConsultaInstitucional;
  const urlConsulta = sanitizarUrlExternaSegura(urlBruta, URL_DERAL_PADRAO, familia === "FIXTURE");
  return {
    familia,
    sigla: precoDeral.siglaFonte,
    valor: pracaSelecionada ? pracaSelecionada.valor : precoDeral.valor,
    moeda: precoDeral.moeda,
    unidade: precoDeral.unidade,
    indicacaoTemporal: precoDeral.indicacaoTemporal,
    dataLabel: `Ref.: ${formatarDataPreco(precoDeral.dataReferencia)}`,
    dataReferencia: precoDeral.dataReferencia,
    origem: pracaSelecionada ? pracaSelecionada.registroOriginal : precoDeral.registroOriginal,
    documentoHashSha256: precoDeral.documentoHashSha256 || null,
    variacaoSemanalPct: typeof precoDeral.variacaoSemanalPct === "number" ? precoDeral.variacaoSemanalPct : undefined,
    valorSemanaAnterior: typeof precoDeral.valorSemanaAnterior === "number" ? precoDeral.valorSemanaAnterior : undefined,
    urlConsulta,
    ehHistoricoAnual: false,
  };
}

function construirDestaqueIbge(
  fonteIbge: FonteRegiaoApiItem,
  ufAtiva: string,
  unidadeFallback: string
): DestaqueCotacaoCard {
  const anoTexto = fonteIbge.data_referencia ? `Safra ${fonteIbge.data_referencia} (anual)` : "Última safra PAM";
  return {
    familia: "IBGE",
    sigla: "IBGE/SIDRA (PAM)",
    valor: Number(fonteIbge.valor),
    moeda: "BRL",
    unidade: fonteIbge.unidade || unidadeFallback,
    indicacaoTemporal: `Média Histórica Anual · IBGE/PAM (${ufAtiva})`,
    dataLabel: anoTexto,
    dataReferencia: fonteIbge.data_referencia ?? "",
    origem: fonteIbge.registro_origem ?? "SIDRA!T5457(V215/V214)",
    documentoHashSha256: null,
    urlConsulta: sanitizarUrlExternaSegura(fonteIbge.url_consulta, URL_SIDRA_PADRAO),
    ehHistoricoAnual: true,
  };
}

function mapearFonteCatalogo(fonteRef: FonteReferencia): FonteComparativaCard {
  const familia = identificarFamiliaFonte(`${fonteRef.id} ${fonteRef.nome}`);
  return {
    chave: `cat-${fonteRef.id}`,
    familia,
    sigla: fonteRef.nome,
    detalhe: fonteRef.abrangencia,
    valor: null,
    moeda: "BRL",
    urlConsulta: sanitizarUrlExternaSegura(fonteRef.url, URL_CONAB_PADRAO),
  };
}

function coletarOutrasFontes(
  entrada: EntradaResolucaoCard,
  fonteIbge: FonteRegiaoApiItem | null,
  familiaExcluida: FamiliaFonteMercado | null
): FonteComparativaCard[] {
  const lista: FonteComparativaCard[] = [];
  const familiasPresentes = new Set<FamiliaFonteMercado>();

  if (entrada.precoDeral && familiaExcluida !== "DERAL" && familiaExcluida !== "FIXTURE") {
    familiasPresentes.add("DERAL");
    lista.push({
      chave: "deral-pr-ref",
      familia: "DERAL",
      sigla: "DERAL-PR",
      detalhe: `Ref. semanal PR · ${entrada.precoDeral.pracaReferencia}`,
      valor: entrada.precoDeral.valor,
      moeda: entrada.precoDeral.moeda,
      urlConsulta: sanitizarUrlExternaSegura(entrada.precoDeral.urlConsultaInstitucional, URL_DERAL_PADRAO),
    });
  }

  if (fonteIbge && typeof fonteIbge.valor === "number" && familiaExcluida !== "IBGE") {
    familiasPresentes.add("IBGE");
    lista.push({
      chave: `ibge-${entrada.ufAtiva}`,
      familia: "IBGE",
      sigla: `IBGE/PAM (${entrada.ufAtiva})`,
      detalhe: `Histórico anual · Safra ${fonteIbge.data_referencia ?? "PAM"}`,
      valor: fonteIbge.valor,
      moeda: "BRL",
      urlConsulta: sanitizarUrlExternaSegura(fonteIbge.url_consulta, URL_SIDRA_PADRAO),
    });
  }

  for (const fonteRef of entrada.produto.fontesReferencia) {
    const item = mapearFonteCatalogo(fonteRef);
    if (item.familia === "DERAL" || item.familia === familiaExcluida || familiasPresentes.has(item.familia)) {
      continue;
    }
    familiasPresentes.add(item.familia);
    lista.push(item);
  }

  return lista;
}

function resolverCtaSemDestaque(
  produto: ProdutoCatalogo,
  outrasFontes: FonteComparativaCard[],
  filtro: FonteFiltroMercado
): { rotulo: string; href: string; ariaLabel: string } {
  if (filtro === "IBGE") {
    return {
      rotulo: "Consultar no IBGE/SIDRA",
      href: URL_SIDRA_PADRAO,
      ariaLabel: `Consultar ${produto.nome} no portal IBGE/SIDRA`,
    };
  }
  if (filtro === "B3") {
    return {
      rotulo: "Consultar na B3",
      href: URL_B3_PADRAO,
      ariaLabel: `Consultar ${produto.nome} na B3`,
    };
  }
  const preferida =
    outrasFontes.find((f) => f.familia !== "DERAL") ??
    outrasFontes[0] ??
    null;
  if (preferida) {
    const familiaPrincipal = identificarFamiliaFonte(produto.fontePrincipalNome);
    const rotuloFonte =
      preferida.familia === familiaPrincipal ? produto.fontePrincipalNome : preferida.sigla;
    return {
      rotulo: `Consultar no ${rotuloFonte}`,
      href: preferida.urlConsulta,
      ariaLabel: `Consultar ${produto.nome} em ${rotuloFonte}`,
    };
  }
  const hrefFallback = sanitizarUrlExternaSegura(produto.urlConsultaInstitucional, URL_CONAB_PADRAO);
  return {
    rotulo: `Consultar no ${produto.fontePrincipalNome}`,
    href: hrefFallback,
    ariaLabel: `Consultar no ${produto.fontePrincipalNome}: ${produto.nome}`,
  };
}

function obterUrlDownloadDeral(precoDeral: PrecoPublicoItem, produto: ProdutoCatalogo): string | null {
  if (identificarFamiliaFonte(precoDeral.siglaFonte) === "FIXTURE") {
    return precoDeral.urlDocumentoDownload ?? null;
  }
  const candidata = precoDeral.urlDocumentoDownload ?? produto.urlDocumentoDownload ?? precoDeral.documentoOficial;
  return candidata && isUrlInstitucionalSegura(candidata) ? candidata : null;
}

function resolverRegiaoLabel(
  entrada: EntradaResolucaoCard,
  destaque: DestaqueCotacaoCard | null,
  pracaSelecionada: PracaRegionalDeralItem | null,
  fonteIbge: FonteRegiaoApiItem | null
): string {
  const nomeUf = obterNomeUf(entrada.ufAtiva);
  if (destaque?.familia === "IBGE" && fonteIbge) {
    return fonteIbge.praca;
  }
  if (destaque && (destaque.familia === "DERAL" || destaque.familia === "FIXTURE")) {
    return pracaSelecionada
      ? `${pracaSelecionada.praca}/PR (Núcleo DERAL)`
      : entrada.precoDeral?.pracaReferencia ?? entrada.produto.pracaReferencia;
  }
  return `${nomeUf} (${entrada.ufAtiva})`;
}

/**
 * Resolve o estado unificado de exibição de cada card em /mercado para a região e fonte selecionadas.
 */
export function resolverExibicaoCardMercado(entrada: EntradaResolucaoCard): ExibicaoCardMercado {
  const ufAtiva = String(entrada.ufAtiva || "PR").trim().toUpperCase();
  const nomeUf = obterNomeUf(ufAtiva);
  const filtro = normalizarFonteFiltro(entrada.fonteAtiva);
  const { selecionada: pracaSel, indisponivel: avisoPraca } = resolverPracaDeral(
    entrada.precoDeral,
    ufAtiva,
    entrada.pracaAtiva
  );
  const fonteIbge =
    entrada.regiaoMultiItem?.fontes.find(
      (f) => identificarFamiliaFonte(f.sigla_fonte) === "IBGE" && typeof f.valor === "number" && f.valor > 0
    ) ?? null;

  if (filtro === "CEPEA" || filtro === "CONAB" || filtro === "B3") {
    const fonteMatch = entrada.produto.fontesReferencia.find(
      (f) => identificarFamiliaFonte(`${f.id} ${f.nome}`) === filtro
    );
    const nomeFonte = fonteMatch?.nome ?? (filtro === "CEPEA" ? "CEPEA/ESALQ" : filtro === "CONAB" ? "CONAB/MAPA" : "B3");
    const urlFonte = sanitizarUrlExternaSegura(
      fonteMatch?.url,
      filtro === "B3" ? URL_B3_PADRAO : URL_CONAB_PADRAO
    );
    return {
      destaque: null,
      badgeCabecalho: { texto: "Consulta Direta", variant: "outline" },
      mostrarFaixaPr: false,
      pracaRegionalSelecionada: null,
      avisoPracaIndisponivel: false,
      regiaoLabel: `${nomeUf} (${ufAtiva})`,
      motivoIndisponivel: `Consulta oficial direta no ${nomeFonte}`,
      subtituloIndisponivel: `Acesse o portal primário para cotação em ${nomeUf} (${ufAtiva}).`,
      outrasFontes: [],
      ctaPrincipal: {
        rotulo: `Consultar no ${nomeFonte}`,
        href: urlFonte,
        ariaLabel: `Consultar ${entrada.produto.nome} em ${nomeFonte}`,
      },
      urlDownloadXls: null,
      naturezaPreco: entrada.produto.tipoIndicador === "FISICO_SPOT" ? "Mercado Físico (Spot)" : "Estatístico / Conjuntura",
      modoConsultaDireta: true,
    };
  }

  let destaque: DestaqueCotacaoCard | null = null;
  let badgeCabecalho: ExibicaoCardMercado["badgeCabecalho"] = { texto: "Preço indisponível", variant: "outline" };

  if (filtro === "IBGE") {
    if (fonteIbge) {
      destaque = construirDestaqueIbge(fonteIbge, ufAtiva, entrada.produto.unidade);
      badgeCabecalho = { texto: "Histórico Anual IBGE", variant: "warning" };
    }
  } else if (filtro === "DERAL" || (filtro === "TODAS" && ufAtiva === "PR")) {
    if (entrada.precoDeral) {
      destaque = construirDestaqueDeral(entrada.produto, entrada.precoDeral, pracaSel);
      badgeCabecalho = { texto: "Preço Público Real", variant: "success" };
    } else if (filtro === "TODAS" && fonteIbge) {
      destaque = construirDestaqueIbge(fonteIbge, ufAtiva, entrada.produto.unidade);
      badgeCabecalho = { texto: "Histórico Anual IBGE", variant: "warning" };
    }
  } else if (fonteIbge) {
    destaque = construirDestaqueIbge(fonteIbge, ufAtiva, entrada.produto.unidade);
    badgeCabecalho = { texto: "Histórico Anual IBGE", variant: "warning" };
  } else if (entrada.precoDeral) {
    badgeCabecalho = { texto: "Referência externa (PR)", variant: "info" };
  }

  const familiaExcluida = destaque ? destaque.familia : null;
  const outrasFontes =
    filtro === "DERAL" || filtro === "IBGE"
      ? []
      : coletarOutrasFontes(entrada, fonteIbge, familiaExcluida);

  const ehDeralOuFixture = Boolean(destaque && (destaque.familia === "DERAL" || destaque.familia === "FIXTURE"));
  const mostrarFaixaPr = Boolean(
    ehDeralOuFixture &&
      entrada.precoDeral &&
      (pracaSel ||
        (typeof entrada.precoDeral.valorMinimoRegional === "number" &&
          typeof entrada.precoDeral.valorMaximoRegional === "number"))
  );

  const motivoIndisponivel =
    filtro === "IBGE"
      ? "Série de valor da produção indisponível no IBGE/PAM para este produto."
      : filtro === "DERAL"
        ? "Cotação semanal DERAL-PR indisponível para este item."
        : ufAtiva !== "PR"
          ? `Sem cotação corrente oficial para ${nomeUf} (${ufAtiva}).`
          : "Preço oficial verificável indisponível";

  const subtituloIndisponivel =
    !destaque && entrada.precoDeral && ufAtiva !== "PR" && filtro === "TODAS"
      ? "Veja abaixo a referência semanal do Paraná (DERAL-PR) e os canais nacionais."
      : "Consulte os portais institucionais homologados abaixo.";

  const ctaPrincipal = destaque
    ? {
        rotulo: `Consultar no ${destaque.sigla}`,
        href: destaque.urlConsulta,
        ariaLabel: `Consultar no ${destaque.sigla}: ${entrada.produto.nome}`,
      }
    : resolverCtaSemDestaque(entrada.produto, outrasFontes, filtro);

  return {
    destaque,
    badgeCabecalho,
    mostrarFaixaPr,
    pracaRegionalSelecionada: ehDeralOuFixture ? pracaSel : null,
    avisoPracaIndisponivel: ehDeralOuFixture && avisoPraca,
    regiaoLabel: resolverRegiaoLabel(entrada, destaque, pracaSel, fonteIbge),
    motivoIndisponivel,
    subtituloIndisponivel,
    outrasFontes,
    ctaPrincipal,
    urlDownloadXls: ehDeralOuFixture && entrada.precoDeral ? obterUrlDownloadDeral(entrada.precoDeral, entrada.produto) : null,
    naturezaPreco: ehDeralOuFixture
      ? "Preço Médio Produtor (Oficial)"
      : destaque?.familia === "IBGE"
        ? "Média Anual Ponderada (PAM/IBGE)"
        : entrada.produto.tipoIndicador === "FISICO_SPOT"
          ? "Mercado Físico (Spot)"
          : "Estatístico / Conjuntura",
    modoConsultaDireta: false,
  };
}
