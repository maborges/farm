import { BarChart3, DollarSign, Info, Percent, Scale, TrendingUp } from "lucide-react";
import { CatalogoMercado } from "@/components/mercado/catalogo-mercado";
import { IbgeProducaoCard } from "@/components/mercado/ibge-producao-card";
import { IbgeValorProducaoCard } from "@/components/mercado/ibge-valor-producao-card";
import { IndicadoresMacroCard } from "@/components/mercado/indicadores-macro-card";
import { PtaxCard } from "@/components/mercado/ptax-card";
import { Badge } from "@/components/ui/badge";
import { PRODUTOS_CATALOGO } from "@/lib/mercado/catalogo";

export default async function MercadoPage() {
  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      {/* Cabeçalho da Seção */}
      <div className="border-b border-border pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-base sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Mercado e Indicadores Agro</span>
          </h1>
          <Badge variant="outline" className="text-[10px]">
            Cotações físicas e estatísticas oficiais
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Câmbio do Banco Central, indicadores macroeconômicos e estatísticas de produção do IBGE.
        </p>

        {/* Barra de Atalhos Rápidos Mobile/Tablet para Navegação entre Blocos */}
        <nav
          aria-label="Atalhos das seções de mercado"
          data-testid="mercado-quick-jump"
          className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pt-2.5 sm:pt-3"
        >
          <a
            href="#secao-catalogo"
            className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-primary/10 text-primary border border-primary/25 text-[11px] font-semibold active:scale-95 transition-transform"
          >
            <Scale className="w-3 h-3" />
            <span>Commodities</span>
          </a>
          <a
            href="#secao-ptax"
            className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-muted/60 hover:bg-muted text-foreground border border-border/70 text-[11px] font-medium active:scale-95 transition-transform"
          >
            <DollarSign className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>Câmbio PTAX</span>
          </a>
          <a
            href="#secao-macro"
            className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-muted/60 hover:bg-muted text-foreground border border-border/70 text-[11px] font-medium active:scale-95 transition-transform"
          >
            <Percent className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>Selic & IPCA</span>
          </a>
          <a
            href="#secao-ibge"
            className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-sm bg-muted/60 hover:bg-muted text-foreground border border-border/70 text-[11px] font-medium active:scale-95 transition-transform"
          >
            <BarChart3 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
            <span>Produção IBGE</span>
          </a>
        </nav>
      </div>

      {/* Câmbio Oficial (PTAX - Banco Central do Brasil) */}
      <div id="secao-ptax" className="w-full scroll-mt-20">
        <PtaxCard />
      </div>

      {/* Indicadores Econômicos e Câmbio Oficial (BCB) */}
      <div id="secao-macro" className="w-full scroll-mt-20">
        <IndicadoresMacroCard />
      </div>

      {/* Inteligência Agropecuária e Estatísticas Oficiais de Produção (IBGE/SIDRA) */}
      <div id="secao-ibge-valor" className="w-full scroll-mt-20">
        <IbgeValorProducaoCard />
      </div>

      {/* Referências anuais para culturas sem cotação DERAL homologada */}
      <div id="secao-ibge" className="w-full scroll-mt-20">
        <IbgeProducaoCard />
      </div>

      {/* Aviso de Transparência e Rastreabilidade Institucional */}
      <div className="p-3 sm:p-3.5 rounded-sm border border-emerald-600/30 bg-emerald-600/5 text-xs text-foreground flex items-start gap-2.5">
        <Info className="w-4 h-4 text-emerald-700 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
        <div className="flex flex-col gap-0.5">
          <p className="font-semibold text-xs">
            Política de Dados Físicos e Rastreabilidade Institucional
          </p>
          <p className="text-[11px] text-muted-foreground">
            O DeepFarms adota a política estrita de não exibir cotações agrícolas simuladas, desatualizadas ou sem autorização explícita de redistribuição comercial. O catálogo abaixo disponibiliza canais oficiais homologados para consulta direta nas instituições primárias de pesquisa e mercado (DERAL/SEAB-PR, CONAB, CEPEA/ESALQ e B3).
          </p>
        </div>
      </div>

      {/* Catálogo Extensível de Produtos e Indicadores de Mercado */}
      <section id="secao-catalogo" className="flex flex-col gap-3 pt-1 scroll-mt-20">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-2">
              <Scale className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Catálogo de Commodities e Referências Oficiais
            </h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Consulte fontes primárias, classificações agronômicas e praças de referência de grãos, café, pecuária, fibras e cana.
            </p>
          </div>
        </div>

        <CatalogoMercado initialProdutos={PRODUTOS_CATALOGO} mostrarPrecosDeral />
      </section>
    </div>
  );
}
