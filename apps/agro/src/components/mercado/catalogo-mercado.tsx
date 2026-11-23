"use client";

import * as React from "react";
import {
  AlertTriangle,
  BarChart3,
  Beef,
  BookOpen,
  Building2,
  ChevronDown,
  Clock,
  Coffee,
  Download,
  ExternalLink,
  Factory,
  FileSpreadsheet,
  Layers,
  Leaf,
  MapPin,
  RefreshCw,
  Scale,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sprout,
  Star,
  TrendingDown,
  TrendingUp,
  Wheat,
  WifiOff,
  X,
} from "lucide-react";
import { HorizontalScrollRail } from "@/components/layout/horizontal-scroll-rail";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input, inputBaseClassName } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { agroApiUrl } from "@/lib/api-url";
import { useLocalidadeClima } from "@/lib/clima/localidade-store";
import {
  CATEGORIAS_ATIVAS_EXIBICAO,
  CATEGORIAS_MERCADO,
  filtrarProdutos,
  obterContagemPorCategoria,
  type CategoriaMercado,
  type ProdutoCatalogo,
} from "@/lib/mercado/catalogo";
import {
  ordenarProdutosComFavoritos,
  useFavoritosMercado,
} from "@/lib/mercado/favoritos-store";
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
import { formatDateBr, type PtaxPublicaV1 } from "@/lib/mercado/ptax";
import {
  UFS_MERCADO_BRASIL,
  filtrarProdutosPorFonte,
  isUfValida,
  resolverExibicaoCardMercado,
  type CotacaoRegiaoApiItem,
  type DestaqueCotacaoCard,
  type ExibicaoCardMercado,
} from "@/lib/mercado/resolucao-regional";
import { cn } from "@/lib/utils";

interface CatalogoMercadoProps {
  initialProdutos: ProdutoCatalogo[];
  mostrarPrecosDeral?: boolean;
}

type EstadoPrecos =
  | "CARREGANDO"
  | "ATUAL"
  | "DEFASADO"
  | "CACHE_ANTIGO"
  | "ERRO"
  | "INDISPONIVEL"
  | "FORA_ESCOPO";

function IconeCommodity({
  categoria,
  id,
  className,
}: {
  categoria: CategoriaMercado;
  id: string;
  className?: string;
}) {
  if (id === "cafe-arabica") return <Coffee className={className} />;
  if (categoria === "PECUARIA") return <Beef className={className} />;
  if (categoria === "GRAOS_CEREAIS" || categoria === "GRAOS_CEREAIS_OLEAGINOSAS") {
    return <Wheat className={className} />;
  }
  if (categoria === "CANA_DERIVADOS") return <Factory className={className} />;
  if (categoria === "OUTROS") return <Leaf className={className} />;
  if (categoria === "FIBRAS" || categoria === "FIBRAS_OUTROS") return <Layers className={className} />;
  return <Sprout className={className} />;
}

interface BlocoCotacaoDestaqueProps {
  destaque: DestaqueCotacaoCard;
  exibicao: ExibicaoCardMercado;
  precoDeral?: PrecoPublicoItem;
  estadoPrecos: EstadoPrecos;
  pracaAtiva: string;
  currency: string;
  quote: PtaxPublicaV1 | null;
  loadingMoeda: boolean;
}

function BlocoCotacaoDestaque({
  destaque,
  exibicao,
  precoDeral,
  estadoPrecos,
  pracaAtiva,
  currency,
  quote,
  loadingMoeda,
}: BlocoCotacaoDestaqueProps) {
  const cotacaoValida =
    quote &&
    quote.moeda === currency &&
    typeof quote.cotacaoVenda === "number" &&
    quote.cotacaoVenda > 0
      ? quote
      : null;

  const valorConvertido = cotacaoValida
    ? converterBrlParaMoeda(destaque.valor, cotacaoValida.cotacaoVenda!)
    : null;
  const precoConvertidoFormatado =
    valorConvertido !== null ? formatarPrecoMoeda(valorConvertido, currency) : null;

  const sufixoEstado =
    destaque.familia === "DERAL"
      ? estadoPrecos === "CACHE_ANTIGO"
        ? " · dado salvo"
        : estadoPrecos === "DEFASADO"
          ? " · defasado"
          : ""
      : "";

  const ehHistorico = destaque.ehHistoricoAnual;

  return (
    <div
      className={cn(
        "p-3 md:p-2.5 rounded-lg md:rounded-sm border flex flex-col gap-1.5 min-h-[92px] justify-between",
        ehHistorico
          ? "bg-amber-500/5 dark:bg-amber-950/20 border-amber-500/30"
          : "bg-emerald-500/5 dark:bg-emerald-950/20 border-emerald-500/20"
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <span
          className={cn(
            "text-[10px] font-medium flex items-center gap-1 min-w-0",
            ehHistorico
              ? "text-amber-900 dark:text-amber-300"
              : "text-emerald-800 dark:text-emerald-300"
          )}
        >
          {ehHistorico ? (
            <BarChart3 className="size-3 text-amber-700 dark:text-amber-300 shrink-0" />
          ) : (
            <Clock className="size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
          )}
          <span className="truncate">
            {destaque.indicacaoTemporal}
            {sufixoEstado}
          </span>
        </span>
        <Badge variant={ehHistorico ? "warning" : "recommendation"} className="shrink-0 text-[10px]">
          {destaque.sigla}
        </Badge>
      </div>

      {/* Preço Oficial em Reais + Variação Semanal */}
      <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1 pt-0.5">
        <div className="min-w-0">
          <span className="text-xl font-bold tracking-tight text-foreground tabular-nums">
            {formatarPrecoPublico(destaque.valor, destaque.moeda)}
          </span>
          <span className="text-[11px] text-muted-foreground ml-1.5">
            / {destaque.unidade}
          </span>
        </div>

        <div className="text-right flex flex-col items-end gap-0.5 shrink-0">
          {typeof destaque.variacaoSemanalPct === "number" && (
            <Badge
              data-testid="variacao-semanal-badge"
              variant={
                destaque.variacaoSemanalPct > 0
                  ? "success"
                  : destaque.variacaoSemanalPct < 0
                    ? "warning"
                    : "info"
              }
              title={
                destaque.valorSemanaAnterior
                  ? `Média da semana anterior (MSA): ${formatarPrecoPublico(destaque.valorSemanaAnterior, destaque.moeda)}`
                  : "Variação semanal oficial DERAL"
              }
              className="text-[10px]"
            >
              {destaque.variacaoSemanalPct > 0 ? (
                <TrendingUp className="size-2.5" />
              ) : destaque.variacaoSemanalPct < 0 ? (
                <TrendingDown className="size-2.5" />
              ) : null}
              {destaque.variacaoSemanalPct > 0 ? "+" : ""}
              {destaque.variacaoSemanalPct.toLocaleString("pt-BR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
              % sem.
            </Badge>
          )}
          <span className="text-[10px] text-muted-foreground block">
            {destaque.dataLabel}
          </span>
        </div>
      </div>

      {ehHistorico && (
        <p className="text-[10px] font-medium text-amber-900 dark:text-amber-200 pt-1 border-t border-amber-500/20">
          Referência estatística anual (safra consolidada) — não é cotação do dia.
        </p>
      )}

      {/* Faixa Regional PR ou Destaque do Núcleo (somente quando DERAL PR está ativo) */}
      {exibicao.mostrarFaixaPr && precoDeral && (
        <div className="flex flex-wrap items-center justify-between gap-1 text-[10px] text-muted-foreground pt-1 border-t border-emerald-500/10">
          {exibicao.pracaRegionalSelecionada ? (
            <span className="font-medium text-emerald-800 dark:text-emerald-300">
              Núcleo {exibicao.pracaRegionalSelecionada.praca} · Média PR:{" "}
              {formatarPrecoPublico(precoDeral.valor, precoDeral.moeda)}
            </span>
          ) : exibicao.avisoPracaIndisponivel ? (
            <span className="italic">
              Sem cotação em {pracaAtiva} · exibindo Média PR
            </span>
          ) : (
            <span>
              Faixa PR ({precoDeral.pracasRegionais?.length ?? 0} praças):{" "}
              <strong className="text-foreground/90">
                {formatarPrecoPublico(
                  precoDeral.valorMinimoRegional ?? precoDeral.valor,
                  precoDeral.moeda
                )}
              </strong>{" "}
              ({precoDeral.pracaMinimoRegional}) a{" "}
              <strong className="text-foreground/90">
                {formatarPrecoPublico(
                  precoDeral.valorMaximoRegional ?? precoDeral.valor,
                  precoDeral.moeda
                )}
              </strong>{" "}
              ({precoDeral.pracaMaximoRegional})
            </span>
          )}
        </div>
      )}

      {/* Equivalente Cambial Reativo */}
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-1.5 pt-1 border-t text-xs",
          ehHistorico ? "border-amber-500/20" : "border-emerald-500/10"
        )}
        data-testid="conversao-cambial-card"
      >
        {precoConvertidoFormatado ? (
          <div className="flex items-baseline gap-1 text-emerald-800 dark:text-emerald-300 font-medium min-w-0 truncate">
            <span className="text-[10px] text-muted-foreground">Equiv.:</span>
            <span className="font-mono font-bold text-foreground">
              ≈ {precoConvertidoFormatado}
            </span>
            <span className="text-[10px] text-muted-foreground truncate">
              / {destaque.unidade}
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

        {cotacaoValida && (
          <span
            className="text-[9.5px] text-muted-foreground whitespace-nowrap"
            title={`PTAX Venda: ${cotacaoValida.cotacaoVenda!.toFixed(4)} BCB`}
          >
            PTAX {formatDateBr(cotacaoValida.dataCotacao ?? "")}
          </span>
        )}
      </div>
    </div>
  );
}

interface CardCommodityProps {
  produto: ProdutoCatalogo;
  exibicao: ExibicaoCardMercado;
  precoDeral?: PrecoPublicoItem;
  estadoPrecos: EstadoPrecos;
  pracaAtiva: string;
  currency: string;
  quote: PtaxPublicaV1 | null;
  loadingMoeda: boolean;
  ehFavorito: boolean;
  onToggleFavorito: (_id: string) => void;
}

function CardCommodity({
  produto,
  exibicao,
  precoDeral,
  estadoPrecos,
  pracaAtiva,
  currency,
  quote,
  loadingMoeda,
  ehFavorito,
  onToggleFavorito,
}: CardCommodityProps) {
  return (
    <Card
      data-commodity-id={produto.id}
      className={cn(
        "justify-between hover:border-primary/40 transition-colors",
        ehFavorito && "border-amber-500/40 ring-1 ring-amber-500/20"
      )}
    >
      <CardHeader className="flex flex-col gap-2 border-b border-border/50">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2.5 min-w-0 flex-1">
            <div className="p-2 rounded-lg md:rounded-sm bg-muted text-foreground shrink-0">
              <IconeCommodity
                categoria={produto.categoriaMercado}
                id={produto.id}
                className="size-4 text-emerald-700 dark:text-emerald-400"
              />
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="text-sm font-semibold text-foreground leading-snug break-words">
                {produto.nome}
              </CardTitle>
              <CardDescription className="text-xs md:text-[11px] mt-0.5">
                {precoDeral ? precoDeral.unidade : produto.unidade}
              </CardDescription>
            </div>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => onToggleFavorito(produto.id)}
            data-testid={`btn-favorito-${produto.id}`}
            aria-pressed={ehFavorito}
            aria-label={ehFavorito ? `Remover ${produto.nome} dos favoritos` : `Fixar ${produto.nome} nos favoritos`}
            title={ehFavorito ? "Desafixar dos favoritos" : "Fixar no topo como favorito"}
            className="shrink-0 -mt-0.5 -mr-1"
          >
            <Star
              className={cn(
                "size-3.5 transition-colors",
                ehFavorito ? "fill-amber-400 text-amber-500" : "text-muted-foreground"
              )}
            />
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <Badge
            variant={exibicao.badgeCabecalho.variant}
            className="whitespace-normal h-auto py-0.5 leading-tight text-left text-[10px]"
          >
            {exibicao.badgeCabecalho.texto}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-2.5 flex-1 justify-between">
        {/* Bloco Principal de Preço ou Indisponibilidade */}
        {exibicao.destaque ? (
          <BlocoCotacaoDestaque
            destaque={exibicao.destaque}
            exibicao={exibicao}
            precoDeral={precoDeral}
            estadoPrecos={estadoPrecos}
            pracaAtiva={pracaAtiva}
            currency={currency}
            quote={quote}
            loadingMoeda={loadingMoeda}
          />
        ) : (
          <div className="p-3 md:p-2.5 rounded-lg md:rounded-sm bg-muted/40 border border-border/60 flex flex-col gap-1.5">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <span className="text-xs md:text-[10px] text-muted-foreground block">
                  Valor de Comercialização ({produto.moeda})
                </span>
                <span className="text-xs font-semibold text-foreground leading-snug block mt-0.5">
                  {estadoPrecos === "CARREGANDO" && !exibicao.modoConsultaDireta
                    ? "Carregando preço oficial…"
                    : exibicao.motivoIndisponivel}
                </span>
              </div>
              {exibicao.badgeCabecalho.texto === "Preço indisponível" && (
                <Badge variant="recommendation" className="shrink-0 text-[10px]">
                  {produto.fontePrincipalNome}
                </Badge>
              )}
            </div>
            <p className="text-xs md:text-[10px] text-muted-foreground leading-snug">
              {exibicao.subtituloIndisponivel}
            </p>
          </div>
        )}

        {/* Praça / Região e Outras Fontes Comparativas */}
        <div className="flex flex-col gap-1.5 text-xs md:text-[11px]">
          <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5 text-muted-foreground">
            <span className="flex items-center gap-1 shrink-0">
              <MapPin className="size-3 text-muted-foreground shrink-0" />
              Praça / Região:
            </span>
            <span className="font-medium text-foreground text-right">
              {exibicao.regiaoLabel}
            </span>
          </div>

          {exibicao.outrasFontes.length > 0 && (
            <div className="rounded-lg md:rounded-sm border border-border/60 bg-muted/25 p-2.5 md:p-2 flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs md:text-[10px] font-semibold text-foreground">
                <span className="flex items-center gap-1">
                  <Scale className="size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  {exibicao.destaque
                    ? `Outras fontes (${exibicao.outrasFontes.length})`
                    : `Fontes de referência (${exibicao.outrasFontes.length})`}
                </span>
              </div>

              <div className="divide-y divide-border/40 text-xs md:text-[10px]">
                {exibicao.outrasFontes.map((fonte) => (
                  <div key={fonte.chave} className="py-1 flex items-center justify-between gap-2">
                    <span className="text-muted-foreground min-w-0 flex-1 leading-snug">
                      <strong className="text-foreground">{fonte.sigla}</strong> · {fonte.detalhe}
                    </span>
                    {typeof fonte.valor === "number" ? (
                      <span className="font-semibold text-emerald-800 dark:text-emerald-300 tabular-nums shrink-0">
                        {formatarPrecoPublico(fonte.valor, fonte.moeda)}
                      </span>
                    ) : (
                      <a
                        href={fonte.urlConsulta}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-0.5 text-emerald-700 dark:text-emerald-300 hover:underline font-medium shrink-0"
                      >
                        Consultar <ExternalLink className="size-2.5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Detalhes Agronômicos e Auditoria Criptográfica Recolhíveis */}
        <Collapsible className="group rounded-lg md:rounded-sm border border-border/50 bg-muted/20">
          <CollapsibleTrigger className="flex w-full cursor-pointer list-none items-center justify-between gap-2 px-3 md:px-2.5 py-2 md:py-1.5 text-xs md:text-[11px] font-medium text-muted-foreground hover:text-foreground [&::-webkit-details-marker]:hidden">
            <span>Detalhes e auditoria</span>
            <ChevronDown className="size-3.5 shrink-0 transition-transform group-open:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent className="border-t border-border/40 px-2.5 py-2 flex flex-col gap-1.5 text-[10px] text-muted-foreground">
            <p className="leading-relaxed">{produto.descricao}</p>
            <div className="flex flex-col gap-0.5 pt-1 border-t border-border/30">
              <span>Classificação Agronômica:</span>
              <span className="font-medium text-foreground leading-snug">
                {produto.classificacaoAgronomica}
              </span>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-1 pt-1 border-t border-border/30">
              <span>Natureza do Preço:</span>
              <span className="font-medium text-foreground">{exibicao.naturezaPreco}</span>
            </div>
            {exibicao.destaque && (
              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/30">
                <span title={`Origem: ${exibicao.destaque.origem}`}>
                  Origem: <strong className="font-mono text-foreground">{exibicao.destaque.origem}</strong>
                </span>
                {exibicao.destaque.documentoHashSha256 && (
                  <span className="font-mono text-[9px]" title={`SHA-256: ${exibicao.destaque.documentoHashSha256}`}>
                    SHA: {exibicao.destaque.documentoHashSha256.slice(0, 8)}…
                  </span>
                )}
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>

        {/* Rodapé Compacto de Ações */}
        <div className="pt-2 border-t border-border/40 flex items-center gap-1.5">
          <a
            href={exibicao.ctaPrincipal.href}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "flex-1 min-w-0 justify-between")}
            aria-label={exibicao.ctaPrincipal.ariaLabel}
          >
            <span className="flex items-center gap-1.5 min-w-0 truncate">
              <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="truncate">{exibicao.ctaPrincipal.rotulo}</span>
            </span>
            <ExternalLink className="size-3 text-muted-foreground shrink-0" />
          </a>

          {exibicao.urlDownloadXls && (
            <a
              href={exibicao.urlDownloadXls}
              target="_blank"
              rel="noopener noreferrer"
              download
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "shrink-0 px-2 text-xs text-muted-foreground hover:text-primary"
              )}
              title="Baixar planilha oficial semanal auditada (.xls)"
              aria-label={`Baixar planilha oficial semanal com cotação de ${produto.nome}`}
            >
              <FileSpreadsheet className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>.xls</span>
              <Download className="size-3 opacity-70" />
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Catálogo público com favoritos persistentes, seleção por Região (UF), Núcleo DERAL-PR e Fonte.
 */
export function CatalogoMercado({ initialProdutos, mostrarPrecosDeral = false }: CatalogoMercadoProps) {
  const { localidade, isLoaded: localidadeLoaded } = useLocalidadeClima();
  const { favoritos, isLoaded: favoritosLoaded, toggleFavorito } = useFavoritosMercado();
  const [busca, setBusca] = React.useState("");
  const [categoriaAtiva, setCategoriaAtiva] = React.useState<CategoriaMercado | "TODAS">("TODAS");
  const [apenasFavoritos, setApenasFavoritos] = React.useState(false);
  const [ufSelecionadaManual, setUfSelecionadaManual] = React.useState<string | null>(null);
  const [pracaAtiva, setPracaAtiva] = React.useState<string>("MEDIA_ESTADUAL");
  const [fonteAtiva, setFonteAtiva] = React.useState<string>("TODAS");
  const [filtrosSheetAberto, setFiltrosSheetAberto] = React.useState(false);
  const [regiaoMultiMap, setRegiaoMultiMap] = React.useState<Record<string, CotacaoRegiaoApiItem>>({});
  const [precosMap, setPrecosMap] = React.useState<Record<string, PrecoPublicoItem>>({});
  const [estadoPrecos, setEstadoPrecos] = React.useState<EstadoPrecos>(
    mostrarPrecosDeral ? "CARREGANDO" : "FORA_ESCOPO"
  );
  const [tentativa, setTentativa] = React.useState(0);
  const { currency, quote, loading: loadingMoeda } = useMoedaMercado();

  const ufLocalidadeValida =
    localidadeLoaded && localidade?.uf && isUfValida(localidade.uf)
      ? localidade.uf.trim().toUpperCase()
      : null;
  const ufAtiva = ufSelecionadaManual ?? ufLocalidadeValida ?? "PR";
  const pracasDisponiveis = React.useMemo(() => {
    const conjunto = new Set<string>();
    if (ufAtiva === "PR") {
      for (const item of Object.values(precosMap)) {
        for (const p of item.pracasRegionais ?? []) {
          if (p.praca) conjunto.add(p.praca);
        }
      }
    } else {
      for (const item of Object.values(regiaoMultiMap)) {
        for (const fonte of item.fontes ?? []) {
          if (
            fonte.uf === ufAtiva &&
            (fonte.tipo_fonte === "OFICIAL_ESTADUAL" || fonte.tipo_fonte === "PARCEIRO_AUTORIZADO") &&
            fonte.praca &&
            !fonte.praca.includes("Média Estadual")
          ) {
            conjunto.add(fonte.praca);
          }
        }
      }
    }
    return Array.from(conjunto).sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [ufAtiva, precosMap, regiaoMultiMap]);
  const pracaAtivaEfetiva = pracasDisponiveis.length > 0 ? pracaAtiva : "MEDIA_ESTADUAL";

  React.useEffect(() => {
    if (!mostrarPrecosDeral || typeof window === "undefined") {
      return;
    }
    let cancelado = false;
    const controller = new AbortController();

    const cached = readSavedPrecos(window.localStorage);
    const temCache = Boolean(cached && cached.itens.length > 0);

    async function carregar() {
      try {
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
        if (cancelado) return;
        if (temCache && cached) {
          const mapaCache: Record<string, PrecoPublicoItem> = {};
          for (const item of cached.itens) {
            mapaCache[item.id] = item;
          }
          setPrecosMap(mapaCache);
          setEstadoPrecos("CACHE_ANTIGO");
        } else {
          setEstadoPrecos("ERRO");
        }
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
    if (fonteAtiva === "CEPEA" || fonteAtiva === "CONAB" || fonteAtiva === "B3") {
      return;
    }
    const controller = new AbortController();
    const params = new URLSearchParams({ uf: ufAtiva, incluir_ibge: "true" });
    if (pracaAtivaEfetiva !== "MEDIA_ESTADUAL") {
      params.set("praca", pracaAtivaEfetiva);
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
  }, [ufAtiva, pracaAtivaEfetiva, fonteAtiva, mostrarPrecosDeral]);

  const contagem = React.useMemo(() => {
    return obterContagemPorCategoria(initialProdutos);
  }, [initialProdutos]);

  const produtosFiltrados = React.useMemo(() => {
    const porTextoECategoria = filtrarProdutos(initialProdutos, {
      busca,
      categoria: categoriaAtiva,
    });
    const porFonte = filtrarProdutosPorFonte(porTextoECategoria, fonteAtiva);
    const filtradosFav = apenasFavoritos
      ? porFonte.filter((p) => favoritos.includes(p.id))
      : porFonte;
    return ordenarProdutosComFavoritos(filtradosFav, favoritos);
  }, [initialProdutos, busca, categoriaAtiva, fonteAtiva, apenasFavoritos, favoritos]);

  const fontesUfDinamicas = React.useMemo(() => {
    const mapa = new Map<string, string>();
    for (const item of Object.values(regiaoMultiMap)) {
      for (const fonte of item.fontes ?? []) {
        if (
          fonte.uf === ufAtiva &&
          (fonte.tipo_fonte === "OFICIAL_ESTADUAL" || fonte.tipo_fonte === "PARCEIRO_AUTORIZADO")
        ) {
          const upper = fonte.sigla_fonte.toUpperCase();
          if (upper.includes("IEA")) mapa.set("IEA", `${fonte.sigla_fonte} (Diário SP)`);
          else if (upper.includes("EMATER")) mapa.set("EMATER", `${fonte.sigla_fonte} (Semanal RS)`);
          else if (fonte.tipo_fonte === "PARCEIRO_AUTORIZADO") {
            mapa.set("PARCEIRO", "Parceiros Autorizados da UF");
          }
        }
      }
    }
    return Array.from(mapa.entries());
  }, [regiaoMultiMap, ufAtiva]);

  const totalGeral = initialProdutos.length;
  const dataReferenciaPrecos = Object.values(precosMap)[0]?.dataReferencia;
  const filtrosAvancadosAtivos =
    (pracaAtivaEfetiva !== "MEDIA_ESTADUAL" ? 1 : 0) +
    (fonteAtiva !== "TODAS" ? 1 : 0) +
    (apenasFavoritos ? 1 : 0);

  return (
    <div className="flex flex-col gap-3.5 md:gap-4">
      {/* Painel de Filtros Regionais, Favoritos e Busca */}
      <div className="rounded-xl md:rounded-sm border border-border/60 bg-muted/20 p-3 flex flex-col gap-2.5 md:gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="relative flex-1 min-w-[210px] sm:max-w-md">
            <Search className="size-4 md:size-3.5 absolute left-3 md:left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            <Input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por produto, praça ou fonte..."
              className="pl-9 md:pl-8 pr-9 md:pr-7 md:text-xs"
              aria-label="Buscar produtos agropecuários no catálogo"
            />
            {busca && (
              <button
                type="button"
                onClick={() => setBusca("")}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 size-8 md:size-6 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground cursor-pointer"
                aria-label="Limpar campo de busca"
              >
                <X className="size-4 md:size-3.5" />
              </button>
            )}
          </div>

          {/* Botão Mobile de Filtros Avançados (Bottom Sheet) */}
          <Button
            type="button"
            variant={filtrosAvancadosAtivos > 0 ? "default" : "outline"}
            onClick={() => setFiltrosSheetAberto(true)}
            data-testid="btn-filtros-mercado-mobile"
            aria-label="Abrir filtros avançados de mercado"
            className="sm:hidden shrink-0"
          >
            <SlidersHorizontal className="size-4" />
            <span>Filtros</span>
            {filtrosAvancadosAtivos > 0 && (
              <span className="inline-flex min-w-5 h-5 items-center justify-center rounded-full bg-primary-foreground/20 px-1 text-xs font-bold">
                {filtrosAvancadosAtivos}
              </span>
            )}
          </Button>

          {/* Controles Desktop / Tablet inline */}
          <div className="hidden sm:flex flex-wrap items-center justify-end gap-2 shrink-0">
            <Button
              type="button"
              variant={apenasFavoritos ? "default" : "outline"}
              size="sm"
              data-testid="filtro-apenas-favoritos"
              aria-pressed={apenasFavoritos}
              onClick={() => setApenasFavoritos((prev) => !prev)}
              className="shrink-0"
            >
              <Star
                className={cn(
                  "size-3.5",
                  apenasFavoritos
                    ? "fill-current"
                    : favoritosLoaded && favoritos.length > 0
                      ? "fill-amber-400 text-amber-500"
                      : ""
                )}
              />
              <span>Favoritos ({favoritosLoaded ? favoritos.length : 0})</span>
            </Button>

            <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
              <BookOpen className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>
                Exibindo <strong>{produtosFiltrados.length}</strong> de {totalGeral}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 @[520px]/main:grid-cols-2 @[820px]/main:grid-cols-3 gap-2.5">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <Label
                htmlFor="select-uf-mercado"
                className="text-xs md:text-[11px] font-medium text-muted-foreground flex items-center gap-1"
              >
                <MapPin className="size-3.5 md:size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Região (Estado / UF)</span>
              </Label>
              <span className="sm:hidden text-xs text-muted-foreground">
                <strong>{produtosFiltrados.length}</strong> de {totalGeral}
              </span>
            </div>
            <select
              id="select-uf-mercado"
              value={ufAtiva}
              onChange={(e) => {
                const nextUf = e.target.value;
                setUfSelecionadaManual(nextUf);
                setPracaAtiva("MEDIA_ESTADUAL");
              }}
              aria-label="Selecionar estado ou região (UF)"
              data-testid="seletor-uf-mercado"
              className={cn(inputBaseClassName, "w-full min-w-0 md:text-xs px-3 md:px-2.5")}
            >
              {UFS_MERCADO_BRASIL.map((uf) => (
                <option key={uf.sigla} value={uf.sigla}>
                  {uf.nome} ({uf.sigla})
                  {uf.sigla === "PR"
                    ? " — 20 Núcleos DERAL + IBGE"
                    : uf.sigla === "SP"
                      ? " — EDRs IEA-SP + IBGE"
                      : ""}
                </option>
              ))}
            </select>
          </div>

          {pracasDisponiveis.length > 0 && (
            <div className="hidden sm:flex flex-col gap-1 min-w-0">
              <Label
                htmlFor="select-praca-deral"
                className="text-[11px] font-medium text-muted-foreground"
              >
                {ufAtiva === "PR" ? "Núcleo Regional DERAL-PR" : `Praça / Região (${ufAtiva})`}
              </Label>
              <select
                id="select-praca-deral"
                value={pracaAtivaEfetiva}
                onChange={(e) => setPracaAtiva(e.target.value)}
                aria-label={`Selecionar praça ou núcleo regional (${ufAtiva})`}
                data-testid="seletor-praca-deral"
                className={cn(inputBaseClassName, "w-full min-w-0 md:text-xs px-2.5")}
              >
                <option value="MEDIA_ESTADUAL">
                  {ufAtiva} — Média Estadual ({pracasDisponiveis.length} praças)
                </option>
                {pracasDisponiveis.map((praca) => (
                  <option key={praca} value={praca}>
                    {ufAtiva === "PR" ? `Núcleo Regional: ${praca}` : praca}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div
            className={cn(
              "hidden sm:flex flex-col gap-1 min-w-0",
              pracasDisponiveis.length > 0 ? "" : "@[520px]/main:col-span-1 @[820px]/main:col-span-2"
            )}
          >
            <Label
              htmlFor="select-fonte-mercado"
              className="text-[11px] font-medium text-muted-foreground flex items-center gap-1"
            >
              <Building2 className="size-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>Fonte de Dados</span>
            </Label>
            <select
              id="select-fonte-mercado"
              value={fonteAtiva}
              onChange={(e) => setFonteAtiva(e.target.value)}
              aria-label="Filtrar por fonte de dados de mercado"
              data-testid="seletor-fonte-mercado"
              className={cn(inputBaseClassName, "w-full min-w-0 md:text-xs px-2.5")}
            >
              <option value="TODAS">Todas (Comparativo Multi-Fonte)</option>
              <option value="DERAL">DERAL/SEAB-PR (Físico Semanal PR)</option>
              <option value="IEA">IEA/SAA-SP (Diário SP / EDRs)</option>
              {fontesUfDinamicas
                .filter(([val]) => val !== "IEA")
                .map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              <option value="IBGE">IBGE/SIDRA (Média Histórica Anual PAM)</option>
              <option value="CEPEA">CEPEA/ESALQ (Indicador Spot)</option>
              <option value="CONAB">CONAB/MAPA (Referência Federal)</option>
              <option value="B3">B3 / Futuros</option>
            </select>
          </div>
        </div>
      </div>

      {/* Bottom Sheet de Filtros Avançados no Mobile */}
      <Sheet open={filtrosSheetAberto} onOpenChange={setFiltrosSheetAberto}>
        <SheetContent side="bottom" data-testid="sheet-filtros-mercado">
          <SheetHeader className="px-4 pt-1 pb-2 border-b border-border/60">
            <SheetTitle className="text-base font-bold">Filtros de Mercado</SheetTitle>
            <SheetDescription className="text-xs">
              Refine por praça regional, fonte oficial e favoritos salvos.
            </SheetDescription>
          </SheetHeader>

          <div className="flex flex-col gap-4 px-4 py-1">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">Somente favoritos</p>
                <p className="text-xs text-muted-foreground">
                  {favoritosLoaded ? favoritos.length : 0} produto(s) fixado(s)
                </p>
              </div>
              <Button
                type="button"
                variant={apenasFavoritos ? "default" : "outline"}
                size="sm"
                aria-pressed={apenasFavoritos}
                onClick={() => setApenasFavoritos((prev) => !prev)}
                className="shrink-0"
              >
                <Star
                  className={cn(
                    "size-4",
                    apenasFavoritos ? "fill-current" : "text-amber-500"
                  )}
                />
                <span>{apenasFavoritos ? "Ativo" : "Ativar"}</span>
              </Button>
            </div>

            {pracasDisponiveis.length > 0 && (
              <div className="flex flex-col gap-1.5 min-w-0">
                <Label htmlFor="mobile-select-praca-deral" className="text-xs font-medium text-muted-foreground">
                  {ufAtiva === "PR" ? "Núcleo Regional DERAL-PR" : `Praça / Região (${ufAtiva})`}
                </Label>
                <select
                  id="mobile-select-praca-deral"
                  value={pracaAtivaEfetiva}
                  onChange={(e) => setPracaAtiva(e.target.value)}
                  className={cn(inputBaseClassName, "w-full min-w-0")}
                >
                  <option value="MEDIA_ESTADUAL">
                    {ufAtiva} — Média Estadual ({pracasDisponiveis.length} praças)
                  </option>
                  {pracasDisponiveis.map((praca) => (
                    <option key={praca} value={praca}>
                      {ufAtiva === "PR" ? `Núcleo Regional: ${praca}` : praca}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex flex-col gap-1.5 min-w-0">
              <Label htmlFor="mobile-select-fonte-mercado" className="text-xs font-medium text-muted-foreground">
                Fonte de Dados
              </Label>
              <select
                id="mobile-select-fonte-mercado"
                value={fonteAtiva}
                onChange={(e) => setFonteAtiva(e.target.value)}
                className={cn(inputBaseClassName, "w-full min-w-0")}
              >
                <option value="TODAS">Todas (Comparativo Multi-Fonte)</option>
                <option value="DERAL">DERAL/SEAB-PR (Físico Semanal PR)</option>
                <option value="IEA">IEA/SAA-SP (Diário SP / EDRs)</option>
                {fontesUfDinamicas
                  .filter(([val]) => val !== "IEA")
                  .map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
                  ))}
                <option value="IBGE">IBGE/SIDRA (Média Histórica Anual PAM)</option>
                <option value="CEPEA">CEPEA/ESALQ (Indicador Spot)</option>
                <option value="CONAB">CONAB/MAPA (Referência Federal)</option>
                <option value="B3">B3 / Futuros</option>
              </select>
            </div>
          </div>

          <SheetFooter className="flex-row gap-2 border-t border-border/60 pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setPracaAtiva("MEDIA_ESTADUAL");
                setFonteAtiva("TODAS");
                setApenasFavoritos(false);
              }}
              className="flex-1"
            >
              Limpar
            </Button>
            <Button
              type="button"
              variant="default"
              onClick={() => setFiltrosSheetAberto(false)}
              className="flex-1 font-semibold"
            >
              Ver resultados ({produtosFiltrados.length})
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Navegação por Categorias com Indicação Visual de Rolagem Horizontal */}
      <HorizontalScrollRail
        role="tablist"
        ariaLabel="Filtro por categoria de mercado"
        testId="catalogo-categorias-rail"
        contentClassName="pb-0.5"
      >
        <Button
          variant={categoriaAtiva === "TODAS" ? "default" : "outline"}
          size="sm"
          onClick={() => setCategoriaAtiva("TODAS")}
          className="shrink-0 snap-start"
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
              className="shrink-0 snap-start"
              role="tab"
              aria-selected={selecionada}
            >
              {meta.label} ({qtd})
            </Button>
          );
        })}
      </HorizontalScrollRail>

      {estadoPrecos !== "ATUAL" && mostrarPrecosDeral && (
        <div
          className="min-h-11 p-3 rounded-sm border border-amber-500/30 bg-amber-500/10 dark:border-amber-400/30 dark:bg-amber-500/15 flex flex-wrap items-center justify-between gap-2.5 text-xs"
          role="status"
          aria-live="polite"
          data-testid="estado-precos"
        >
          <span className="flex items-center gap-2 text-amber-950 dark:text-amber-200 min-w-0 flex-1">
            {estadoPrecos === "CARREGANDO" ? (
              <RefreshCw className="size-4 animate-spin text-amber-700 dark:text-amber-300 shrink-0" />
            ) : estadoPrecos === "DEFASADO" || estadoPrecos === "CACHE_ANTIGO" ? (
              <AlertTriangle className="size-4 text-amber-700 dark:text-amber-300 shrink-0" />
            ) : (
              <WifiOff className="size-4 text-amber-700 dark:text-amber-300 shrink-0" />
            )}
            <span>
              {estadoPrecos === "CARREGANDO" && "Carregando preços oficiais…"}
              {estadoPrecos === "DEFASADO" &&
                `Referência semanal DERAL/SEAB-PR aguardando novo boletim oficial${dataReferenciaPrecos ? ` (última referência publicada: ${formatarDataPreco(dataReferenciaPrecos)})` : ""}.`}
              {estadoPrecos === "CACHE_ANTIGO" && "Exibindo dado salvo; a atualização da fonte está indisponível."}
              {estadoPrecos === "ERRO" && "Não foi possível consultar os preços oficiais."}
              {estadoPrecos === "INDISPONIVEL" && "A fonte respondeu sem preços oficiais verificáveis."}
              {estadoPrecos === "FORA_ESCOPO" &&
                "Preços dinâmicos DERAL ficam fora deste MVP; consulte as referências oficiais listadas em cada item."}
            </span>
          </span>
          {(estadoPrecos === "DEFASADO" ||
            estadoPrecos === "ERRO" ||
            estadoPrecos === "INDISPONIVEL" ||
            estadoPrecos === "CACHE_ANTIGO") && (
            <Button variant="outline" size="sm" onClick={() => setTentativa((valor) => valor + 1)} className="shrink-0">
              <RefreshCw className="size-3.5" />
              <span>{estadoPrecos === "DEFASADO" ? "Atualizar" : "Tentar novamente"}</span>
            </Button>
          )}
        </div>
      )}

      {/* Grid Responsivo ou Estado Vazio */}
      {produtosFiltrados.length === 0 ? (
        <Card variant="muted" size="sm" className="text-center py-6">
          <CardContent className="flex flex-col items-center gap-2">
            {apenasFavoritos && favoritos.length === 0 ? (
              <Star className="size-6 text-amber-500" />
            ) : (
              <Layers className="size-6 text-muted-foreground" />
            )}
            <p className="text-xs font-semibold text-foreground">
              {apenasFavoritos && favoritos.length === 0
                ? "Nenhum produto fixado nos favoritos"
                : "Nenhum produto encontrado"}
            </p>
            <p className="text-[11px] text-muted-foreground max-w-sm">
              {apenasFavoritos && favoritos.length === 0
                ? "Toque na estrela de qualquer produto para fixá-lo no topo da sua lista."
                : busca
                  ? `Não encontramos resultados para "${busca}" nos filtros selecionados.`
                  : "Nenhum item corresponde à combinação atual de categoria, fonte e favoritos."}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setBusca("");
                setCategoriaAtiva("TODAS");
                setFonteAtiva("TODAS");
                setApenasFavoritos(false);
              }}
              className="mt-1"
            >
              Limpar filtros
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 @[580px]/main:grid-cols-2 @[880px]/main:grid-cols-3 gap-3.5">
          {produtosFiltrados.map((produto) => {
            const precoDeral = precosMap[produto.id];
            const exibicao = resolverExibicaoCardMercado({
              produto,
              precoDeral,
              regiaoMultiItem: regiaoMultiMap[produto.id] ?? null,
              ufAtiva,
              pracaAtiva: pracaAtivaEfetiva,
              fonteAtiva,
            });
            return (
              <CardCommodity
                key={produto.id}
                produto={produto}
                exibicao={exibicao}
                precoDeral={precoDeral}
                estadoPrecos={estadoPrecos}
                pracaAtiva={pracaAtivaEfetiva}
                currency={currency}
                quote={quote}
                loadingMoeda={loadingMoeda}
                ehFavorito={favoritos.includes(produto.id)}
                onToggleFavorito={toggleFavorito}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
