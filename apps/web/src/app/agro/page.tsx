import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";
import {
  ArrowDown,
  ArrowRight,
  Calculator,
  Check,
  CloudSun,
  ExternalLink,
  Globe2,
  Laptop,
  MapPin,
  MessageCircle,
  Smartphone,
  ShieldCheck,
  Sprout,
  Tablet,
  TrendingUp,
  UserRound,
  WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { LandingAnimations } from "@/components/landing/LandingAnimations";
import { ThemeToggle } from "@/components/landing/ThemeToggle";
import { ProductSwitcher } from "@/components/landing/ProductSwitcher";
import { LandingHeroBackground } from "@/components/landing/LandingHeroBackground";

export const metadata: Metadata = {
  title: "DeepFarms Agro | Ferramentas gratuitas para o produtor rural",
  description:
    "Acompanhe clima e indicadores do agro, consulte referências de mercado e use calculadoras rurais no celular, inclusive sem internet.",
  alternates: { canonical: "/agro" },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://app.deepfarms.com.br/agro",
    siteName: "DeepFarms",
    title: "DeepFarms Agro | Ferramentas gratuitas para o produtor rural",
    description: "Clima, mercado e calculadoras rurais gratuitas, disponíveis no celular e preparados para uso offline.",
    images: [{ url: "/images/agro/agro-inicio.png", alt: "DeepFarms Agro" }],
  },
};

const features = [
  {
    id: "inicio",
    number: "01",
    icon: Smartphone,
    eyebrow: "Acesso rápido às ferramentas",
    title: "Uma central simples para começar",
    description:
      "A tela inicial reúne atalhos para Clima, Mercado, Calculadoras e Conta, com navegação adaptada ao dispositivo e indicação do estado da conexão.",
    points: ["Atalhos para os recursos principais", "Navegação adaptada para celular, tablet e computador", "Instalação do aplicativo sugerida no celular"],
    imageLabel: "Tela inicial: atalhos e navegação do aplicativo",
    imageFile: "/images/agro/agro-inicio.png",
  },
  {
    id: "clima",
    number: "02",
    icon: CloudSun,
    eyebrow: "Planeje com o céu em vista",
    title: "Clima para decisões do dia a dia",
    description:
      "Consulte condições atuais e previsões horárias e diárias para localidades rurais. Selecione municípios ou use sua localização para acompanhar a sua região.",
    points: ["Condições meteorológicas atuais", "Previsões por hora e por dia", "Avisos agrometeorológicos"],
    imageLabel: "Tela Clima: condições, previsão e avisos",
    imageFile: "/images/agro/agro-clima.png",
  },
  {
    id: "mercado",
    number: "03",
    icon: TrendingUp,
    eyebrow: "Consulte referências confiáveis",
    title: "Mercado e indicadores do agro",
    description:
      "Acesse referências de commodities e indicadores econômicos com origem identificada. Cada dado informa fonte, unidade e período de referência para apoiar a consulta.",
    points: ["Referências de DERAL/SEAB-PR, CONAB, CEPEA/ESALQ, B3 e IRGA", "Dólar PTAX e indicadores do Banco Central", "Estatísticas de produção do IBGE"],
    imageLabel: "Tela Mercado: commodities, PTAX e indicadores",
    imageFile: "/images/agro/agro-mercado.png",
  },
  {
    id: "calculadoras",
    number: "04",
    icon: Calculator,
    eyebrow: "Resolva contas direto no campo",
    title: "Cinco calculadoras rurais",
    description:
      "Ferramentas práticas para converter medidas, estimar custos e organizar contas frequentes da produção. Os cálculos são feitos no próprio aparelho e podem ser usados offline.",
    points: ["Sacas, quilos e toneladas", "Hectares, metros quadrados e alqueires regionais", "Estimativa de frete por saca ou tonelada", "Custo por hectare e ponto de equilíbrio", "Conversor de massa, área, volume e comprimento"],
    imageLabel: "Tela Calculadoras: ferramentas e conversões",
    imageFile: "/images/agro/agro-calculadoras.png",
  },
  {
    id: "offline",
    number: "05",
    icon: WifiOff,
    eyebrow: "Feito para a realidade da conexão rural",
    title: "Aplicativo instalável e preparado para offline",
    description:
      "Instale o DeepFarms Agro como um aplicativo no celular. A interface se adapta a celular, tablet e computador; ferramentas e conteúdos previamente carregados continuam acessíveis quando a conexão falha.",
    points: ["Instalação como PWA", "Calculadoras disponíveis sem internet", "Conteúdo em cache e aviso de conexão"],
    imageLabel: "Tela do app instalado e estado sem conexão",
    imageFile: "/images/agro/agro-offline.png",
  },
  {
    id: "conta",
    number: "06",
    icon: UserRound,
    eyebrow: "Acesso individual e opcional",
    title: "Conta do produtor sob seu controle",
    description:
      "As consultas e calculadoras não exigem cadastro. A conta individual é opcional e separada das contas empresariais do DeepFarms Gestão.",
    points: ["Uso público das ferramentas", "Conta individual opcional", "Controles de privacidade e sessão"],
    imageLabel: "Tela Conta: acesso individual e privacidade",
    imageFile: "/images/agro/agro-conta.png",
  },
];

function ScreenshotPlaceholder({ label, file }: { label: string; file: string }) {
  const imageSource = file.startsWith("/") ? file : null;

  return (
        <div className="relative mx-auto w-full max-w-[280px] sm:max-w-[300px]">
          <div className="relative rounded-[2.5rem] border-[5px] border-[#1b2b22] bg-[#0c1610] p-1.5 shadow-2xl shadow-black/40 ring-1 ring-white/10">
            {/* Notch / Speaker sutil do smartphone */}
            <div className="absolute left-1/2 top-3 z-10 h-1 w-12 -translate-x-1/2 rounded-full bg-black/60 backdrop-blur-xs" />

            {/* Container da tela perfeitamente ajustado sem sobras cinzas */}
            <div className="relative aspect-[340/760] w-full overflow-hidden rounded-[2.1rem] bg-black">
              {imageSource ? (
                <Image
                  src={imageSource}
                  alt={label}
                  fill
                  sizes="(max-width: 640px) 280px, 300px"
                  className="object-cover"
                  priority={false}
                />
              ) : (
                <div className="flex size-full flex-col items-center justify-center bg-muted/20 p-6 text-center">
                  <Smartphone className="mx-auto mb-3 size-7 text-primary/70" />
                  <p className="text-xs font-semibold text-foreground">Captura a inserir</p>
                  <p className="mt-2 text-[10px] text-muted-foreground">{label}</p>
                </div>
              )}
            </div>
          </div>
          <div className="mt-2 text-center text-[10px] font-medium tracking-wide text-primary/70">
            {imageSource ? "DeepFarms Agro" : `Imagem pendente: ${file}`}
          </div>
        </div>
        );
}

        function DevicePreview({
          kind,
          title,
          description,
          image,
}: {
          kind: "mobile" | "tablet" | "desktop";
        title: string;
        description: string;
        image: string;
}) {
  const isMobile = kind === "mobile";
        const isDesktop = kind === "desktop";
        const DeviceIcon = isMobile ? Smartphone : isDesktop ? Laptop : Tablet;

        return (
        <figure className="flex h-full flex-col rounded-sm border border-border/60 bg-card p-4 sm:p-5">
          <div className="mb-3 flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <DeviceIcon className="size-4" />
            </span>
            <figcaption className="text-sm font-semibold">{title}</figcaption>
          </div>
            <div className="mx-auto flex w-full flex-1 items-center justify-center overflow-hidden rounded-sm bg-muted/15 p-3">
              {isMobile && (
                <div className="relative aspect-[337/756] w-full max-w-[190px] overflow-hidden rounded-[2rem] border-[4px] border-[#1b2b22] bg-[#0c1610] p-1 shadow-lg ring-1 ring-white/10">
                  <div className="relative size-full overflow-hidden rounded-[1.6rem] bg-black">
                    <Image
                      src={image}
                      alt={`Captura real do DeepFarms Agro em ${title.toLowerCase()}`}
                      fill
                      sizes="190px"
                      className="object-cover"
                    />
                  </div>
                </div>
              )}
              {kind === "tablet" && (
                <div className="relative aspect-[572/769] w-full max-w-[270px] overflow-hidden rounded-[1.2rem] border-[5px] border-[#1b2b22] bg-[#0c1610] p-1 shadow-lg ring-1 ring-white/10">
                  <div className="relative size-full overflow-hidden rounded-[0.8rem] bg-black">
                    <Image
                      src={image}
                      alt={`Captura real do DeepFarms Agro em ${title.toLowerCase()}`}
                      fill
                      sizes="270px"
                      className="object-cover"
                    />
                  </div>
                </div>
              )}
              {isDesktop && (
                <div className="relative aspect-[1250/949] w-full max-w-[380px] overflow-hidden rounded-t-md border-[4px] border-b-[8px] border-[#1b2b22] bg-[#0c1610] shadow-lg ring-1 ring-white/10">
                  <div className="relative size-full overflow-hidden bg-black">
                    <Image
                      src={image}
                      alt={`Captura real do DeepFarms Agro em ${title.toLowerCase()}`}
                      fill
                      sizes="380px"
                      className="object-cover"
                    />
                  </div>
                </div>
              )}
            </div>
            <p className="mt-4 text-xs leading-5 text-muted-foreground">{description}</p>
            <p className="mt-2 text-[10px] text-muted-foreground/80">Captura real do aplicativo.</p>
        </figure>
        );
}

        export default function AgroLandingPage() {
  return (
        <main className="min-h-dvh overflow-x-hidden bg-background text-foreground">
          <section className="relative overflow-hidden border-b border-border/50">
            <LandingHeroBackground />
            <div className="relative mx-auto max-w-7xl px-6 pb-16 pt-6 lg:px-10 lg:pb-24 lg:pt-8">
              <header className="landing-hero-reveal mb-10 flex flex-wrap items-center justify-between gap-4 lg:mb-12">
                <div className="flex items-center gap-4 sm:gap-6">
                  <Link href="/agro" aria-label="DeepFarms Agro" className="flex items-center gap-3">
                    <span className="flex size-12 items-center justify-center">
                      <Image src="/logos/deepfarms-mark.svg" alt="" width={48} height={48} className="size-full object-contain" />
                    </span>
                    <span>
                      <span className="block text-xl font-semibold uppercase tracking-[0.16em] text-primary">DeepFarms</span>
                      <span className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Agro</span>
                    </span>
                  </Link>
                  <ProductSwitcher active="agro" className="hidden lg:inline-flex" />
                </div>
                <nav aria-label="Navegação de produtos" className="flex flex-wrap items-center gap-2">
                  <ProductSwitcher active="agro" className="lg:hidden" />
                  <ThemeToggle />
                  <Button asChild variant="outline" size="sm"><Link href="#recursos">Conhecer o Agro</Link></Button>
                  <Button asChild size="sm"><a href="https://agro.deepfarms.com.br" target="_blank" rel="noopener noreferrer">Abrir aplicativo <ExternalLink className="size-3.5" /></a></Button>
                </nav>
              </header>

              <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
                <div className="space-y-7">
                  <Badge variant="secondary" className="landing-hero-reveal landing-hero-badge gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-primary"><Sprout className="size-3.5" /> Uma ferramenta para a rotina rural</Badge>
                  <div className="space-y-4">
                    <h1 className="landing-hero-reveal landing-hero-title max-w-2xl text-4xl font-light leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">O campo pede respostas. <span className="font-semibold text-primary">Tenha ferramentas à mão.</span></h1>
                    <p className="landing-hero-reveal landing-hero-copy max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">DeepFarms Agro reúne clima, referências de mercado e calculadoras rurais em um aplicativo gratuito que você pode instalar no celular.</p>
                  </div>
                  <div className="landing-hero-reveal landing-hero-actions flex flex-wrap gap-2">
                    <Button asChild size="sm"><a href="https://agro.deepfarms.com.br" target="_blank" rel="noopener noreferrer">Acessar DeepFarms Agro <ArrowRight className="size-3.5" /></a></Button>
                    <Button asChild variant="outline" size="sm"><Link href="#recursos">Explorar recursos <ArrowDown className="size-3.5" /></Link></Button>
                  </div>
                  <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-medium text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-primary" /> Gratuito para produtores</span>
                    <span className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-primary" /> Sem cadastro obrigatório</span>
                    <span className="inline-flex items-center gap-1.5"><Check className="size-3.5 text-primary" /> Pode ser instalado como app</span>
                  </div>
                </div>
                <div className="relative mx-auto w-full max-w-[450px]">
                  <div className="absolute -inset-8 rounded-full bg-primary/10 blur-3xl" />
                  <Card className="landing-hero-card relative overflow-hidden rounded-sm border-foreground/10 bg-card/90 p-0 shadow-2xl shadow-primary/10">
                    <div className="flex items-center justify-between border-b border-border/70 px-4 py-3"><div><div className="text-xs font-bold">DeepFarms Agro</div><div className="text-[10px] text-muted-foreground">Central do produtor</div></div><Badge variant="outline" className="text-[9px]">Aplicativo PWA</Badge></div>
                    <div className="grid grid-cols-2 gap-2 p-3 sm:gap-3 sm:p-4">
                      {[
                        { icon: CloudSun, title: "Clima", description: "Previsão local" },
                        { icon: TrendingUp, title: "Mercado", description: "Dados e referências" },
                        { icon: Calculator, title: "Calculadoras", description: "5 ferramentas" },
                        { icon: MapPin, title: "Sua região", description: "Busca de municípios" },
                      ].map(({ icon: Icon, title, description }) => <div key={title} className="min-h-28 rounded-sm border border-border/70 bg-background p-3"><div className="mb-5 flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary"><Icon className="size-4" /></div><div className="text-xs font-bold">{title}</div><div className="mt-1 text-[10px] text-muted-foreground">{description}</div></div>)}
                    </div>
                    <div className="mx-3 mb-3 flex items-center gap-2 rounded-sm bg-primary/5 px-3 py-2.5 text-[10px] text-muted-foreground"><WifiOff className="size-3.5 shrink-0 text-primary" /> Calculadoras disponíveis mesmo quando o sinal não chega.</div>
                  </Card>
                </div>
              </div>
            </div>
          </section>

          <section id="recursos" className="mx-auto max-w-7xl scroll-mt-8 px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
            <div className="mb-12 max-w-2xl">
              <Badge variant="secondary" className="mb-3 bg-primary/8 text-primary">Recursos do aplicativo</Badge>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">O essencial para consultar, calcular e seguir a rotina.</h2>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">Conheça o que já faz parte do DeepFarms Agro. Os quadros de tela estão preparados para receber capturas reais do aplicativo.</p>
            </div>
            <div className="space-y-8 lg:space-y-12">
              {features.map(({ id, number, icon: Icon, eyebrow, title, description, points, imageLabel, imageFile }, index) => (
                <article key={id} data-animate className="grid items-center gap-8 rounded-sm border border-border/60 bg-card/40 p-5 sm:p-8 lg:grid-cols-2 lg:gap-12 lg:p-10">
                  <div className={`space-y-5 ${index % 2 ? "lg:order-2" : ""}`}>
                    <div className="flex items-center gap-3"><span className="text-xs font-bold tracking-widest text-primary/60">{number}</span><span className="h-px w-8 bg-primary/30" /><span className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary">{eyebrow}</span></div>
                    <div className="flex items-start gap-3"><span className="mt-1 flex size-10 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary"><Icon className="size-5" /></span><h3 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h3></div>
                    <p className="max-w-xl text-sm leading-7 text-muted-foreground">{description}</p>
                    <ul className="grid gap-2 sm:grid-cols-2">{points.map((point) => <li key={point} className="flex items-start gap-2 text-xs leading-5 text-foreground/80"><Check className="mt-0.5 size-3.5 shrink-0 text-primary" />{point}</li>)}</ul>
                  </div>
                  <div className={`flex justify-center ${index % 2 ? "lg:order-1" : ""}`}><ScreenshotPlaceholder label={imageLabel} file={imageFile} /></div>
                </article>
              ))}
            </div>
          </section>

          <section data-animate className="border-y border-border/50 bg-muted/25">
            <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-20">
              <div className="mb-10 max-w-2xl">
                <Badge variant="secondary" className="mb-3 bg-primary/8 text-primary">Um app em várias telas</Badge>
                <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Use no celular, tablet ou computador.</h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">O DeepFarms Agro adapta a navegação e a disposição das ferramentas ao tamanho da tela, para você consultar informações onde estiver.</p>
              </div>
              <div className="grid gap-4 lg:grid-cols-3">
                <DevicePreview kind="mobile" title="Celular" image="/images/agro/agro-inicio.png" description="Navegação compacta, atalhos principais e barra inferior para acesso rápido com uma mão." />
                <DevicePreview kind="tablet" title="Tablet" image="/images/agro/agro-tablet.png" description="Interface ampliada com navegação lateral compacta e mais espaço para consultar os cards." />
                <DevicePreview kind="desktop" title="Desktop" image="/images/agro/agro-desktop.png" description="Tela ampla com menu lateral e conteúdo organizado em painéis para consulta no navegador." />
              </div>
            </div>
          </section>

          <section data-animate className="border-y border-border/50 bg-muted/25">
            <div className="mx-auto grid max-w-7xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:px-10 lg:py-20">
              <div><Badge variant="secondary" className="mb-3 bg-primary/8 text-primary">Acesso flexível</Badge><h2 className="text-3xl font-semibold tracking-tight">Comece a usar do seu jeito.</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">O DeepFarms Agro foi pensado para consulta simples e acesso em diferentes dispositivos.</p></div>
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  { icon: Globe2, title: "Acesso público", text: "Consulte clima, mercado e calculadoras sem criar uma conta." },
                  { icon: Smartphone, title: "Instalável", text: "Adicione o PWA à tela inicial e abra como um aplicativo." },
                  { icon: WifiOff, title: "Recursos offline", text: "Use as calculadoras sem conexão e acesse conteúdos previamente carregados." },
                  { icon: ShieldCheck, title: "Conta opcional", text: "Se optar por uma conta, ela é individual e separada da gestão empresarial." },
                ].map(({ icon: Icon, title, text }) => <div key={title} className="rounded-sm border border-border/60 bg-card p-4"><Icon className="mb-4 size-4 text-primary" /><div className="text-sm font-bold">{title}</div><p className="mt-1 text-xs leading-5 text-muted-foreground">{text}</p></div>)}
              </div>
            </div>
          </section>

          <section data-animate className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-20">
            <Card className="overflow-hidden rounded-sm border-primary/20 bg-primary/5 p-0">
              <CardContent className="flex flex-col gap-6 p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between lg:p-10">
                <div className="max-w-2xl"><Badge variant="outline" className="mb-3 border-primary/25 text-primary">Em planejamento</Badge><h2 className="text-2xl font-semibold tracking-tight">Uma comunidade de produtores também está no horizonte.</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">A área Comunidade prevê diretório regional, grupos por tema e troca consentida de contatos. Ela segue em planejamento e não é apresentada como recurso já disponível.</p></div>
                <MessageCircle className="hidden size-12 shrink-0 text-primary/40 sm:block" />
              </CardContent>
            </Card>
          </section>

          <section data-animate className="mx-auto max-w-7xl px-5 pb-16 sm:px-8 lg:px-10 lg:pb-24">
            <div className="flex flex-col gap-5 rounded-sm bg-[#153b2b] p-6 text-white sm:p-9 lg:flex-row lg:items-center lg:justify-between">
              <div><p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-200">DeepFarms Agro</p><h2 className="text-2xl font-semibold sm:text-3xl">Leve ferramentas úteis para o seu dia no campo.</h2><p className="mt-2 text-sm text-white/70">Gratuito para produtores. Acesse no navegador ou instale no seu celular.</p></div>
              <Button asChild variant="secondary" size="sm" className="shrink-0"><a href="https://agro.deepfarms.com.br" target="_blank" rel="noopener noreferrer">Abrir aplicativo <ArrowRight className="size-3.5" /></a></Button>
            </div>
          </section>

          <footer className="border-t border-border/50 bg-muted/20 px-5 sm:px-8 lg:px-10">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 py-7 sm:flex-row sm:items-center sm:justify-between">
              <Link href="/" className="text-xs font-bold uppercase tracking-[0.14em] text-primary">DeepFarms · Gestão rural integrada</Link>
              <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground"><Link href="/" className="hover:text-primary">Conheça o DeepFarms Gestão</Link><a href="https://agro.deepfarms.com.br" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-primary">Aplicativo Agro <ExternalLink className="size-3" /></a><span>© {new Date().getFullYear()} DeepFarms</span></div>
            </div>
          </footer>
          <LandingAnimations />
        </main>
        );
}

