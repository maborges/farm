"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Eye, Recycle } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Switch } from "@/components/ui/switch";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/shared/page-header";
import { cn } from "@/lib/utils";
import type { DevolucaoEmbalagem } from "@farm/zod-schemas";

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

function diasParaPrazo(prazo: string): number {
    const hoje = new Date();
    const limite = new Date(`${prazo}T00:00:00`);
    return Math.ceil((limite.getTime() - hoje.getTime()) / (1000 * 60 * 60 * 24));
}

export function LogisticaReversaClient({ initialDevolucoes }: { initialDevolucoes: DevolucaoEmbalagem[] }) {
    const [apenasPendentes, setApenasPendentes] = useState(false);

    const { data: devolucoes = [], isLoading } = useQuery<DevolucaoEmbalagem[]>({
        queryKey: ["agricola", "logistica-reversa-embalagens"],
        queryFn: () => apiFetch<DevolucaoEmbalagem[]>("/agricola/logistica-reversa-embalagens"),
        initialData: initialDevolucoes,
    });

    const lista = apenasPendentes ? devolucoes.filter((d) => d.status === "PENDENTE") : devolucoes;

    const columns: ColumnDef<DevolucaoEmbalagem>[] = useMemo(() => [
        {
            id: "produto",
            header: "Produto",
            accessorKey: "produto_id",
            cell: (_value, row) => <span className="font-medium">{row.produto_id.slice(0, 8)}</span>,
        },
        {
            id: "quantidade",
            header: "Embalagens (devolvidas/compradas)",
            accessorFn: (row) => row.quantidade_embalagens_devolvidas,
            cell: (_value, row) => (
                <span className="text-sm">
                    {row.quantidade_embalagens_devolvidas} / {row.quantidade_embalagens_compradas}
                </span>
            ),
        },
        {
            id: "data_compra",
            header: "Compra",
            accessorKey: "data_compra",
            cell: (_value, row) => formatDate(row.data_compra),
        },
        {
            id: "prazo_limite",
            header: "Prazo legal (1 ano)",
            accessorKey: "prazo_limite",
            cell: (_value, row) => {
                const dias = diasParaPrazo(row.prazo_limite);
                const critico = row.status === "PENDENTE" && dias <= 30;
                return (
                    <span className={cn("text-sm", critico && "text-destructive font-semibold")}>
                        {formatDate(row.prazo_limite)}
                        {critico && dias >= 0 && ` (${dias}d)`}
                    </span>
                );
            },
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            filterOptions: [
                { value: "PENDENTE", label: "Pendente" },
                { value: "DEVOLVIDO", label: "Devolvido" },
                { value: "VENCIDO", label: "Vencido" },
            ],
            cell: (_value, row) => <WorkflowStatusBadge status={row.status} />,
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            isActionColumn: true,
            cell: (_value, row) => (
                <div className="flex items-center justify-end gap-1">
                    <Button size="icon-sm" variant="ghost" title="Ver detalhes" asChild>
                        <Link href={`/dashboard/agricola/logistica-reversa-embalagens/${row.id}`}>
                            <Eye className="size-3.5" />
                        </Link>
                    </Button>
                </div>
            ),
        },
    ], []);

    return (
        <div className="flex flex-col gap-5 p-4 sm:p-6">
            <PageHeader
                title="Logística Reversa de Embalagens"
                description="Devolução de embalagens vazias de defensivos ao posto de recebimento, com prazo legal de 1 ano (Lei 9.974/2000)."
                icon={<Recycle className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Agricultura", href: "/dashboard/agricola" },
                    { label: "Logística Reversa de Embalagens" },
                ]}
                actions={
                    <div className="flex h-9 items-center gap-2 rounded-sm border bg-background px-3 text-xs text-muted-foreground">
                        <Switch checked={apenasPendentes} onCheckedChange={setApenasPendentes} aria-label="Somente pendentes" />
                        <span>Somente pendentes</span>
                    </div>
                }
            />

            <Card className="rounded-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold">Pendências de devolução</CardTitle>
                </CardHeader>
                <CardContent>
                    <DataTable
                        data={lista}
                        columns={columns}
                        isLoading={isLoading}
                        searchPlaceholder="Buscar por produto..."
                        exportFileName="logistica-reversa-embalagens"
                        emptyMessage="Nenhuma pendência de devolução. Pendências nascem automaticamente ao receber compras de defensivos com embalagens registradas."
                    />
                </CardContent>
            </Card>
        </div>
    );
}
