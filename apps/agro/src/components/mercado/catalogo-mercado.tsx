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
} from "lucide-react";
import {
  CATEGORIAS_MERCADO,
  CATEGORIAS_ATIVAS_EXIBICAO,
  filtrarProdutos,
  isUrlInstitucionalSegura,
  obterContagemPorCategoria,
  type CategoriaMercado,
  type ProdutoCatalogo,
} from "@/lib/mercado/catalogo";
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
import { useMoedaMercado } from "@/lib/mercado/moeda-store";
import { formatDateBr } from "@/lib/mercado/ptax";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface CatalogoMercadoProps {
  initialProdutos: ProdutoCatalogo[];
  mostrarPrecosDeral?: boolean;
}

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

  const contagem = React.useMemo(() => {
    return obterContagemPorCategoria(initialProdutos);
  }, [initialProdutos]);

  const produtosFiltrados = React.useMemo(() => {
    return filtrarProdutos(initialProdutos, {
      busca,
      categoria: categoriaAtiva,
    });
  }, [initialProdutos, busca, categoriaAtiva]);

  const totalGeral = initialProdutos.length;
  const dataReferenciaPrecos = Object.values(precosMap)[0]?.dataReferencia;

  return (
    <div className="space-y-4">
      {/* Alerta Metodológico Oficial de Preços Agropecuários */}
      <div className="p-3 rounded-sm bg-muted/40 border border-border/70 flex items-start gap-2.5 text-xs text-muted-foreground">
        <Info className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="text-foreground font-semibold">Preços Públicos Oficiais Verificáveis: </strong>
          Os valores apresentados nos cards vêm do levantamento semanal oficial do DERAL/SEAB-PR, auditados com documento bruto, célula e hash criptográfico SHA-256. Caracterizam preço médio recebido pelo produtor rural e não cotação em tempo real.
        </div>
      </div>

      {estadoPrecos !== "ATUAL" && (
        <div
          className="min-h-11 p-3 rounded-sm border border-amber-500/30 bg-amber-500/5 flex items-center justify-between gap-3 text-xs"
          role="status"
          aria-live="polite"
          data-testid="estado-precos"
        >
          <span className="flex items-center gap-2 text-muted-foreground">
            {estadoPrecos === "CARREGANDO" ? <RefreshCw className="w-4 h-4 animate-spin" /> : estadoPrecos === "DEFASADO" || estadoPrecos === "CACHE_ANTIGO" ? <AlertTriangle className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            {estadoPrecos === "CARREGANDO" && "Carregando preços oficiais…"}
            {estadoPrecos === "DEFASADO" && `A fonte respondeu, mas o preço semanal está defasado${dataReferenciaPrecos ? ` (referência: ${formatarDataPreco(dataReferenciaPrecos)})` : ""}.`}
            {estadoPrecos === "CACHE_ANTIGO" && "Exibindo dado salvo; a atualização da fonte está indisponível."}
            {estadoPrecos === "ERRO" && "Não foi possível consultar os preços oficiais."}
            {estadoPrecos === "INDISPONIVEL" && "A fonte respondeu sem preços oficiais verificáveis."}
            {estadoPrecos === "FORA_ESCOPO" && "Preços dinâmicos DERAL ficam fora deste MVP; consulte as referências oficiais listadas em cada item."}
          </span>
          {(estadoPrecos === "ERRO" || estadoPrecos === "INDISPONIVEL" || estadoPrecos === "CACHE_ANTIGO") && (
            <Button variant="outline" size="sm" className="h-7 rounded-sm text-xs" onClick={() => setTentativa((valor) => valor + 1)}>
              Tentar novamente
            </Button>
          )}
        </div>
      )}

      {/* Barra de Filtros e Busca Responsiva */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between">
        {/* Campo de Busca */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por produto, praça ou fonte..."
            className="pl-8 pr-7 text-xs h-8 rounded-sm"
            aria-label="Buscar produtos agropecuários no catálogo"
          />
          {busca && (
            <button
              type="button"
              onClick={() => setBusca("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-0.5"
              aria-label="Limpar campo de busca"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Contador de Itens Encontrados */}
        <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 self-end sm:self-auto">
          <BookOpen className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
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
          className="rounded-sm text-xs h-7 px-2.5 flex-shrink-0"
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
              className="rounded-sm text-xs h-7 px-2.5 flex-shrink-0"
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
        <div className="p-8 rounded-sm border border-border/80 bg-muted/20 text-center space-y-2">
          <Layers className="w-6 h-6 text-muted-foreground mx-auto" />
          <p className="text-xs font-semibold text-foreground">
            Nenhum produto encontrado
          </p>
          <p className="text-[11px] text-muted-foreground max-w-sm mx-auto">
            Não encontramos resultados para &quot;{busca}&quot; na categoria selecionada.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setBusca("");
              setCategoriaAtiva("TODAS");
            }}
            className="text-xs mt-2 rounded-sm"
          >
            Limpar filtros
          </Button>
        </div>
      ) : (
        /* Grid Responsivo de Cards do Catálogo */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {produtosFiltrados.map((produto) => {
            const Icon = obterIconeCommodity(produto.categoriaMercado, produto.id);
            const isUrlSegura = isUrlInstitucionalSegura(produto.urlInstitucionalPrincipal);
            const precoReal = precosMap[produto.id];

            const cotacaoValida =
              quote &&
              quote.moeda === currency &&
              typeof quote.cotacaoVenda === "number" &&
              quote.cotacaoVenda > 0
                ? quote
                : null;

            const valorConvertido =
              precoReal && cotacaoValida
                ? converterBrlParaMoeda(precoReal.valor, cotacaoValida.cotacaoVenda)
                : null;

            const precoConvertidoFormatado =
              valorConvertido !== null
                ? formatarPrecoMoeda(valorConvertido, currency)
                : null;

            // Segregação clara de URLs: portal institucional navegável vs download de arquivo
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
                className="flex flex-col justify-between border-border/70 hover:border-emerald-600/40 transition-colors shadow-xs rounded-sm"
              >
                <CardHeader className="pb-3 border-b border-border/50">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-sm bg-muted text-foreground flex-shrink-0">
                        <Icon className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-semibold text-foreground">
                          {produto.nome}
                        </CardTitle>
                        <p className="text-[11px] text-muted-foreground">
                          Padrão: {precoReal ? precoReal.unidade : produto.unidade}
                        </p>
                      </div>
                    </div>

                    <Badge
                      variant={precoReal ? "default" : "outline"}
                      className={cn(
                        "text-[10px] rounded-sm flex-shrink-0",
                        precoReal
                          ? "bg-emerald-600 hover:bg-emerald-700 text-white border-transparent"
                          : "border-border text-muted-foreground"
                      )}
                    >
                      {precoReal ? "Preço Público Real" : "Preço indisponível"}
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="pt-3.5 space-y-3 flex-1 flex flex-col justify-between">
                  {/* Bloco de Preço Real Homologado ou Consulta Institucional */}
                  {precoReal ? (
                    <div className="p-2.5 rounded-sm bg-emerald-500/5 dark:bg-emerald-950/20 border border-emerald-500/20 space-y-1.5 min-h-[92px] flex flex-col justify-between">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-emerald-800 dark:text-emerald-300 flex items-center gap-1">
                          <Clock className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                          {precoReal.indicacaoTemporal}
                          {estadoPrecos === "CACHE_ANTIGO" ? " · dado salvo" : estadoPrecos === "DEFASADO" ? " · defasado" : ""}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-[10px] rounded-sm bg-background/80 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 font-semibold"
                        >
                          {precoReal.siglaFonte}
                        </Badge>
                      </div>

                      {/* Preço Oficial em Reais (Sempre Visível) */}
                      <div className="flex items-baseline justify-between gap-2 pt-0.5">
                        <div>
                          <span className="text-lg font-bold tracking-tight text-foreground">
                            {formatarPrecoPublico(precoReal.valor, precoReal.moeda)}
                          </span>
                          <span className="text-[11px] text-muted-foreground ml-1.5">
                            / {precoReal.unidade}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-muted-foreground block">
                            Ref.: {formatarDataPreco(precoReal.dataReferencia)}
                          </span>
                        </div>
                      </div>

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
                        <span title={`Célula de origem: ${precoReal.registroOriginal}`}>
                          Origem: <strong className="font-mono text-foreground/80">{precoReal.registroOriginal}</strong>
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
                      <Badge variant="outline" className="text-[10px] rounded-sm border-emerald-600/30 text-emerald-700 dark:text-emerald-400">
                        {produto.fontePrincipalNome}
                      </Badge>
                    </div>
                  )}

                  {/* Descrição e Classificação Rigorosa */}
                  <div className="space-y-1.5">
                    <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                      {produto.descricao}
                    </p>

                    <div className="p-2 rounded-sm bg-muted/40 border border-border/40 text-[10px] space-y-1">
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

                  {/* Metadados: Praça e Fontes Disponíveis */}
                  <div className="space-y-1.5 text-[11px] pt-1 border-t border-border/40">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-muted-foreground flex-shrink-0" /> Praça Referência:
                      </span>
                      <span
                        className="font-medium text-foreground text-right truncate max-w-[170px]"
                        title={precoReal ? precoReal.pracaReferencia : produto.pracaReferencia}
                      >
                        {precoReal ? precoReal.pracaReferencia : produto.pracaReferencia}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Building2 className="w-3 h-3 text-muted-foreground flex-shrink-0" /> Fonte Oficial:
                      </span>
                      <span className="font-medium text-foreground text-right">
                        {precoReal ? precoReal.siglaFonte : produto.fontePrincipalNome}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Scale className="w-3 h-3 text-muted-foreground flex-shrink-0" /> Fontes Auditadas:
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {produto.fontesReferencia.length} fontes cadastradas
                      </span>
                    </div>
                  </div>

                  {/* Ações: Segregação Clara entre Portal Institucional e Download Bruto */}
                  <div className="pt-2 border-t border-border/40 space-y-1.5">
                    {/* Botão Principal: Abre a página web informativa sem disparar download indesejado */}
                    <a
                      href={urlInstitucional}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        buttonVariants({ variant: "outline", size: "sm" }),
                        "w-full text-xs h-8 rounded-sm justify-between hover:bg-emerald-600/10 hover:text-emerald-700 dark:hover:text-emerald-400 hover:border-emerald-600/30"
                      )}
                      aria-label={`Consultar no ${precoReal?.siglaFonte || produto.fontePrincipalNome}: ${produto.nome}`}
                    >
                      <span className="flex items-center gap-1.5 truncate">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                        <span className="truncate">
                          Consultar no {precoReal?.siglaFonte || produto.fontePrincipalNome}
                        </span>
                      </span>
                      <ExternalLink className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                    </a>

                    {/* Botão Secundário de Download Explícito do Arquivo Bruto */}
                    {urlDownload && (
                      <a
                        href={urlDownload}
                        target="_blank"
                        rel="noopener noreferrer"
                        download
                        className="inline-flex items-center justify-center gap-1.5 text-[10px] text-muted-foreground hover:text-emerald-700 dark:hover:text-emerald-400 font-medium py-1 px-2 rounded-sm border border-border/50 hover:border-emerald-600/30 hover:bg-emerald-500/5 transition-colors w-full"
                        title="Baixar planilha oficial semanal auditada (.xls)"
                        aria-label={`Baixar planilha oficial semanal com cotação de ${produto.nome}`}
                      >
                        <FileSpreadsheet className="w-3 h-3 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                        <span>Baixar planilha oficial (.xls)</span>
                        <Download className="w-2.5 h-2.5 opacity-70" />
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
