"use client";

import Link from "next/link";
import { useState } from "react";
import { Activity, AlertCircle, BarChart3, LineChart, ShieldAlert, Sparkles, Target, TrendingUp, WandSparkles } from "lucide-react";
import { useAppStore } from "@/lib/stores/app-store";
import { Sprout, Plus, X, Loader2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useHasTier } from "@/hooks/use-has-tier";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { MinhasPendenciasChecklist } from "@/components/agricola/minhas-pendencias-checklist";

interface SafraCreate {
    talhao_ids: string[];
    ano_safra: string;
    cultura: string;
    data_plantio_prevista?: string;
    produtividade_meta_sc_ha?: number;
    status: string;
}

type Safra = {
    id: string;
    ano_safra: string;
    cultura: string;
    talhao_id: string;
    produtividade_meta_sc_ha?: number;
    status: string;
    area_plantada_ha?: number;
};

const createSafraColumns = (getTalhaoNome: (id: string) => string): ColumnDef<Safra>[] => [
    {
        id: "ano_safra",
        header: "Safra",
        accessorKey: "ano_safra",
        sortable: true,
        cell: (value) => <span className="font-bold tabular-nums">{value}</span>,
    },
    {
        id: "cultura",
        header: "Cultura",
        accessorKey: "cultura",
        sortable: true,
        filterable: true,
        cell: (value) => <Badge variant="secondary" className="font-semibold text-xs">{value}</Badge>,
    },
    {
        id: "talhao_id",
        header: "Talhão",
        accessorKey: "talhao_id",
        sortable: false,
        cell: (value) => <span className="text-sm font-medium">{getTalhaoNome(String(value))}</span>,
    },
    {
        id: "produtividade_meta_sc_ha",
        header: "Meta (sc/ha)",
        accessorKey: "produtividade_meta_sc_ha",
        sortable: true,
        cell: (value) => <span className="font-bold tabular-nums text-right">{value ?? "—"}</span>,
    },
    {
        id: "status",
        header: "Status",
        accessorKey: "status",
        sortable: true,
        cell: (value: string) => (
            <Badge className={
                value === "EM_ANDAMENTO"
                    ? "bg-[var(--module-agro-bg)] text-[var(--module-agro)] border-[var(--module-agro)]/20"
                    : "bg-[var(--module-operacional-bg)] text-[var(--module-operacional)] border-[var(--module-operacional)]/20"
            }>
                {value.replace("_", " ")}
            </Badge>
        ),
    },
];

function NovaSafraModal({ fazendaId, onClose }: { fazendaId: string; onClose: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<SafraCreate>({
        talhao_ids: [],
        ano_safra: "2024/2025",
        cultura: "Soja",
        status: "PLANEJADA",
    });

    const { data: talhoes = [] } = useQuery({
        queryKey: ["talhoes", fazendaId],
        queryFn: () => apiFetch<any[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${fazendaId}`),
        enabled: !!fazendaId,
    });

    const { data: culturas = [] } = useQuery({
        queryKey: ["culturas"],
        queryFn: () => apiFetch<any[]>("/cadastros/culturas"),
    });

    const safraColumns = createSafraColumns(
        (id) => talhoes.find((talhao: any) => talhao.id === id)?.nome ?? "Talhão não informado"
    );

    const mutation = useMutation({
        mutationFn: (payload: SafraCreate) =>
            apiFetch("/safras/", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            toast.success("Safra planejada com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["safras"] });
            onClose();
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao criar safra."),
    });

    const toggleTalhao = (talhaoid: string) => {
        const current = form.talhao_ids || [];
        if (current.includes(talhaoid)) {
            setForm(f => ({ ...f, talhao_ids: current.filter(id => id !== talhaoid) }));
        } else {
            setForm(f => ({ ...f, talhao_ids: [...current, talhaoid] }));
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.talhao_ids || form.talhao_ids.length === 0) return toast.error("Selecione pelo menos um talhão.");
        mutation.mutate(form);
    };

    const inputClass =
        "w-full rounded-sm border border-border bg-transparent px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-colors placeholder:text-muted-foreground";

    return (
        <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4 bg-black/50">
            <Card className="w-full max-w-md">
                <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                    <div className="flex items-center gap-3">
                        <div className="size-9 rounded-sm bg-[var(--module-agro-bg)] flex items-center justify-center">
                            <Sprout className="size-4 text-[var(--module-agro)]" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-sm text-balance">Nova Safra / Ciclo</h2>
                            <p className="text-xs text-muted-foreground">Planejamento de plantio por talhão</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Fechar modal"
                        className="size-8 rounded-sm hover:bg-muted flex items-center justify-center transition-colors"
                    >
                        <X className="size-4 text-muted-foreground" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-muted-foreground">
                                Ano Agrícola <span className="text-destructive">*</span>
                            </label>
                            <Input
                                required
                                placeholder="Ex: 24/25"
                                className={inputClass}
                                value={form.ano_safra}
                                onChange={e => setForm(f => ({ ...f, ano_safra: e.target.value }))}
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-muted-foreground">
                                Cultura <span className="text-destructive">*</span>
                            </label>
                            <Select
                                value={form.cultura}
                                onValueChange={(value) => setForm((f) => ({ ...f, cultura: value }))}
                            >
                                <SelectTrigger className={inputClass}>
                                    <SelectValue placeholder="Selecione uma cultura" />
                                </SelectTrigger>
                                <SelectContent className="max-h-64">
                                    {culturas.map((c: any) => (
                                        <SelectItem key={c.id} value={c.nome}>
                                            {c.nome}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-semibold text-muted-foreground">
                            Talhões de Destino <span className="text-destructive">*</span> (selecione um ou mais)
                        </label>
                        <div className="border rounded-sm p-3 space-y-2 max-h-48 overflow-y-auto bg-muted/30">
                            {talhoes.length === 0 ? (
                                <p className="text-xs text-muted-foreground">Nenhum talhão disponível</p>
                            ) : (
                                talhoes.map((t: any) => (
                                    <label key={t.id} className="flex items-center gap-2 p-2 rounded hover:bg-muted/50 cursor-pointer transition-colors">
                                        <input
                                            type="checkbox"
                                            checked={(form.talhao_ids || []).includes(t.id)}
                                            onChange={() => toggleTalhao(t.id)}
                                            className="rounded"
                                        />
                                        <span className="text-sm">{t.nome} ({t.area_efetiva_ha} ha)</span>
                                    </label>
                                ))
                            )}
                        </div>
                        {(!form.talhao_ids || form.talhao_ids.length === 0) && (
                            <p className="text-xs text-destructive">Selecione pelo menos um talhão</p>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-muted-foreground">Plantio Previsto</label>
                            <Input
                                type="date"
                                className={inputClass}
                                value={form.data_plantio_prevista}
                                onChange={e => setForm(f => ({ ...f, data_plantio_prevista: e.target.value }))}
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-muted-foreground">Meta (Sc/ha)</label>
                            <Input
                                type="number"
                                step="0.1"
                                placeholder="Ex: 70"
                                className={inputClass}
                                value={form.produtividade_meta_sc_ha}
                                onChange={e => setForm(f => ({ ...f, produtividade_meta_sc_ha: Number(e.target.value) }))}
                            />
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" size="sm" disabled={mutation.isPending || !form.talhao_ids?.length}>
                            {mutation.isPending ? <Loader2 className="size-3.5 mr-1.5 animate-spin" /> : <Plus className="size-3.5 mr-1.5" />}
                            {mutation.isPending ? "Salvando..." : "Planejar Safra"}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}

export default function SafraPage() {
    const { activeFazendaId } = useAppStore();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const [showModal, setShowModal] = useState(false);
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: safras = [], isLoading } = useQuery({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch<Safra[]>(`/safras${qs}`),
        enabled: !!activeFazendaId,
    });

    const { data: talhoes = [] } = useQuery({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch<any[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId,
    });

    const safraColumns = createSafraColumns(
        (id) => talhoes.find((talhao: any) => talhao.id === id)?.nome ?? "Talhão não informado"
    );

    const emAndamento = safras.filter((s) => s.status === "EM_ANDAMENTO").length;
    const areaPlantada = safras.reduce((acc: number, s) => acc + (Number(s.area_plantada_ha) || 0), 0).toFixed(1);
    const metaMedia = (safras.reduce((acc: number, s) => acc + (Number(s.produtividade_meta_sc_ha) || 0), 0) / (safras.length || 1)).toFixed(0);
    const planejadas = safras.filter((s) => s.status === "PLANEJADA").length;

    if (!activeFazendaId) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title="Ciclos de Produção"
                    description="Gerencie as safras e acompanhe o desempenho produtivo"
                    icon={<Sprout className="size-[22px] text-primary" />}
                />
                <EmptyState
                    icon={<Sprout />}
                    title="Selecione uma propriedade"
                    description="Escolha uma fazenda no seletor acima para ver os ciclos de produção."
                />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {showModal && activeFazendaId && (
                <NovaSafraModal fazendaId={activeFazendaId} onClose={() => setShowModal(false)} />
            )}

            <PageHeader
                title="Ciclos de Produção"
                description="Gerencie as safras e acompanhe o desempenho produtivo"
                icon={<Sprout size={22} className="text-primary" />}
                actions={
                    <Button
                        onClick={() => setShowModal(true)}
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                    >
                        <Plus className="size-3.5 mr-1.5" /> Nova Safra
                    </Button>
                }
            />

            <MinhasPendenciasChecklist />

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {isLoading ? (
                    <>
                        {[1, 2, 3, 4].map((i) => (
                            <Card key={i} className="rounded-sm shadow-sm border">
                                <CardContent className="p-5 flex items-start gap-4">
                                    <Skeleton className="size-10 rounded-sm" />
                                    <div className="space-y-2 flex-1">
                                        <Skeleton className="h-3 w-20" />
                                        <Skeleton className="h-7 w-12" />
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </>
                ) : (
                    <>
                        {[
                            { label: "Ciclos Ativos", value: emAndamento, color: "text-blue-600", bg: "bg-blue-100", icon: Sprout },
                            { label: "Área Plantada", value: areaPlantada, sub: "hectares", color: "text-amber-600", bg: "bg-amber-100", icon: Sprout },
                            { label: "Meta Média", value: metaMedia, sub: "sc/ha", color: "text-emerald-600", bg: "bg-emerald-100", icon: Sprout },
                            { label: "Planejadas", value: planejadas, color: "text-purple-600", bg: "bg-purple-100", icon: Sprout },
                        ].map((kpi, idx) => (
                            <Card key={idx} className="rounded-sm shadow-sm border overflow-hidden">
                                <CardContent className="p-5 flex items-start gap-4">
                                    <div className={`size-10 rounded-sm ${kpi.bg} flex items-center justify-center shrink-0`}>
                                        <kpi.icon className={`size-5 ${kpi.color}`} />
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">{kpi.label}</p>
                                        <p className="text-2xl font-black tabular-nums mt-0.5">{kpi.value}</p>
                                        {kpi.sub && <p className="text-[10px] text-muted-foreground mt-0.5">{kpi.sub}</p>}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </>
                )}
            </div>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-[var(--module-agro-bg)] flex items-center justify-center shrink-0">
                            <TrendingUp className="size-5 text-[var(--module-agro)]" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Rentabilidade Agrícola</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Visão oficial derivada da DRE agrícola v1, com margem, resultado operacional e ranking simples de rentabilidade.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Valores podem estar sujeitos à reconciliação.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/rentabilidade">
                                <LineChart className="size-4" />
                                Abrir rentabilidade
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-emerald-100 flex items-center justify-center shrink-0">
                            <Activity className="size-5 text-emerald-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Eficiência Operacional Agrícola</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Leitura oficial de custo, horas e produtividade operacional derivada da DRE agrícola v1, rentabilidade e registros operacionais.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Indicadores sujeitos à reconciliação quando houver warnings relevantes.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/eficiencia">
                                <Activity className="size-4" />
                                Abrir eficiência
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-slate-100 flex items-center justify-center shrink-0">
                            <BarChart3 className="size-5 text-slate-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Benchmark Operacional e Econômico</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Benchmark comparativo oficial derivado exclusivamente da DRE agrícola v1, da rentabilidade oficial e da eficiência operacional oficial.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Benchmark sujeito à reconciliação quando houver warnings relevantes.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/benchmark">
                                <BarChart3 className="size-4" />
                                Abrir benchmark
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-rose-100 flex items-center justify-center shrink-0">
                            <ShieldAlert className="size-5 text-rose-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Diagnóstico Operacional e Econômico</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Diagnósticos oficiais de desvio operacional e econômico derivados exclusivamente da DRE agrícola v1 e dos analytics oficiais.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Diagnósticos sujeitos à reconciliação.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/diagnostico">
                                <ShieldAlert className="size-4" />
                                Abrir diagnóstico
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-violet-100 flex items-center justify-center shrink-0">
                            <Sparkles className="size-5 text-violet-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Recomendações Operacionais e Econômicas Assistidas</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Recomendações determinísticas derivadas da DRE agrícola v1, dos diagnósticos oficiais e dos analytics consolidados.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Recomendações sujeitas à reconciliação.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/recomendacoes">
                                <Sparkles className="size-4" />
                                Abrir recomendações
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-sky-100 flex items-center justify-center shrink-0">
                            <WandSparkles className="size-5 text-sky-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Inteligência Operacional Aplicada</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Planos operacionais assistidos derivados de diagnóstico, recomendações e prioridades, com rastreabilidade completa e sem execução automática.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Somente leitura, sem workflow engine e sem alteração de tarefas reais.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/inteligencia-operacional">
                                <WandSparkles className="size-4" />
                                Abrir inteligência operacional
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm border overflow-hidden">
                <CardContent className="p-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-slate-100 flex items-center justify-center shrink-0">
                            <Target className="size-5 text-slate-700" />
                        </div>
                        <div className="flex flex-col gap-1">
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-sm font-black uppercase tracking-wider">Central Inteligente de Prioridades Agrícolas</h2>
                                <Badge variant={hasProfessionalTier ? "secondary" : "outline"} className="rounded-sm">
                                    {hasProfessionalTier ? "PROFISSIONAL" : "Somente leitura"}
                                </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground max-w-2xl">
                                Fila consolidada de prioridades operacionais e econômicas derivada da DRE agrícola v1, dos diagnósticos, das recomendações, do benchmark e dos warnings oficiais.
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                <AlertCircle className="size-3.5" />
                                Prioridades sujeitas à reconciliação.
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button asChild variant={hasProfessionalTier ? "default" : "outline"} size="sm" className="rounded-sm">
                            <Link href="/dashboard/agricola/prioridades">
                                <Target className="size-4" />
                                Abrir prioridades
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Tabela */}
            <Card className="border-2 p-1">
                {isLoading ? (
                    <div className="p-6 space-y-4">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-40 w-full" />
                    </div>
                ) : (
                    <DataTable
                        data={safras}
                        columns={safraColumns}
                        searchable={true}
                        searchPlaceholder="Buscar safra..."
                        exportable={true}
                        exportFileName="safras"
                        emptyMessage="Nenhum ciclo agrícola planejado"
                    />
                )}
            </Card>
        </div>
    );
}
