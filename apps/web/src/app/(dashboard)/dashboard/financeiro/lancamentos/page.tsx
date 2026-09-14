"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { 
    ClipboardList, 
    TrendingUp, 
    TrendingDown, 
    Filter, 
    Calendar,
    ArrowUpRight,
    ArrowDownRight,
    Calculator,
    Target,
    Plus,
    X,
    Loader2,
    DollarSign
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { parseLocaleNumber } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Lancamento {
    id: string;
    descricao: string;
    tipo: "CUSTO" | "RECEITA";
    categoria: string;
    valor: number;
    data: string;
    origem?: string;
    safra_id?: string;
}

interface LancamentoResumo {
    total_receitas: number;
    total_custos: number;
    saldo: number;
    quantidade_lancamentos: number;
}

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string;
}

interface LancamentoCreate {
    descricao: string;
    valor: number;
    data: string;
    safra_id: string;
    tipo: "RECEITA";
    categoria: string;
}

function RegistrarReceitaDialog({ safras, onClose }: { safras: Safra[], onClose: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<Omit<LancamentoCreate, "tipo">>({
        descricao: "",
        valor: 0,
        data: new Date().toISOString().split("T")[0],
        safra_id: "",
        categoria: "VENDA_PRODUCAO",
    });

    const mutation = useMutation({
        mutationFn: (payload: LancamentoCreate) =>
            apiFetch("/financeiro/lancamentos/", { method: "POST", body: payload }),
        onSuccess: () => {
            toast.success("Receita registrada com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["lancamentos-resumo"] });
            queryClient.invalidateQueries({ queryKey: ["lancamentos-lista"] });
            onClose();
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao registrar receita."),
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.safra_id) return toast.error("Selecione uma safra.");
        if (form.valor <= 0) return toast.error("O valor deve ser maior que zero.");
        mutation.mutate({ ...form, tipo: "RECEITA" });
    };

    const inputClass = "w-full h-8 text-xs rounded-sm border border-border bg-transparent px-3 py-1 text-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all placeholder:text-muted-foreground";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <Card className="w-full max-w-lg shadow-2xl animate-in slide-in-from-bottom-4 duration-300">
                <div className="flex items-center justify-between px-6 py-5 border-b border-border">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-sm bg-green-500/10 flex items-center justify-center">
                            <TrendingUp size={18} className="text-green-600" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-[15px]">Registrar Receita Operacional</h2>
                            <p className="text-xs text-muted-foreground">Venda de produção ou outras entradas financeiras</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="h-8 w-8 rounded-sm hover:bg-muted flex items-center justify-center transition-colors">
                        <X size={16} className="text-muted-foreground" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Descrição</label>
                        <Input
                            required
                            placeholder="Ex: Venda Safra Soja 24/25"
                            className={inputClass}
                            value={form.descricao}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, descricao: e.target.value }))}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Safra / Ciclo</label>
                            <select
                                required
                                className={inputClass}
                                value={form.safra_id}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setForm(f => ({ ...f, safra_id: e.target.value }))}
                            >
                                <option value="">Selecione...</option>
                                {safras.map(s => (
                                    <option key={s.id} value={s.id}>{s.ano_safra} - {s.cultura}</option>
                                ))}
                            </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Categoria</label>
                            <select
                                required
                                className={inputClass}
                                value={form.categoria}
                                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setForm(f => ({ ...f, categoria: e.target.value }))}
                            >
                                <option value="VENDA_PRODUCAO">Venda de produção</option>
                                <option value="OUTRAS_RECEITAS">Outras receitas</option>
                            </select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Data</label>
                            <Input
                                type="date"
                                className={inputClass}
                                value={form.data}
                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, data: e.target.value }))}
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Valor (R$)</label>
                            <div className="relative">
                                <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    required
                                    type="number"
                                    step="0.01"
                                    className={`${inputClass} pl-9`}
                                    value={form.valor}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, valor: parseLocaleNumber(e.target.value) }))}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <Button type="button" variant="outline" size="sm" onClick={onClose} className="rounded-sm">
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            variant="outline"
                            size="sm"
                            disabled={mutation.isPending}
                            className="rounded-sm border-green-600 text-green-700 hover:bg-green-50 shadow-sm"
                        >
                            {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                            Registrar Receita
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LancamentosOperacionaisPage() {
    const { activeFazendaId } = useAppStore();
    const [selectedSafraId, setSelectedSafraId] = useState<string>("");
    const [tipoFilter, setTipoFilter] = useState<string>("");
    const [isReceitaDialogOpen, setIsReceitaDialogOpen] = useState(false);

    // Fetch Safras for filtering
    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras/${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
        enabled: !!activeFazendaId,
    });

    // Build query params
    const queryParams: Record<string, string> = {};
    if (selectedSafraId) queryParams.safra_id = selectedSafraId;
    if (tipoFilter) queryParams.tipo = tipoFilter;

    // Fetch Resumo
    const { data: resumo, isLoading: loadingResumo } = useQuery<LancamentoResumo>({
        queryKey: ["lancamentos-resumo", activeFazendaId, selectedSafraId],
        queryFn: () => apiFetch("/financeiro/lancamentos/resumo", { params: queryParams }),
        enabled: !!activeFazendaId,
    });

    // Fetch Lancamentos
    const { data: lancamentos = [], isLoading: loadingLancamentos } = useQuery<Lancamento[]>({
        queryKey: ["lancamentos-lista", activeFazendaId, selectedSafraId, tipoFilter],
        queryFn: async () => {
            const res = await apiFetch<{ items: Lancamento[], total: number }>("/financeiro/lancamentos", { params: queryParams });
            return res.items || [];
        },
        enabled: !!activeFazendaId,
    });

    const columns: ColumnDef<Lancamento>[] = [
        {
            id: "data",
            header: "Data",
            accessorKey: "data",
            sortable: true,
            cell: (value: string) => (
                <span className="text-xs font-medium text-muted-foreground">
                    {new Date(value).toLocaleDateString("pt-BR")}
                </span>
            ),
        },
        {
            id: "tipo",
            header: "Tipo",
            accessorKey: "tipo",
            cell: (value: string) => (
                <Badge 
                    variant="outline" 
                    className={`rounded-sm text-[10px] uppercase font-bold px-1.5 h-5 ${
                        value === "RECEITA" 
                            ? "bg-green-100 text-green-700 border-green-200" 
                            : "bg-red-100 text-red-700 border-red-200"
                    }`}
                >
                    {value === "RECEITA" ? <ArrowUpRight className="size-2.5 mr-1" /> : <ArrowDownRight className="size-2.5 mr-1" />}
                    {value}
                </Badge>
            ),
        },
        {
            id: "descricao",
            header: "Descrição",
            accessorKey: "descricao",
            sortable: true,
            filterable: true,
            cell: (value: string, row: Lancamento) => (
                <div className="flex flex-col">
                    <span className="font-semibold text-sm">{value}</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-tight">{row.categoria}</span>
                </div>
            ),
        },
        {
            id: "origem",
            header: "Origem",
            accessorKey: "origem",
            cell: (value: string) => (
                <Badge variant="secondary" className="text-[10px] bg-muted/50 text-muted-foreground font-medium rounded-sm">
                    {value || "LANÇAMENTO MANUAL"}
                </Badge>
            ),
        },
        {
            id: "valor",
            header: "Valor",
            accessorKey: "valor",
            sortable: true,
            cell: (value: number, row: Lancamento) => (
                <span className={`font-black tabular-nums ${row.tipo === "RECEITA" ? "text-green-700" : "text-destructive"}`}>
                    {row.tipo === "RECEITA" ? "+" : "-"}{fmt(value).replace("R$\u00a0", "").replace("R$ ", "").trim()}
                </span>
            ),
        },
    ];

    const inputClass = "h-8 text-xs rounded-sm border border-border bg-background px-3 py-1 focus:ring-1 focus:ring-primary outline-none transition-all";

    return (
        <div className="flex flex-col gap-6 p-6 animate-in fade-in duration-500">
            <PageHeader
                title="Lançamentos Operacionais"
                description="Gestão de custos e receitas consolidada por safra e ciclo produtivo."
                icon={<ClipboardList size={22} className="text-primary" />}
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Operacional" }
                ]}
                actions={
                    <Button 
                        variant="outline"
                        size="sm" 
                        className="rounded-sm border-green-600 text-green-700 hover:bg-green-50 font-bold"
                        onClick={() => setIsReceitaDialogOpen(true)}
                    >
                        <Plus size={16} className="mr-2" />
                        Registrar Receita
                    </Button>
                }
            />

            {isReceitaDialogOpen && (
                <RegistrarReceitaDialog 
                    safras={safras} 
                    onClose={() => setIsReceitaDialogOpen(false)} 
                />
            )}

            {/* ── Filters ── */}
            <Card className="rounded-sm border shadow-sm">
                <CardContent className="p-4 flex flex-wrap items-end gap-4">
                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                            <Target size={12} /> Safra / Ciclo
                        </label>
                        <select
                            className={`${inputClass} w-48`}
                            value={selectedSafraId}
                            onChange={(e) => setSelectedSafraId(e.target.value)}
                        >
                            <option value="">Todas as Safras</option>
                            {safras.map(s => (
                                <option key={s.id} value={s.id}>{s.ano_safra} - {s.cultura}</option>
                            ))}
                        </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider flex items-center gap-1.5">
                            <Filter size={12} /> Tipo
                        </label>
                        <select
                            className={`${inputClass} w-32`}
                            value={tipoFilter}
                            onChange={(e) => setTipoFilter(e.target.value)}
                        >
                            <option value="">Todos</option>
                            <option value="RECEITA">Receitas</option>
                            <option value="CUSTO">Custos</option>
                        </select>
                    </div>

                    <Button 
                        variant="outline" 
                        size="sm" 
                        className="h-8 rounded-sm ml-auto"
                        onClick={() => {
                            setSelectedSafraId("");
                            setTipoFilter("");
                        }}
                    >
                        Limpar Filtros
                    </Button>
                </CardContent>
            </Card>

            {/* ── Summary KPIs ── */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="rounded-sm border-l-4 border-l-green-500">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-green-100 flex items-center justify-center shrink-0">
                            <TrendingUp className="size-5 text-green-600" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Total Receitas</p>
                            {loadingResumo ? <Skeleton className="h-7 w-24 mt-1" /> : (
                                <p className="text-2xl font-black tabular-nums text-green-700">{fmt(resumo?.total_receitas ?? 0)}</p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="rounded-sm border-l-4 border-l-red-500">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-red-100 flex items-center justify-center shrink-0">
                            <TrendingDown className="size-5 text-red-600" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Total Custos</p>
                            {loadingResumo ? <Skeleton className="h-7 w-24 mt-1" /> : (
                                <p className="text-2xl font-black tabular-nums text-red-700">{fmt(resumo?.total_custos ?? 0)}</p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                <Card className="rounded-sm border-l-4 border-l-primary bg-primary/5">
                    <CardContent className="p-5 flex items-start gap-4">
                        <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                            <Calculator className="size-5 text-primary" />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider">Resultado (Margem)</p>
                            {loadingResumo ? <Skeleton className="h-7 w-24 mt-1" /> : (
                                <p className={`text-2xl font-black tabular-nums ${(resumo?.saldo ?? 0) >= 0 ? "text-primary" : "text-destructive"}`}>
                                    {fmt(resumo?.saldo ?? 0)}
                                </p>
                            )}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Data Table ── */}
            <Card className="rounded-sm border shadow-sm overflow-hidden">
                <CardHeader className="pb-0 border-b border-border/50 bg-muted/20 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Calendar size={16} className="text-muted-foreground" />
                            Histórico de Lançamentos
                        </CardTitle>
                        <Badge variant="secondary" className="rounded-sm text-[10px] font-bold">
                        {loadingLancamentos ? "..." : lancamentos.length} registros
                        </Badge>
                    </div>
                </CardHeader>
                <div className="p-0">
                    {loadingLancamentos ? (
                        <div className="p-8 space-y-4">
                            <Skeleton className="h-8 w-full" />
                            <Skeleton className="h-8 w-full" />
                            <Skeleton className="h-8 w-full" />
                        </div>
                    ) : (
                        <DataTable
                            data={lancamentos}
                            columns={columns}
                            searchable
                            searchPlaceholder="Pesquisar descrição ou categoria..."
                            exportable
                            exportFileName={`lancamentos_operacionais_${selectedSafraId || 'geral'}`}
                        />
                    )}
                </div>
            </Card>
        </div>
    );
}
