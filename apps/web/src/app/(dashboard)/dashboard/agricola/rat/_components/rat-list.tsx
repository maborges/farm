"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { FileText, MoreHorizontal, Eye, Edit, Trash2 } from "lucide-react";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useHasTier } from "@/hooks/use-has-tier";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Lock } from "lucide-react";
import Link from "next/link";

interface RelatorioTecnico {
    id: string;
    safra_id: string;
    talhao_id: string;
    talhao_nome?: string | null;
    data_visita: string;
    responsavel_tecnico: string;
    objetivo_visita: string;
    status: string;
    safra_nome?: string;
}


export function RelatorioTecnicoList() {
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const { activeFazendaId } = useAppStore();
    const { data: reports = [], isLoading } = useQuery<RelatorioTecnico[]>({
        queryKey: ["relatorios-tecnicos"],
        queryFn: () => apiFetch("/agronomo/rat/"),
        enabled: hasProfessionalTier,
    });

    const { data: talhoes = [] } = useQuery<any[]>({
        queryKey: ["talhoes", activeFazendaId, "rat"],
        queryFn: () => apiFetch(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && hasProfessionalTier,
    });

    const getTalhaoNome = (id: string) => talhoes.find((talhao) => talhao.id === id)?.nome ?? "Talhão não informado";

    if (!hasProfessionalTier) {
        return (
            <div className="p-6">
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Relatórios Técnicos disponíveis no PROFISSIONAL</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>O plano atual mantém o acesso operacional à fazenda. RATs e recomendações técnicas exigem tier PROFISSIONAL.</p>
                        <Button asChild size="sm" className="rounded-sm">
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    const columns: ColumnDef<RelatorioTecnico>[] = [
        {
            id: "data_visita",
            header: "Data",
            accessorKey: "data_visita",
            sortable: true,
            cell: (value: string) => (
                <span className="tabular-nums font-medium">
                    {format(new Date(value), "dd/MM/yyyy", { locale: ptBR })}
                </span>
            ),
        },
        {
            id: "talhao",
            header: "Talhão",
            accessorKey: "talhao_id",
            sortable: true,
            cell: (value: string, row: RelatorioTecnico) => (
                <span className="font-medium">{row.talhao_nome || getTalhaoNome(value)}</span>
            ),
        },
        {
            id: "responsavel",
            header: "Responsável",
            accessorKey: "responsavel_tecnico",
            sortable: true,
        },
        {
            id: "objetivo",
            header: "Objetivo",
            accessorKey: "objetivo_visita",
            cell: (value: string) => (
                <span className="text-muted-foreground truncate max-w-[200px] block" title={value}>
                    {value}
                </span>
            ),
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            sortable: true,
            cell: (value: string) => <WorkflowStatusBadge status={value} />,
        },
        {
            id: "actions",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_, row) => (
                <div className="flex items-center gap-0 justify-end">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="size-7">
                                <MoreHorizontal className="size-3.5" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="rounded-sm">
                            <DropdownMenuItem className="gap-2 text-xs">
                                <Eye className="size-3.5 text-blue-500" /> Visualizar
                            </DropdownMenuItem>
                            <DropdownMenuItem className="gap-2 text-xs">
                                <Edit className="size-3.5 text-amber-500" /> Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem className="gap-2 text-xs text-destructive">
                                <Trash2 className="size-3.5" /> Excluir
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            ),
        },
    ];

    return (
        <DataTable
            data={reports}
            columns={columns}
            searchable
            searchPlaceholder="Buscar por responsável ou objetivo..."
            exportable
            exportFileName="relatorios_tecnicos"
            emptyMessage={isLoading ? "Carregando relatórios..." : "Nenhum relatório técnico encontrado."}
        />
    );
}
