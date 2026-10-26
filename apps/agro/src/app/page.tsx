import Link from "next/link";
import { CloudSun, TrendingUp, Calculator, ArrowRight, ShieldCheck, Sparkles, ExternalLink } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { InstallPrompt } from "@/components/pwa/install-prompt";

export default function HomePage() {
  return (
    <div className="space-y-6">
      {/* Aviso de Instalação PWA */}
      <InstallPrompt />

      {/* Hero / Apresentação Objetiva */}
      <section className="rounded-sm border border-border bg-card p-5 sm:p-6 shadow-xs relative overflow-hidden">
        <div className="max-w-2xl space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="success">Gratuito para Produtores</Badge>
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Sem cadastro obrigatório
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Ferramentas essenciais para o seu dia a dia no campo
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
            Consulte previsão meteorológica para sua microrregião, acompanhe indicadores de mercado e faça conversões agrícolas.
          </p>
        </div>
      </section>

      {/* Grid de Ferramentas Principais */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Acesso Rápido às Ferramentas
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {/* Card Clima */}
          <Link href="/clima" className="group">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div className="p-2.5 rounded-sm bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  <CloudSun className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">Previsão e Alertas</Badge>
              </CardHeader>
              <CardContent className="space-y-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Previsão do Tempo</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription>
                  Previsão horária e acompanhamento agrometeorológico para até 3 dias na sua região.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

          {/* Card Mercado */}
          <Link href="/mercado" className="group">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div className="p-2.5 rounded-sm bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">Cotações Oficiais</Badge>
              </CardHeader>
              <CardContent className="space-y-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Mercado Agrícola</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription>
                  Câmbio Dólar PTAX oficial e referência para soja, milho, café e pecuária conforme praça.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

          {/* Card Calculadoras */}
          <Link href="/calculadoras" className="group">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div className="p-2.5 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Calculator className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">Conversões e Fretes</Badge>
              </CardHeader>
              <CardContent className="space-y-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Calculadoras Rurais</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription>
                  Conversão de sacas, quilogramas, alqueires para hectares e cálculo de frete por tonelada e saca.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

        </div>
      </section>

      {/* Chamada Discreta para DeepFarms Gestão */}
      <section className="p-4 sm:p-5 rounded-sm border border-border/80 bg-muted/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="space-y-1 max-w-xl">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <Sparkles className="w-4 h-4 text-primary" />
            <span>Precisa de controle completo da sua propriedade?</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Conheça o <strong className="text-foreground font-semibold">DeepFarms Gestão</strong>: gestão integrada de talhões, maquinário, defensivos, rebanho e fluxo de caixa.
          </p>
        </div>
        <a
          href="https://deepfarms.com.br"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-sm bg-background hover:bg-accent text-foreground transition-colors flex-shrink-0"
        >
          <span>Conhecer Planos</span>
          <ExternalLink className="w-3.5 h-3.5 text-muted-foreground" />
        </a>
      </section>
    </div>
  );
}
