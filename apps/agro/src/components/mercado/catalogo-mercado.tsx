"use client";

import * as React from "react";
import {
  Search,
  ExternalLink,
  Wheat,
  Coffee,
  Beef,
  Sprout,
  Building2,
  MapPin,
  Scale,
  ShieldCheck,
  X,
  Layers,
  BookOpen,
  Clock,
  Info,
  AlertTriangle,
  RefreshCw,
  WifiOff,
  FileSpreadsheet,
  Download,
  Leaf,
  Factory,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { agroApiUrl } from "@/lib/api-url";
import {
  CATEGORIAS_MERCADO,
  CATEGORIAS_ATIVAS_EXIBICAO,
  filtrarProdutos,
  isUrlInstitucionalSegura,
  obterContagemPorCategoria,
  type CategoriaMercado,
  type ProdutoCatalogo,
} from "@/lib/mercado/catalogo";
import { useMoedaMercado } from "@/lib/mercado/moeda-store";
import {
  converterBrlParaMoeda,
  fetchPrecosPublicos,
  formatarDataPreco,
  formatarPrecoMoeda,
  formatarPrecoPublico,
  readSavedPrecos,
  savePrecos,
  type PrecoPublicoItem,
} from "@/lib/mercado/precos";
import { formatDateBr } from "@/lib/mercado/ptax";
import { cn } from "@/lib/utils";

interface CatalogoMercadoProps {
  initialProdutos: ProdutoCatalogo[];
  mostrarPrecosDeral?: boolean;
}

interface FonteRegiaoApiItem {
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

interface ResumoMultiFonteApi {
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

interface CotacaoRegiaoApiItem {
  id: string;
  nome: string;
  unidade: string;
  uf_consulta: string;
  fontes: FonteRegiaoApiItem[];
  resumo: ResumoMultiFonteApi;
}

const UFS_AGRO_REGIOES: { sigla: string; nome: string }[] = [
  { sigla: "PR", nome: "Paraná (PR) — 20 Núcleos DERAL + IBGE" },
  { sigla: "MT", nome: "Mato Grosso (MT)" },
  { sigla: "GO", nome: "Goiás (GO)" },
  { sigla: "MS", nome: "Mato Grosso do Sul (MS)" },
  { sigla: "RS", nome: "Rio Grande do Sul (RS)" },
  { sigla: "SP", nome: "São Paulo (SP)" },
  { sigla: "MG", nome: "Minas Gerais (MG)" },
  { sigla: "BA", nome: "Bahia (BA)" },
  { sigla: "SC", nome: "Santa Catarina (SC)" },
  { sigla: "TO", nome: "Tocantins (TO)" },
  { sigla: "MA", nome: "Maranhão (MA)" },
  { sigla: "PI", nome: "Piauí (PI)" },
  { sigla: "PA", nome: "Pará (PA)" },
  { sigla: "RO", nome: "Rondônia (RO)" },
  { sigla: "ES", nome: "Espírito Santo (ES)" },
];

function obterIconeCommodity(categoria: CategoriaMercado, id: string) {
  if (id === "cafe-arabica") {
    return Coffee;
  }
  if (categoria === "PECUARIA") {
    return Beef;
  }
  if (categoria === "GRAOS_CEREAIS" || categoria === "GRAOS_CEREAIS_OLEAGINOSAS") {
    return Wheat;
  }
  if (categoria === "CANA_DERIVADOS") {
    return Factory;
  }
  if (categoria === "OUTROS") {
    return Leaf;
  }
  if (categoria === "FIBRAS" || categoria === "FIBRAS_OUTROS") {
    return Layers;
  }
  return Sprout;
}

export function CatalogoMercado({ initialProdutos, mostrarPrecosDeral = false }: CatalogoMercadoProps) {
  const [busca, setBusca] = React.useState("");
  const [categoriaAtiva, setCategoriaAtiva] = React.useState<CategoriaMercado | "TODAS">("TODAS");
  const [ufAtiva, setUfAtiva] = React.useState<string>("PR");
  const [pracaAtiva, setPracaAtiva] = React.useState<string>("MEDIA_ESTADUAL");
  const [fonteAtiva, setFonteAtiva] = React.useState<string>("TODAS");
  const [regiaoMultiMap, setRegiaoMultiMap] = React.useState<Record<string, CotacaoRegiaoApiItem>>({});
  const [precosMap, setPrecosMap] = React.useState<Record<string, PrecoPublicoItem>>({});
  const [estadoPrecos, setEstadoPrecos] = React.useState<"CARREGANDO" | "ATUAL" | "DEFASADO" | "CACHE_ANTIGO" | "ERRO" | "INDISPONIVEL" | "FORA_ESCOPO">(mostrarPrecosDeral ? "CARREGANDO" : "FORA_ESCOPO");
  const [tentativa, setTentativa] = React.useState(0);
  const { currency, quote, loading: loadingMoeda } = useMoedaMercado();

  React.useEffect(() => {
    if (!mostrarPrecosDeral) {
      setPrecosMap({});
      setEstadoPrecos("FORA_ESCOPO");
      return;
    }
    let cancelado = false;
    const controller = new AbortController();

    let temCache = false;
    if (typeof window !== "undefined") {
      const cached = readSavedPrecos(window.localStorage);
      if (cached && cached.itens.length > 0) {
        temCache = true;
        const mapa: Record<string, PrecoPublicoItem> = {};
        for (const item of cached.itens) {
          mapa[item.id] = item;
        }
        setPrecosMap(mapa);
        setEstadoPrecos("CACHE_ANTIGO");
      }
    }

    async function carregar() {
      try {
        if (typeof window === "undefined") return;
        const res = await fetchPrecosPublicos(window.location, controller.signal);
        if (!cancelado && res && res.itens.length > 0) {
          const mapa: Record<string, PrecoPublicoItem> = {};
          for (const item of res.itens) {
            mapa[item.id] = item;
          }
          setPrecosMap(mapa);
          savePrecos(window.localStorage, res);
          setEstadoPrecos(res.estadoDisponibilidade === "NORMAL" ? "ATUAL" : "DEFASADO");
        } else if (!cancelado) {
          setPrecosMap({});
          setEstadoPrecos("INDISPONIVEL");
        }
      } catch {
        if (!cancelado) setEstadoPrecos(temCache ? "CACHE_ANTIGO" : "ERRO");
      }
    }

    void carregar();

    return () => {
      cancelado = true;
      controller.abort();
    };
  }, [tentativa, mostrarPrecosDeral]);

  React.useEffect(() => {
    const recuperar = () => setTentativa((valor) => valor + 1);
    window.addEventListener("online", recuperar);
    return () => window.removeEventListener("online", recuperar);
  }, []);

  React.useEffect(() => {
    if (!mostrarPrecosDeral || typeof window === "undefined") return;
    if (ufAtiva === "PR" && fonteAtiva !== "IBGE") {
      setRegiaoMultiMap({});
      return;
    }
    const controller = new AbortController();
    const params = new URLSearchParams({ uf: ufAtiva, incluir_ibge: "true" });
    if (ufAtiva === "PR" && pracaAtiva !== "MEDIA_ESTADUAL") {
      params.set("praca", pracaAtiva);
    }
    fetch(agroApiUrl(`/api/v1/public/mercado/cotacoes-regiao?${params.toString()}`), {
      credentials: "omit",
      signal: controller.signal,
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((payload) => {
        if (payload && Array.isArray(payload.itens)) {
          const mapa: Record<string, CotacaoRegiaoApiItem> = {};
          for (const it of payload.itens as CotacaoRegiaoApiItem[]) {
            if (it && typeof it.id === "string") mapa[it.id] = it;
          }
          setRegiaoMultiMap(mapa);
        }
      })
      .catch(() => {
        /* Fallback silencioso mantendo fontes locais e DERAL */
      });
    return () => controller.abort();
  }, [ufAtiva, pracaAtiva, fonteAtiva, mostrarPrecosDeral]);

  const contagem = React.useMemo(() => {
    return obterContagemPorCategoria(initialProdutos);
  }, [initialProdutos]);

  const produtosFiltrados = React.useMemo(() => {
    const base = filtrarProdutos(initialProdutos, {
      busca,
      categoria: categoriaAtiva,
    });
    if (fonteAtiva === "TODAS" || fonteAtiva === "DERAL" || fonteAtiva === "IBGE") {
      return base;
    }
    const fLow = fonteAtiva.toLowerCase();
    return base.filter((p) =>
      p.fontesReferencia.some(
        (f) => f.nome.toLowerCase().includes(fLow) || f.id.toLowerCase().includes(fLow)
      )
    );
  }, [initialProdutos, busca, categoriaAtiva, fonteAtiva]);

  const totalGeral = initialProdutos.length;
  const dataReferenciaPrecos = Object.values(precosMap)[0]?.dataReferencia;
  const pracasDisponiveis = React.useMemo(() => {
    const conjunto = new Set<string>();
    for (const item of Object.values(precosMap)) {
      for (const p of item.pracasRegionais ?? []) {
        if (p.praca) conjunto.add(p.praca);
      }
    }
    return Array.from(conjunto).sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [precosMap]);

  return (
    <div className="flex flex-col gap-4">
      {/* Alerta Metodológico Oficial de Preços Agropecuários */}
      <Alert variant="default">
        <Info className="size-4 text-emerald-600 dark:text-emerald-400" />
        <AlertTitle className="text-xs">Preços Públicos Oficiais Verificáveis</AlertTitle>
        <AlertDescription className="text-xs">
          Os valores apresentados nos cards vêm do levantamento semanal oficial do DERAL/SEAB-PR, auditados com documento bruto, célula e hash criptográfico SHA-256. Caracterizam preço médio recebido pelo produtor rural e não cotação em tempo real.
        </AlertDescription>
      </Alert>

      {estadoPrecos !== "ATUAL" && (
        <div
          className="min-h-11 p-3 rounded-sm border border-amber-500/30 bg-amber-500/10 dark:border-amber-400/30 dark:bg-amber-500/15 flex items-center justify-between gap-3 text-xs"
          role="status"
          aria-live="polite"
          data-testid="estado-precos"
        >
          <span className="flex items-center gap-2 text-amber-950 dark:text-amber-200">
            {estadoPrecos === "CARREGANDO" ? (
              <RefreshCw className="size-4 animate-spin text-amber-700 dark:text-amber-300" />
            ) : estadoPrecos === "DEFASADO" || estadoPrecos === "CACHE_ANTIGO" ? (
              <AlertTriangle className="size-4 text-amber-700 dark:text-amber-300" />
            ) : (
              <WifiOff className="size-4 text-amber-700 dark:text-amber-300" />
            )}
            {estadoPrecos === "CARREGANDO" && "Carregando preços oficiais…"}
            {estadoPrecos === "DEFASADO" && `Referência semanal DERAL/SEAB-PR aguardando novo boletim oficial${dataReferenciaPrecos ? ` (última referência publicada: ${formatarDataPreco(dataReferenciaPrecos)})` : ""}.`}
            {estadoPrecos === "CACHE_ANTIGO" && "Exibindo dado salvo; a atualização da fonte está indisponível."}
            {estadoPrecos === "ERRO" && "Não foi possível consultar os preços oficiais."}
            {estadoPrecos === "INDISPONIVEL" && "A fonte respondeu sem preços oficiais verificáveis."}
            {estadoPrecos === "FORA_ESCOPO" && "Preços dinâmicos DERAL ficam fora deste MVP; consulte as referências oficiais listadas em cada item."}
          </span>
          {(estadoPrecos === "DEFASADO" || estadoPrecos === "ERRO" || estadoPrecos === "INDISPONIVEL" || estadoPrecos === "CACHE_ANTIGO") && (
            <Button variant="outline" size="sm" onClick={() => setTentativa((valor) => valor + 1)}>
              <RefreshCw className="size-3.5" />
              <span>{estadoPrecos === "DEFASADO" ? "Atualizar" : "Tentar novamente"}</span>
            </Button>
          )}
        </div>
      )}

      {/* Barra de Filtros e Busca Responsiva */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
        {/* Campo de Busca */}
        <div className="relative flex-1 max-w-md">
          <Search className="size-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por produto, praça ou fonte..."
            className="pl-8 pr-7 text-xs"
            aria-label="Buscar produtos agropecuários no catálogo"
          />
          {busca && (
            <button
              type="button"
              onClick={() => setBusca("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-0.5 cursor-pointer"
              aria-label="Limpar campo de busca"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Seletores de Região (UF), Núcleo Regional e Fonte de Dados */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5">
            <MapPin className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <select
              value={ufAtiva}
              onChange={(e) => {
                setUfAtiva(e.target.value);
                if (e.target.value !== "PR") setPracaAtiva("MEDIA_ESTADUAL");
              }}
              aria-label="Selecionar estado ou região (UF)"
              data-testid="seletor-uf-mercado"
              className={cn(inputBaseClassName, "w-auto text-xs px-2")}
            >
              {UFS_AGRO_REGIOES.map((uf) => (
                <option key={uf.sigla} value={uf.sigla}>
                  Região: {uf.nome}
                </option>
              ))}
            </select>
          </div>

          {ufAtiva === "PR" && pracasDisponiveis.length > 0 && (
            <div className="flex items-center gap-1.5">
              <select
                value={pracaAtiva}
                onChange={(e) => setPracaAtiva(e.target.value)}
                aria-label="Selecionar praça ou núcleo regional DERAL-PR"
                data-testid="seletor-praca-deral"
                className={cn(inputBaseClassName, "w-auto text-xs px-2")}
              >
                <option value="MEDIA_ESTADUAL">Paraná — Média Estadual ({pracasDisponiveis.length} núcleos)</option>
                {pracasDisponiveis.map((praca) => (
                  <option key={praca} value={praca}>
                    Núcleo Regional: {praca}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-1.5">
            <Building2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <select
              value={fonteAtiva}
              onChange={(e) => setFonteAtiva(e.target.value)}
              aria-label="Filtrar por fonte de dados de mercado"
              data-testid="seletor-fonte-mercado"
              className={cn(inputBaseClassName, "w-auto text-xs px-2")}
            >
              <option value="TODAS">Fonte: Todas (Comparativo Multi-Fonte)</option>
              <option value="DERAL">Fonte: DERAL/SEAB-PR (Físico Semanal)</option>
              <option value="IBGE">Fonte: IBGE/SIDRA (PAM Regional UF)</option>
              <option value="CEPEA">Fonte: CEPEA/ESALQ (Indicador Spot)</option>
              <option value="CONAB">Fonte: CONAB/MAPA (Referência Federal)</option>
              <option value="B3">Fonte: B3 / Futuros</option>
            </select>
          </div>
        </div>

        {/* Contador de Itens Encontrados */}
        <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 self-end sm:self-auto">
          <BookOpen className="size-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>
            Exibindo <strong>{produtosFiltrados.length}</strong> de {totalGeral} produtos
          </span>
        </div>
      </div>

      {/* Navegação por Categorias de Mercado (Pills) */}
      <div
        className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none"
        role="tablist"
        aria-label="Filtro por categoria de mercado"
      >
        <Button
          variant={categoriaAtiva === "TODAS" ? "default" : "outline"}
          size="sm"
          onClick={() => setCategoriaAtiva("TODAS")}
          className="shrink-0"
          role="tab"
          aria-selected={categoriaAtiva === "TODAS"}
        >
          Todos ({totalGeral})
        </Button>

        {CATEGORIAS_ATIVAS_EXIBICAO.map((catKey) => {
          const meta = CATEGORIAS_MERCADO[catKey];
          const selecionada = categoriaAtiva === catKey;
          const qtd = contagem[catKey] ?? 0;

          return (
            <Button
              key={catKey}
              variant={selecionada ? "default" : "outline"}
              size="sm"
              onClick={() => setCategoriaAtiva(catKey)}
              className="shrink-0"
              role="tab"
              aria-selected={selecionada}
            >
              {meta.label} ({qtd})
            </Button>
          );
        })}
      </div>

      {/* Estado Vazio de Busca */}
      {produtosFiltrados.length === 0 ? (
        <Card variant="muted" size="sm" className="text-center py-6">
          <CardContent className="flex flex-col items-center gap-2">
            <Layers className="size-6 text-muted-foreground" />
            <p className="text-xs font-semibold text-foreground">
              Nenhum produto encontrado
            </p>
            <p className="text-[11px] text-muted-foreground max-w-sm">
              Não encontramos resultados para &quot;{busca}&quot; na categoria selecionada.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setBusca("");
                setCategoriaAtiva("TODAS");
              }}
              className="mt-1"
            >
              Limpar filtros
            </Button>
          </CardContent>
        </Card>
      ) : (
        /* Grid Responsivo de Cards do Catálogo */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {produtosFiltrados.map((produto) => {
            const Icon = obterIconeCommodity(produto.categoriaMercado, produto.id);
            const isUrlSegura = isUrlInstitucionalSegura(produto.urlInstitucionalPrincipal);
            const precoReal = precosMap[produto.id];
            const regiaoMultiItem = regiaoMultiMap[produto.id] ?? null;
            const fonteIbgeUf =
              regiaoMultiItem?.fontes.find((f) => f.sigla_fonte === "IBGE/SIDRA (PAM)") ?? null;
            const pracaRegionalSelecionada =
              precoReal && ufAtiva === "PR" && pracaAtiva !== "MEDIA_ESTADUAL"
                ? (precoReal.pracasRegionais ?? []).find((p) => p.praca === pracaAtiva) ?? null
                : null;
            const usarPrecoIbgePrincipal =
              (ufAtiva !== "PR" || fonteAtiva === "IBGE") &&
              fonteIbgeUf &&
              typeof fonteIbgeUf.valor === "number";
            const valorExibido = usarPrecoIbgePrincipal
              ? fonteIbgeUf.valor
              : pracaRegionalSelecionada
                ? pracaRegionalSelecionada.valor
                : precoReal?.valor ?? null;
            const registroExibido = usarPrecoIbgePrincipal
              ? fonteIbgeUf.registro_origem ?? "SIDRA!T5457"
              : pracaRegionalSelecionada
                ? pracaRegionalSelecionada.registroOriginal
                : precoReal?.registroOriginal ?? "";

            const cotacaoValida =
              quote &&
              quote.moeda === currency &&
              typeof quote.cotacaoVenda === "number" &&
              quote.cotacaoVenda > 0
                ? quote
                : null;

            const valorConvertido =
              valorExibido !== null && cotacaoValida
                ? converterBrlParaMoeda(valorExibido, cotacaoValida.cotacaoVenda)
                : null;

            const precoConvertidoFormatado =
              valorConvertido !== null
                ? formatarPrecoMoeda(valorConvertido, currency)
                : null;

            const urlInstitucional =
              precoReal?.urlConsultaInstitucional ||
              produto.urlConsultaInstitucional ||
              (isUrlSegura ? produto.urlInstitucionalPrincipal : "https://www.agricultura.pr.gov.br/deral/precos");

            const urlDownload =
              precoReal?.urlDocumentoDownload ||
              produto.urlDocumentoDownload ||
              (precoReal ? precoReal.documentoOficial : null);

            return (
              <Card
                key={produto.id}
                data-commodity-id={produto.id}
                className="justify-between hover:border-primary/40 transition-colors"
              >
                <CardHeader className="border-b border-border/50">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-sm bg-muted text-foreground shrink-0">
                      <Icon className="size-4 text-emerald-700 dark:text-emerald-400" />
                    </div>
                    <div>
                      <CardTitle className="text-sm font-semibold text-foreground">
                        {produto.nome}
                      </CardTitle>
                      <CardDescription className="text-[11px]">
                        Padrão: {precoReal ? precoReal.unidade : produto.unidade}
                      </CardDescription>
                    </div>
                  </div>

                  <CardAction>
                    <Badge
                      variant={precoReal ? "success" : "outline"}
                    >
                      {precoReal ? "Preço Público Real" : "Preço indisponível"}
                    </Badge>
                  </CardAction>
                </CardHeader>

                <CardContent className="flex flex-col gap-3 flex-1 justify-between">
                  {/* Bloco de Preço Real Homologado ou Consulta Institucional */}
                  {precoReal ? (
                    <div className="p-2.5 rounded-sm bg-emerald-500/5 dark:bg-emerald-950/20 border border-emerald-500/20 flex flex-col gap-1.5 min-h-[92px] justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-emerald-800 dark:text-emerald-300 flex items-center gap-1">
                          <Clock className="size-3 text-emerald-600 dark:text-emerald-400" />
                          {precoReal.indicacaoTemporal}
                          {estadoPrecos === "CACHE_ANTIGO" ? " · dado salvo" : estadoPrecos === "DEFASADO" ? " · defasado" : ""}
                        </span>
                        <Badge variant="recommendation">
                          {precoReal.siglaFonte}
                        </Badge>
                      </div>

                      {/* Preço Oficial em Reais (Sempre Visível) + Variação Semanal */}
                      <div className="flex items-baseline justify-between gap-2 pt-0.5">
                        <div>
                          <span className="text-lg font-bold tracking-tight text-foreground">
                            {formatarPrecoPublico(valorExibido ?? precoReal.valor, precoReal.moeda)}
                          </span>
                          <span className="text-[11px] text-muted-foreground ml-1.5">
                            / {precoReal.unidade}
                          </span>
                        </div>
                        <div className="text-right flex flex-col items-end gap-0.5">
                          {typeof precoReal.variacaoSemanalPct === "number" && (
                            <Badge
                              data-testid="variacao-semanal-badge"
                              variant={
                                precoReal.variacaoSemanalPct > 0
                                  ? "success"
                                  : precoReal.variacaoSemanalPct < 0
                                    ? "warning"
                                    : "info"
                              }
                              title={
                                precoReal.valorSemanaAnterior
                                  ? `Média da semana anterior (MSA): ${formatarPrecoPublico(precoReal.valorSemanaAnterior, precoReal.moeda)}`
                                  : "Variação semanal oficial DERAL"
                              }
                              className="text-[10px]"
                            >
                              {precoReal.variacaoSemanalPct > 0 ? (
                                <TrendingUp className="size-2.5" />
                              ) : precoReal.variacaoSemanalPct < 0 ? (
                                <TrendingDown className="size-2.5" />
                              ) : null}
                              {precoReal.variacaoSemanalPct > 0 ? "+" : ""}
                              {precoReal.variacaoSemanalPct.toLocaleString("pt-BR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              })}
                              % sem.
                            </Badge>
                          )}
                          <span className="text-[10px] text-muted-foreground block">
                            Ref.: {formatarDataPreco(precoReal.dataReferencia)}
                          </span>
                        </div>
                      </div>

                      {/* Faixa Regional Mín–Máx ou Destaque do Núcleo Selecionado */}
                      {(pracaRegionalSelecionada ||
                        (typeof precoReal.valorMinimoRegional === "number" &&
                          typeof precoReal.valorMaximoRegional === "number")) && (
                        <div className="flex flex-wrap items-center justify-between gap-1 text-[10px] text-muted-foreground pt-1 border-t border-emerald-500/10">
                          {pracaRegionalSelecionada ? (
                            <span className="font-medium text-emerald-800 dark:text-emerald-300">
                              Núcleo {pracaRegionalSelecionada.praca} · Média PR: {formatarPrecoPublico(precoReal.valor, precoReal.moeda)}
                            </span>
                          ) : pracaAtiva !== "MEDIA_ESTADUAL" ? (
                            <span className="italic">
                              Sem cotação em {pracaAtiva} · exibindo Média PR
                            </span>
                          ) : (
                            <span>
                              Faixa PR ({precoReal.pracasRegionais?.length ?? 0} praças):{" "}
                              <strong className="text-foreground/90">
                                {formatarPrecoPublico(precoReal.valorMinimoRegional ?? precoReal.valor, precoReal.moeda)}
                              </strong>{" "}
                              ({precoReal.pracaMinimoRegional}) a{" "}
                              <strong className="text-foreground/90">
                                {formatarPrecoPublico(precoReal.valorMaximoRegional ?? precoReal.valor, precoReal.moeda)}
                              </strong>{" "}
                              ({precoReal.pracaMaximoRegional})
                            </span>
                          )}
                        </div>
                      )}

                      {/* Equivalente Cambial Reativo na Moeda Selecionada */}
                      <div
                        className="flex items-center justify-between gap-2 pt-1 border-t border-emerald-500/10 text-xs"
                        data-testid="conversao-cambial-card"
                      >
                        {precoConvertidoFormatado ? (
                          <div className="flex items-baseline gap-1 text-emerald-800 dark:text-emerald-300 font-medium truncate">
                            <span className="text-[10px] text-muted-foreground">Equiv.:</span>
                            <span className="font-mono font-bold text-foreground">
                              ≈ {precoConvertidoFormatado}
                            </span>
                            <span className="text-[10px] text-muted-foreground truncate">
                              / {precoReal.unidade}
                            </span>
                          </div>
                        ) : loadingMoeda ? (
                          <span className="text-[10px] text-muted-foreground flex items-center gap-1 animate-pulse">
                            <RefreshCw className="size-2.5 animate-spin" /> Atualizando cotação de {currency}…
                          </span>
                        ) : (
                          <span className="text-[10px] text-muted-foreground italic">
                            Câmbio de {currency} indisponível
                          </span>
                        )}

                        {cotacaoValida && typeof cotacaoValida.cotacaoVenda === "number" && (
                          <span
                            className="text-[9.5px] text-muted-foreground whitespace-nowrap"
                            title={`PTAX Venda: ${cotacaoValida.cotacaoVenda.toFixed(4)} BCB`}
                          >
                            PTAX {formatDateBr(cotacaoValida.dataCotacao ?? "")}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between text-[9.5px] text-muted-foreground pt-1 border-t border-emerald-500/10">
                        <span title={`Célula de origem: ${registroExibido || precoReal.registroOriginal}`}>
                          Origem: <strong className="font-mono text-foreground/80">{registroExibido || precoReal.registroOriginal}</strong>
                        </span>
                        <span className="font-mono text-[9px] text-muted-foreground/80" title={`SHA-256: ${precoReal.documentoHashSha256}`}>
                          SHA: {precoReal.documentoHashSha256.slice(0, 8)}…
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-sm bg-muted/40 border border-border/60 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] text-muted-foreground block">
                          Valor de Comercialização ({produto.moeda})
                        </span>
                        <span className="text-xs font-semibold text-foreground">
                          {estadoPrecos === "CARREGANDO" ? "Carregando preço oficial…" : "Preço oficial verificável indisponível"}
                        </span>
                      </div>
                      <Badge variant="recommendation">
                        {produto.fontePrincipalNome}
                      </Badge>
                    </div>
                  )}

                  {/* Descrição e Classificação Rigorosa */}
                  <div className="flex flex-col gap-1.5">
                    <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                      {produto.descricao}
                    </p>

                    <div className="p-2 rounded-sm bg-muted/40 border border-border/40 text-[10px] flex flex-col gap-1">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Classificação Agronômica:</span>
                        <span className="font-medium text-foreground text-right truncate max-w-[170px]">
                          {produto.classificacaoAgronomica}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Natureza do Preço:</span>
                        <span className="font-medium text-foreground">
                          {precoReal
                            ? "Preço Médio Produtor (Oficial)"
                            : produto.tipoIndicador === "FISICO_SPOT"
                            ? "Mercado Físico (Spot)"
                            : "Estatístico / Conjuntura"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Metadados e Comparativo Multi-Fonte por Região */}
                  <div className="flex flex-col gap-1.5 text-[11px] pt-1 border-t border-border/40">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MapPin className="size-3 text-muted-foreground shrink-0" /> Região / Praça:
                      </span>
                      <span
                        className="font-medium text-foreground text-right truncate max-w-[180px]"
                        title={
                          usarPrecoIbgePrincipal && fonteIbgeUf
                            ? fonteIbgeUf.praca
                            : pracaRegionalSelecionada
                              ? `${pracaRegionalSelecionada.praca}/PR (Núcleo DERAL)`
                              : precoReal
                                ? precoReal.pracaReferencia
                                : produto.pracaReferencia
                        }
                      >
                        {usarPrecoIbgePrincipal && fonteIbgeUf
                          ? fonteIbgeUf.praca
                          : pracaRegionalSelecionada
                            ? `${pracaRegionalSelecionada.praca}/PR (Núcleo DERAL)`
                            : precoReal
                              ? precoReal.pracaReferencia
                              : produto.pracaReferencia}
                      </span>
                    </div>

                    {/* Comparativo Lado a Lado das Fontes Homologadas para o Produto */}
                    <div className="rounded-sm border border-border/60 bg-muted/25 p-2 flex flex-col gap-1">
                      <div className="flex items-center justify-between text-[10px] font-semibold text-foreground">
                        <span className="flex items-center gap-1">
                          <Scale className="size-3 text-emerald-600 dark:text-emerald-400" />
                          Fontes por Região ({produto.fontesReferencia.length + (fonteIbgeUf ? 1 : 0)})
                        </span>
                        {precoReal?.valorMinimoRegional && precoReal?.valorMaximoRegional && (
                          <span className="text-[9.5px] font-normal text-muted-foreground tabular-nums">
                            Média PR: {formatarPrecoPublico(precoReal.valor, precoReal.moeda)}
                          </span>
                        )}
                      </div>

                      <div className="divide-y divide-border/40 text-[10px]">
                        {precoReal && (
                          <div className="py-1 flex items-center justify-between gap-2">
                            <span className="text-muted-foreground truncate">
                              <strong className="text-foreground">DERAL-PR</strong> ·{" "}
                              {pracaRegionalSelecionada ? `Núcleo ${pracaRegionalSelecionada.praca}` : "Média 20 Núcleos"}
                            </span>
                            <span className="font-semibold text-foreground tabular-nums shrink-0">
                              {formatarPrecoPublico(
                                pracaRegionalSelecionada ? pracaRegionalSelecionada.valor : precoReal.valor,
                                precoReal.moeda
                              )}
                            </span>
                          </div>
                        )}

                        {fonteIbgeUf && typeof fonteIbgeUf.valor === "number" && (
                          <div className="py-1 flex items-center justify-between gap-2">
                            <span className="text-muted-foreground truncate">
                              <strong className="text-foreground">IBGE/PAM ({ufAtiva})</strong> · Média Regional ({fonteIbgeUf.data_referencia})
                            </span>
                            <span className="font-semibold text-emerald-800 dark:text-emerald-300 tabular-nums shrink-0">
                              {formatarPrecoPublico(fonteIbgeUf.valor, "BRL")}
                            </span>
                          </div>
                        )}

                        {produto.fontesReferencia
                          .filter((f) => f.id !== "deral-pr")
                          .map((fonteRef) => (
                            <div key={fonteRef.id} className="py-1 flex items-center justify-between gap-2">
                              <span className="text-muted-foreground truncate" title={`${fonteRef.entidade} — ${fonteRef.abrangencia}`}>
                                <strong className="text-foreground">{fonteRef.nome}</strong> · {fonteRef.abrangencia}
                              </span>
                              <a
                                href={fonteRef.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-0.5 text-emerald-700 dark:text-emerald-300 hover:underline font-medium shrink-0"
                              >
                                Consultar <ExternalLink className="size-2.5" />
                              </a>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>

                  {/* Ações: Segregação Clara entre Portal Institucional e Download Bruto */}
                  <div className="pt-2 border-t border-border/40 flex flex-col gap-1.5">
                    {/* Botão Principal: Abre a página web informativa sem disparar download indesejado */}
                    <a
                      href={urlInstitucional}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        buttonVariants({ variant: "outline", size: "sm" }),
                        "w-full justify-between"
                      )}
                      aria-label={`Consultar no ${precoReal?.siglaFonte || produto.fontePrincipalNome}: ${produto.nome}`}
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span className="truncate">
                          Consultar no {precoReal?.siglaFonte || produto.fontePrincipalNome}
                        </span>
                      </span>
                      <ExternalLink className="size-3 text-muted-foreground shrink-0" />
                    </a>

                    {/* Botão Secundário de Download Explícito do Arquivo Bruto */}
                    {urlDownload && (
                      <a
                        href={urlDownload}
                        target="_blank"
                        rel="noopener noreferrer"
                        download
                        className={cn(
                          buttonVariants({ variant: "ghost", size: "xs" }),
                          "w-full text-[10px] text-muted-foreground hover:text-primary border border-border/50"
                        )}
                        title="Baixar planilha oficial semanal auditada (.xls)"
                        aria-label={`Baixar planilha oficial semanal com cotação de ${produto.nome}`}
                      >
                        <FileSpreadsheet className="size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span>Baixar planilha oficial (.xls)</span>
                        <Download className="size-2.5 opacity-70" />
                      </a>
                    )}

                    <p className="text-[9px] text-muted-foreground text-center">
                      Abre a fonte oficial governamental em nova aba
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
