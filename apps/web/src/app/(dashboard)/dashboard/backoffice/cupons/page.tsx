"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Tag, Plus, Calendar, Percent, DollarSign,
    Check, Copy, ToggleLeft, ToggleRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { StatusBadge } from "@/components/ui/status-badge";

interface Cupom {
    id: string;
    codigo: string;
    tipo: string;
    valor: number;
    aplicavel_em: string;
    uso_maximo: number;
    uso_atual: number;
    uso_por_cliente: number;
    data_inicio: string;
    data_fim: string;
    ativo: boolean;
    pode_ser_usado: boolean;
}

const TIPO_LABELS: Record<string, string> = {
    percentual: "Percentual (%)",
    valor_fixo: "Valor Fixo (R$)",
};

const APLICAVEL_LABELS: Record<string, string> = {
    primeira_mensalidade: "Primeira Mensalidade",
    todos_meses: "Todos os Meses",
    plano_anual: "Plano Anual",
};

export default function CuponsBackofficePage() {
    const queryClient = useQueryClient();
    const [showCreateDialog, setShowCreateDialog] = useState(false);
    const [formData, setFormData] = useState({
        codigo: "",
        tipo: "percentual",
        valor: 0,
        aplicavel_em: "primeira_mensalidade",
        duracao_meses: null as number | null,
        uso_maximo: 100,
        uso_por_cliente: 1,
        data_inicio: "",
        data_fim: "",
        ativo: true,
    });

    const { data: cupons = [], isLoading } = useQuery<Cupom[]>({
        queryKey: ["backoffice", "cupons"],
        queryFn: () => apiFetch("/backoffice/cupons"),
    });

    const createMutation = useMutation({
        mutationFn: (data: typeof formData) =>
            apiFetch("/backoffice/cupons", {
                method: "POST",
                body: JSON.stringify(data),
                headers: { "Content-Type": "application/json" },
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "cupons"] });
            toast.success("Cupom criado com sucesso!");
            setShowCreateDialog(false);
            resetForm();
        },
        onError: (err: any) => toast.error(err.message || "Erro ao criar cupom"),
    });

    const toggleMutation = useMutation({
        mutationFn: (cupomId: string) =>
            apiFetch(`/backoffice/cupons/${cupomId}`, { method: "DELETE" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "cupons"] });
            toast.success("Status do cupom atualizado!");
        },
        onError: (err: any) => toast.error(err.message || "Erro ao atualizar cupom"),
    });

    const resetForm = () => {
        setFormData({
            codigo: "",
            tipo: "percentual",
            valor: 0,
            aplicavel_em: "primeira_mensalidade",
            duracao_meses: null,
            uso_maximo: 100,
            uso_por_cliente: 1,
            data_inicio: "",
            data_fim: "",
            ativo: true,
        });
    };

    const stats = {
        total: cupons.length,
        ativos: cupons.filter((c) => c.ativo).length,
        disponiveis: cupons.filter((c) => c.pode_ser_usado).length,
        usosTotal: cupons.reduce((sum, c) => sum + c.uso_atual, 0),
    };

    // Definição das colunas da DataTable
    const columns: ColumnDef<Cupom>[] = [
        {
            id: "codigo",
            header: "Código",
            accessorKey: "codigo",
            cell: (value, row) => (
                <div className="flex items-center gap-2">
                    <code className="font-mono font-bold text-foreground bg-muted px-2 py-0.5 rounded text-sm">
                        {value}
                    </code>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                            e.stopPropagation();
                            navigator.clipboard.writeText(value);
                            toast.success("Código copiado!");
                        }}
                    >
                        <Copy className="size-3" />
                    </Button>
                </div>
            ),
            exportFormat: (value) => value,
        },
        {
            id: "tipo",
            header: "Tipo",
            accessorKey: "tipo",
            cell: (value) => (
                <Badge
                    variant="outline"
                    className={`text-[10px] uppercase font-bold ${
                        value === "percentual"
                            ? "bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30"
                            : "bg-emerald-500/10 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30"
                    }`}
                >
                    {value === "percentual" ? <Percent className="size-3 mr-1" /> : <DollarSign className="size-3 mr-1" />}
                    {TIPO_LABELS[value] ?? value}
                </Badge>
            ),
            exportFormat: (value) => TIPO_LABELS[value] ?? value,
        },
        {
            id: "desconto",
            header: "Desconto",
            accessorFn: (row) => row.tipo === "percentual" ? `${row.valor}%` : `R$ ${row.valor.toFixed(2)}`,
            cell: (value) => <span className="font-bold text-foreground">{value}</span>,
        },
        {
            id: "aplicavel_em",
            header: "Aplicável em",
            accessorKey: "aplicavel_em",
            cell: (value) => (
                <span className="text-xs text-muted-foreground">
                    {APLICAVEL_LABELS[value] ?? value}
                </span>
            ),
            exportFormat: (value) => APLICAVEL_LABELS[value] ?? value,
        },
        {
            id: "uso",
            header: "Uso",
            accessorFn: (row) => `${row.uso_atual}/${row.uso_maximo}`,
            cell: (_, row) => (
                <div className="flex flex-col">
                    <span className="text-sm font-bold">
                        {row.uso_atual} / {row.uso_maximo}
                    </span>
                    <div className="w-20 h-1.5 bg-muted rounded-full mt-1 overflow-hidden">
                        <div
                            className="h-full bg-primary rounded-full transition-all"
                            style={{ width: `${Math.min((row.uso_atual / row.uso_maximo) * 100, 100)}%` }}
                        />
                    </div>
                </div>
            ),
            sortable: false,
        },
        {
            id: "validade",
            header: "Validade",
            accessorFn: (row) => `${row.data_inicio} → ${row.data_fim}`,
            cell: (_, row) => (
                <div className="flex flex-col text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <Calendar size={10} />
                        {format(new Date(row.data_inicio), "dd/MM/yy", { locale: ptBR })}
                        {" → "}
                        {format(new Date(row.data_fim), "dd/MM/yy", { locale: ptBR })}
                    </span>
                </div>
            ),
            exportFormat: (_, row) =>
                `${format(new Date(row.data_inicio), "dd/MM/yyyy")} → ${format(new Date(row.data_fim), "dd/MM/yyyy")}`,
        },
        {
            id: "status",
            header: "Status",
            accessorFn: (row) =>
                row.pode_ser_usado ? "disponivel" : row.ativo ? "esgotado" : "inativo",
            cell: (_, row) => {
                if (row.pode_ser_usado) {
                    return (
                        <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-200 text-[10px] font-black uppercase dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30">
                            Disponível
                        </Badge>
                    );
                }
                if (row.ativo) {
                    return (
                        <Badge className="bg-amber-500/10 text-amber-700 border-amber-200 text-[10px] font-black uppercase dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30">
                            Esgotado
                        </Badge>
                    );
                }
                return (
                    <StatusBadge status="inativo" />
                );
            },
            exportFormat: (_, row) =>
                row.pode_ser_usado ? "Disponível" : row.ativo ? "Esgotado" : "Inativo",
        },
        {
            id: "acoes",
            header: "",
            accessorKey: "id",
            cell: (_, row) => row.ativo ? (
                <div className="flex items-center gap-1 justify-end">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-700 hover:bg-red-50"
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleMutation.mutate(row.id);
                        }}
                        disabled={toggleMutation.isPending}
                    >
                        <ToggleLeft className="size-4 mr-1" /> Desativar
                    </Button>
                </div>
            ) : null,
            sortable: false,
            filterable: false,
            exportable: false,
        },
    ];

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-16 w-full" />
                <div className="grid gap-4 md:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-24" />
                    ))}
                </div>
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Cupons & Promoções"
                description="Gerencie cupons de desconto para assinaturas."
                icon={<Tag className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Planos & Preços", href: "/dashboard/backoffice/plans" },
                    { label: "Cupons de Desconto" },
                ]}
                actions={
                    <Button onClick={() => setShowCreateDialog(true)} size="sm" variant="outline" className="rounded-sm">
                        <Plus className="size-4 mr-2" /> Novo Cupom
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard
                    icon={Tag}
                    label="Total"
                    value={stats.total}
                    color="primary"
                />
                <StatCard
                    icon={Check}
                    label="Ativos"
                    value={stats.ativos}
                    color="success"
                />
                <StatCard
                    icon={ToggleRight}
                    label="Disponíveis"
                    value={stats.disponiveis}
                    color="backoffice"
                />
                <StatCard
                    icon={Percent}
                    label="Usos Realizados"
                    value={stats.usosTotal}
                    color="warning"
                />
            </div>

            {/* DataTable */}
            <DataTable
                data={cupons}
                columns={columns}
                searchPlaceholder="Buscar por código..."
                exportFileName="cupons-backoffice"
                emptyMessage="Nenhum cupom encontrado."
                rowClassName={() => "group"}
            />

            {/* Create Dialog */}
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-lg overflow-hidden p-0 flex flex-col">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="flex items-center gap-2">
                            <Tag className="size-5" /> Novo Cupom
                        </DialogTitle>
                        <DialogDescription>
                            Crie um cupom de desconto para oferecer aos assinantes.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="flex-1 overflow-y-auto px-6 py-5">
                        <div className="grid gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="codigo">Código do Cupom</Label>
                                <Input
                                    id="codigo"
                                    placeholder="Ex: AGRO2026"
                                    value={formData.codigo}
                                    onChange={(e) => setFormData({ ...formData, codigo: e.target.value.toUpperCase() })}
                                    className="font-mono uppercase"
                                />
                            </div>

                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="grid gap-2">
                                    <Label>Tipo de Desconto</Label>
                                    <Select
                                        value={formData.tipo}
                                        onValueChange={(v) => setFormData({ ...formData, tipo: v })}
                                    >
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="percentual">Percentual (%)</SelectItem>
                                            <SelectItem value="valor_fixo">Valor Fixo (R$)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="valor">Valor</Label>
                                    <Input
                                        id="valor"
                                        type="number"
                                        min={0}
                                        step={formData.tipo === "percentual" ? 1 : 0.01}
                                        max={formData.tipo === "percentual" ? 100 : undefined}
                                        value={formData.valor || ""}
                                        onChange={(e) => setFormData({ ...formData, valor: parseFloat(e.target.value) || 0 })}
                                    />
                                </div>
                            </div>

                            <div className="grid gap-2">
                                <Label>Aplicável em</Label>
                                <Select
                                    value={formData.aplicavel_em}
                                    onValueChange={(v) => setFormData({ ...formData, aplicavel_em: v })}
                                >
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="primeira_mensalidade">Primeira Mensalidade</SelectItem>
                                        <SelectItem value="todos_meses">Todos os Meses</SelectItem>
                                        <SelectItem value="plano_anual">Plano Anual</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {formData.aplicavel_em === "todos_meses" && (
                                <div className="grid gap-2">
                                    <Label htmlFor="duracao">Duração (meses)</Label>
                                    <Input
                                        id="duracao"
                                        type="number"
                                        min={1}
                                        placeholder="Ex: 3"
                                        value={formData.duracao_meses ?? ""}
                                        onChange={(e) => setFormData({ ...formData, duracao_meses: parseInt(e.target.value) || null })}
                                    />
                                </div>
                            )}

                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="grid gap-2">
                                    <Label htmlFor="uso_maximo">Uso Máximo (total)</Label>
                                    <Input
                                        id="uso_maximo"
                                        type="number"
                                        min={1}
                                        value={formData.uso_maximo}
                                        onChange={(e) => setFormData({ ...formData, uso_maximo: parseInt(e.target.value) || 1 })}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="uso_cliente">Uso por Cliente</Label>
                                    <Input
                                        id="uso_cliente"
                                        type="number"
                                        min={1}
                                        value={formData.uso_por_cliente}
                                        onChange={(e) => setFormData({ ...formData, uso_por_cliente: parseInt(e.target.value) || 1 })}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="grid gap-2">
                                    <Label htmlFor="data_inicio">Data Início</Label>
                                    <Input
                                        id="data_inicio"
                                        type="date"
                                        value={formData.data_inicio}
                                        onChange={(e) => setFormData({ ...formData, data_inicio: e.target.value })}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="data_fim">Data Fim</Label>
                                    <Input
                                        id="data_fim"
                                        type="date"
                                        value={formData.data_fim}
                                        onChange={(e) => setFormData({ ...formData, data_fim: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <DialogFooter className="border-t px-6 py-5">
                        <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                            Cancelar
                        </Button>
                        <Button
                            onClick={() => createMutation.mutate(formData)}
                            disabled={createMutation.isPending || !formData.codigo || !formData.valor || !formData.data_inicio || !formData.data_fim}
                        >
                            {createMutation.isPending ? "Criando..." : "Criar Cupom"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
