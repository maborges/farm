"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import {
    Users, Plus, Wallet, Clock, CheckCircle2,
    AlertTriangle, ChevronRight, UserCheck,
    Hammer, CalendarDays, BadgeCheck, X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/page-header";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DashboardRH {
    total_colaboradores_ativos: number;
    total_diaristas: number;
    total_empreiteiros: number;
    gasto_diarias_mes: number;
    gasto_empreitadas_mes: number;
    total_pendente_diarias: number;
    total_pendente_empreitadas: number;
    empreitadas_abertas: number;
}

interface Colaborador {
    id: string;
    pessoa_id: string;
    // campos desnormalizados retornados pelo backend via join
    nome?: string;
    cpf?: string;
    cargo?: string;
    tipo_contrato: string;
    valor_diaria?: number;
    data_admissao?: string;
    ativo: boolean;
}

interface Pessoa {
    id: string;
    nome_exibicao: string;
    tipo: string;
}

interface Diaria {
    id: string;
    colaborador_id: string;
    data: string;
    horas_trabalhadas: number;
    atividade: string;
    valor_diaria: number;
    status: string;
    observacoes?: string;
}

interface Empreitada {
    id: string;
    colaborador_id: string;
    descricao: string;
    unidade: string;
    quantidade: number;
    valor_unitario: number;
    valor_total: number;
    data_inicio: string;
    data_fim?: string;
    status: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

const tipoColor: Record<string, string> = {
    CLT:          "bg-blue-100 text-blue-700",
    DIARISTA:     "bg-amber-100 text-amber-700",
    EMPREITEIRO:  "bg-purple-100 text-purple-700",
    TERCEIRO:     "bg-slate-100 text-slate-700",
};

const statusEmpColor: Record<string, string> = {
    ABERTA:    "bg-blue-100 text-blue-700",
    CONCLUIDA: "bg-amber-100 text-amber-700",
    PAGA:      "bg-green-100 text-green-700",
    CANCELADA: "bg-red-100 text-red-700",
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function RHPage() {
    const qc = useQueryClient();


    const [showNovoColaborador, setShowNovoColaborador] = useState(false);
    const [showNovaDiaria, setShowNovaDiaria] = useState(false);
    const [showNovaEmpreitada, setShowNovaEmpreitada] = useState(false);
    const [selectedDiarias, setSelectedDiarias] = useState<Set<string>>(new Set());

    // ── Queries ──
    const { data: dash } = useQuery<DashboardRH>({
        queryKey: ["rh-dashboard"],
        queryFn: () => apiFetch("/rh/dashboard"),
    });

    const { data: colaboradores = [], isLoading: loadingCol } = useQuery<Colaborador[]>({
        queryKey: ["rh-colaboradores"],
        queryFn: () => apiFetch("/rh/colaboradores?ativo=true"),
    });

    const { data: diarias = [], isLoading: loadingDiarias } = useQuery<Diaria[]>({
        queryKey: ["rh-diarias"],
        queryFn: () => apiFetch("/rh/diarias"),
    });

    const { data: empreitadas = [], isLoading: loadingEmp } = useQuery<Empreitada[]>({
        queryKey: ["rh-empreitadas"],
        queryFn: () => apiFetch("/rh/empreitadas"),
    });

    // ── Pessoas (para selector no form de colaborador) ──
    const { data: pessoas = [] } = useQuery<Pessoa[]>({
        queryKey: ["pessoas-rh"],
        queryFn: () => apiFetch("/cadastros/pessoas"),
    });

    // ── Forms ──
    const colForm = useForm<{ pessoa_id: string; cargo?: string; tipo_contrato: string; valor_diaria?: number; data_admissao?: string }>({
        defaultValues: { pessoa_id: "", tipo_contrato: "DIARISTA", valor_diaria: 0 },
    });
    const diariaForm = useForm<Partial<Diaria> & { colaborador_id: string }>({
        defaultValues: { colaborador_id: "", data: "", horas_trabalhadas: 8, atividade: "GERAL", valor_diaria: 0 },
    });
    const empForm = useForm<Partial<Empreitada> & { colaborador_id: string }>({
        defaultValues: { colaborador_id: "", descricao: "", unidade: "HECTARE", quantidade: 0, valor_unitario: 0, data_inicio: "" },
    });

    // ── Mutations ──
    const criarColMut = useMutation({
        mutationFn: (d: any) => apiFetch("/rh/colaboradores", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-colaboradores"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); setShowNovoColaborador(false); colForm.reset(); },
    });

    const criarDiariaMut = useMutation({
        mutationFn: (d: any) => apiFetch("/rh/diarias", { method: "POST", body: JSON.stringify({ ...d, valor_diaria: Number(d.valor_diaria), horas_trabalhadas: Number(d.horas_trabalhadas) }) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-diarias"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); setShowNovaDiaria(false); diariaForm.reset(); },
    });

    const pagarDiariasMut = useMutation({
        mutationFn: () => apiFetch("/rh/diarias/pagar-lote", { method: "POST", body: JSON.stringify({ ids: [...selectedDiarias] }) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-diarias"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); setSelectedDiarias(new Set()); },
    });

    const criarEmpMut = useMutation({
        mutationFn: (d: any) => apiFetch("/rh/empreitadas", { method: "POST", body: JSON.stringify({ ...d, quantidade: Number(d.quantidade), valor_unitario: Number(d.valor_unitario) }) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-empreitadas"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); setShowNovaEmpreitada(false); empForm.reset(); },
    });

    const concluirEmpMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/rh/empreitadas/${id}/concluir`, { method: "PATCH", body: JSON.stringify({}) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-empreitadas"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); },
    });

    const pagarEmpMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/rh/empreitadas/${id}/pagar`, { method: "PATCH" }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["rh-empreitadas"] }); qc.invalidateQueries({ queryKey: ["rh-dashboard"] }); },
    });

    // ── Derived ──
    const nomeColaborador = (id: string) => {
        const col = colaboradores.find(c => c.id === id);
        return col?.nome ?? pessoas.find(p => p.id === col?.pessoa_id)?.nome_exibicao ?? id.slice(0, 8);
    };

    const diariasPendentes = diarias.filter(d => d.status === "PENDENTE");
    const toggleDiaria = (id: string) => {
        const next = new Set(selectedDiarias);
        next.has(id) ? next.delete(id) : next.add(id);
        setSelectedDiarias(next);
    };
    const toggleAllPendentes = () => {
        if (selectedDiarias.size === diariasPendentes.length) {
            setSelectedDiarias(new Set());
        } else {
            setSelectedDiarias(new Set(diariasPendentes.map(d => d.id)));
        }
    };

    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
                title="Recursos Humanos"
                description="Colaboradores, lançamentos de diárias e empreitadas."
                icon={<Users className="text-primary" />}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setShowNovoColaborador(true)}>
                            <UserCheck size={14} /> Colaborador
                        </Button>
                        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setShowNovaDiaria(true)}>
                            <CalendarDays size={14} /> Diária
                        </Button>
                        <Button size="sm" className="gap-1.5" onClick={() => setShowNovaEmpreitada(true)}>
                            <Hammer size={14} /> Empreitada
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card variant="info">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">Colaboradores</p>
                        <p className="text-2xl font-black text-card-title">{dash?.total_colaboradores_ativos ?? "—"}</p>
                        <p className="text-[10px] text-card-description mt-1">
                            {dash?.total_diaristas ?? 0} diaristas · {dash?.total_empreiteiros ?? 0} empreiteiros
                        </p>
                    </CardContent>
                </Card>
                <Card variant="warning">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">Diárias (mês)</p>
                        <p className="text-xl font-black text-card-title">{fmt(dash?.gasto_diarias_mes ?? 0)}</p>
                        <p className="text-[10px] text-alert-destructive-icon font-semibold mt-1">
                            pendente: {fmt(dash?.total_pendente_diarias ?? 0)}
                        </p>
                    </CardContent>
                </Card>
                <Card className="border-[var(--module-backoffice)]/30 bg-[var(--module-backoffice-bg)]">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-[var(--module-backoffice)]">Empreitadas (mês)</p>
                        <p className="text-xl font-black text-[var(--module-backoffice)]">{fmt(dash?.gasto_empreitadas_mes ?? 0)}</p>
                        <p className="text-[10px] text-muted-foreground mt-1">{dash?.empreitadas_abertas ?? 0} em aberto</p>
                    </CardContent>
                </Card>
                <Card variant="destructive">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">Total a Pagar</p>
                        <p className="text-xl font-black text-card-title">
                            {fmt((dash?.total_pendente_diarias ?? 0) + (dash?.total_pendente_empreitadas ?? 0))}
                        </p>
                        <p className="text-[10px] text-card-description mt-1">diárias + empreitadas</p>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="colaboradores">
                <TabsList className="bg-muted/50 p-1">
                    <TabsTrigger value="colaboradores" className="gap-1.5"><Users size={13} /> Colaboradores</TabsTrigger>
                    <TabsTrigger value="diarias" className="gap-1.5"><CalendarDays size={13} /> Diárias</TabsTrigger>
                    <TabsTrigger value="empreitadas" className="gap-1.5"><Hammer size={13} /> Empreitadas</TabsTrigger>
                </TabsList>

                {/* ── Colaboradores ── */}
                <TabsContent value="colaboradores" className="mt-4">
                    <Card>
                        <CardContent className="p-0">
                            {loadingCol ? (
                                <div className="p-4 space-y-3">{[1,2,3].map(i=><Skeleton key={i} className="h-14 w-full"/>)}</div>
                            ) : colaboradores.length === 0 ? (
                                <div className="text-center py-12 text-muted-foreground">
                                    <Users className="mx-auto size-10 opacity-30 mb-3"/>
                                    <p className="font-bold">Nenhum colaborador cadastrado</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-border/50">
                                    {colaboradores.map(c => (
                                        <div key={c.id} className="flex items-center justify-between p-4 hover:bg-muted/20">
                                            <div className="flex items-center gap-3">
                                                <div className="size-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm shrink-0">
                                                    {(c.nome ?? pessoas.find(p => p.id === c.pessoa_id)?.nome_exibicao ?? "?").charAt(0).toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="font-bold text-sm">
                                                        {c.nome ?? pessoas.find(p => p.id === c.pessoa_id)?.nome_exibicao ?? c.pessoa_id.slice(0, 8)}
                                                    </p>
                                                    <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                                                        {c.cargo && <span>{c.cargo}</span>}
                                                        {c.data_admissao && <span>· desde {new Date(c.data_admissao).toLocaleDateString("pt-BR")}</span>}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                {c.valor_diaria && (
                                                    <div className="hidden md:block text-right">
                                                        <p className="text-[10px] text-muted-foreground">Diária</p>
                                                        <p className="text-sm font-bold">{fmt(c.valor_diaria)}</p>
                                                    </div>
                                                )}
                                                <Badge className={`text-[10px] h-5 px-2 border-none ${tipoColor[c.tipo_contrato] ?? "bg-muted"}`}>
                                                    {c.tipo_contrato}
                                                </Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Diárias ── */}
                <TabsContent value="diarias" className="mt-4">
                    <Card>
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-base">Lançamentos de Diárias</CardTitle>
                                    <CardDescription>{diariasPendentes.length} pendente(s) de pagamento</CardDescription>
                                </div>
                                {selectedDiarias.size > 0 && (
                                    <Button size="sm" className="gap-1.5 bg-green-600 hover:bg-green-700"
                                        onClick={() => pagarDiariasMut.mutate()}
                                        disabled={pagarDiariasMut.isPending}>
                                        <BadgeCheck size={14} /> Pagar {selectedDiarias.size} selecionada(s)
                                    </Button>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingDiarias ? (
                                <div className="p-4 space-y-3">{[1,2,3].map(i=><Skeleton key={i} className="h-12 w-full"/>)}</div>
                            ) : diarias.length === 0 ? (
                                <div className="text-center py-12 text-muted-foreground">
                                    <CalendarDays className="mx-auto size-10 opacity-30 mb-3"/>
                                    <p className="font-bold">Nenhuma diária lançada</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-border/50">
                                    {/* header select all */}
                                    {diariasPendentes.length > 0 && (
                                        <div className="flex items-center gap-3 px-4 py-2 bg-muted/30">
                                            <Checkbox
                                                checked={selectedDiarias.size === diariasPendentes.length && diariasPendentes.length > 0}
                                                onCheckedChange={toggleAllPendentes}
                                            />
                                            <span className="text-xs text-muted-foreground">Selecionar todas as pendentes</span>
                                        </div>
                                    )}
                                    {diarias.map(d => (
                                        <div key={d.id} className={`flex items-center justify-between p-4 hover:bg-muted/20 ${selectedDiarias.has(d.id) ? "bg-green-50" : ""}`}>
                                            <div className="flex items-center gap-3">
                                                {d.status === "PENDENTE" ? (
                                                    <Checkbox
                                                        checked={selectedDiarias.has(d.id)}
                                                        onCheckedChange={() => toggleDiaria(d.id)}
                                                    />
                                                ) : (
                                                    <CheckCircle2 className="size-4 text-green-500 shrink-0" />
                                                )}
                                                <div>
                                                    <p className="font-bold text-sm">{nomeColaborador(d.colaborador_id)}</p>
                                                    <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
                                                        <span>{new Date(d.data).toLocaleDateString("pt-BR")}</span>
                                                        <span>· {d.atividade}</span>
                                                        <span>· {d.horas_trabalhadas}h</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <p className="font-black text-sm">{fmt(d.valor_diaria)}</p>
                                                <Badge className={d.status === "PAGO"
                                                    ? "bg-green-100 text-green-700 border-none text-[10px] h-5 px-2"
                                                    : "bg-amber-100 text-amber-700 border-none text-[10px] h-5 px-2"}>
                                                    {d.status}
                                                </Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Empreitadas ── */}
                <TabsContent value="empreitadas" className="mt-4">
                    <Card>
                        <CardContent className="p-0">
                            {loadingEmp ? (
                                <div className="p-4 space-y-3">{[1,2,3].map(i=><Skeleton key={i} className="h-16 w-full"/>)}</div>
                            ) : empreitadas.length === 0 ? (
                                <div className="text-center py-12 text-muted-foreground">
                                    <Hammer className="mx-auto size-10 opacity-30 mb-3"/>
                                    <p className="font-bold">Nenhuma empreitada registrada</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-border/50">
                                    {empreitadas.map(e => (
                                        <div key={e.id} className="flex items-center justify-between p-4 hover:bg-muted/20 gap-4">
                                            <div className="flex items-center gap-3 min-w-0">
                                                <div className={`size-9 rounded-sm flex items-center justify-center shrink-0 ${e.status === "PAGA" ? "bg-green-100 text-green-700" : e.status === "ABERTA" ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"}`}>
                                                    <Hammer size={16} />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-bold text-sm truncate">{e.descricao}</p>
                                                    <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground flex-wrap">
                                                        <span>{nomeColaborador(e.colaborador_id)}</span>
                                                        <span>· {e.quantidade} {e.unidade}</span>
                                                        <span>· {new Date(e.data_inicio).toLocaleDateString("pt-BR")}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 shrink-0">
                                                <div className="text-right hidden md:block">
                                                    <p className="text-[10px] text-muted-foreground">{fmt(e.valor_unitario)}/{e.unidade}</p>
                                                    <p className="font-black text-sm">{fmt(e.valor_total)}</p>
                                                </div>
                                                <Badge className={`text-[10px] h-5 px-2 border-none ${statusEmpColor[e.status] ?? "bg-muted"}`}>
                                                    {e.status}
                                                </Badge>
                                                {e.status === "ABERTA" && (
                                                    <Button size="sm" variant="outline" className="text-xs gap-1"
                                                        onClick={() => concluirEmpMut.mutate(e.id)}
                                                        disabled={concluirEmpMut.isPending}>
                                                        Concluir
                                                    </Button>
                                                )}
                                                {e.status === "CONCLUIDA" && (
                                                    <Button size="sm" className="text-xs gap-1 bg-green-600 hover:bg-green-700"
                                                        onClick={() => pagarEmpMut.mutate(e.id)}
                                                        disabled={pagarEmpMut.isPending}>
                                                        <BadgeCheck size={12} /> Pagar
                                                    </Button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* ── Dialog: Novo Colaborador ── */}
            <Dialog open={showNovoColaborador} onOpenChange={setShowNovoColaborador}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader><DialogTitle>Cadastrar Colaborador</DialogTitle></DialogHeader>
                    <form onSubmit={colForm.handleSubmit(d => criarColMut.mutate(d))} className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="col-span-2">
                                <Label>Pessoa *</Label>
                                <Select
                                    value={colForm.watch("pessoa_id") ?? ""}
                                    onValueChange={(value) => colForm.setValue("pessoa_id", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue placeholder="Selecione uma pessoa…" />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {pessoas.map(p => <SelectItem key={p.id} value={p.id}>{p.nome_exibicao}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    A pessoa deve estar cadastrada em <a href="/cadastros/pessoas" className="underline text-primary">Cadastros → Pessoas</a>.
                                </p>
                            </div>
                            <div>
                                <Label>Cargo / Função</Label>
                                <Input placeholder="Ex: Tratorista" {...colForm.register("cargo")} className="mt-1" />
                            </div>
                            <div>
                                <Label>Tipo de Contrato</Label>
                                <Select
                                    value={colForm.watch("tipo_contrato") ?? "DIARISTA"}
                                    onValueChange={(value) => colForm.setValue("tipo_contrato", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        <SelectItem value="DIARISTA">Diarista</SelectItem>
                                        <SelectItem value="EMPREITEIRO">Empreiteiro</SelectItem>
                                        <SelectItem value="CLT">CLT</SelectItem>
                                        <SelectItem value="TERCEIRO">Terceiro</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Valor da Diária (R$)</Label>
                                <Input type="number" step="0.01" {...colForm.register("valor_diaria")} className="mt-1" />
                            </div>
                            <div>
                                <Label>Data de Admissão</Label>
                                <Input type="date" {...colForm.register("data_admissao")} className="mt-1" />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowNovoColaborador(false)}>Cancelar</Button>
                            <Button type="submit" disabled={criarColMut.isPending}>{criarColMut.isPending ? "Salvando…" : "Cadastrar"}</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* ── Dialog: Nova Diária ── */}
            <Dialog open={showNovaDiaria} onOpenChange={setShowNovaDiaria}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader><DialogTitle>Lançar Diária</DialogTitle></DialogHeader>
                    <form onSubmit={diariaForm.handleSubmit(d => criarDiariaMut.mutate(d))} className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="col-span-2">
                                <Label>Colaborador</Label>
                                <Select
                                    value={diariaForm.watch("colaborador_id") ?? ""}
                                    onValueChange={(value) => diariaForm.setValue("colaborador_id", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue placeholder="Selecione…" />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {colaboradores.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Data</Label>
                                <Input type="date" {...diariaForm.register("data", { required: true })} className="mt-1" />
                            </div>
                            <div>
                                <Label>Horas</Label>
                                <Input type="number" step="0.5" defaultValue={8} {...diariaForm.register("horas_trabalhadas")} className="mt-1" />
                            </div>
                            <div>
                                <Label>Atividade</Label>
                                <Select
                                    value={diariaForm.watch("atividade") ?? "GERAL"}
                                    onValueChange={(value) => diariaForm.setValue("atividade", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {["GERAL","PLANTIO","COLHEITA","CAPINA","MANUTENCAO","IRRIGACAO","PULVERIZACAO","CARREGAMENTO"].map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Valor da Diária (R$)</Label>
                                <Input type="number" step="0.01" {...diariaForm.register("valor_diaria", { required: true })} className="mt-1" />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowNovaDiaria(false)}>Cancelar</Button>
                            <Button type="submit" disabled={criarDiariaMut.isPending}>{criarDiariaMut.isPending ? "Lançando…" : "Lançar Diária"}</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* ── Dialog: Nova Empreitada ── */}
            <Dialog open={showNovaEmpreitada} onOpenChange={setShowNovaEmpreitada}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader><DialogTitle>Registrar Empreitada</DialogTitle></DialogHeader>
                    <form onSubmit={empForm.handleSubmit(d => criarEmpMut.mutate(d))} className="space-y-4">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="col-span-2">
                                <Label>Colaborador / Equipe</Label>
                                <Select
                                    value={empForm.watch("colaborador_id") ?? ""}
                                    onValueChange={(value) => empForm.setValue("colaborador_id", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue placeholder="Selecione…" />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {colaboradores.map(c => <SelectItem key={c.id} value={c.id}>{c.nome}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="col-span-2">
                                <Label>Descrição do Serviço</Label>
                                <Input placeholder="Ex: Colheita de soja — Talhão 3" {...empForm.register("descricao", { required: true })} className="mt-1" />
                            </div>
                            <div>
                                <Label>Unidade</Label>
                                <Select
                                    value={empForm.watch("unidade") ?? "HECTARE"}
                                    onValueChange={(value) => empForm.setValue("unidade", value, { shouldDirty: true, shouldValidate: true })}
                                >
                                    <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {["HECTARE","SACA","HORA","UNIDADE","METRO"].map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Quantidade</Label>
                                <Input type="number" step="0.01" {...empForm.register("quantidade", { required: true })} className="mt-1" />
                            </div>
                            <div>
                                <Label>Valor Unitário (R$)</Label>
                                <Input type="number" step="0.01" {...empForm.register("valor_unitario", { required: true })} className="mt-1" />
                            </div>
                            <div>
                                <Label>Início</Label>
                                <Input type="date" {...empForm.register("data_inicio", { required: true })} className="mt-1" />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowNovaEmpreitada(false)}>Cancelar</Button>
                            <Button type="submit" disabled={criarEmpMut.isPending}>{criarEmpMut.isPending ? "Salvando…" : "Registrar"}</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
