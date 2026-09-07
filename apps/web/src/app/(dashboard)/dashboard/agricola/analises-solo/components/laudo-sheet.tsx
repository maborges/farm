"use client";

import * as React from "react";
import { SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
    BookOpen, Beaker, BarChart2, TrendingUp, 
    AlertTriangle, CheckCircle2, Droplets, Leaf, Lock
} from "lucide-react";
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer
} from "recharts";

interface AnaliseSolo {
    id: string;
    talhao_id: string;
    data_coleta: string;
    laboratorio?: string;
    ph_agua?: number;
    ph_cacl2?: number;
    materia_organica_pct?: number;
    fosforo_p?: number;
    potassio_k?: number;
    calcio_ca?: number;
    magnesio_mg?: number;
    aluminio_al?: number;
    hidrogenio_al_hal?: number;
    ctc?: number;
    v_pct?: number;
}

interface Recomendacao {
    cultura: string;
    calagem?: {
        necessaria: boolean;
        dose_t_ha: number;
        v_atual_pct: number;
        v_meta_pct: number;
        observacao: string;
    };
    fosforo?: {
        nivel: string;
        label: string;
        rec_p2o5_kg_ha: number;
        observacao: string;
    };
    potassio?: {
        nivel: string;
        label: string;
        rec_k2o_kg_ha: number;
        observacao: string;
    };
    nitrogenio?: {
        rec_n_kg_ha: number;
        observacao: string;
    };
    interpretacoes: {
        ph?: { nivel: string; label: string; cor: string };
        materia_organica?: { nivel: string; label: string };
        fosforo?: { nivel: string; label: string };
        potassio?: { nivel: string; label: string };
    };
}

interface CulturaDisponivel {
    id: string;
    nome: string;
    grupo: string | null;
    sistema: boolean;
    v_meta_pct_padrao: number | null;
}

interface LaudoSheetProps {
    analise: AnaliseSolo | null;
    recomendacao: Recomendacao | null;
    isLoading: boolean;
    talhaoNome: string;
    cultura: string;
    culturas: CulturaDisponivel[];
    onCulturaChange: (id: string, nome: string) => void;
    hasProfessionalTier: boolean;
}

const nivelBadge: Record<string, string> = {
    MUITO_BAIXO: "bg-red-100 text-red-700",
    BAIXO:       "bg-orange-100 text-orange-700",
    MEDIO:       "bg-amber-100 text-amber-700",
    IDEAL:       "bg-green-100 text-green-700",
    ALTO:        "bg-blue-100 text-blue-700",
    MUITO_ALTO:  "bg-purple-100 text-purple-700",
};

function NivelBadge({ nivel, label }: { nivel?: string; label?: string }) {
    if (!nivel || !label) return null;
    return (
        <Badge className={`text-[10px] h-5 px-2 border-none rounded-sm font-bold tracking-tight ${nivelBadge[nivel] ?? "bg-muted"}`}>
            {label}
        </Badge>
    );
}

function Param({ label, value, unit, nivel, nivelLabel }: {
    label: string; value?: number | null; unit: string;
    nivel?: string; nivelLabel?: string;
}) {
    if (value == null) return null;
    return (
        <div className="flex items-center justify-between py-2 border-b border-border/20 last:border-0 hover:bg-muted/50 px-2 rounded-sm transition-colors">
            <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
            <div className="flex items-center gap-2">
                <span className="text-xs font-black tabular-nums">{value.toFixed(2)} {unit}</span>
                {nivel && nivelLabel && <NivelBadge nivel={nivel} label={nivelLabel} />}
            </div>
        </div>
    );
}

const GRUPOS: Record<string, string> = {
    GRAOS: "Grãos",
    FIBRAS: "Fibras",
    FRUTAS: "Frutas",
    HORTALICAS: "Hortaliças",
    PASTAGEM: "Pastagem",
    OUTRO: "Outros",
};

const GRUPOS_ORDEM = ["GRAOS", "FIBRAS", "FRUTAS", "HORTALICAS", "PASTAGEM", "OUTRO"] as const;

const FALLBACK_CULTURAS = [
    { id: "", nome: "Soja", grupo: "GRAOS" },
    { id: "", nome: "Milho", grupo: "GRAOS" },
    { id: "", nome: "Trigo", grupo: "GRAOS" },
    { id: "", nome: "Arroz", grupo: "GRAOS" },
    { id: "", nome: "Feijão", grupo: "GRAOS" },
    { id: "", nome: "Sorgo", grupo: "GRAOS" },
    { id: "", nome: "Algodão", grupo: "FIBRAS" },
    { id: "", nome: "Cana-de-açúcar", grupo: "OUTRO" },
    { id: "", nome: "Café", grupo: "OUTRO" },
    { id: "", nome: "Citros", grupo: "FRUTAS" },
    { id: "", nome: "Banana", grupo: "FRUTAS" },
    { id: "", nome: "Hortaliças", grupo: "HORTALICAS" },
    { id: "", nome: "Pastagem", grupo: "PASTAGEM" },
    { id: "", nome: "Girassol", grupo: "GRAOS" },
    { id: "", nome: "Canola", grupo: "GRAOS" },
    { id: "", nome: "Cevada", grupo: "GRAOS" },
];

function normalizeText(value: string) {
    return value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
}

function CulturaSelect({
    culturas,
    value,
    onChange,
}: {
    culturas: CulturaDisponivel[];
    value: string;
    onChange: (id: string, nome: string) => void;
}) {
    const [search, setSearch] = React.useState("");
    const lista = culturas.length > 0 ? culturas : FALLBACK_CULTURAS;
    const filteredList = React.useMemo(() => {
        if (!search.trim()) return lista;
        const searchTerm = normalizeText(search);
        return lista.filter((cultura) =>
            normalizeText(cultura.nome).includes(searchTerm) ||
            normalizeText(GRUPOS[cultura.grupo ?? "OUTRO"] ?? cultura.grupo ?? "Outros").includes(searchTerm)
        );
    }, [lista, search]);

    const grupos = React.useMemo(() => {
        const grouped = filteredList.reduce<Record<string, typeof lista>>((acc, c) => {
            const g = c.grupo ?? "OUTRO";
            if (!acc[g]) acc[g] = [];
            acc[g].push(c as typeof lista[0]);
            return acc;
        }, {});

        return Object.entries(grouped).sort(([grupoA], [grupoB]) => {
            const indexA = GRUPOS_ORDEM.indexOf(grupoA as typeof GRUPOS_ORDEM[number]);
            const indexB = GRUPOS_ORDEM.indexOf(grupoB as typeof GRUPOS_ORDEM[number]);
            const ordemA = indexA === -1 ? Number.MAX_SAFE_INTEGER : indexA;
            const ordemB = indexB === -1 ? Number.MAX_SAFE_INTEGER : indexB;
            return ordemA - ordemB;
        });
    }, [filteredList]);

    const activeCultura = lista.find(c => c.id === value || c.nome === value);
    const activeValue = activeCultura ? (activeCultura.id || activeCultura.nome) : value;

    return (
        <Select
            value={activeValue}
            onValueChange={(val: string) => {
                const c = lista.find(x => (x.id || x.nome) === val);
                if (c) onChange(c.id, c.nome);
            }}
        >
            <SelectTrigger className="w-56 bg-white dark:bg-background">
                <SelectValue placeholder={activeCultura?.nome || "Selecionar cultura"} />
            </SelectTrigger>
            <SelectContent>
                <div className="sticky top-0 z-10 border-b bg-sidebar p-2">
                    <input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Buscar cultura..."
                        className="h-8 w-full rounded-sm border border-sidebar-border bg-background px-2 text-xs outline-none focus:border-primary/50"
                    />
                </div>
                {grupos.length === 0 && (
                    <div className="px-3 py-3 text-xs text-muted-foreground">
                        Nenhuma cultura encontrada.
                    </div>
                )}
                {grupos.map(([grupo, items]) => (
                    <SelectGroup key={grupo}>
                        <div className="px-2 py-1.5 text-[9px] uppercase tracking-widest text-muted-foreground font-bold">
                            {GRUPOS[grupo] ?? grupo}
                        </div>
                        {items.map((c) => (
                            <SelectItem
                                key={c.id || c.nome}
                                value={c.id || c.nome}
                                className="text-xs"
                            >
                                {c.nome}
                            </SelectItem>
                        ))}
                    </SelectGroup>
                ))}
            </SelectContent>
        </Select>
    );
}

export function LaudoSheet({
    analise,
    recomendacao,
    isLoading,
    talhaoNome,
    cultura,
    culturas,
    onCulturaChange,
    hasProfessionalTier,
}: LaudoSheetProps) {
    if (!analise) return null;

    const radarData = [
        { subject: "pH",  value: Math.min(100, ((analise.ph_agua ?? 0) / 7) * 100) },
        { subject: "V%",  value: analise.v_pct ?? 0 },
        { subject: "P",   value: Math.min(100, ((analise.fosforo_p ?? 0) / 60) * 100) },
        { subject: "K",   value: Math.min(100, ((analise.potassio_k ?? 0) / 200) * 100) },
        { subject: "M.O.", value: Math.min(100, ((analise.materia_organica_pct ?? 0) / 5) * 100) },
    ];

    const phInterp = analise.ph_agua != null
        ? (analise.ph_agua < 4.5 ? { nivel: "MUITO_BAIXO", label: "Muito Ácido" }
         : analise.ph_agua < 5.5 ? { nivel: "BAIXO",       label: "Ácido" }
         : analise.ph_agua < 6.5 ? { nivel: "IDEAL",        label: "Adequado" }
         : analise.ph_agua < 7.5 ? { nivel: "ALTO",         label: "Alcalino" }
         :                         { nivel: "MUITO_ALTO",   label: "Muito Alcalino" })
        : null;

    return (
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto border-l shadow-2xl">
            <SheetHeader className="mb-6 px-5 sm:px-6 pt-6 pb-0">
                <div className="flex items-center gap-2">
                    <div className="size-10 bg-primary/10 rounded-sm flex items-center justify-center text-primary">
                        <BookOpen size={20} />
                    </div>
                    <div>
                        <SheetTitle className="text-xl font-black tracking-tight">Laudo Digital de Solo</SheetTitle>
                        <SheetDescription className="text-[11px] font-bold uppercase tracking-widest text-primary/70">
                            Talhão: {talhaoNome} · {new Date(analise.data_coleta).toLocaleDateString("pt-BR")}
                        </SheetDescription>
                    </div>
                </div>
            </SheetHeader>

            <div className="flex flex-col px-5 sm:px-6">
                {/* Parâmetros químicos */}
                <section className="pb-8">
                    <h3 className="text-[10px] font-black uppercase text-muted-foreground mb-3 flex items-center gap-1.5 tracking-tighter">
                        <Beaker size={12} className="text-primary" /> Análise Química Detalhada
                    </h3>
                    <div className="bg-muted/30 rounded-sm p-4 border border-border/40">
                        <Param label="pH (H₂O)" value={analise.ph_agua} unit=""
                            nivel={phInterp?.nivel} nivelLabel={phInterp?.label} />
                        <Param label="Matéria Orgânica" value={analise.materia_organica_pct} unit="%" />
                        <Param label="Fósforo (P)" value={analise.fosforo_p} unit="mg/dm³"
                            nivel={recomendacao?.interpretacoes.fosforo?.nivel}
                            nivelLabel={recomendacao?.interpretacoes.fosforo?.label} />
                        <Param label="Potássio (K)" value={analise.potassio_k} unit="mg/dm³"
                            nivel={recomendacao?.interpretacoes.potassio?.nivel}
                            nivelLabel={recomendacao?.interpretacoes.potassio?.label} />
                        <Param label="Cálcio (Ca)" value={analise.calcio_ca} unit="cmolc/dm³" />
                        <Param label="Magnésio (Mg)" value={analise.magnesio_mg} unit="cmolc/dm³" />
                        <Param label="Alumínio (Al)" value={analise.aluminio_al} unit="cmolc/dm³" />
                        <Param label="V% (Saturação bases)" value={analise.v_pct} unit="%" />
                    </div>
                </section>

                {/* Radar Plot */}
                <section className="py-8 border-t border-border/40">
                    <h3 className="text-[10px] font-black uppercase text-muted-foreground mb-4 flex items-center gap-1.5 tracking-tighter">
                        <BarChart2 size={12} className="text-primary" /> Equilíbrio Mineral (Relação Real / Ideal)
                    </h3>
                    <div className="h-[240px] bg-emerald-50/20 dark:bg-emerald-950/5 rounded-sm flex items-center justify-center border border-emerald-100/50 dark:border-emerald-900/20">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                                <PolarGrid strokeOpacity={0.1} />
                                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))", fontWeight: 700 }} />
                                <Radar
                                    name="Perfil"
                                    dataKey="value"
                                    stroke="hsl(var(--primary))"
                                    fill="hsl(var(--primary))"
                                    fillOpacity={0.3}
                                    strokeWidth={3}
                                />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </section>

                {/* Recomendações Section */}
                <section className="space-y-4 py-8 border-t border-border/40 pb-10">
                    <div className="flex items-center justify-between">
                        <h3 className="text-[10px] font-black uppercase text-muted-foreground flex items-center gap-1.5 tracking-tighter">
                            <TrendingUp size={12} className="text-primary" /> Prescrição Técnica Agronômica
                        </h3>
                        {/* Selector dinâmico de culturas */}
                        <CulturaSelect
                            culturas={culturas}
                            value={cultura}
                            onChange={onCulturaChange}
                        />
                    </div>

                    {!hasProfessionalTier ? (
                        <Alert className="rounded-sm">
                            <Lock className="size-4" />
                            <AlertTitle>Prescrição técnica disponível no PROFISSIONAL</AlertTitle>
                            <AlertDescription className="space-y-3">
                                <p>
                                    O plano atual mantém a leitura da análise de solo. Recomendações agronômicas automáticas exigem tier PROFISSIONAL.
                                </p>
                                <Button asChild size="sm" className="rounded-sm">
                                    <Link href="/dashboard/settings/billing">Ver planos</Link>
                                </Button>
                            </AlertDescription>
                        </Alert>
                    ) : isLoading ? (
                        <div className="space-y-3">
                            <Skeleton className="h-24 w-full rounded-sm" />
                            <Skeleton className="h-24 w-full rounded-sm" />
                        </div>
                    ) : recomendacao ? (
                        <div className="space-y-3">
                            {/* Calagem */}
                            {recomendacao.calagem && (
                                <div className={`p-4 rounded-sm border-l-4 ${recomendacao.calagem.necessaria ? "bg-red-50/50 dark:bg-red-950/10 border-red-500" : "bg-emerald-50/50 dark:bg-emerald-950/10 border-emerald-500 shadow-sm"}`}>
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className={`size-6 rounded-full flex items-center justify-center ${recomendacao.calagem.necessaria ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"}`}>
                                            {recomendacao.calagem.necessaria ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                                        </div>
                                        <p className="font-black text-sm uppercase tracking-tight">
                                            {recomendacao.calagem.necessaria ? "Necessário Corrigir Acidez (Calagem)" : "Status de Acidez: Adequado"}
                                        </p>
                                    </div>
                                    <p className="text-[11px] text-muted-foreground leading-relaxed italic">{recomendacao.calagem.observacao}</p>
                                    {recomendacao.calagem.necessaria && (
                                        <div className="mt-4 flex items-center justify-between bg-white dark:bg-background p-2 rounded-sm border border-red-100 dark:border-red-900/30 shadow-xs">
                                            <div>
                                                <p className="text-[9px] font-black text-muted-foreground uppercase">Dose Recomendada</p>
                                                <p className="text-xl font-black text-red-600">{recomendacao.calagem.dose_t_ha.toFixed(2)} <span className="text-[10px] text-muted-foreground">t/ha (PRNT 100%)</span></p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-[9px] font-black text-muted-foreground uppercase">V% Meta</p>
                                                <p className="text-sm font-bold text-red-700">{recomendacao.calagem.v_meta_pct}%</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Fósforo */}
                            {recomendacao.fosforo && (
                                <div className="p-4 rounded-sm border bg-muted/20 border-border/40 group hover:border-blue-500/30 transition-colors">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Droplets size={14} className="text-blue-500" />
                                        <p className="font-black text-xs uppercase tracking-tight">Fósforo (P₂O₅)</p>
                                        <NivelBadge nivel={recomendacao.fosforo.nivel} label={recomendacao.fosforo.label} />
                                    </div>
                                    <p className="text-[11px] text-muted-foreground leading-relaxed mb-3">{recomendacao.fosforo.observacao}</p>
                                    <div className="flex items-center justify-between bg-blue-50/50 dark:bg-blue-950/20 p-2 rounded-sm">
                                        <span className="text-[10px] font-bold text-blue-700 uppercase">Adubação Sugerida</span>
                                        <span className="text-sm font-black text-blue-700">{recomendacao.fosforo.rec_p2o5_kg_ha} <span className="text-[9px]">kg/ha</span></span>
                                    </div>
                                </div>
                            )}

                            {/* Potássio */}
                            {recomendacao.potassio && (
                                <div className="p-4 rounded-sm border bg-muted/20 border-border/40 group hover:border-amber-500/30 transition-colors">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Leaf size={14} className="text-amber-500" />
                                        <p className="font-black text-xs uppercase tracking-tight">Potássio (K₂O)</p>
                                        <NivelBadge nivel={recomendacao.potassio.nivel} label={recomendacao.potassio.label} />
                                    </div>
                                    <p className="text-[11px] text-muted-foreground leading-relaxed mb-3">{recomendacao.potassio.observacao}</p>
                                    <div className="flex items-center justify-between bg-amber-50/50 dark:bg-amber-950/20 p-2 rounded-sm">
                                        <span className="text-[10px] font-bold text-amber-700 uppercase">Adubação Sugerida</span>
                                        <span className="text-sm font-black text-amber-700">{recomendacao.potassio.rec_k2o_kg_ha} <span className="text-[9px]">kg/ha</span></span>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : null}
                </section>
            </div>
        </SheetContent>
    );
}
