"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, ArrowRight, MessageCircle, ShieldCheck, TrendingUp } from "lucide-react";
import {
    useIAGrowthPlanoRecomendado,
    useIAGrowthPlanoRecomendadoClique,
} from "@/hooks";
import { IACommercialAssistantWidget } from "@/components/ia/ia-commercial-assistant-widget";
import { IncentivoGrowthCard } from "@/components/ia/incentivo-growth-card";

const URGENCIA_BADGE: Record<string, { label: string; className: string }> = {
    ALTA: { label: "Urgência Alta", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400" },
    MEDIA: { label: "Recomendado", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400" },
    BAIXA: { label: "Sugestão", className: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400" },
};

const TIPO_OFERTA_BADGE: Record<string, { label: string; className: string }> = {
    SEM_INCENTIVO: { label: "Recomendado", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400" },
    INCENTIVO_LEVE: { label: "Sugestão", className: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400" },
    INCENTIVO_FORTE: { label: "Oportunidade", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400" },
    EDUCATIVO: { label: "Ajuda", className: "bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400" },
    CONSULTIVO: { label: "Ajuda", className: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900/30 dark:text-slate-300" },
};

export function PlanoRecomendadoCard() {
    const router = useRouter();
    const { data, isLoading } = useIAGrowthPlanoRecomendado();
    const cliqueMut = useIAGrowthPlanoRecomendadoClique();

    if (isLoading) {
        return <Skeleton className="h-[260px] w-full rounded-sm" />;
    }
    if (!data) return null;

    const upgrade = data.plano_recomendado !== data.plano_atual;
    const urgenciaBadge = URGENCIA_BADGE[data.nivel_urgencia] ?? URGENCIA_BADGE.BAIXA;
    const tipoOfertaBadge = TIPO_OFERTA_BADGE[data.tipo_oferta] ?? TIPO_OFERTA_BADGE.CONSULTIVO;

    const handleCtaPrincipal = async () => {
        if (data.log_id) {
            try {
                await cliqueMut.mutateAsync(data.log_id);
            } catch { /* não bloqueia navegação */ }
        }
        router.push(data.cta_url);
    };

    const handleCtaSecundaria = async () => {
        if (!data.cta_secundaria_url) return;
        if (data.log_id) {
            try { await cliqueMut.mutateAsync(data.log_id); } catch { /* idem */ }
        }
        router.push(data.cta_secundaria_url);
    };

    return (
        <Card className="rounded-sm shadow-sm overflow-hidden border-l-4 border-l-emerald-500/70">
            <CardHeader className="pb-3 bg-emerald-50/30 dark:bg-emerald-950/10">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                        <Sparkles size={16} className="text-emerald-600" />
                        <CardTitle className="text-sm font-bold uppercase tracking-wide">
                            Plano recomendado para você
                        </CardTitle>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <Badge variant="outline" className={`text-[10px] rounded-sm ${tipoOfertaBadge.className}`}>
                            {tipoOfertaBadge.label}
                        </Badge>
                        <Badge variant="outline" className={`text-[10px] rounded-sm ${urgenciaBadge.className}`}>
                            {urgenciaBadge.label}
                        </Badge>
                    </div>
                </div>
                <CardDescription className="text-xs mt-1">
                    Análise consultiva — seu plano atual permanece ativo até você decidir.
                </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4 pt-4">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                    <div className="space-y-0.5">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Atualmente</p>
                        <p className="text-sm font-semibold">{data.plano_atual_label}</p>
                    </div>
                    <ArrowRight size={14} className="text-muted-foreground shrink-0" />
                    <div className="space-y-0.5 text-right">
                        <p className="text-[10px] uppercase font-bold text-emerald-600 tracking-wider">Sugerido</p>
                        <p className="text-sm font-bold text-emerald-700 dark:text-emerald-400">{data.plano_recomendado_label}</p>
                    </div>
                    <div className="ml-auto text-right">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Fit</p>
                        <p className="text-sm font-bold tabular-nums">
                            {Math.round((data.score_fit ?? 0) * 100)}%
                        </p>
                    </div>
                </div>

                {data.motivos.length > 0 && (
                    <div className="space-y-1.5">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider flex items-center gap-1.5">
                            <TrendingUp size={11} /> Por que esse plano
                        </p>
                        <ul className="space-y-1 text-xs text-foreground/80">
                            {data.motivos.slice(0, 3).map((m, i) => (
                                <li key={i} className="flex items-start gap-1.5">
                                    <span className="text-emerald-600 mt-1.5 size-1.5 rounded-full bg-emerald-500 shrink-0" />
                                    <span>{m}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {data.mensagem_oferta && (
                    <div className="rounded-sm border border-border/60 bg-muted/20 p-3 space-y-1.5">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Abordagem comercial</p>
                        <p className="text-xs text-foreground/80 leading-relaxed">{data.mensagem_oferta}</p>
                        {data.beneficio_destacado && (
                            <p className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                                Benefício destacado: {data.beneficio_destacado}
                            </p>
                        )}
                    </div>
                )}

                {data.incentivo && (
                    <IncentivoGrowthCard incentivo={data.incentivo} compact />
                )}

                {data.funcionalidades_mais_relevantes.length > 0 && (
                    <div className="space-y-1.5">
                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider flex items-center gap-1.5">
                            <ShieldCheck size={11} /> O que se desbloqueia
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                            {data.funcionalidades_mais_relevantes.slice(0, 5).map((f, i) => (
                                <Badge key={i} variant="secondary" className="text-[10px] rounded-sm font-normal">{f}</Badge>
                            ))}
                        </div>
                    </div>
                )}

                <div className="flex flex-col sm:flex-row gap-2 pt-1">
                    <Button
                        onClick={handleCtaPrincipal}
                        disabled={cliqueMut.isPending}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-sm flex-1 gap-1.5"
                    >
                        {upgrade ? "Ver plano recomendado" : data.cta_label}
                        <ArrowRight size={14} />
                    </Button>
                    {upgrade && (
                        <Button
                            onClick={handleCtaPrincipal}
                            disabled={cliqueMut.isPending}
                            variant="outline"
                            className="text-xs font-bold rounded-sm"
                        >
                            Solicitar upgrade
                        </Button>
                    )}
                    {data.cta_secundaria_url && data.cta_secundaria_label && (
                        <Button
                            onClick={handleCtaSecundaria}
                            disabled={cliqueMut.isPending}
                            variant="ghost"
                            className="text-xs rounded-sm gap-1.5"
                        >
                            <MessageCircle size={14} />
                            {data.cta_secundaria_label}
                        </Button>
                    )}
                </div>

                <div className="flex justify-end">
                    <IACommercialAssistantWidget
                        surface="upgrade-card"
                        compact
                        triggerLabel="Assistente comercial"
                    />
                </div>
            </CardContent>
        </Card>
    );
}
