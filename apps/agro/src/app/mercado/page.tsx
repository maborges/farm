import { TrendingUp, Info, Scale } from "lucide-react";
import { PtaxCard } from "@/components/mercado/ptax-card";
import { IndicadoresMacroCard } from "@/components/mercado/indicadores-macro-card";
import { IbgeProducaoCard } from "@/components/mercado/ibge-producao-card";
import { IbgeValorProducaoCard } from "@/components/mercado/ibge-valor-producao-card";
import { CatalogoMercado } from "@/components/mercado/catalogo-mercado";
import { PRODUTOS_CATALOGO } from "@/lib/mercado/catalogo";
import { Badge } from "@/components/ui/badge";

export default async function MercadoPage() {
  return (
    <div className="space-y-5">
      {/* Cabeçalho da Seção */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            Mercado e Indicadores Agro
          </h1>
          <Badge variant="outline" className="text-[10px]">Cotações físicas e estatísticas oficiais</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          Câmbio do Banco Central, indicadores macroeconômicos e estatísticas de produção do IBGE.
        </p>
      </div>

      {/* Câmbio Oficial (PTAX - Banco Central do Brasil) */}
      <div className="w-full">
        <PtaxCard />
      </div>

      {/* Indicadores Econômicos e Câmbio Oficial (BCB) */}
      <div className="w-full">
        <IndicadoresMacroCard />
      </div>

      {/* Inteligência Agropecuária e Estatísticas Oficiais de Produção (IBGE/SIDRA) */}
      <div className="w-full">
        <IbgeValorProducaoCard />
      </div>

      {/* Referências anuais para culturas sem cotação DERAL homologada */}
      <div className="w-full">
        <IbgeProducaoCard />
      </div>

      {/* Aviso de Transparência e Rastreabilidade Institucional */}
      <div className="p-3.5 rounded-sm border border-emerald-600/30 bg-emerald-600/5 text-xs text-foreground flex items-start gap-2.5">
        <Info className="w-4 h-4 text-emerald-700 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
        <div className="space-y-0.5">
          <p className="font-semibold text-xs">Política de Dados Físicos e Rastreabilidade Institucional</p>
          <p className="text-[11px] text-muted-foreground">
            O DeepFarms adota a política estrita de não exibir cotações agrícolas simuladas, desatualizadas ou sem autorização explícita de redistribuição comercial. O catálogo abaixo disponibiliza canais oficiais homologados para consulta direta nas instituições primárias de pesquisa e mercado (DERAL/SEAB-PR, CONAB, CEPEA/ESALQ e B3).
          </p>
        </div>
      </div>

      {/* Catálogo Extensível de Produtos e Indicadores de Mercado */}
      <section className="space-y-3 pt-1">
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
