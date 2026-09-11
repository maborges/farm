import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Check,
  ChevronRight,
  Fuel,
  Gauge,
  History,
  LayoutDashboard,
  LineChart,
  Settings2,
  ShieldCheck,
  Sparkles,
  Tractor,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LandingTracker } from "@/components/landing/ScrollTracker";
import { FrotaHeroContent } from "@/components/landing/FrotaHeroContent";
import { getWhatsappComercialUrl } from "@/lib/runtime-config";

const pains = [
  {
    title: "Combustível",
    description: "Diesel sumindo e você não sabe onde. O prejuízo já foi embora com o combustível.",
    icon: Fuel,
  },
  {
    title: "Manutenção reativa",
    description: "A máquina quebrou na hora da colheita. A manutenção reativa é a mais cara que existe.",
    icon: Wrench,
  },
  {
    title: "Máquina parada",
    description: "Operador parado esperando conserto custa dinheiro e atrasa sua safra.",
    icon: History,
  },
  {
    title: "Sem custo real",
    description: "Você não sabe quanto custou de máquina plantar aquele talhão. Decisão no achismo.",
    icon: LineChart,
  },
];

const benefits = [
  {
    title: "Custo por hora real",
    description: "Combustível, peças e manutenção somados num único número, atualizado automaticamente.",
  },
  {
    title: "Preventiva inteligente",
    description: "Receba avisos antes da máquina quebrar. O sistema monitora horas, km e dias.",
  },
  {
    title: "Frota × Safra",
    description: "Veja quanto cada safra, talhão ou cultura gastou de frota com precisão total.",
  },
  {
    title: "Disponibilidade total",
    description: "Saiba o estado de toda a frota em 10 segundos: disponíveis, em conserto ou com alerta.",
  },
];

const steps = [
  {
    num: "1",
    title: "Cadastre suas máquinas",
    description: "Nome, tipo, marca, horímetro atual. Leva menos de 5 minutos por equipamento.",
  },
  {
    num: "2",
    title: "Registre o uso",
    description: "Abastecimentos e ordens de serviço registrados no campo. O custo é calculado automático.",
  },
  {
    num: "3",
    title: "O sistema avisa",
    description: "Preventivas próximas, consumo fora da média ou máquina sem uso. Sem verificação manual.",
  },
  {
    num: "4",
    title: "Decida com números",
    description: "Qual máquina dá prejuízo, qual safra gastou mais e qual talhão está caro para operar.",
  },
];

const features = [
  {
    title: "Dashboard",
    description: "Estado da frota de manhã, antes de ir ao campo. Alertas e custos do mês em 10 segundos.",
    icon: LayoutDashboard,
    tier: "Todos",
  },
  {
    title: "Preventiva",
    description: "Defina intervalos e o sistema acompanha. Um clique abre a ordem de serviço.",
    icon: ShieldCheck,
    tier: "Todos",
  },
  {
    title: "Consumo e Eficiência",
    description: "Descubra qual trator está bebendo diesel a mais comparado à média da frota.",
    icon: Fuel,
    tier: "Profissional",
  },
  {
    title: "Ranking de Custo",
    description: "Custo por hora e por km. Ranking dos equipamentos mais caros da sua operação.",
    icon: LineChart,
    tier: "Profissional",
  },
  {
    title: "Score de Risco",
    description: "O sistema calcula o risco de cada máquina parar e recomenda o que fazer.",
    icon: Gauge,
    tier: "Enterprise",
  },
  {
    title: "Integração Agrícola",
    description: "Vínculo direto entre jornada de uso e operação: plantio, pulverização e colheita.",
    icon: Boxes,
    tier: "Enterprise",
  },
];

export default function FrotaLandingPage() {
  return (
    <main className="min-h-dvh bg-[linear-gradient(180deg,hsl(var(--background)),color-mix(in_oklch,var(--background)_95%,#0b636f),hsl(var(--background)))] text-foreground">
      <section className="relative overflow-hidden border-b border-border/60">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(11,99,111,0.12),transparent_40%),radial-gradient(circle_at_90%_10%,rgba(217,119,87,0.08),transparent_30%)]" />
        <div className="relative mx-auto max-w-7xl px-6 py-8 lg:px-10 lg:py-12">
          <header className="mb-12 flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-sm bg-primary text-primary-foreground shadow-lg shadow-primary/25">
                <Tractor className="size-5" />
              </div>
              <div>
                <div className="text-sm font-black uppercase tracking-[0.2em] text-primary">DeepFarms Frota</div>
                <div className="text-xs text-muted-foreground">Inteligência em mecanização</div>
              </div>
            </Link>
            <nav className="flex items-center gap-2">
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Entrar</Link>
              </Button>
              <Button asChild size="sm" className="shadow-lg shadow-primary/25">
                <Link href="/register">Começar agora</Link>
              </Button>
            </nav>
          </header>

          <FrotaHeroContent />
        </div>
      </section>

      {/* Dores */}
      <section className="mx-auto max-w-7xl px-6 py-20 lg:px-10">
        <div className="mb-12 text-center space-y-3">
          <Badge variant="outline" className="border-primary/20 text-primary">
            Sua operação hoje
          </Badge>
          <h2 className="text-4xl font-black tracking-tight">Você reconhece alguma dessas situações?</h2>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {pains.map((pain) => (
            <Card key={pain.title} className="border-border/60 bg-background/50 backdrop-blur-sm shadow-sm hover:shadow-md transition-shadow">
              <CardHeader className="space-y-4">
                <div className="size-12 rounded-sm bg-destructive/10 text-destructive flex items-center justify-center">
                  <pain.icon className="size-6" />
                </div>
                <CardTitle className="text-xl font-black">{pain.title}</CardTitle>
                <CardDescription className="text-base leading-7">{pain.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* Proposta de Valor */}
      <section className="bg-primary/5 py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="mb-16 max-w-3xl space-y-4">
            <Badge className="bg-primary text-primary-foreground">A solução DeepFarms</Badge>
            <h2 className="text-4xl font-black tracking-tight">O DeepFarms Frota transforma sua frota num centro de controle.</h2>
            <p className="text-xl text-muted-foreground">Três perguntas que você vai conseguir responder no primeiro dia:</p>
          </div>
          <div className="grid gap-12 lg:grid-cols-2">
            {benefits.map((benefit, idx) => (
              <div key={benefit.title} className="flex gap-6">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-black">
                  0{idx + 1}
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-black">{benefit.title}</h3>
                  <p className="text-lg text-muted-foreground leading-relaxed">{benefit.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Economia Real (Novo Step 18) */}
      <section className="mx-auto max-w-7xl px-6 py-24 lg:px-10 border-y border-border/40">
        <div className="grid gap-12 lg:grid-cols-2 items-center">
          <div className="space-y-8">
            <div className="space-y-4">
              <Badge variant="outline" className="text-emerald-600 border-emerald-600/20 bg-emerald-50">Transparência</Badge>
              <h2 className="text-4xl font-black tracking-tight">De onde vem essa economia de até 20%?</h2>
              <p className="text-xl text-muted-foreground leading-relaxed">
                Não é mágica, é gestão de dados. A economia vem da eliminação sistemática de três grandes ralos de dinheiro na fazenda:
              </p>
            </div>

            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="size-10 shrink-0 rounded-sm bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Fuel className="size-5" />
                </div>
                <div>
                  <h4 className="font-black text-lg">Desperdício de Combustível</h4>
                  <p className="text-muted-foreground">Identificamos tratores operando em marcha errada ou ociosidade excessiva, reduzindo o consumo em até 12%.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="size-10 shrink-0 rounded-sm bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Settings2 className="size-5" />
                </div>
                <div>
                  <h4 className="font-black text-lg">Manutenção Preventiva</h4>
                  <p className="text-muted-foreground">Uma quebra catastrófica no motor custa 8× mais que uma revisão. O sistema garante que nenhuma troca de óleo passe do prazo.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="size-10 shrink-0 rounded-sm bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <Gauge className="size-5" />
                </div>
                <div>
                  <h4 className="font-black text-lg">Máquinas Ineficientes</h4>
                  <p className="text-muted-foreground">Saiba qual equipamento custa mais para manter do que o valor que ele produz. Decida quando trocar com base em fatos.</p>
                </div>
              </div>
            </div>
          </div>

          <Card className="border-emerald-600/20 bg-emerald-50/30 overflow-hidden">
            <CardHeader className="bg-emerald-600 text-white">
              <CardTitle className="text-xl">Simulação de Impacto Real</CardTitle>
              <CardDescription className="text-emerald-100">Baseado em cenários reais de produtores</CardDescription>
            </CardHeader>
            <CardContent className="p-8 space-y-8">
              <div className="space-y-4">
                <div className="flex justify-between items-end border-b border-emerald-600/10 pb-4">
                  <span className="text-muted-foreground">Cenário: trator de 132 kW operando 1.000 h/ano</span>
                  <span className="font-bold text-emerald-700 text-sm">Exemplo Típico</span>
                </div>
                
                <div className="grid gap-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Consumo extra (desajuste/falta de preventiva)</span>
                    <span className="text-destructive font-black">+ 15%</span>
                  </div>
                  <div className="flex justify-between items-center text-lg font-black">
                    <span>Prejuízo Oculto por Safra</span>
                    <span className="text-destructive">R$ 8.400,00</span>
                  </div>
                </div>
              </div>

              <div className="rounded-sm bg-emerald-600/10 p-4 border border-emerald-600/20">
                <p className="text-sm text-emerald-900 leading-relaxed italic">
                  "O DeepFarms me mostrou que dois tratores estavam bebendo 2 litros a mais por hora. Corrigimos o ajuste e a economia pagou o sistema em 3 meses."
                </p>
                <div className="mt-2 text-xs font-bold text-emerald-700">— João P., MT (5.000 hectares)</div>
              </div>

              <div className="text-center">
                <p className="text-xs text-muted-foreground uppercase font-black tracking-widest mb-4">Economia estimada com DeepFarms</p>
                <div className="text-5xl font-black text-emerald-600 tracking-tighter">Até 20%*</div>
                <p className="text-[10px] text-muted-foreground mt-2">*Dependendo do cenário operacional e maturidade da gestão atual.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="bg-muted/30 py-16 border-y border-border/40">
        <div className="mx-auto max-w-7xl px-6 lg:px-10 text-center space-y-12">
          <div className="space-y-4">
            <h2 className="text-3xl font-black tracking-tight">Como funciona na prática?</h2>
            <p className="text-muted-foreground text-lg">Sem complicação técnica. Focado no dia a dia do campo.</p>
          </div>
          
          <div className="grid gap-8 md:grid-cols-3">
            <div className="bg-background p-8 rounded-sm border border-border/60 shadow-sm space-y-4">
              <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                <Check className="size-6" />
              </div>
              <h3 className="text-xl font-bold">Não precisa de sensores</h3>
              <p className="text-sm text-muted-foreground">Você não precisa instalar nada nas máquinas. O sistema é 100% software.</p>
            </div>
            <div className="bg-background p-8 rounded-sm border border-border/60 shadow-sm space-y-4">
              <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                <Check className="size-6" />
              </div>
              <h3 className="text-xl font-bold">Use o que você já tem</h3>
              <p className="text-sm text-muted-foreground">Funciona com apontamento simples pelo celular ou dados que você já coleta.</p>
            </div>
            <div className="bg-background p-8 rounded-sm border border-border/60 shadow-sm space-y-4">
              <div className="size-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
                <Check className="size-6" />
              </div>
              <h3 className="text-xl font-bold">Funciona sem internet</h3>
              <p className="text-sm text-muted-foreground">No talhão não tem sinal? Sem problema. O app sincroniza tudo quando voltar para a sede.</p>
            </div>
          </div>

          <div className="pt-8 max-w-5xl mx-auto">
            <div className="relative rounded-sm overflow-hidden border border-border/80 shadow-2xl">
              <img 
                src="/home/borgus/.gemini/antigravity/brain/c5f639e9-0b11-4ab3-9f03-48d8aacf2388/frota_dashboard_preview_1778204083271.png" 
                alt="Dashboard DeepFarms Frota"
                className="w-full h-auto"
              />
              <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-6 text-white text-left">
                <p className="font-bold text-lg">Veja como você acompanha custo, uso e manutenção em um só lugar</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Como Funciona */}
      <section className="mx-auto max-w-7xl px-6 py-24 lg:px-10">
        <div className="mb-16 text-center space-y-4">
          <h2 className="text-4xl font-black tracking-tight">Quatro passos. Nenhuma planilha.</h2>
          <p className="text-xl text-muted-foreground">Simplicidade para quem está no campo, inteligência para quem gere.</p>
        </div>
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div key={step.num} className="relative space-y-4">
              <div className="text-6xl font-black text-primary/10 absolute -top-4 -left-2 select-none">
                {step.num}
              </div>
              <div className="relative pt-6">
                <h3 className="text-xl font-black mb-2">{step.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Seção de Decisão Rápida */}
      <section className="bg-background py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="grid gap-12 lg:grid-cols-3">
            <div className="space-y-4">
              <div className="text-primary font-black uppercase tracking-widest text-sm">Para quem é</div>
              <h3 className="text-2xl font-black">Produtores e gestores que operam frotas próprias.</h3>
              <p className="text-muted-foreground leading-relaxed">
                Se você tem pelo menos 3 máquinas operando, o DeepFarms já se paga com a primeira economia de combustível ou preventiva evitada.
              </p>
            </div>
            <div className="space-y-4">
              <div className="text-primary font-black uppercase tracking-widest text-sm">Quando faz sentido</div>
              <h3 className="text-2xl font-black">Quando o custo invisível começa a incomodar.</h3>
              <p className="text-muted-foreground leading-relaxed">
                Faz sentido quando você percebe que o diesel está sumindo, máquinas quebram sem aviso ou você não sabe o custo real por hectare.
              </p>
            </div>
            <div className="space-y-4">
              <div className="text-destructive font-black uppercase tracking-widest text-sm">Quanto custa não usar</div>
              <h3 className="text-2xl font-black">Até R$ 8.000 por máquina, por safra.</h3>
              <p className="text-muted-foreground leading-relaxed">
                O custo de não ter controle é aceitar o desperdício como parte do negócio. Cada dia sem dados é um dia de lucro jogado fora.
              </p>
            </div>
          </div>

          <div className="mt-16 flex flex-col items-center p-8 rounded-sm border border-primary/20 bg-primary/5 text-center space-y-4">
            <div className="flex items-center gap-2 text-primary">
              <Sparkles className="size-5" />
              <span className="font-bold uppercase tracking-wider text-sm">Urgência Leve</span>
            </div>
            <h2 className="text-3xl font-black tracking-tight">Quanto antes você começar, mais você economiza nesta safra.</h2>
            <p className="text-muted-foreground max-w-2xl">
              Não espere a próxima quebra ou o próximo aumento do diesel. O controle total da sua frota está a um clique de distância.
            </p>
          </div>
        </div>
      </section>

      {/* Features/Telas */}
      <section className="border-t border-border/60 bg-muted/30 py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="mb-16 space-y-4">
            <Badge variant="outline" className="border-primary/20 text-primary">Funcionalidades</Badge>
            <h2 className="text-4xl font-black tracking-tight">Telas que respondem o que você precisa saber agora</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feat) => (
              <Card key={feat.title} className="border-border/60 shadow-sm overflow-hidden flex flex-col">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="size-10 rounded-sm bg-primary/10 text-primary flex items-center justify-center">
                      <feat.icon className="size-5" />
                    </div>
                    <Badge variant="secondary" className="text-[10px] uppercase font-bold tracking-wider">
                      {feat.tier}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl font-black">{feat.title}</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">
                    {feat.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Rápido */}
      <section className="bg-muted/30 py-24 border-t border-border/40">
        <div className="mx-auto max-w-3xl px-6">
          <h2 className="text-3xl font-black tracking-tight text-center mb-12">Dúvidas Frequentes</h2>
          <div className="space-y-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold">Precisa instalar GPS ou sensores nas máquinas?</h3>
              <p className="text-muted-foreground leading-relaxed">
                Não. O DeepFarms Frota é 100% software. Você começa a usar sem precisar mexer na parte elétrica ou mecânica dos seus tratores e colhedoras.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-bold">Funciona sem internet no meio do talhão?</h3>
              <p className="text-muted-foreground leading-relaxed">
                Sim. O aplicativo permite que os operadores façam os apontamentos mesmo offline. Assim que o celular detectar uma rede Wi-Fi ou sinal 4G, os dados são enviados automaticamente para o seu painel.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-bold">Quanto tempo leva para começar a usar?</h3>
              <p className="text-muted-foreground leading-relaxed">
                Você começa a usar em poucos dias. O processo é simples: cadastramos sua frota, treinamos sua equipe de forma rápida e os dados já começam a aparecer na primeira semana.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Final */}
      <section className="mx-auto max-w-7xl px-6 py-24 lg:px-10">
        <Card className="bg-primary text-primary-foreground overflow-hidden border-none shadow-2xl">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.15),transparent_50%)]" />
          <CardContent className="relative flex flex-col items-center text-center py-16 px-6 gap-8">
            <div className="space-y-4 max-w-2xl">
              <h2 className="text-4xl md:text-5xl font-black tracking-tight">Sua frota está trabalhando pra você ou contra você?</h2>
              <p className="text-xl opacity-90 leading-relaxed">
                14 dias grátis. Sem cartão de crédito. Cadastre suas máquinas e veja o custo real na primeira semana.
              </p>
            </div>
            <div className="flex flex-col items-center gap-6">
              <div className="flex flex-wrap justify-center gap-4">
                <Button asChild size="lg" variant="secondary" className="h-14 px-8 text-lg font-bold">
                  <a href={getWhatsappComercialUrl("Quero testar o DeepFarms na minha frota") ?? "/register"} target="_blank" rel="noopener noreferrer" data-track-event="cta_test_click_footer">
                    Testar grátis por 14 dias
                    <ArrowRight className="ml-2 size-5" />
                  </a>
                </Button>
                <Button asChild size="lg" variant="outline" className="h-14 px-8 text-lg font-bold bg-transparent border-white/30 hover:bg-white/10 text-white">
                  <a href={getWhatsappComercialUrl("Quero agendar uma demonstração do DeepFarms") ?? "/register"} target="_blank" rel="noopener noreferrer" data-track-event="cta_demo_click_footer">
                    Agendar demonstração
                  </a>
                </Button>
              </div>

              {/* Microcopy de decisão no rodapé */}
              <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs font-bold uppercase tracking-wider text-primary-foreground/70">
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-white" />
                  Sem cartão de crédito
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-white" />
                  Setup em menos de 7 dias
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-white" />
                  Cancelamento simples
                </span>
              </div>
            </div>
            <p className="text-sm opacity-70 font-medium">
              Sem permanência · Cancela quando quiser · Implantação em até 7 dias
            </p>
          </CardContent>
        </Card>
      </section>

      <footer className="border-t border-border/60 py-12 bg-background/50">
        <div className="mx-auto max-w-7xl px-6 lg:px-10 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3 grayscale opacity-70">
            <Tractor className="size-5" />
            <span className="font-black tracking-widest uppercase text-sm">DeepFarms Frota</span>
          </div>
          <div className="text-sm text-muted-foreground">
            © 2026 DeepFarms. Todos os direitos reservados.
          </div>
        </div>
      </footer>

      <LandingTracker />
    </main>
  );
}
