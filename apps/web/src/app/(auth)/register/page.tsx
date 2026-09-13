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
        <div
            className="relative flex min-h-dvh overflow-hidden bg-slate-100 dark:bg-slate-950"
            style={{
                backgroundImage: "url('/images/deepfarms-hero.webp')",
                backgroundSize: "cover",
                backgroundPosition: "center",
            }}
        >
            <div className="absolute inset-0 z-0 bg-white/40 dark:bg-slate-950/55" />

            {/* ── Painel hero (desktop) ─── */}
            <div className="relative hidden flex-col overflow-hidden bg-transparent lg:flex lg:w-[58%]">

                <div className="relative z-10 flex flex-col justify-between h-full p-14">

                    {/* Logo */}
                    <div className="inline-flex items-center gap-4 rounded-sm border border-primary/20 bg-white/45 px-4 py-3 shadow-sm backdrop-blur-sm dark:border-white/15 dark:bg-white/8">
                        <div className="flex size-14 shrink-0 items-center justify-center">
                            <Image src="/logos/deepfarms-mark.svg" alt="DeepFarms" width={56} height={56} className="size-full object-contain dark:hidden" />
                            <Image src="/logos/deepfarms-mark-negative.svg" alt="DeepFarms" width={56} height={56} className="hidden size-full object-contain dark:block" />
                        </div>
                        <div>
                            <div className="text-xl font-semibold uppercase tracking-[0.18em] text-slate-950 dark:text-white">DeepFarms</div>
                            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600 dark:text-white/65">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Headline */}
                    <div className="space-y-10 max-w-md">
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                                Solicitar Acesso
                            </p>
                            <h1 className="text-5xl font-light text-slate-950 leading-[1.1] text-balance dark:text-white">
                                A nova era da{" "}
                                <span className="text-primary font-semibold">
                                    produtividade
                                </span>{" "}
                                rural.
                            </h1>
                            <p className="text-base text-slate-700 leading-relaxed text-pretty dark:text-white/50">
                                Crie sua conta e comece a gerir sua fazenda com dados
                                reais, mapas precisos e controle total de insumos.
                            </p>
                        </div>

                        {/* Steps de onboarding */}
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-600 mb-4 dark:text-white/30">
                                Como funciona
                            </p>
                            {STEPS.map(({ step, title, desc }) => (
                                <div key={step} className="flex items-start gap-4">
                                    <div className="flex size-9 shrink-0 items-center justify-center rounded-sm border border-primary/30 bg-primary/10 text-primary text-xs font-semibold">
                                        {step}
                                    </div>
                                    <div>
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white/80">{title}</p>
                                        <p className="text-xs text-slate-600 dark:text-white/35">{desc}</p>
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
                        <p className="text-xs text-slate-500 dark:text-white/20">© 2026 DeepFarms · Tecnologia de Precisão</p>
                        <p className="text-xs text-slate-500 dark:text-white/20">v2.4.1</p>
                    </div>
                </div>
            </div>

            {/* ── Formulário ─── */}
            <div className="relative z-10 flex flex-1 flex-col items-center justify-center overflow-y-auto px-6 py-8 lg:py-12">

                {/* Watermark Logo */}
                <div 
                    className="absolute inset-0 z-0 opacity-5 dark:opacity-10 pointer-events-none"
                    style={{
                        backgroundImage: "url('/logos/deepfarms-mark.svg')",
                        backgroundSize: "60%",
                        backgroundRepeat: "no-repeat",
                        backgroundPosition: "center",
                    }}
                />

                <div className="relative w-full max-w-[560px] space-y-6">

                    {/* Logo mobile */}
                    <div className="lg:hidden inline-flex items-center justify-center gap-4 mb-4 rounded-sm border border-primary/20 bg-white/45 px-4 py-3 shadow-sm backdrop-blur-sm dark:border-white/15 dark:bg-white/8">
                        <div className="flex size-14 shrink-0 items-center justify-center">
                            <Image src="/logos/deepfarms-mark.svg" alt="DeepFarms" width={56} height={56} className="size-full object-contain" />
                        </div>
                        <div className="text-left">
                            <div className="text-xl font-semibold uppercase tracking-[0.18em] text-primary">DeepFarms</div>
                            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Card glassmorphism adaptativo */}
                    <div className="rounded-sm border border-slate-900/10 bg-white/65 p-6 text-slate-900 shadow-2xl shadow-black/10 backdrop-blur-sm [&_label]:text-slate-800 [&_p]:text-slate-700 [&_input]:border-slate-400/50 [&_input]:bg-white/45 [&_input]:text-slate-900 [&_input]:placeholder:text-slate-600/60 dark:border-white/8 dark:bg-white/5 dark:shadow-black/20 dark:text-slate-100 dark:[&_label]:text-slate-200 dark:[&_p]:text-slate-300 dark:[&_input]:border-white/20 dark:[&_input]:bg-white/10 dark:[&_input]:text-white dark:[&_input]:placeholder:text-white/50 lg:p-8">
                        <RegisterForm />
                    </div>

                    <p className="text-center text-xs text-muted-foreground/30">
                        © 2026 DeepFarms · Tecnologia de Precisão
                    </p>
                </div>
            </div>
        </div>
    );
}
