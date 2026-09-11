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
        <div className="flex min-h-dvh bg-background">

            {/* ── Painel hero (desktop) ─── */}
            <div
                className="hidden lg:flex lg:w-[58%] flex-col relative overflow-hidden rounded-r-sm"
                style={{
                    backgroundImage: "url('/images/login-bg.png')",
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                }}
            >
                <div className="absolute inset-0 bg-gradient-to-br from-black/80 to-primary/20 z-0" />

                {/* Conteúdo sobre a imagem */}
                <div className="relative z-10 flex flex-col justify-between h-full p-14">

                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center rounded-sm bg-white/10 backdrop-blur-sm border border-white/15 shadow-lg">
                            <Image src="/logos/agrosaas-mark.svg" alt="DeepFarms" width={22} height={22} className="opacity-90" />
                        </div>
                        <div>
                            <div className="text-lg font-light uppercase tracking-widest text-white">DeepFarms</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-white/60">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Centro — headline */}
                    <div className="space-y-8 max-w-lg">
                        <div className="space-y-3">
                            <p className="text-[10px] font-medium uppercase tracking-widest text-primary">
                                {badgeLabel}
                            </p>
                            <h1 className="text-5xl font-light text-white leading-[1.1] text-balance">
                                {title}
                            </h1>
                        </div>

                        <p className="text-base text-white/50 leading-relaxed text-pretty">
                            {description}
                        </p>

                        {/* Métricas de confiança */}
                        <div className="grid grid-cols-3 gap-4">
                            {stats.map(({ value, label }) => (
                                <div key={label} className="rounded-sm border border-white/8 bg-white/5 backdrop-blur-sm p-4 space-y-1">
                                    <p className="text-2xl font-light text-white">{value}</p>
                                    <p className="text-[11px] font-medium uppercase tracking-wide text-white/40 leading-tight">{label}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Rodapé */}
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-white/20">© 2026 DeepFarms · Tecnologia de Precisão</p>
                        <p className="text-xs text-white/20">v2.4.1</p>
                    </div>
                </div>
            </div>

            {/* ── Formulário ─── */}
            <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 relative overflow-hidden bg-slate-50/30 dark:bg-transparent">
                
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

                {/* Blobs decorativos sutis */}
                <div className="absolute top-[10%] right-[10%] size-64 bg-primary/10 rounded-full blur-3xl -z-10 animate-pulse" />
                <div className="absolute bottom-[10%] left-[10%] size-96 bg-primary/5 rounded-full blur-3xl -z-10" />

                <div className={`relative w-full ${contentMaxWidthClassName} space-y-8`}>

                    {/* Logo mobile */}
                    <div className="lg:hidden flex items-center gap-3 mb-6">
                        <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 shadow-sm ring-1 ring-primary/20 backdrop-blur-sm">
                            <Image src="/logos/agrosaas-mark.svg" alt="DeepFarms" width={22} height={22} className="opacity-90" />
                        </div>
                        <div>
                            <div className="text-lg font-light uppercase tracking-widest text-primary">DeepFarms</div>
                            <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Gestão rural premium</div>
                        </div>
                    </div>

                    {/* Card do formulário com glassmorphism adaptativo */}
                    <Card className="rounded-sm border-border glass shadow-2xl shadow-primary/5 p-8 overflow-hidden relative">
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
