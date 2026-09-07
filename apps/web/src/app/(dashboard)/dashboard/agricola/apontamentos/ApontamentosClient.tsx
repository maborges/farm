"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { ClipboardList, Plus, Calendar, Tractor, CheckCircle2, Clock } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { useAppStore } from "@/lib/stores/app-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { getWorkflowStyle } from "@/components/ui/status-badge";

export interface Operacao {
    id: string;
    tipo: string;
    descricao?: string;
    status: string;
    area_aplicada_ha?: number;
    custo_total?: number;
    data_prevista?: string;
    data_realizada?: string;
}

export interface TipoOperacao {
    id: string;
    tipo_operacao: string;
    fases_permitidas: string[];
    descricao?: string | null;
}

export function ApontamentosClient({ 
    initialOrdens, initialTipos, initialActiveFazendaId 
}: { 
    initialOrdens: Operacao[], initialTipos: TipoOperacao[], initialActiveFazendaId?: string 
}) {
    const { activeFazendaId, isVisaoGrupo } = useAppStore();

    const { data: ordens = [], isLoading } = useQuery<Operacao[]>({
        // A chave do query muda caso a visao global ou ID da fazenda mude
        queryKey: ["operacoes", activeFazendaId, isVisaoGrupo],
        queryFn: async () => {
            try {
                return await apiFetch<any[]>(
                    isVisaoGrupo ? "/operacoes" : `/operacoes?unidade_produtiva_id=${activeFazendaId}`
                );
            } catch (err) {
                console.error("Erro ao buscar operacoes", err);
                return [];
            }
        },
        initialData: activeFazendaId === initialActiveFazendaId && !isVisaoGrupo ? initialOrdens : undefined,
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes", "tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        initialData: initialTipos,
        staleTime: 5 * 60 * 1000,
    });

    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao || tipo;

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'PLANEJADA': return <Calendar className="h-3.5 w-3.5" />;
            case 'EM_ANDAMENTO': return <Clock className="h-3.5 w-3.5" />;
            case 'REALIZADA': return <CheckCircle2 className="h-3.5 w-3.5" />;
            default: return <Tractor className="h-3.5 w-3.5" />;
        }
    };



    const columns: ColumnDef<Operacao>[] = [
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => {
                const style = getWorkflowStyle(String(value));
                return (
                    <Badge className={`flex w-max items-center gap-1.5 ${style.className}`}>
                        {getStatusIcon(String(value))}
                        {style.label}
                    </Badge>
                );
            },
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar status...",
            exportFormat: (value) => String(value).replace("_", " "),
        },
        {
            id: "atividade",
            header: "Operação / Trato",
            accessorKey: "tipo",
            cell: (value, row) => (
                <div>
                    <p className="font-semibold text-primary">{getTipoLabel(value)}</p>
                    <p className="text-xs text-muted-foreground font-medium truncate max-w-[250px] mt-0.5">
                        {row.descricao || "Sem detalhes adicionais."}
                    </p>
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar operação...",
            exportFormat: (value, row) => `${getTipoLabel(value)} - ${row.descricao || ""}`,
        },
        {
            id: "area",
            header: "Área Aplicada",
            accessorKey: "area_aplicada_ha",
            cell: (value) => (
                <span className="text-sm">{value ? `${value.toFixed(2)} ha` : '-'}</span>
            ),
            sortable: true,
            exportFormat: (value) => value ? `${value.toFixed(2)} ha` : '-',
        },
        {
            id: "custo",
            header: "Custo Total",
            accessorKey: "custo_total",
            cell: (value) => (
                <span className="text-sm font-medium">
                    {value && value > 0 ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value) : '-'}
                </span>
            ),
            sortable: true,
            exportFormat: (value) => value && value > 0 ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value) : '-',
        },
        {
            id: "previsao",
            header: "Previsão",
            accessorKey: "data_prevista",
            cell: (value) => (
                <span className="text-sm">{value ? new Date(value).toLocaleDateString('pt-BR') : '-'}</span>
            ),
            sortable: true,
            exportFormat: (value) => value ? new Date(value).toLocaleDateString('pt-BR') : '-',
        },
        {
            id: "execucao",
            header: "Execução",
            accessorKey: "data_realizada",
            cell: (value) => (
                <span className="text-sm">{value ? new Date(value).toLocaleDateString('pt-BR') : '-'}</span>
            ),
            sortable: true,
            exportFormat: (value) => value ? new Date(value).toLocaleDateString('pt-BR') : '-',
        },
    ];


    return (
        <div className="flex flex-col gap-6">
            <PageHeader
                title="Caderno de Campo"
                description="Gerencie operações agrícolas, aplicações e tratos culturais da lavoura."
                icon={<ClipboardList className="h-7 w-7 text-primary" />}
                actions={
                    <Button size="sm" className="w-full sm:w-auto">
                        <Plus className="mr-2 size-4" />
                        Nova Operação
                    </Button>
                }
            />

            {/* DataTable */}
            <DataTable
                data={ordens}
                columns={columns}
                searchable
                searchPlaceholder="Buscar operação, tipo..."
                exportable
                exportFileName="apontamentos-campo"
                emptyMessage="Nenhum apontamento encontrado."
            />
        </div>
    );
}
