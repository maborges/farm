import Link from "next/link";
import {
  ArrowRight,
  Calculator,
  CloudSun,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  User,
  Users,
  WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { InstallPrompt } from "@/components/pwa/install-prompt";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-4 sm:gap-6">
      {/* Aviso de Instalação PWA */}
      <InstallPrompt />

      {/* Cabeçalho Compacto de App Mobile / Hero Adaptativo no Desktop */}
      <section className="rounded-sm border border-border bg-card p-3.5 sm:p-5 shadow-xs relative overflow-hidden">
        <div className="max-w-2xl flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <Badge variant="success" className="text-[10px]">
              Gratuito para Produtores
            </Badge>
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Sem cadastro obrigatório
            </span>
            <span className="text-[11px] text-muted-foreground hidden sm:inline-flex items-center gap-1">
              • <WifiOff className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> Modo Offline Ativo
            </span>
          </div>
          <h1 className="text-base sm:text-xl md:text-2xl font-bold tracking-tight text-foreground leading-snug">
            Ferramentas essenciais para o seu dia a dia no campo
          </h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Consulte previsão meteorológica para sua microrregião, acompanhe indicadores de mercado e faça conversões agrícolas.
          </p>
        </div>
      </section>

      {/* Atalhos Rápidos estilo App Launcher (Mobile & Tablet First) */}
      <section className="flex flex-col gap-2.5" aria-label="Acesso rápido às ferramentas">
        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Acesso Rápido às Ferramentas
          </h2>
          <span className="text-[10px] text-muted-foreground sm:hidden">
            Toque para abrir
          </span>
        </div>

        {/* Grade de Ícones Rápidos para Toque no Celular (App Tiles) */}
        <div className="grid grid-cols-4 gap-2 sm:hidden" data-testid="mobile-launcher-tiles">
          <Link
            href="/clima"
            className="flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-sm border border-border bg-card active:scale-95 transition-transform shadow-xs"
          >
            <div className="p-2 rounded-sm bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <CloudSun className="w-5 h-5" />
            </div>
            <span className="text-[11px] font-semibold text-foreground">Clima</span>
          </Link>

          <Link
            href="/mercado"
            className="flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-sm border border-border bg-card active:scale-95 transition-transform shadow-xs"
          >
            <div className="p-2 rounded-sm bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <span className="text-[11px] font-semibold text-foreground">Mercado</span>
          </Link>

          <Link
            href="/calculadoras"
            className="flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-sm border border-border bg-card active:scale-95 transition-transform shadow-xs"
          >
            <div className="p-2 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Calculator className="w-5 h-5" />
            </div>
            <span className="text-[11px] font-semibold text-foreground">Cálculos</span>
          </Link>

          <Link
            href="/conta"
            className="flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-sm border border-border bg-card active:scale-95 transition-transform shadow-xs"
          >
            <div className="p-2 rounded-sm bg-primary/10 text-primary">
              <User className="w-5 h-5" />
            </div>
            <span className="text-[11px] font-semibold text-foreground">Conta</span>
          </Link>
        </div>

        {/* Cards Detalhados Adaptativos */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Card Clima */}
          <Link href="/clima" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2 p-3.5 sm:p-5 sm:pb-2">
                <div className="p-2.5 rounded-sm bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  <CloudSun className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Previsão e Alertas
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 p-3.5 pt-0 sm:p-5 sm:pt-0">
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
          <Link href="/mercado" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2 p-3.5 sm:p-5 sm:pb-2">
                <div className="p-2.5 rounded-sm bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Cotações Oficiais
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 p-3.5 pt-0 sm:p-5 sm:pt-0">
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
          <Link href="/calculadoras" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2 p-3.5 sm:p-5 sm:pb-2">
                <div className="p-2.5 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Calculator className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Conversões e Fretes
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 p-3.5 pt-0 sm:p-5 sm:pt-0">
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

          {/* Card Comunidade & Rede */}
          <Link href="/comunidade" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 hover:shadow-xs transition-all">
              <CardHeader className="flex flex-row items-start justify-between pb-2 p-3.5 sm:p-5 sm:pb-2">
                <div className="p-2.5 rounded-sm bg-purple-500/10 text-purple-600 dark:text-purple-400">
                  <Users className="w-5 h-5" />
                </div>
                <Badge variant="outline" className="text-[10px]">
                  Rede Técnica
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-col gap-1 p-3.5 pt-0 sm:p-5 sm:pt-0">
                <CardTitle className="flex items-center justify-between">
                  <span>Comunidade de Produtores</span>
                  <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription>
                  Diretório regional, grupos técnicos por cultura e troca consentida de contatos rurais.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>
        </div>
      </section>

      {/* Chamada Discreta para DeepFarms Gestão */}
      <section className="p-3.5 sm:p-4 rounded-sm border border-border/80 bg-muted/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex flex-col gap-1 max-w-xl">
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
