import { BarChart3, DollarSign, Info, Percent, Scale, TrendingUp } from "lucide-react";
import { CatalogoMercado } from "@/components/mercado/catalogo-mercado";
import { IbgeProducaoCard } from "@/components/mercado/ibge-producao-card";
import { IbgeValorProducaoCard } from "@/components/mercado/ibge-valor-producao-card";
import { IndicadoresMacroCard } from "@/components/mercado/indicadores-macro-card";
import { PtaxCard } from "@/components/mercado/ptax-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { PRODUTOS_CATALOGO } from "@/lib/mercado/catalogo";

export default async function MercadoPage() {
  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      {/* Cabeçalho da Seção */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-base sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <TrendingUp className="size-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Mercado e Indicadores Agro</span>
          </h1>
          <Badge variant="outline">
            Cotações físicas e estatísticas oficiais
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Câmbio do Banco Central, indicadores macroeconômicos e estatísticas de produção do IBGE.
        </p>

        {/* Barra de Atalhos Rápidos Mobile/Tablet para Navegação entre Blocos */}
        <nav
          aria-label="Atalhos das seções de mercado"
          data-testid="mercado-quick-jump"
          className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pt-1"
        >
          <Button asChild variant="default" size="sm" className="shrink-0">
            <a href="#secao-catalogo">
              <Scale className="size-3.5" />
              <span>Commodities</span>
            </a>
          </Button>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <a href="#secao-ptax">
              <DollarSign className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Câmbio PTAX</span>
            </a>
          </Button>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <a href="#secao-macro">
              <Percent className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Selic &amp; IPCA</span>
            </a>
          </Button>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <a href="#secao-ibge">
              <BarChart3 className="size-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Produção IBGE</span>
            </a>
          </Button>
        </nav>
      </div>

      <Separator />

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
      <Alert variant="success">
        <Info className="size-4" />
        <AlertTitle className="text-xs">
          Política de Dados Físicos e Rastreabilidade Institucional
        </AlertTitle>
        <AlertDescription className="text-xs">
          O DeepFarms adota a política estrita de não exibir cotações agrícolas simuladas, desatualizadas ou sem autorização explícita de redistribuição comercial. O catálogo abaixo disponibiliza canais oficiais homologados para consulta direta nas instituições primárias de pesquisa e mercado (DERAL/SEAB-PR, CONAB, CEPEA/ESALQ e B3).
        </AlertDescription>
      </Alert>

      {/* Catálogo Extensível de Produtos e Indicadores de Mercado */}
      <section id="secao-catalogo" className="flex flex-col gap-3 pt-1 scroll-mt-20">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-2">
              <Scale className="size-4 text-emerald-600 dark:text-emerald-400" />
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
