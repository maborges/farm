import { RegisterForm } from "@/components/auth/register-form";
import { CheckCircle2 } from "lucide-react";
import Image from "next/image";

const STEPS = [
    { step: "01", title: "Crie sua conta", desc: "Dados pessoais e de acesso" },
    { step: "02", title: "Sua propriedade", desc: "Cadastro da fazenda e CNPJ" },
    { step: "03", title: "Comece a gerir", desc: "Dashboard pronto em segundos" },
];

export default function RegisterPage() {
    return (
        <div className="flex min-h-dvh bg-background">

            {/* ── Painel hero (desktop) ─── */}
            <div
                className="hidden lg:flex lg:w-[58%] flex-col relative overflow-hidden rounded-r-lg"
                style={{
                    backgroundImage: "url('/images/login-bg.png')",
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                }}
            >
                <div className="absolute inset-0 bg-gradient-to-br from-black/80 to-primary/20 z-0" />

                <div className="relative z-10 flex flex-col justify-between h-full p-14">

                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center rounded-sm bg-white/10 backdrop-blur-sm border border-white/15 shadow-lg">
                            <Image src="/logos/agrosaas-mark.svg" alt="AgroSaaS" width={22} height={22} className="opacity-90" />
                        </div>
                        <div>
                            <div className="text-lg font-light uppercase tracking-widest text-white">AgroSaaS</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-white/60">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Headline */}
                    <div className="space-y-10 max-w-md">
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                                Solicitar Acesso
                            </p>
                            <h1 className="text-5xl font-light text-white leading-[1.1] text-balance">
                                A nova era da{" "}
                                <span className="text-primary font-semibold">
                                    produtividade
                                </span>{" "}
                                rural.
                            </h1>
                            <p className="text-base text-white/50 leading-relaxed text-pretty">
                                Crie sua conta e comece a gerir sua fazenda com dados
                                reais, mapas precisos e controle total de insumos.
                            </p>
                        </div>

                        {/* Steps de onboarding */}
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-white/30 mb-4">
                                Como funciona
                            </p>
                            {STEPS.map(({ step, title, desc }) => (
                                <div key={step} className="flex items-start gap-4">
                                    <div className="flex size-9 shrink-0 items-center justify-center rounded-sm border border-primary/30 bg-primary/10 text-primary text-xs font-semibold">
                                        {step}
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-white/80">{title}</p>
                                        <p className="text-xs text-white/35">{desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Garantia */}
                        <div className="flex items-center gap-3 rounded-lg border border-primary/15 bg-primary/10 px-4 py-3">
                            <CheckCircle2 className="size-5 text-primary shrink-0" />
                            <p className="text-sm text-primary/80 leading-snug">
                                Sem cartão de crédito · 14 dias grátis · Cancele quando quiser
                            </p>
                        </div>
                    </div>

                    {/* Rodapé */}
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-white/20">© 2026 AgroSaaS · Tecnologia de Precisão</p>
                        <p className="text-xs text-white/20">v2.4.1</p>
                    </div>
                </div>
            </div>

            {/* ── Formulário ─── */}
            <div className="flex flex-1 flex-col items-center justify-center px-6 py-8 lg:py-12 relative overflow-y-auto">

                {/* Watermark Logo */}
                <div 
                    className="absolute inset-0 z-0 opacity-5 dark:opacity-10 pointer-events-none"
                    style={{
                        backgroundImage: "url('/logos/agrosaas-mark.svg')",
                        backgroundSize: "60%",
                        backgroundRepeat: "no-repeat",
                        backgroundPosition: "center",
                    }}
                />

                <div className="relative w-full max-w-[560px] space-y-6">

                    {/* Logo mobile */}
                    <div className="lg:hidden flex items-center justify-center gap-3 mb-4">
                        <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 shadow-sm ring-1 ring-primary/20 backdrop-blur-sm">
                            <Image src="/logos/agrosaas-mark.svg" alt="AgroSaaS" width={22} height={22} className="opacity-90" />
                        </div>
                        <div className="text-left">
                            <div className="text-lg font-light uppercase tracking-widest text-primary">AgroSaaS</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Card glassmorphism adaptativo */}
                    <div className="rounded-sm border border-border bg-card/50 backdrop-blur-xl shadow-2xl shadow-black/10 p-6 lg:p-8">
                        <RegisterForm />
                    </div>

                    <p className="text-center text-xs text-muted-foreground/30">
                        © 2026 AgroSaaS · Tecnologia de Precisão
                    </p>
                </div>
            </div>
        </div>
    );
}
