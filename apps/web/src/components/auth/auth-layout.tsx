import Image from "next/image";
import type { ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";

interface AuthLayoutStep {
    step: string;
    title: string;
    desc: string;
}

interface AuthLayoutHighlightNotice {
    title: string;
    text: ReactNode;
}

interface AuthLayoutProps {
    children: ReactNode;
    badgeLabel?: string;
    title?: ReactNode;
    description?: string;
    stats?: Array<{ value: string; label: string }>;
    steps?: AuthLayoutStep[];
    highlightNotice?: AuthLayoutHighlightNotice;
    guaranteeText?: string;
    contentMaxWidthClassName?: string;
    cardClassName?: string;
}

const defaultStats = [
    { value: "256-bit", label: "Criptografia SSL" },
    { value: "99.9%", label: "Uptime garantido" },
    { value: "24/7", label: "Suporte dedicado" },
];

export function AuthLayout({
    children,
    badgeLabel = "Acesso seguro",
    title = "Proteja sua conta com segurança.",
    description = "Acesse sua plataforma com autenticação segura e contexto multiempresa em tempo real.",
    stats = defaultStats,
    steps,
    highlightNotice,
    guaranteeText,
    contentMaxWidthClassName = "max-w-[500px]",
    cardClassName = "p-7 lg:p-8",
}: AuthLayoutProps) {
    return (
        <div
            className="relative flex min-h-dvh lg:h-dvh overflow-x-hidden lg:overflow-hidden bg-slate-100 dark:bg-slate-950"
            style={{
                backgroundImage: "url('/images/deepfarms-hero.webp')",
                backgroundSize: "cover",
                backgroundPosition: "center",
            }}
        >
            <div className="absolute inset-0 z-0 bg-white/40 dark:bg-slate-950/55" />

            {/* ── Painel hero à esquerda (sem linha divisória, ocupando 42%–44% no desktop) ─── */}
            <div className="relative hidden flex-col overflow-hidden bg-transparent lg:flex lg:w-[42%] xl:w-[44%] shrink-0">
                <div className="relative z-10 flex flex-col justify-between h-full p-10 xl:p-12">
                    {/* Logo */}
                    <div className="inline-flex items-center gap-4 rounded-sm border border-primary/20 bg-white/45 px-4 py-3 shadow-sm backdrop-blur-sm w-fit dark:border-white/15 dark:bg-white/8">
                        <div className="flex size-14 shrink-0 items-center justify-center">
                            <Image
                                src="/logos/deepfarms-mark.svg"
                                alt="DeepFarms"
                                width={56}
                                height={56}
                                className="size-full object-contain dark:hidden"
                            />
                            <Image
                                src="/logos/deepfarms-mark-negative.svg"
                                alt="DeepFarms"
                                width={56}
                                height={56}
                                className="hidden size-full object-contain dark:block"
                            />
                        </div>
                        <div>
                            <div className="text-xl font-semibold uppercase tracking-[0.18em] text-slate-950 dark:text-white">
                                DeepFarms
                            </div>
                            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600 dark:text-white/65">
                                Gestão rural premium
                            </div>
                        </div>
                    </div>

                    {/* Centro — headline + steps ou métricas */}
                    <div className="space-y-6 max-w-lg my-auto py-4">
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                                {badgeLabel}
                            </p>
                            <h1 className="text-4xl xl:text-5xl font-light text-slate-950 leading-[1.1] text-balance dark:text-white">
                                {title}
                            </h1>
                            <p className="text-sm xl:text-base text-slate-700 leading-relaxed text-pretty dark:text-white/50">
                                {description}
                            </p>
                        </div>

                        {steps && steps.length > 0 ? (
                            <div className="space-y-3">
                                <p className="text-[10px] font-medium uppercase tracking-widest text-slate-600 dark:text-white/30">
                                    Como funciona
                                </p>
                                {steps.map(({ step, title: stepTitle, desc }) => (
                                    <div key={step} className="flex items-start gap-3.5">
                                        <div className="flex size-8 shrink-0 items-center justify-center rounded-sm border border-primary/30 bg-primary/10 text-primary text-xs font-semibold">
                                            {step}
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-800 dark:text-white/80">
                                                {stepTitle}
                                            </p>
                                            <p className="text-xs text-slate-600 dark:text-white/35">
                                                {desc}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 gap-3.5">
                                {stats.map(({ value, label }) => (
                                    <div
                                        key={label}
                                        className="rounded-sm border border-slate-900/10 bg-white/35 backdrop-blur-sm p-3.5 space-y-1 dark:border-white/8 dark:bg-white/5"
                                    >
                                        <p className="text-xl xl:text-2xl font-light text-slate-950 dark:text-white">
                                            {value}
                                        </p>
                                        <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600 leading-tight dark:text-white/40">
                                            {label}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        )}

                        {highlightNotice && (
                            <div className="rounded-sm border border-primary/20 bg-white/40 dark:bg-white/5 p-3.5 space-y-1 backdrop-blur-sm">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                                    {highlightNotice.title}
                                </p>
                                <div className="text-xs text-slate-700 dark:text-white/60 leading-relaxed">
                                    {highlightNotice.text}
                                </div>
                            </div>
                        )}

                        {guaranteeText && (
                            <div className="flex items-center gap-3 rounded-sm border border-primary/15 bg-primary/10 px-4 py-2.5">
                                <CheckCircle2 className="size-4 text-primary shrink-0" />
                                <p className="text-xs xl:text-sm text-primary/80 leading-snug">
                                    {guaranteeText}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Rodapé */}
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-slate-500 dark:text-white/20">
                            © 2026 DeepFarms · Tecnologia de Precisão
                        </p>
                        <p className="text-xs text-slate-500 dark:text-white/20">v2.4.1</p>
                    </div>
                </div>
            </div>

            {/* ── Área de Dados à Direita (56%–58% no desktop, com transparência glassmorphism original) ─── */}
            <div className="relative z-10 flex flex-1 flex-col items-center justify-center overflow-y-auto lg:overflow-hidden px-5 py-6 lg:px-8 lg:py-6">
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

                {/* Blobs decorativos sutis */}
                <div className="absolute top-[10%] right-[10%] size-64 bg-primary/10 rounded-full blur-3xl -z-10 animate-pulse" />
                <div className="absolute bottom-[10%] left-[10%] size-96 bg-primary/5 rounded-full blur-3xl -z-10" />

                <div className={`relative w-full ${contentMaxWidthClassName} space-y-3`}>
                    {/* Logo mobile */}
                    <div className="lg:hidden inline-flex items-center gap-4 mb-3 rounded-sm border border-primary/20 bg-white/45 px-4 py-3 shadow-sm backdrop-blur-sm dark:border-white/15 dark:bg-white/8">
                        <div className="flex size-12 shrink-0 items-center justify-center">
                            <Image
                                src="/logos/deepfarms-mark.svg"
                                alt="DeepFarms"
                                width={48}
                                height={48}
                                className="size-full object-contain"
                            />
                        </div>
                        <div>
                            <div className="text-lg font-semibold uppercase tracking-[0.18em] text-primary">
                                DeepFarms
                            </div>
                            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                Gestão rural premium
                            </div>
                        </div>
                    </div>

                    {/* Card do formulário com a transparência glassmorphism original */}
                    <Card
                        className={`relative overflow-hidden rounded-sm border-slate-900/10 bg-white/65 ${cardClassName} text-slate-900 shadow-2xl shadow-black/10 backdrop-blur-sm [&_label]:text-slate-800 [&_p]:text-slate-700 [&_input]:border-slate-400/50 [&_input]:bg-white/45 [&_input]:text-slate-900 [&_input]:placeholder:text-slate-600/60 dark:border-white/8 dark:bg-white/5 dark:shadow-black/20 dark:text-slate-100 dark:[&_label]:text-slate-200 dark:[&_p]:text-slate-300 dark:[&_input]:border-white/20 dark:[&_input]:bg-white/10 dark:[&_input]:text-white dark:[&_input]:placeholder:text-white/50`}
                    >
                        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
                        {children}
                    </Card>

                    <p className="text-center text-xs text-muted-foreground/30 font-semibold tracking-wider uppercase">
                        Protegido por criptografia end-to-end · SOC 2 Type II
                    </p>
                </div>
            </div>
        </div>
    );
}
