"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import {
    Hammer, Plus, CheckCircle2, Wallet, Clock,
    AlertTriangle, ChevronRight, Building2, CalendarDays,
    BadgeCheck, BarChart3, Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Sheet, SheetContent, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Colaborador {
    id: string;
    nome: string;
    cargo?: string;
    tipo_contrato: string;
}

interface Empreitada {
    id: string;
    colaborador_id: string;
    colaborador_nome?: string;
    descricao: string;
    unidade: string;
    quantidade: number;
    valor_unitario: number;
    valor_total: number;
    data_inicio: string;
    data_previsao_fim?: string;
    data_conclusao?: string;
    data_pagamento?: string;
    status: string;
    observacoes?: string;
}

interface NovaEmpreitadaForm {
    colaborador_id: string;
    descricao: string;
    unidade: string;
    quantidade: number;
    valor_unitario: number;
    data_inicio: string;
    data_previsao_fim: string;
    observacoes: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

const dataBR = (s?: string) =>
    s ? new Date(s + "T00:00:00").toLocaleDateString("pt-BR") : "—";

const STATUS_CONFIG: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
    ABERTA:    { label: "Em Andamento", className: "bg-blue-100 text-blue-700 border-none",   icon: <Clock size={10} /> },
    CONCLUIDA: { label: "Concluída",    className: "bg-amber-100 text-amber-700 border-none", icon: <CheckCircle2 size={10} /> },
    PAGA:      { label: "Paga",         className: "bg-green-100 text-green-700 border-none", icon: <BadgeCheck size={10} /> },
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function EmpreitadasPage() {
    const qc = useQueryClient();

    const [showNova, setShowNova] = useState(false);
    const [selected, setSelected] = useState<Empreitada | null>(null);
    const [filterStatus, setFilterStatus] = useState<string>("TODAS");

    // ── Queries ──
    const { data: empreitadas = [], isLoading } = useQuery<Empreitada[]>({
        queryKey: ["empreitadas"],
        queryFn: () => apiFetch("/rh/empreitadas"),
    });

    const { data: colaboradores = [] } = useQuery<Colaborador[]>({
        queryKey: ["colaboradores"],
        queryFn: () => apiFetch("/rh/colaboradores"),
    });

    // ── Mutations ──
    const form = useForm<NovaEmpreitadaForm>({
        defaultValues: {
            colaborador_id: "", descricao: "", unidade: "ha",
            quantidade: 1, valor_unitario: 0,
            data_inicio: new Date().toISOString().split("T")[0],
            data_previsao_fim: "", observacoes: "",
        },
    });

    const criarMutation = useMutation({
        mutationFn: (d: NovaEmpreitadaForm) =>
            apiFetch("/rh/empreitadas", {
                method: "POST",
                body: JSON.stringify({
                    ...d,
                    quantidade: Number(d.quantidade),
                    valor_unitario: Number(d.valor_unitario),
                    data_previsao_fim: d.data_previsao_fim || null,
                }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["empreitadas"] });
            setShowNova(false);
            form.reset();
        },
    });

    const concluirMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/rh/empreitadas/${id}/concluir`, { method: "PATCH" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["empreitadas"] });
            setSelected(prev => prev ? { ...prev, status: "CONCLUIDA" } : null);
        },
    });

    const pagarMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/rh/empreitadas/${id}/pagar`, { method: "PATCH" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["empreitadas"] });
            setSelected(prev => prev ? { ...prev, status: "PAGA" } : null);
        },
    });

    // ── Derived ──
    const filtered = filterStatus === "TODAS"
        ? empreitadas
        : empreitadas.filter(e => e.status === filterStatus);

    const totAberta   = empreitadas.filter(e => e.status === "ABERTA").length;
    const totConcluida = empreitadas.filter(e => e.status === "CONCLUIDA").length;
    const totPaga     = empreitadas.filter(e => e.status === "PAGA").length;
    const valorPendente = empreitadas
        .filter(e => e.status !== "PAGA")
        .reduce((acc, e) => acc + e.valor_total, 0);
    const valorPago = empreitadas
        .filter(e => e.status === "PAGA")
        .reduce((acc, e) => acc + e.valor_total, 0);

    const hoje = new Date().toISOString().split("T")[0];
    const vencidas = empreitadas.filter(
        e => e.status === "ABERTA" && e.data_previsao_fim && e.data_previsao_fim < hoje
    ).length;

    const columns: ColumnDef<Empreitada>[] = [
        {
            id: "descricao",
            header: "Descrição",
            accessorKey: "descricao",
            cell: (value, row) => (
                <div>
                    <p className="text-sm font-semibold truncate max-w-[240px]">{value}</p>
                    <p className="text-xs text-muted-foreground">
                        {row.quantidade} {row.unidade} × {fmt(row.valor_unitario)}
                    </p>
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar descrição...",
            exportFormat: (value, row) => `${value} (${row.quantidade} ${row.unidade} × ${fmt(row.valor_unitario)})`,
        },
        {
            id: "empreiteiro",
            header: "Empreiteiro",
            accessorKey: "colaborador_nome",
            cell: (value, row) => (
                <div className="flex items-center gap-1.5 text-sm">
                    <Users size={12} className="text-muted-foreground" />
                    {value ?? row.colaborador_id.slice(0, 8)}
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar empreiteiro...",
            exportFormat: (value, row) => value ?? row.colaborador_id,
        },
        {
            id: "valor_total",
            header: "Valor Total",
            accessorKey: "valor_total",
            cell: (value) => (
                <span className="font-bold text-sm text-right block">{fmt(value)}</span>
            ),
            sortable: true,
            exportFormat: (value) => fmt(value),
        },
        {
            id: "prazo",
            header: "Prazo",
            accessorKey: "data_previsao_fim",
            cell: (value, row) => {
                const isVencida = row.status === "ABERTA" && value && value < hoje;
                return value ? (
                    <span className={`text-xs ${isVencida ? "text-red-600 font-semibold" : "text-muted-foreground"}`}>
                        {isVencida && <AlertTriangle size={10} className="inline mr-1" />}
                        {dataBR(value)}
                    </span>
                ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                );
            },
            sortable: true,
            exportFormat: (value) => dataBR(value),
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => {
                const cfg = STATUS_CONFIG[value] ?? { label: value, className: "bg-muted", icon: null };
                return (
                    <Badge className={`text-[10px] h-5 px-2 gap-1 ${cfg.className}`}>
                        {cfg.icon} {cfg.label}
                    </Badge>
                );
            },
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar status...",
            exportFormat: (value) => STATUS_CONFIG[value]?.label ?? value,
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_, row) => (
                <div className="flex items-center gap-0 justify-end">
                    <Button
                        size="icon"
                        variant="ghost"
                        className="size-7"
                        aria-label="Ver detalhes"
                        onClick={() => setSelected(row)}
                    >
                        <ChevronRight className="size-3.5" />
                    </Button>
                </div>
            ),
        },
    ];

    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
                title="Diaristas & Empreitadas"
                description="Contratos de serviço por produção, empreiteiros e diaristas."
                icon={<Hammer className="text-primary" />}
                actions={
                    <Button size="sm" className="gap-1.5" onClick={() => setShowNova(true)}>
                        <Plus size={14} /> Nova Empreitada
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card variant="info">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description flex items-center gap-1">
                            <BarChart3 size={10} /> Em Andamento
                        </p>
                        <p className="text-2xl font-black text-card-title">{totAberta}</p>
                        {vencidas > 0 && (
                            <p className="text-[10px] text-alert-destructive-icon font-semibold flex items-center gap-1 mt-0.5">
                                <AlertTriangle size={9} /> {vencidas} vencida{vencidas > 1 ? "s" : ""}
                            </p>
                        )}
                    </CardContent>
                </Card>
                <Card variant="warning">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">Concluídas</p>
                        <p className="text-2xl font-black text-card-title">{totConcluida}</p>
                        <p className="text-[10px] text-card-description mt-0.5">aguardando pagto.</p>
                    </CardContent>
                </Card>
                <Card variant="success">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">Pagas</p>
                        <p className="text-2xl font-black text-card-title">{totPaga}</p>
                        <p className="text-[10px] text-card-description mt-0.5">{fmt(valorPago)}</p>
                    </CardContent>
                </Card>
                <Card variant="destructive">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-bold uppercase text-card-description">A Pagar</p>
                        <p className="text-xl font-black text-card-title tabular-nums">{fmt(valorPendente)}</p>
                        <p className="text-[10px] text-card-description mt-0.5">concluídas + abertas</p>
                    </CardContent>
                </Card>
            </div>

            {/* Filter tabs */}
            <div className="flex items-center gap-2 flex-wrap">
                {["TODAS", "ABERTA", "CONCLUIDA", "PAGA"].map(s => (
                    <button
                        key={s}
                        onClick={() => setFilterStatus(s)}
                        className={`text-xs px-3 py-1 rounded-full border transition-colors font-semibold ${
                            filterStatus === s
                                ? "bg-primary text-primary-foreground border-primary"
                                : "bg-background text-muted-foreground border-border hover:bg-muted"
                        }`}
                    >
                        {s === "TODAS" ? "Todas" : STATUS_CONFIG[s]?.label ?? s}
                        {s !== "TODAS" && (
                            <span className="ml-1.5 opacity-70">
                                ({empreitadas.filter(e => e.status === s).length})
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* DataTable */}
            <DataTable
                data={filtered}
                columns={columns}
                searchable
                searchPlaceholder="Buscar empreitada ou empreiteiro..."
                exportable
                exportFileName="empreitadas"
                emptyMessage={
                    filterStatus === "TODAS"
                        ? 'Nenhuma empreitada. Clique em "Nova Empreitada" para começar.'
                        : `Nenhuma empreitada com status "${STATUS_CONFIG[filterStatus]?.label}".`
                }
            />

            {/* ── Sheet: Detalhes ──────────────────────────────────────────── */}
            <Sheet open={!!selected} onOpenChange={open => !open && setSelected(null)}>
                <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
                    {selected && (
                        <>
                            <SheetHeader className="mb-6">
                                <SheetTitle className="flex items-center gap-2">
                                    <Hammer size={16} className="text-primary" />
                                    Empreitada — Detalhes
                                </SheetTitle>
                            </SheetHeader>

                            <div className="space-y-4">
                                {/* Status banner */}
                                {(() => {
                                    const cfg = STATUS_CONFIG[selected.status];
                                    const isVencida = selected.status === "ABERTA" && selected.data_previsao_fim && selected.data_previsao_fim < hoje;
                                    return (
                                        <div className={`flex items-center gap-2 p-3 rounded-sm border text-sm font-semibold ${
                                            isVencida ? "border-red-300 bg-red-50 text-red-700" : `${cfg?.className} border-current/20`
                                        }`}>
                                            {isVencida ? <AlertTriangle size={14} /> : cfg?.icon}
                                            {isVencida ? "Prazo vencido — aguardando conclusão" : cfg?.label}
                                        </div>
                                    );
                                })()}

                                {/* Info grid */}
                                <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Descrição</p>
                                        <p className="font-semibold mt-0.5">{selected.descricao}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Empreiteiro</p>
                                        <p className="font-semibold mt-0.5 flex items-center gap-1">
                                            <Building2 size={12} className="text-muted-foreground" />
                                            {selected.colaborador_nome ?? "—"}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Quantidade</p>
                                        <p className="mt-0.5">{selected.quantidade} {selected.unidade}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Valor Unitário</p>
                                        <p className="mt-0.5">{fmt(selected.valor_unitario)}/{selected.unidade}</p>
                                    </div>
                                    <div className="col-span-2">
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground">Valor Total</p>
                                        <p className="text-2xl font-black mt-0.5">{fmt(selected.valor_total)}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground flex items-center gap-1">
                                            <CalendarDays size={9} /> Início
                                        </p>
                                        <p className="mt-0.5">{dataBR(selected.data_inicio)}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-bold uppercase text-muted-foreground flex items-center gap-1">
                                            <CalendarDays size={9} /> Previsão Fim
                                        </p>
                                        <p className="mt-0.5">{dataBR(selected.data_previsao_fim)}</p>
                                    </div>
                                    {selected.data_conclusao && (
                                        <div>
                                            <p className="text-[10px] font-bold uppercase text-muted-foreground">Concluída em</p>
                                            <p className="mt-0.5">{dataBR(selected.data_conclusao)}</p>
                                        </div>
                                    )}
                                    {selected.data_pagamento && (
                                        <div>
                                            <p className="text-[10px] font-bold uppercase text-muted-foreground">Paga em</p>
                                            <p className="mt-0.5 text-green-700 font-semibold">{dataBR(selected.data_pagamento)}</p>
                                        </div>
                                    )}
                                    {selected.observacoes && (
                                        <div className="col-span-2">
                                            <p className="text-[10px] font-bold uppercase text-muted-foreground">Observações</p>
                                            <p className="mt-0.5 text-sm">{selected.observacoes}</p>
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                {selected.status === "ABERTA" && (
                                    <Button
                                        className="w-full gap-2 mt-2"
                                        variant="outline"
                                        disabled={concluirMutation.isPending}
                                        onClick={() => concluirMutation.mutate(selected.id)}
                                    >
                                        <CheckCircle2 size={14} />
                                        {concluirMutation.isPending ? "Salvando…" : "Marcar como Concluída"}
                                    </Button>
                                )}
                                {selected.status === "CONCLUIDA" && (
                                    <Button
                                        className="w-full gap-2 mt-2 bg-green-600 hover:bg-green-700"
                                        disabled={pagarMutation.isPending}
                                        onClick={() => pagarMutation.mutate(selected.id)}
                                    >
                                        <Wallet size={14} />
                                        {pagarMutation.isPending ? "Registrando…" : "Registrar Pagamento"}
                                    </Button>
                                )}
                                {selected.status === "PAGA" && (
                                    <div className="flex items-center gap-2 p-3 rounded-sm bg-green-50 text-green-700 text-sm font-semibold">
                                        <BadgeCheck size={15} /> Empreitada concluída e paga.
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </SheetContent>
            </Sheet>

            {/* ── Dialog: Nova Empreitada ──────────────────────────────────── */}
            <Dialog open={showNova} onOpenChange={setShowNova}>
                <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Hammer size={16} /> Nova Empreitada
                        </DialogTitle>
                    </DialogHeader>
                    <form
                        onSubmit={form.handleSubmit(d => criarMutation.mutate(d))}
                        className="space-y-4"
                    >
                        <div>
                            <Label>Empreiteiro / Diarista</Label>
                            <Select
                                value={form.watch("colaborador_id") ?? ""}
                                onValueChange={(value) => form.setValue("colaborador_id", value, { shouldDirty: true, shouldValidate: true })}
                            >
                                <SelectTrigger className="mt-1 h-8 rounded-sm border-input bg-background px-3 text-sm">
                                    <SelectValue placeholder="Selecione…" />
                                </SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    {colaboradores.map(c => (
                                        <SelectItem key={c.id} value={c.id}>
                                            {c.nome} {c.cargo ? `— ${c.cargo}` : ""}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>Descrição do Serviço</Label>
                            <Input
                                placeholder="Ex: Roçagem de pastagem, colheita manual…"
                                {...form.register("descricao", { required: true })}
                                className="mt-1"
                            />
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                            <div>
                                <Label>Unidade</Label>
                                <Input
                                    placeholder="ha, sc, t, m²…"
                                    {...form.register("unidade", { required: true })}
                                    className="mt-1"
                                />
                            </div>
                            <div>
                                <Label>Quantidade</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    {...form.register("quantidade", { required: true })}
                                    className="mt-1"
                                />
                            </div>
                            <div>
                                <Label>Valor/Unidade (R$)</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    {...form.register("valor_unitario", { required: true })}
                                    className="mt-1"
                                />
                            </div>
                        </div>

                        {/* Preview do valor total */}
                        {(() => {
                            const qtd = Number(form.watch("quantidade")) || 0;
                            const vu = Number(form.watch("valor_unitario")) || 0;
                            const total = qtd * vu;
                            return total > 0 ? (
                                <div className="text-sm p-2 rounded-sm bg-muted/30 flex justify-between">
                                    <span className="text-muted-foreground">Valor total estimado:</span>
                                    <span className="font-black">{fmt(total)}</span>
                                </div>
                            ) : null;
                        })()}

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label>Data Início</Label>
                                <Input
                                    type="date"
                                    {...form.register("data_inicio", { required: true })}
                                    className="mt-1"
                                />
                            </div>
                            <div>
                                <Label>Previsão de Término</Label>
                                <Input
                                    type="date"
                                    {...form.register("data_previsao_fim")}
                                    className="mt-1"
                                />
                            </div>
                        </div>

                        <div>
                            <Label>Observações</Label>
                            <Input
                                placeholder="Condições, local, detalhes…"
                                {...form.register("observacoes")}
                                className="mt-1"
                            />
                        </div>

                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setShowNova(false)}>
                                Cancelar
                            </Button>
                            <Button type="submit" disabled={criarMutation.isPending}>
                                {criarMutation.isPending ? "Criando…" : "Criar Empreitada"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
