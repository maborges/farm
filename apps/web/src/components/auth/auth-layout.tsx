import Image from "next/image";
import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

interface AuthLayoutProps {
    children: ReactNode;
    badgeLabel?: string;
    title?: string;
    description?: string;
    stats?: Array<{ value: string; label: string }>;
    contentMaxWidthClassName?: string;
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
    contentMaxWidthClassName = "max-w-[420px]",
}: AuthLayoutProps) {
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

                {/* Conteúdo sobre a imagem */}
                <div className="relative z-10 flex flex-col justify-between h-full p-14">

                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center">
                            <Image src="/logos/deepfarms-mark.svg" alt="DeepFarms" width={40} height={40} className="size-full object-contain dark:hidden" />
                            <Image src="/logos/deepfarms-mark-negative.svg" alt="DeepFarms" width={40} height={40} className="hidden size-full object-contain dark:block" />
                        </div>
                        <div>
                            <div className="text-lg font-light uppercase tracking-widest text-slate-950 dark:text-white">DeepFarms</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-slate-600 dark:text-white/60">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Centro — headline */}
                    <div className="space-y-8 max-w-lg">
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                                {badgeLabel}
                            </p>
                            <h1 className="text-5xl font-light text-slate-950 leading-[1.1] text-balance dark:text-white">
                                {title}
                            </h1>
                        </div>

                        <p className="text-base text-slate-700 leading-relaxed text-pretty dark:text-white/50">
                            {description}
                        </p>

                        {/* Métricas de confiança */}
                        <div className="grid grid-cols-3 gap-4">
                            {stats.map(({ value, label }) => (
                                <div key={label} className="rounded-sm border border-slate-900/10 bg-white/35 backdrop-blur-sm p-4 space-y-1 dark:border-white/8 dark:bg-white/5">
                                    <p className="text-2xl font-light text-slate-950 dark:text-white">{value}</p>
                                    <p className="text-[11px] font-medium uppercase tracking-wide text-slate-600 leading-tight dark:text-white/40">{label}</p>
                                </div>
                            ))}
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
            <div className="relative z-10 flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-12">
                
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

                <div className={`relative w-full ${contentMaxWidthClassName} space-y-8`}>

                    {/* Logo mobile */}
                    <div className="lg:hidden flex items-center gap-3 mb-6">
                        <div className="flex size-10 items-center justify-center">
                            <Image src="/logos/deepfarms-mark.svg" alt="DeepFarms" width={40} height={40} className="size-full object-contain" />
                        </div>
                        <div>
                            <div className="text-lg font-light uppercase tracking-widest text-primary">DeepFarms</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Card do formulário com glassmorphism adaptativo */}
                    <Card className="relative overflow-hidden rounded-sm border-slate-900/10 bg-white/65 p-8 text-slate-900 shadow-2xl shadow-black/10 backdrop-blur-sm [&_label]:text-slate-800 [&_p]:text-slate-700 [&_input]:border-slate-400/50 [&_input]:bg-white/45 [&_input]:text-slate-900 [&_input]:placeholder:text-slate-600/60 dark:border-white/8 dark:bg-white/5 dark:shadow-black/20 dark:text-slate-100 dark:[&_label]:text-slate-200 dark:[&_p]:text-slate-300 dark:[&_input]:border-white/20 dark:[&_input]:bg-white/10 dark:[&_input]:text-white dark:[&_input]:placeholder:text-white/50">
                        {/* Overlay de brilho sutil no topo do card */}
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
