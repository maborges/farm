"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { ArrowDownCircle, ArrowUpCircle, Repeat, RefreshCw, SlidersHorizontal, ArrowDown, ArrowUp, BarChart3, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";

interface Movimentacao {
    id: string; tipo: string; produto_id: string; nome_produto: string | null;
    quantidade: number; unidade_medida: string; custo_unitario: number | null;
    deposito_origem_id: string | null; deposito_destino_id: string | null;
    data_movimentacao: string; observacoes: string | null;
}

const tipoIcon: Record<string, React.ReactNode> = {
    ENTRADA: <ArrowDownCircle className="size-3.5 text-green-600" />,
    SAIDA: <ArrowUpCircle className="size-3.5 text-red-500" />,
    TRANSFERENCIA: <RefreshCw className="size-3.5 text-blue-500" />,
    AJUSTE: <SlidersHorizontal className="size-3.5 text-yellow-600" />,
};

const tipoColor: Record<string, string> = {
    ENTRADA: "bg-green-100 text-green-800",
    SAIDA: "bg-red-100 text-red-700",
    TRANSFERENCIA: "bg-blue-100 text-blue-800",
    AJUSTE: "bg-yellow-100 text-yellow-800",
};

export default function MovimentacoesPage() {
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: movs = [], isLoading } = useQuery<Movimentacao[]>({
        queryKey: ["estoque", "movimentacoes", activeFazendaId],
        queryFn: () => apiFetch(`/estoque/movimentacoes${qs}`),
    });

    const entradas = movs.filter(m => m.tipo === "ENTRADA").length;
    const saidas = movs.filter(m => m.tipo === "SAIDA").length;
    const transferencias = movs.filter(m => m.tipo === "TRANSFERENCIA").length;

    const columns: ColumnDef<Movimentacao>[] = [
        {
            id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (_v, m) => (
                <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded ${tipoColor[m.tipo] || "bg-muted"}`}>
                    {tipoIcon[m.tipo]}{m.tipo}
                </span>
            )
        },
        { id: "produto", header: "Produto", accessorKey: "nome_produto", cell: (_v, m) => m.nome_produto || m.produto_id },
        { id: "quantidade", header: "Qtd", accessorKey: "quantidade", cell: (_v, m) => `${m.quantidade} ${m.unidade_medida}` },
        { id: "custo_unitario", header: "Custo Unit.", accessorKey: "custo_unitario", cell: (_v, m) => m.custo_unitario != null ? m.custo_unitario.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—" },
        { id: "data_movimentacao", header: "Data", accessorKey: "data_movimentacao", cell: (_v, m) => new Date(m.data_movimentacao).toLocaleDateString("pt-BR") },
        { id: "observacoes", header: "Obs.", accessorKey: "observacoes", cell: (_v, m) => <span className="text-xs text-muted-foreground truncate max-w-[180px] block">{m.observacoes || "—"}</span> },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Movimentações de Estoque"
                description="Histórico completo de entradas, saídas, transferências e ajustes"
                icon={<Activity className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Operacional", href: "/dashboard/operacional" }, { label: "Estoque", href: "/dashboard/operacional/estoque" }, { label: "Movimentações" }]}
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Total Movimentações", value: movs.length, icon: BarChart3, bg: "bg-primary/10", color: "text-primary" },
                    { label: "Entradas Realizadas", value: entradas, icon: ArrowDown, bg: "bg-emerald-100 dark:bg-emerald-900/30", color: "text-emerald-600" },
                    { label: "Saídas Realizadas", value: saidas, icon: ArrowUp, bg: "bg-red-100 dark:bg-red-900/30", color: "text-red-500" },
                    { label: "Transferências", value: transferencias, icon: RefreshCw, bg: "bg-blue-100 dark:bg-blue-900/30", color: "text-blue-500" },
                ].map((k, i) => (
                    <Card key={i} className="rounded-sm shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className={cn("size-10 rounded-sm flex items-center justify-center shrink-0", k.bg)}>
                                <k.icon className={cn("size-5", k.color)} />
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{k.label}</p>
                                <div className="text-2xl font-black tabular-nums tracking-tight mt-0.5">
                                    {isLoading ? <Skeleton className="h-7 w-8" /> : k.value}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {isLoading ? <Skeleton className="h-40 w-full rounded-sm" /> :
                movs.length === 0
                    ? <div className="text-center py-12 text-sm text-muted-foreground rounded-sm border-2 border-dashed bg-muted/20">
                        <Repeat className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                        <p>Nenhuma movimentação registrada no período.</p>
                      </div>
                    : <DataTable columns={columns} data={movs} searchable exportable />
            }
        </div>
    );
}
