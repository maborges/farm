import Link from "next/link";
import {
  ArrowRight,
  Calculator,
  CloudSun,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  WifiOff,
} from "lucide-react";
import { InstallPrompt } from "@/components/pwa/install-prompt";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-4 sm:gap-6">
      {/* Aviso de Instalação PWA */}
      <InstallPrompt />

      {/* Cabeçalho Compacto de App Mobile / Hero Adaptativo no Desktop */}
      <Card size="sm" className="relative overflow-hidden">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
            <Badge variant="success">
              Gratuito para Produtores
            </Badge>
            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
              <ShieldCheck className="size-3.5 text-primary" /> Sem cadastro obrigatório
            </span>
            <span className="text-[11px] text-muted-foreground hidden sm:inline-flex items-center gap-1">
              • <WifiOff className="size-3 text-emerald-600 dark:text-emerald-400" /> Modo Offline Ativo
            </span>
          </div>
          <h1 className="text-base sm:text-xl md:text-2xl font-bold tracking-tight text-foreground leading-snug pt-1">
            Ferramentas essenciais para o seu dia a dia no campo
          </h1>
          <CardDescription className="text-xs leading-relaxed">
            Consulte previsão meteorológica para sua microrregião, acompanhe indicadores de mercado e faça conversões agrícolas.
          </CardDescription>
        </CardHeader>
      </Card>

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
        <div className="grid grid-cols-4 gap-2.5 sm:hidden" data-testid="mobile-launcher-tiles">
          <Link
            href="/clima"
            className="flex min-h-[80px] flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl border border-border/60 bg-card active:scale-95 transition-transform shadow-sm"
          >
            <div className="p-2.5 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <CloudSun className="size-5" />
            </div>
            <span className="text-xs font-semibold text-foreground">Clima</span>
          </Link>

          <Link
            href="/mercado"
            className="flex min-h-[80px] flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl border border-border/60 bg-card active:scale-95 transition-transform shadow-sm"
          >
            <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
              <TrendingUp className="size-5" />
            </div>
            <span className="text-xs font-semibold text-foreground">Mercado</span>
          </Link>

          <Link
            href="/calculadoras"
            className="flex min-h-[80px] flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl border border-border/60 bg-card active:scale-95 transition-transform shadow-sm"
          >
            <div className="p-2.5 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Calculator className="size-5" />
            </div>
            <span className="text-xs font-semibold text-foreground">Cálculos</span>
          </Link>

          <Link
            href="/comunidade"
            className="flex min-h-[80px] flex-col items-center justify-center gap-1.5 p-2.5 rounded-xl border border-border/60 bg-card active:scale-95 transition-transform shadow-sm"
          >
            <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400">
              <Users className="size-5" />
            </div>
            <span className="text-xs font-semibold text-foreground">Rede</span>
          </Link>
        </div>

        {/* Cards Detalhados Adaptativos */}
        <div className="hidden sm:grid sm:grid-cols-2 gap-3">
          {/* Card Clima */}
          <Link href="/clima" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 transition-all">
              <CardHeader>
                <div className="p-2.5 rounded-sm bg-blue-500/10 text-blue-600 dark:text-blue-400 w-fit">
                  <CloudSun className="size-5" />
                </div>
                <CardAction>
                  <Badge variant="outline">
                    Previsão e Alertas
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Previsão do Tempo</span>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription className="text-xs">
                  Previsão horária e acompanhamento agrometeorológico para até 3 dias na sua região.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

          {/* Card Mercado */}
          <Link href="/mercado" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 transition-all">
              <CardHeader>
                <div className="p-2.5 rounded-sm bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 w-fit">
                  <TrendingUp className="size-5" />
                </div>
                <CardAction>
                  <Badge variant="outline">
                    Cotações Oficiais
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Mercado Agrícola</span>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription className="text-xs">
                  Câmbio Dólar PTAX oficial e referência para soja, milho, café e pecuária conforme praça.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

          {/* Card Calculadoras */}
          <Link href="/calculadoras" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 transition-all">
              <CardHeader>
                <div className="p-2.5 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 w-fit">
                  <Calculator className="size-5" />
                </div>
                <CardAction>
                  <Badge variant="outline">
                    Conversões e Fretes
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Calculadoras Rurais</span>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription className="text-xs">
                  Conversão de sacas, quilogramas, alqueires para hectares e cálculo de frete por tonelada e saca.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>

          {/* Card Comunidade & Rede */}
          <Link href="/comunidade" className="group active:scale-[0.99] transition-transform">
            <Card className="h-full hover:border-primary/50 transition-all">
              <CardHeader>
                <div className="p-2.5 rounded-sm bg-purple-500/10 text-purple-600 dark:text-purple-400 w-fit">
                  <Users className="size-5" />
                </div>
                <CardAction>
                  <Badge variant="outline">
                    Rede Técnica
                  </Badge>
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-1">
                <CardTitle className="flex items-center justify-between">
                  <span>Comunidade de Produtores</span>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </CardTitle>
                <CardDescription className="text-xs">
                  Diretório regional, grupos técnicos por cultura e troca consentida de contatos rurais.
                </CardDescription>
              </CardContent>
            </Card>
          </Link>
        </div>
      </section>

      {/* Chamada Discreta para DeepFarms Gestão */}
      <Card variant="muted" size="sm">
        <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex flex-col gap-1 max-w-xl">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <Sparkles className="size-4 text-primary" />
              <span>Precisa de controle completo da sua propriedade?</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Conheça o <strong className="text-foreground font-semibold">DeepFarms Gestão</strong>: gestão integrada de talhões, maquinário, defensivos, rebanho e fluxo de caixa.
            </p>
          </div>
          <Button asChild variant="outline" size="sm" className="shrink-0">
            <a
              href="https://deepfarms.com.br"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span>Conhecer Planos</span>
              <ExternalLink className="size-3.5 text-muted-foreground" />
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
