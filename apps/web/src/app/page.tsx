import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";
import {
  ArrowRight,
  BarChart3,
  Boxes,
  Brain,
  BriefcaseBusiness,
  Check,
  ChevronRight,
  ClipboardList,
  Coins,
  FileCheck2,
  Gauge,
  Globe2,
  Layers3,
  Leaf,
  LineChart,
  LockKeyhole,
  Map,
  MessagesSquare,
  Rocket,
  Scale,
  Shield,
  ShieldCheck,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Sprout,
  Target,
  Tractor,
  TrendingUp,
  Users,
  Wallet,
  Zap,
  Network,
  Handshake,
  Database,
  Plug,
  Server,
  Workflow,
  Key,
  Microscope,
  Activity,
  HardDrive,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LandingTracker } from "@/components/landing/ScrollTracker";
import { LandingAnimations } from "@/components/landing/LandingAnimations";
import { LandingCarousel } from "@/components/landing/LandingCarousel";
import { LandingFAQ } from "@/components/landing/LandingFAQ";
import { CountUp } from "@/components/landing/CountUp";
import { ThemeToggle } from "@/components/landing/ThemeToggle";
import { ProductSwitcher } from "@/components/landing/ProductSwitcher";
import { LandingHeroBackground } from "@/components/landing/LandingHeroBackground";
import { apiFetchServer } from "@/lib/api-server";
import { ModuloMetadata, Modulos, ModulosPorCategoria, normalizeModuleId, type ModuloId } from "@/lib/constants/modulos";

/* ─────────────────── SEO ─────────────────── */
export const metadata: Metadata = {
  title: "DeepFarms | Plataforma de Gestão Rural Integrada",
  description:
    "Campo, estoque e financeiro em uma única plataforma. Conformidade EUDR, rastreabilidade SHA-256, IA financeira e gestão por safra. Comece grátis.",
};

/* ═══════════════════════════════════════════════════════
   Data
   ═══════════════════════════════════════════════════════ */

const trustBadges = [
  { icon: Globe2, label: "Conformidade EUDR", description: "Desmatamento Zero" },
  { icon: ShieldCheck, label: "SHA-256", description: "Criptografia de Dados" },
  { icon: FileCheck2, label: "Fairtrade Ready", description: "Auditoria Limpa" },
  { icon: LockKeyhole, label: "LGPD", description: "Privacidade e Proteção" },
  { icon: Shield, label: "Isolamento entre produtores", description: "Proteção total" },
  { icon: Smartphone, label: "PWA Offline", description: "Acesso sem Internet" },
];

const painPoints = [
  {
    icon: ClipboardList,
    title: "Planilhas desconectadas",
    description: "Campo, compras e gestão seguem fluxos paralelos que exigem retrabalho diário.",
  },
  {
    icon: Globe2,
    title: "Risco de embargo (EUDR)",
    description: "Sem polígonos GeoJSON, sua exportação corre risco de retenção por falta de prova.",
  },
  {
    icon: FileCheck2,
    title: "Fraudes em fichas de EPI",
    description: "Auditorias exigem assinaturas reais. Papéis rasgam, somem ou geram passivos.",
  },
  {
    icon: Coins,
    title: "Custo por hectare estimado",
    description: "Sem origem operacional, margem e custo viram aproximação em vez de gestão real.",
  },
];

const howItWorksSteps = [
  {
    icon: Handshake,
    step: "01",
    title: "Implantação Assistida",
    description: "Onboarding inteligente que adapta a plataforma à sua cultura (ex: Café, Soja) e configura templates sem dor de cabeça.",
  },
  {
    icon: Plug,
    step: "02",
    title: "Integração ERP Transparente",
    description: "Conecte nativamente seu Sankhya ou outro ERP. Cadastros, insumos e parceiros sincronizados em tempo real.",
  },
  {
    icon: Smartphone,
    step: "03",
    title: "Caderno de Campo PWA",
    description: "Sua equipe executa ordens offline. Apontamentos, assinaturas e imagens sincronizam automaticamente com a rede.",
  },
  {
    icon: Brain,
    step: "04",
    title: "Motores de Inteligência",
    description: "Alertas proativos e recomendações inteligentes protegem sua margem e garantem a rentabilidade por safra.",
  },
];

const integrationFlow = [
  {
    icon: ClipboardList,
    step: "01",
    title: "Planejamento",
    description: "A tarefa é planejada com o insumo e a quantidade previstos para o talhão, dentro da Safra.",
  },
  {
    icon: Boxes,
    step: "02",
    title: "Estoque",
    description: "Ao confirmar a Ordem de Serviço, o sistema gera automaticamente a lista de separação para o almoxarifado.",
  },
  {
    icon: ShoppingCart,
    step: "03",
    title: "Compras",
    description: "Cotação com fornecedores, emissão de pedido e recebimento repõem o estoque antes da falta.",
  },
  {
    icon: Key,
    step: "04",
    title: "Requisição de Material",
    description: "O operador confere a quantidade retirada e assina digitalmente. É aqui que o estoque baixa de fato.",
  },
  {
    icon: Layers3,
    step: "05",
    title: "Devolução de Sobra",
    description: "Insumo não usado e ferramentas voltam ao almoxarifado com registro auditável, sem perda silenciosa.",
  },
];

const integrationBenefits = [
  {
    icon: Check,
    title: "Zero dupla baixa",
    description: "O insumo só sai do estoque quando fisicamente conferido, nunca duas vezes pela mesma tarefa.",
  },
  {
    icon: Network,
    title: "Rastreabilidade ponta a ponta",
    description: "Cada saco ou litro retirado tem responsável, data e talhão de destino registrados.",
  },
  {
    icon: Workflow,
    title: "Menos perda, mais controle",
    description: "Sobras retornam ao estoque de forma auditável em vez de se perderem sem registro.",
  },
];

const modules = [
  {
    icon: Microscope,
    title: "Agricultura de Precisão (VRA)",
    description: "Análise de solo georreferenciada com prescrições automatizadas de fertilidade.",
    features: ["Amostragem em Zonas de Manejo", "Interpolação Estatística de Nutrientes", "Mapas de Taxa Variável (ISOXML)", "Diretrizes Embrapa"],
  },
  {
    icon: Activity,
    title: "Pecuária de Precisão",
    description: "Rastreio e performance animal individual através de base de dados temporal de alta performance.",
    features: ["Cálculo Temporal de GMD", "Rastreabilidade SISBOV", "Reprodução e IATF", "Manejos Sanitários e Vacinas"],
  },
  {
    icon: Sprout,
    title: "Gestão Agrícola 360º",
    description: "Trate a safra como um projeto com Tollgates (gates de qualidade) intransponíveis.",
    features: ["Planejamento de Safra e Croqui", "Apontamentos Offline-First (PWA)", "Beneficiamento e Embalagem", "Assinatura Digital no Campo"],
  },
  {
    icon: Coins,
    title: "Custo 360º e DRE Operacional",
    description: "Descubra a margem exata de cada talhão cruzando despesas ativas com vendas realizadas.",
    features: ["DRE Operacional por Safra", "Fechamento Contábil Isolado", "Rateio Automático de Insumos", "Receitas Manuais e Múltiplas Moedas"],
  },
  {
    icon: Tractor,
    title: "GMA (Gestão de Frota)",
    description: "Apuração rigorosa do custo da máquina e manutenções preventivas integradas à safra.",
    features: ["Rateio de Custo Máquina/Hora", "Manutenção Preventiva", "Hodômetro e Horímetro", "Consumo de Combustível"],
    href: "/frota",
  },
  {
    icon: ShoppingCart,
    title: "Suprimentos e Estoques",
    description: "Inteligência de compras com alertas de preços fora do histórico e gestão contínua de lotes.",
    features: ["Reposição Automática de Estoque", "Score de Fornecedor Ideal", "Alerta de Variação de Preço (>15%)", "Ledger Operacional Único"],
  },
  {
    icon: Scale,
    title: "Risco Comercial e Hedge",
    description: "Acompanhamento diário da matriz física versus financeira (B3/Tradings).",
    features: ["Mark-to-Market Diário", "Proteção de Margem de Colheita", "Alertas de Capacidade Física", "Posições Futuras Consolidadas"],
  },
];

const differentiators = [
  {
    icon: Key,
    title: "Segurança e isolamento de dados",
    description: "Isolamento PostgreSQL (Row Level Security) e Keycloak, impedindo matematicamente o vazamento de dados entre fazendas.",
  },
  {
    icon: Server,
    title: "Orquestração Enterprise (K3s)",
    description: "Clusterização com alta disponibilidade e balanceamento Traefik, dimensionado para grandes demandas On-Premise ou Cloud.",
  },
  {
    icon: HardDrive,
    title: "TimescaleDB Temporal",
    description: "Banco de dados otimizado para milhões de eventos, garantindo cálculo veloz do GMD (ganho de peso diário) do rebanho.",
  },
  {
    icon: Workflow,
    title: "Wizard de Implantação Rígido",
    description: "Máquina de estados operacional (Tollgates) garantindo que nenhuma fazenda entre em Go-Live sem os checklists obrigatórios completos.",
  },
  {
    icon: Network,
    title: "Gateways Nativos ERP",
    description: "Sincronização bidirecional e assíncrona robusta (ex: Sankhya), com diagnóstico em tempo real sem expor senhas em texto puro.",
  },
  {
    icon: LockKeyhole,
    title: "Compliance e ESG Prontos",
    description: "Módulo completo de Evidências, Não Conformidades (NC) e Planos de Ação (PA) blindado temporalmente para auditorias limpas.",
  },
];

const complianceCards = [
  {
    icon: Globe2,
    title: "EUDR",
    subtitle: "Desmatamento Zero Comprovado",
    description: "Polígonos GeoJSON dos talhões integrados com satélite. Exigência obrigatória para exportações à UE.",
    badge: "Obrigatório 2025",
    color: "from-red-500/15 to-red-500/5" as const,
    iconColor: "text-red-500" as const,
  },
  {
    icon: FileCheck2,
    title: "Fairtrade",
    subtitle: "Fichas de EPI com Validade Legal",
    description: "Assinaturas reais dos trabalhadores em Canvas pelo celular, mesmo offline. Sem fichas de papel.",
    badge: "Auditoria Ready",
    color: "from-emerald-500/15 to-emerald-500/5" as const,
    iconColor: "text-emerald-500" as const,
  },
  {
    icon: Shield,
    title: "LGPD",
    subtitle: "Dados isolados por produtor",
    description: "Cada produtor tem seus dados protegidos. Controle por papéis: Proprietário, Agrônomo, Gerente, Operador.",
    badge: "Compliance",
    color: "from-blue-500/15 to-blue-500/5" as const,
    iconColor: "text-blue-500" as const,
  },
  {
    icon: ShieldCheck,
    title: "SHA-256",
    subtitle: "Cadeia Criptográfica",
    description: "Hash encadeado em cada etapa. Passaporte do Produto acessível via QR Code, irrefutável.",
    badge: "Blockchain-Ready",
    color: "from-amber-700/15 to-amber-700/5" as const,
    iconColor: "text-amber-700" as const,
  },
];

const aiFeatures = [
  { icon: Target, title: "Decisão C-Level e Magic Actions", description: "O Copiloto identifica custos excedentes que corroem sua margem e sugere ações de 1 clique, como revisar um uso excessivo de herbicida." },
  { icon: Brain, title: "Mesa de Simulação (What-If)", description: "Estresse o mercado antes que ele o faça: simule altas de 30% no preço do adubo e preveja riscos severos para a viabilidade da safra atual." },
  { icon: Zap, title: "IA Adaptativa e Gamificada", description: "O motor entende seu apetite ao risco (Conservador vs Agressivo) e exibe um score de acerto, calculando quantos prejuízos o Copiloto ajudou a empresa a evitar." },
];

const testimonials = [
  {
    quote: "Antes do DeepFarms, eu gastava 3 dias por mês fechando planilhas. Hoje o DRE da safra está pronto em tempo real, e a IA já me avisa se a margem está caindo.",
    author: "Carlos Mendonça",
    role: "Produtor de Soja e Milho",
    region: "Mato Grosso",
  },
  {
    quote: "A conformidade EUDR era um pesadelo. Com os polígonos GeoJSON e o passaporte SHA-256, nosso exportador ficou tranquilo e a venda fechou sem atraso.",
    author: "Fernanda Oliveira",
    role: "Gestora de Exportação",
    region: "Sul de Minas",
  },
  {
    quote: "O módulo de frota nos mostrou que duas máquinas custavam 40% mais por hora. Com a manutenção preventiva, reduzimos paradas em 60%.",
    author: "Ricardo Borges",
    role: "Gerente de Operações",
    region: "Goiás",
  },
  {
    quote: "A captura de assinaturas offline resolveu nosso problema com fichas de EPI. Na última auditoria Fairtrade, passamos sem uma não-conformidade.",
    author: "Ana Beatriz Lima",
    role: "Coordenadora de Qualidade",
    region: "Bahia",
  },
];

interface LandingPlan {
  id: string;
  nome: string;
  descricao?: string | null;
  descricao_marketing?: string | null;
  modulos_inclusos: string[];
  preco_mensal: number;
  preco_anual: number;
  plan_tier: string;
  tem_trial: boolean;
  dias_trial: number;
  is_free: boolean;
  destaque: boolean;
  ordem: number;
}

async function getLandingPlans(): Promise<LandingPlan[]> {
  try {
    return await apiFetchServer<LandingPlan[]>("/billing/plans/landing");
  } catch {
    return [];
  }
}

function formatPlanPrice(plan: LandingPlan): { value: string; period: string } {
  if (plan.is_free || plan.preco_mensal === 0) return { value: "Grátis", period: "" };
  if (!plan.preco_mensal) return { value: "Sob consulta", period: "" };
  return {
    value: new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(plan.preco_mensal),
    period: "/mês",
  };
}

function getPlanFeatures(plan: LandingPlan): string[] {
  const names = plan.modulos_inclusos
    .map((moduleId) => ModuloMetadata[normalizeModuleId(moduleId)]?.nome)
    .filter((name): name is string => Boolean(name));
  const visible = names.slice(0, 6);
  const remaining = names.length - visible.length;
  return remaining > 0 ? [...visible, `+ ${remaining} módulos incluídos`] : visible;
}

const moduleCategoryLabels: Record<string, string> = {
  IMOVEIS: "Imóveis rurais",
  AGRICOLA: "Agricultura",
  PECUARIA: "Pecuária",
  FINANCEIRO: "Financeiro",
  OPERACIONAL: "Operação",
  RH: "Pessoas e segurança",
  AMBIENTAL: "Ambiental",
  EXTENSAO: "Extensões inteligentes",
};

const moduleIconMap: Partial<Record<ModuloId, LucideIcon>> = {
  [Modulos.CORE]: Layers3,
  [Modulos.IMOVEIS_CADASTRO]: Map,
  [Modulos.IMOVEIS_ARRENDAMENTOS]: Handshake,
  [Modulos.IMOVEIS_AVALIACAO]: Scale,
  [Modulos.AGRICOLA_PLANEJAMENTO]: ClipboardList,
  [Modulos.AGRICOLA_CAMPO]: Sprout,
  [Modulos.AGRICOLA_DEFENSIVOS]: ShieldCheck,
  [Modulos.AGRICOLA_PRECISAO]: Microscope,
  [Modulos.AGRICOLA_COLHEITA]: Tractor,
  [Modulos.AGRICOLA_CLIMATICO]: Globe2,
  [Modulos.AGRICOLA_INTELIGENCIA]: Brain,
  [Modulos.PECUARIA_REBANHO]: Users,
  [Modulos.PECUARIA_GENETICA]: Network,
  [Modulos.PECUARIA_CONFINAMENTO]: Boxes,
  [Modulos.PECUARIA_LEITE]: Activity,
  [Modulos.PECUARIA_CLIMATICO]: Globe2,
  [Modulos.PECUARIA_INTELIGENCIA]: Brain,
  [Modulos.FINANCEIRO_TESOURARIA]: Wallet,
  [Modulos.FINANCEIRO_CUSTOS_ABC]: Coins,
  [Modulos.FINANCEIRO_FISCAL]: FileCheck2,
  [Modulos.FINANCEIRO_HEDGING]: TrendingUp,
  [Modulos.OPERACIONAL_FROTA]: Tractor,
  [Modulos.OPERACIONAL_ESTOQUE]: Boxes,
  [Modulos.OPERACIONAL_COMPRAS]: ShoppingCart,
  [Modulos.OPERACIONAL_BALANCA]: Scale,
  [Modulos.RH_REMUNERACAO]: Users,
  [Modulos.RH_SEGURANCA]: Shield,
  [Modulos.AMBIENTAL_COMPLIANCE]: Leaf,
  [Modulos.AMBIENTAL_CARBONO]: Activity,
  [Modulos.EXTENSAO_IA_COPILOT]: Brain,
  [Modulos.EXTENSAO_IOT_SENSORES]: Gauge,
  [Modulos.EXTENSAO_ERP_BRIDGE]: Plug,
};

const moduleCatalogSections: Array<{ key: string; title: string; ids: ModuloId[] }> = [
  { key: "CORE", title: "Núcleo da plataforma", ids: [Modulos.CORE] },
  ...Object.entries(ModulosPorCategoria).map(([key, ids]) => ({
    key,
    title: moduleCategoryLabels[key] ?? key,
    ids,
  })),
];

const faqItems = [
  {
    question: "Posso testar a plataforma grátis?",
    answer: "Sim! Os planos publicados podem oferecer período de teste, conforme a configuração comercial vigente. Consulte as opções disponíveis e comece sem compromisso.",
  },
  {
    question: "Como funciona o acesso por produtor?",
    answer: "Cada produtor possui dados completamente isolados. Um único usuário pode acessar múltiplas propriedades sem deslogar, com controle granular por papéis.",
  },
  {
    question: "A plataforma funciona offline?",
    answer: "Sim. O PWA de Campo é offline-first. Registre operações, capture evidências e colete assinaturas sem conexão. Os dados sincronizam automaticamente.",
  },
  {
    question: "O que é a conformidade EUDR?",
    answer: "O EUDR exige que exportadores provem desmatamento zero. O DeepFarms gera polígonos GeoJSON, integra satélite e cria passaportes SHA-256 de conformidade.",
  },
  {
    question: "Posso migrar dados de planilhas?",
    answer: "Sim. Oferecemos ferramentas de importação. No Enterprise, temos onboarding dedicado para transição completa.",
  },
  {
    question: "Quais dispositivos são suportados?",
    answer: "Painel web em qualquer navegador moderno. PWA de Campo em smartphones e tablets Android e iOS com captura de assinaturas na tela touch.",
  },
  {
    question: "Como funciona a IA financeira?",
    answer: "O Copiloto analisa dados em tempo real: identifica riscos, simula cenários e gera planos de ação. Aprende com suas decisões e se adapta ao seu perfil de risco.",
  },
  {
    question: "Atende diferentes culturas?",
    answer: "Sim. Suporta soja, milho, café, algodão, pecuária de corte e leite, operações mistas. Templates operacionais por cultura.",
  },
];

/* ═══════════════════════════════════════════════════════
   Reusable section wrapper for consistent visual identity
   ═══════════════════════════════════════════════════════ */

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "muted" | "accent";
  id?: string;
}

function Section({ children, className = "", variant = "default", id, ...props }: SectionProps) {
  const base = "relative px-6 lg:px-10";
  const bg =
    variant === "muted"
      ? "bg-muted/25"
      : variant === "accent"
        ? "bg-[linear-gradient(180deg,hsl(var(--primary)/0.08),hsl(var(--module-operacional)/0.04),transparent)]"
        : "";

  return (
    <section id={id} className={`${base} ${bg} ${className}`} {...props}>
      {/* Subtle top divider */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-border/60 to-transparent" />
      <div className="mx-auto max-w-7xl py-14 lg:py-16">
        {children}
      </div>
    </section>
  );
}

function SectionHeader({
  badge,
  title,
  subtitle,
  center = true,
}: {
  badge: string;
  title: string;
  subtitle?: string;
  center?: boolean;
}) {
  return (
    <div className={`mb-10 max-w-2xl space-y-3 ${center ? "mx-auto flex flex-col items-center text-center" : "flex flex-col items-start"}`}>
      <Badge variant="secondary" className="bg-primary/8 text-primary text-[11px] font-bold uppercase tracking-[0.14em]">
        {badge}
      </Badge>
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl lg:text-4xl">{title}</h2>
      {subtitle && <p className="text-muted-foreground leading-7">{subtitle}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════ */

export default async function Home() {
  const landingPlans = await getLandingPlans();
  const trialPlan = landingPlans.find((plan) => plan.tem_trial && plan.dias_trial > 0);

  return (
    <main className="min-h-dvh bg-background text-foreground overflow-x-hidden">

      {/* ═══════════ HERO ═══════════ */}
      <section className="relative overflow-hidden border-b border-border/50">
        <LandingHeroBackground />

        <div className="relative mx-auto max-w-7xl px-6 pb-10 pt-6 lg:px-10 lg:pb-14 lg:pt-8">
          {/* Nav */}
          <header className="landing-hero-reveal mb-10 flex flex-wrap items-center justify-between gap-4 lg:mb-12">
            <div className="flex items-center gap-4 sm:gap-6">
              <div className="flex items-center gap-3">
                <div className="flex size-12 items-center justify-center">
                  <Image src="/logos/deepfarms-mark.svg" alt="DeepFarms" width={48} height={48} className="size-full object-contain" />
                </div>
                <div>
                  <div className="text-xl font-semibold uppercase tracking-[0.16em] text-primary">DeepFarms</div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Gestão rural integrada</div>
                </div>
              </div>
              <ProductSwitcher active="gestao" className="hidden lg:inline-flex" />
            </div>
            <nav className="flex flex-wrap items-center gap-2">
              <ProductSwitcher active="gestao" className="lg:hidden" />
              <ThemeToggle />
              <Button asChild variant="outline" size="sm"><Link href="/login">Entrar</Link></Button>
              <Button asChild size="sm"><Link href="/register">Começar grátis</Link></Button>
            </nav>
          </header>

          {/* Content */}
          <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center lg:gap-10">
            <div className="space-y-6">
              <Badge className="landing-hero-reveal landing-hero-badge rounded-full border border-primary/20 bg-background/80 px-3 text-[10px] font-black uppercase tracking-[0.18em] text-primary shadow-sm">
                <Globe2 className="mr-1.5 size-3" />
                Conformidade EUDR 2025 · Fairtrade · LGPD
              </Badge>

              <h1 className="landing-hero-reveal landing-hero-title max-w-[600px] text-4xl font-light leading-[1.1] tracking-tight text-balance sm:text-5xl md:text-6xl lg:text-[4rem]">
                Campo, estoque e financeiro{" "}
                <span className="font-semibold text-primary">
                  integrados em um único lugar.
                </span>
              </h1>

              <p className="landing-hero-reveal landing-hero-copy max-w-xl text-base leading-7 text-muted-foreground lg:text-lg lg:leading-8">
                Controle operacional com saldo confiável, origem financeira vinculada e visão por safra.
                Elimine planilhas e tome decisões com dados reais.
              </p>

              <div className="landing-hero-reveal landing-hero-actions flex flex-wrap gap-2">
                <Button asChild size="sm">
                  <Link href="/register" data-track-event="cta_test_click">
                    Começar grátis <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm">
                  <Link href="/login" data-track-event="cta_demo_click">
                    Ver demonstração <ChevronRight className="size-3.5" />
                  </Link>
                </Button>
              </div>

              <div className="landing-hero-reveal landing-hero-proof grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                {[
                  { icon: ShieldCheck, label: "GeoJSON EUDR" },
                  { icon: LockKeyhole, label: "Assinatura Offline" },
                  { icon: Shield, label: "SHA-256" },
                  { icon: Sprout, label: "Fechamento por Safra" },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="landing-proof-card rounded-sm border border-border/60 bg-card/80 px-3 py-2.5 text-xs font-semibold shadow-sm backdrop-blur">
                    <div className="flex items-center gap-1.5">
                      <Icon className="size-3.5 text-primary" />
                      <span>{label}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Executive card */}
            <Card className="landing-hero-card rounded-sm overflow-hidden border-primary/12 bg-card/92 py-0 shadow-2xl shadow-primary/8 backdrop-blur">
              <CardHeader className="border-b border-border/50 bg-muted/30 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-lg font-black">Visão executiva</CardTitle>
                    <CardDescription className="text-xs">Dados que antes ficavam espalhados em planilhas.</CardDescription>
                  </div>
                  <Badge variant="secondary" className="landing-status-pulse bg-primary/10 text-primary text-[10px]">Ao vivo</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 p-4">
                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    { icon: Gauge, label: "Saldo confiável", value: "98,7%" },
                    { icon: ClipboardList, label: "Operações", value: "1.248" },
                    { icon: Wallet, label: "Origem vinculada", value: "91%" },
                    { icon: BriefcaseBusiness, label: "Unidades", value: "12" },
                  ].map(({ icon: Icon, label, value }) => (
                    <div key={label} className="rounded-sm border border-border/50 bg-background/90 p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <Icon className="size-3.5 text-primary" />
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
                      </div>
                      <div className="text-xl font-black">{value}</div>
                    </div>
                  ))}
                </div>
                <div className="rounded-sm bg-primary/5 p-3 text-xs leading-6 text-muted-foreground">
                  Elimine a ruptura entre execução, estoque e fechamento financeiro. A operação nasce no campo e chega ao resultado com contexto.
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ═══════════ TRUST BAR ═══════════ */}
      <div className="overflow-hidden border-y border-border/40 bg-muted/20 py-3">
        <div className="marquee-track">
          {[...trustBadges, ...trustBadges, ...trustBadges].map(({ icon: Icon, label, description }, i) => (
            <div key={`${label}-${i}`} className="flex shrink-0 items-center gap-2.5 px-8">
              <div className="flex items-center gap-1.5">
                <Icon className="size-4 text-primary/70" />
                <span className="text-[11px] font-bold uppercase tracking-wider text-foreground/80">{label}</span>
              </div>
              <span className="text-[11px] font-medium text-muted-foreground">{description}</span>
              <span className="ml-8 text-border/60">·</span>
            </div>
          ))}
        </div>
      </div>

      {/* ═══════════ DORES ═══════════ */}
      <Section variant="default" data-animate>
        <SectionHeader
          badge="Dores que resolvemos"
          title="Quando o dado não fecha, a decisão vira aposta."
          subtitle="Problemas que custam tempo, dinheiro e oportunidades todos os dias."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-animate-stagger>
          {painPoints.map((pain) => {
            const Icon = pain.icon;
            return (
              <Card key={pain.title} className="relative overflow-hidden rounded-sm group h-full border-border/40 bg-card/60 backdrop-blur-md py-0 shadow-sm transition-all duration-500 hover:-translate-y-1.5 hover:border-primary/40 hover:bg-card/90 hover:shadow-xl hover:shadow-primary/10">
                {/* Decorative background glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                <div className="absolute -right-8 -top-8 size-32 rounded-full bg-primary/5 blur-3xl transition-all duration-500 group-hover:bg-primary/10" />

                <CardHeader className="relative gap-3 p-6 pb-6">
                  <div className="flex size-11 items-center justify-center rounded-sm bg-primary/10 text-primary ring-1 ring-primary/20 transition-all duration-500 group-hover:bg-primary group-hover:text-primary-foreground group-hover:ring-primary/50 group-hover:shadow-md">
                    <Icon className="size-5 transition-transform duration-500 group-hover:scale-110" />
                  </div>
                  <div>
                    <CardTitle className="text-lg font-black tracking-tight">{pain.title}</CardTitle>
                    <CardDescription className="mt-1.5 text-sm leading-relaxed text-muted-foreground/90">{pain.description}</CardDescription>
                  </div>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </Section>

      {/* ═══════════ CATÁLOGO COMPLETO DE MÓDULOS ═══════════ */}
      <Section variant="accent" data-animate>
        <SectionHeader
          badge="Catálogo completo"
          title="Todos os módulos, organizados para a sua operação."
          subtitle="Do cadastro rural às extensões de IA, cada frente da plataforma fica visível e pode evoluir com o seu negócio."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-animate-stagger>
          {moduleCatalogSections.map(({ key, title, ids }) => (
            <Card key={key} className="rounded-sm border-border/50 bg-card/75 py-0 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/35 hover:shadow-lg hover:shadow-primary/8">
              <CardHeader className="border-b border-border/40 p-5 pb-4">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base font-black tracking-tight">{title}</CardTitle>
                  <Badge variant="secondary" className="bg-primary/8 text-[10px] font-bold text-primary">{ids.length} {ids.length === 1 ? "módulo" : "módulos"}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3 p-5">
                {ids.map((moduleId) => {
                  const moduleInfo = ModuloMetadata[moduleId];
                  if (!moduleInfo) return null;
                  const ModuleIcon = moduleIconMap[moduleId] ?? Layers3;
                  return (
                    <div key={moduleId} className="flex items-start gap-2.5">
                      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary ring-1 ring-primary/15" aria-hidden="true">
                        <ModuleIcon className="size-4" strokeWidth={1.8} />
                      </span>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-foreground">{moduleInfo.nome}</div>
                        <div className="mt-0.5 text-[11px] leading-5 text-muted-foreground">{moduleInfo.descricao}</div>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </div>
      </Section>

      {/* ═══════════ COMO FUNCIONA ═══════════ */}
      <Section variant="muted" data-animate>
        <SectionHeader
          badge="Como funciona"
          title="Da fazenda ao resultado em 4 passos"
          subtitle="Um fluxo simples que conecta campo, gestão e decisão financeira."
          center
        />
        <div className="relative grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-animate-stagger>
          {/* Connecting line */}
          <div className="pointer-events-none absolute inset-x-12 top-8 hidden h-px bg-gradient-to-r from-primary/20 via-primary/30 to-primary/20 xl:block" />

          {howItWorksSteps.map(({ icon: Icon, step, title, description }) => (
            <div key={step} className="relative rounded-sm border border-border/50 bg-card/80 p-5 text-center shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md">
              <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full border-2 border-primary/20 bg-background shadow-sm">
                <Icon className="size-5 text-primary" />
              </div>
              <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-primary/50">Passo {step}</div>
              <h3 className="mb-1.5 text-sm font-black">{title}</h3>
              <p className="text-xs leading-5 text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ MÓDULOS ═══════════ */}
      <Section variant="default" data-animate>
        <SectionHeader
          badge="Módulos"
          title="A suíte completa para gestão rural em uma plataforma só."
          subtitle="Agricultura, pecuária, estoque, financeiro, suprimentos, frota, hedge e comercial."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-animate-stagger>
          {modules.map(({ icon: Icon, title, description, features, href }) => {
            const Inner = (
              <Card className="relative overflow-hidden rounded-sm group h-full border-border/40 bg-card/60 backdrop-blur-md py-0 shadow-sm transition-all duration-500 hover:-translate-y-1.5 hover:border-primary/40 hover:bg-card/90 hover:shadow-xl hover:shadow-primary/10">
                {/* Decorative background glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                <div className="absolute -right-8 -top-8 size-32 rounded-full bg-primary/5 blur-3xl transition-all duration-500 group-hover:bg-primary/10" />
                
                <CardHeader className="relative gap-3 p-6 pb-4">
                  <div className="flex size-11 items-center justify-center rounded-sm bg-primary/10 text-primary ring-1 ring-primary/20 transition-all duration-500 group-hover:bg-primary group-hover:text-primary-foreground group-hover:ring-primary/50 group-hover:shadow-md">
                    <Icon className="size-5 transition-transform duration-500 group-hover:scale-110" />
                  </div>
                  <div>
                    <CardTitle className="text-lg font-black tracking-tight">{title}</CardTitle>
                    <CardDescription className="mt-1.5 text-sm leading-relaxed text-muted-foreground/90">{description}</CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="relative space-y-2.5 px-6 pb-6 pt-0">
                  {features.map((f) => (
                    <div key={f} className="flex items-center gap-2.5 text-xs font-medium text-muted-foreground transition-colors group-hover:text-foreground/80">
                      <div className="flex size-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
                        <Check className="size-2.5" strokeWidth={3} />
                      </div>
                      <span>{f}</span>
                    </div>
                  ))}
                  {href && (
                    <div className="mt-4 flex w-fit items-center text-xs font-bold text-primary transition-all group-hover:translate-x-1">
                      Saiba mais <ArrowRight className="ml-1 size-3.5 transition-transform group-hover:translate-x-1" />
                    </div>
                  )}
                </CardContent>
              </Card>
            );
            if (href) return <Link key={title} href={href}>{Inner}</Link>;
            return <div key={title}>{Inner}</div>;
          })}
        </div>
      </Section>

      {/* ═══════════ INTEGRAÇÃO ENTRE MÓDULOS ═══════════ */}
      <Section variant="muted" data-animate>
        <SectionHeader
          badge="Integração entre módulos"
          title="Do planejamento ao almoxarifado, sem ruptura de dados."
          subtitle="Cada etapa da operação alimenta a próxima automaticamente — o insumo só sai do estoque quando é fisicamente conferido no campo."
          center
        />
        <div className="relative grid gap-4 sm:grid-cols-2 xl:grid-cols-5" data-animate-stagger>
          <div className="pointer-events-none absolute inset-x-10 top-8 hidden h-px bg-gradient-to-r from-primary/20 via-primary/30 to-primary/20 xl:block" />

          {integrationFlow.map(({ icon: Icon, step, title, description }) => (
            <div key={step} className="relative rounded-sm border border-border/50 bg-card/80 p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md">
              <div className="mb-3 flex size-11 items-center justify-center rounded-full border-2 border-primary/20 bg-background shadow-sm">
                <Icon className="size-5 text-primary" />
              </div>
              <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-primary/50">Etapa {step}</div>
              <h3 className="mb-1.5 text-sm font-black">{title}</h3>
              <p className="text-xs leading-5 text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {integrationBenefits.map(({ icon: Icon, title, description }) => (
            <div key={title} className="flex gap-3 rounded-sm border border-border/40 bg-card/60 p-4">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary ring-1 ring-primary/20">
                <Icon className="size-4" />
              </div>
              <div>
                <h4 className="text-xs font-black">{title}</h4>
                <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ DIFERENCIAIS ═══════════ */}
      <Section variant="accent" data-animate>
        <SectionHeader
          badge="Diferenciais técnicos"
          title="Arquitetura que sustenta a promessa."
          subtitle="Contratos operacionais consolidados na base, não apenas painéis bonitos."
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-animate-stagger>
          {differentiators.map(({ icon: Icon, title, description }) => (
            <Card key={title} className="relative overflow-hidden rounded-sm group h-full border-border/40 bg-card/60 backdrop-blur-md py-0 shadow-sm transition-all duration-500 hover:-translate-y-1.5 hover:border-primary/40 hover:bg-card/90 hover:shadow-xl hover:shadow-primary/10">
              {/* Decorative background glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
              <div className="absolute -right-8 -top-8 size-32 rounded-full bg-primary/5 blur-3xl transition-all duration-500 group-hover:bg-primary/10" />

              <CardHeader className="relative gap-3 p-6 pb-6">
                <div className="flex size-11 items-center justify-center rounded-sm bg-primary/10 text-primary ring-1 ring-primary/20 transition-all duration-500 group-hover:bg-primary group-hover:text-primary-foreground group-hover:ring-primary/50 group-hover:shadow-md">
                  <Icon className="size-5 transition-transform duration-500 group-hover:scale-110" />
                </div>
                <div>
                  <CardTitle className="text-lg font-black tracking-tight">{title}</CardTitle>
                  <CardDescription className="mt-1.5 text-sm leading-relaxed text-muted-foreground/90">{description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      </Section>

      {/* ═══════════ CONFORMIDADES ═══════════ */}
      <Section variant="default" data-animate>
        <SectionHeader
          badge="Conformidades"
          title="Preparado para o que o mercado já cobra."
          subtitle="Exportação europeia, auditorias de certificação e proteção de dados."
          center
        />
        <div className="grid gap-4 sm:grid-cols-2" data-animate-stagger>
          {complianceCards.map(({ icon: Icon, title, subtitle, description, badge, color, iconColor }) => (
            <div
              key={title}
              className={`rounded-sm border border-border/50 bg-gradient-to-br ${color} p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md`}
            >
              <div className="mb-3 flex items-center justify-between">
                <div className={`flex size-10 items-center justify-center rounded-sm bg-background/80 ${iconColor}`}>
                  <Icon className="size-4.5" />
                </div>
                <Badge className="border-0 bg-background/60 text-[10px] font-bold text-foreground/70">{badge}</Badge>
              </div>
              <h3 className="text-lg font-black">{title}</h3>
              <div className="mb-2 text-xs font-semibold text-primary">{subtitle}</div>
              <p className="text-sm leading-6 text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ IA COPILOTO ═══════════ */}
      <Section variant="accent" data-animate>
        <SectionHeader
          badge="Inteligência Artificial"
          title="Copiloto que aprende com suas decisões."
          subtitle="Identifica riscos, simula cenários e recomenda ações com transparência e score de acerto."
          center
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-animate-stagger>
          {aiFeatures.map(({ icon: Icon, title, description }) => (
            <div key={title} className="rounded-sm border border-primary/8 bg-card/85 p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md">
              <div className="mb-3 flex size-9 items-center justify-center rounded-sm bg-gradient-to-br from-primary/12 to-primary/5 text-primary">
                <Icon className="size-4" />
              </div>
              <h3 className="mb-1 text-sm font-black">{title}</h3>
              <p className="text-xs leading-5 text-muted-foreground">{description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ ESTATÍSTICAS ═══════════ */}
      <Section variant="muted" data-animate>
        <SectionHeader
          badge="Impacto em números"
          title="Resultados que falam por si."
          center
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { end: 1248, suffix: "+", label: "Operações rastreadas" },
            { end: 98.7, suffix: "%", label: "Saldo confiável", decimals: 1 },
            { end: 6, suffix: " módulos", label: "Integrados" },
            { end: 0, suffix: "", label: "Planilhas paralelas", isZero: true },
          ].map(({ end, suffix, label, decimals, isZero }) => (
            <div key={label} className="rounded-sm border border-border/50 bg-card/90 p-6 text-center shadow-sm">
              <div className="mb-1.5 text-3xl font-black text-primary sm:text-4xl">
                {isZero ? "Zero" : <CountUp end={end} suffix={suffix} decimals={decimals ?? 0} />}
              </div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══════════ DEPOIMENTOS ═══════════ */}
      <Section variant="default" data-animate>
        <SectionHeader
          badge="Depoimentos"
          title="Quem usa, recomenda."
          subtitle="Produtores e gestores que transformaram sua operação."
          center
        />
        <LandingCarousel slides={testimonials} />
      </Section>

      {/* ═══════════ PLANOS ═══════════ */}
      <Section variant="muted" id="planos" data-animate>
        <SectionHeader
          badge="Planos 100% Transparentes"
          title="Todos os pacotes com 100% dos módulos liberados."
          subtitle="Você não paga por módulo bloqueado. O valor é calculado de forma justa apenas pela sua área produtiva equivalente e pela quantidade de acessos simultâneos no painel web."
          center
        />

        {/* Quadro de Transparência do Cálculo antes do Cadastro */}
        <div className="mb-8 rounded-sm border border-primary/25 bg-card/90 p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-3">
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider text-primary">
                Como calculamos sua mensalidade ou anuidade?
              </h3>
              <p className="text-xs text-muted-foreground">
                Logo no primeiro passo antes de preencher o cadastro, você simula sua área e acessos para saber exatamente o valor a pagar.
              </p>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link href="/register">
                Simular meu valor agora <ArrowRight className="ml-1.5 size-3.5" />
              </Link>
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-sm border border-border/50 bg-background/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-black text-foreground">
                <Layers3 className="size-3.5 text-primary" /> 100% dos Módulos
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Do pacote Familiar ao Grupo, todos os assinantes têm acesso integral a todos os módulos da plataforma.
              </p>
            </div>
            <div className="rounded-sm border border-border/50 bg-background/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-black text-foreground">
                <Leaf className="size-3.5 text-emerald-600" /> Reserva Legal e APP Isentas
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Áreas de preservação ambiental (<strong>APP e Reserva Legal</strong>) são 100% isentas (R$ 0) e <em>Safra + Safrinha</em> no mesmo talhão não pagam em dobro.
              </p>
            </div>
            <div className="rounded-sm border border-border/50 bg-background/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-black text-foreground">
                <Smartphone className="size-3.5 text-emerald-600" /> App Campo 100% Isento
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Cadastre usuários ilimitados. Só conta quem estiver logado ao mesmo tempo na Web. O <strong>App Campo no celular não consome acesso simultâneo</strong>.
              </p>
            </div>
            <div className="rounded-sm border border-border/50 bg-background/70 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-black text-foreground">
                <Sparkles className="size-3.5 text-primary" /> Duplo Desconto no Anual
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                No plano Anual você garante <strong>2 meses grátis</strong> no pacote base + <strong>20% de desconto</strong> nas licenças extras de acesso simultâneo.
              </p>
            </div>
          </div>
        </div>
        {landingPlans.length === 0 ? (
          <Card className="mx-auto max-w-2xl rounded-sm border-border/60 bg-card/80 text-center shadow-sm">
            <CardContent className="space-y-3 p-8">
              <div className="mx-auto flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary"><Sprout className="size-5" /></div>
              <h3 className="text-lg font-black">Planos em atualização</h3>
              <p className="text-sm leading-6 text-muted-foreground">Nossa equipe está preparando as opções comerciais para publicação. Fale com um especialista para conhecer a plataforma.</p>
              <Button asChild size="sm" className="mt-2"><Link href="/login">Falar com especialista <ArrowRight className="size-3.5" /></Link></Button>
            </CardContent>
          </Card>
        ) : (
        <div className="grid gap-5 lg:grid-cols-3" data-animate-stagger>
          {landingPlans.map((plan) => {
            const price = formatPlanPrice(plan);
            const features = getPlanFeatures(plan);
            const badge = plan.destaque ? "Mais escolhido" : plan.tem_trial && plan.dias_trial > 0 ? `${plan.dias_trial} dias grátis` : plan.plan_tier;
            return (
            <Card
              key={plan.id}
              className={
                plan.destaque
                  ? "rounded-sm gradient-border border-primary/20 bg-[linear-gradient(180deg,hsl(var(--primary)/0.08),hsl(var(--card)/0.92))] py-0 shadow-xl shadow-primary/8"
                  : "rounded-sm border-border/60 py-0 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md"
              }
            >
              <CardHeader className="space-y-2 p-5 pb-3">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-xl font-black">{plan.nome}</CardTitle>
                  <Badge className={plan.destaque ? "bg-primary text-primary-foreground text-[10px]" : "border border-primary/20 bg-background text-primary text-[10px]"}>
                    {badge}
                  </Badge>
                </div>
                <CardDescription className="text-sm leading-6">{plan.descricao_marketing || plan.descricao || "Estruture sua operação rural com dados confiáveis."}</CardDescription>
                <div className="flex items-baseline gap-0.5">
                  <span className="text-3xl font-black">{price.value}</span>
                  {price.period && <span className="text-sm text-muted-foreground">{price.period}</span>}
                </div>
              </CardHeader>
              <CardContent className="space-y-2 px-5 pb-3 pt-0">
                {features.map((f) => (
                  <div key={f} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <Check className="mt-0.5 size-3.5 shrink-0 text-primary" />
                    <span>{f}</span>
                  </div>
                ))}
              </CardContent>
              <div className="px-5 pb-5">
                <Button asChild className="w-full" variant="outline" size="sm">
                  <Link href="/register" data-track-event="plan_select" data-track-plan={plan.nome}>
                    {plan.tem_trial ? "Começar agora" : "Escolher plano"} <ArrowRight className="size-3.5" />
                  </Link>
                </Button>
              </div>
            </Card>
            );
          })}
        </div>
        )}
      </Section>

      {/* ═══════════ FAQ ═══════════ */}
      <Section variant="default" data-animate>
        <div className="mx-auto max-w-3xl">
          <SectionHeader badge="Perguntas frequentes" title="Tire suas dúvidas." center />
          <LandingFAQ items={faqItems} />
        </div>
      </Section>

      {/* ═══════════ CTA FINAL ═══════════ */}
      <Section variant="accent" data-animate>
        <Card className="overflow-hidden rounded-sm border-primary/20 bg-primary/5 py-0 shadow-sm">
          <CardContent className="flex flex-col gap-6 p-6 lg:flex-row lg:items-center lg:justify-between lg:p-8">
            <div className="space-y-3">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-primary">
                Pronto para transformar sua gestão?
              </div>
              <h2 className="max-w-md text-2xl font-black tracking-tight sm:text-3xl">
                Troque retrabalho por operação integrada.
              </h2>
              <p className="max-w-lg text-sm text-muted-foreground leading-6">
                {trialPlan ? `${trialPlan.dias_trial} dias grátis no ${trialPlan.nome}.` : "Escolha o plano que acompanha o momento da sua operação."} Sem compromisso.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 sm:flex-row">
              <Button asChild size="sm">
                <Link href="/register" data-track-event="cta_test_click">Começar grátis <ArrowRight className="size-3.5" /></Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/login" data-track-event="cta_demo_click">Ver demonstração <ChevronRight className="size-3.5" /></Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </Section>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="border-t border-border/50 bg-muted/30 px-6 lg:px-10">
        <div className="mx-auto max-w-7xl py-12">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="flex size-8 items-center justify-center rounded-sm bg-primary text-primary-foreground">
                  <Sprout className="size-3.5" />
                </div>
                <span className="text-xs font-black uppercase tracking-[0.2em] text-primary">DeepFarms</span>
              </div>
              <p className="text-xs leading-5 text-muted-foreground">
                Plataforma de gestão rural integrada. Campo, estoque e financeiro em um único lugar.
              </p>
            </div>
            <div className="space-y-3">
              <h4 className="text-xs font-black uppercase tracking-wider text-foreground">Produto</h4>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li><Link href="/agro" className="hover:text-primary">DeepFarms Agro</Link></li>
                <li><Link href="/register" className="hover:text-primary">Começar grátis</Link></li>
                <li><Link href="/login" className="hover:text-primary">Demonstração</Link></li>
                <li><Link href="/frota" className="hover:text-primary">Módulo Frota</Link></li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="text-xs font-black uppercase tracking-wider text-foreground">Conformidades</h4>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li className="flex items-center gap-1.5"><Globe2 className="size-3 text-primary/50" />EUDR</li>
                <li className="flex items-center gap-1.5"><FileCheck2 className="size-3 text-primary/50" />Fairtrade</li>
                <li className="flex items-center gap-1.5"><Shield className="size-3 text-primary/50" />LGPD</li>
                <li className="flex items-center gap-1.5"><ShieldCheck className="size-3 text-primary/50" />SHA-256</li>
              </ul>
            </div>
            <div className="space-y-3">
              <h4 className="text-xs font-black uppercase tracking-wider text-foreground">Contato</h4>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li>contato@deepfarms.com.br</li>
                <li>+55 (11) 9 9999-0000</li>
                <li className="pt-1 text-[10px]">Seg a Sex, 8 h às 18 h</li>
              </ul>
            </div>
          </div>

          <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-border/40 pt-6 sm:flex-row">
            <div className="flex flex-wrap items-center gap-4 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              <div className="flex items-center gap-1.5"><LockKeyhole className="size-3 text-primary/50" />Dados criptografados</div>
              <div className="flex items-center gap-1.5"><ShieldCheck className="size-3 text-primary/50" />99.9% uptime</div>
              <div className="flex items-center gap-1.5"><LineChart className="size-3 text-primary/50" />ISO 27001</div>
            </div>
            <div className="text-[10px] text-muted-foreground">
              © {new Date().getFullYear()} DeepFarms. Todos os direitos reservados.
            </div>
          </div>
        </div>
      </footer>

      <LandingTracker />
      <LandingAnimations />
    </main>
  );
}
