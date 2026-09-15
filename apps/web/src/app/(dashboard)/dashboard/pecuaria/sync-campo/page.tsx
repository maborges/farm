"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { 
    RefreshCcw, AlertCircle, CheckCircle2, 
    Clock, Smartphone, CalendarDays 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { format } from "date-fns";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card";

interface SyncStatusResponse {
    tarefa_campo_id: string;
    type: string;
    status_tarefa: string;
    status_processamento: string;
    total_processado: number;
    total_erros: number;
    mensagem_erro?: string;
    operador_id?: string;
    lote_id?: string;
    data_execucao?: string;
    data_processamento?: string;
}

interface SyncStatusPaginatedResponse {
    items: SyncStatusResponse[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

type StatusFilter = "" | "SUCCESS" | "ERROR" | "PENDENTE";

function isStatusFilter(value: string): value is StatusFilter {
    return value === "" || value === "SUCCESS" || value === "ERROR" || value === "PENDENTE";
}

export default function SyncCampoPage() {
    const queryClient = useQueryClient();
    const [page, setPage] = useState(1);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("");

    const { data, isLoading, isFetching } = useQuery({
        queryKey: ["campo-sync-status", page, statusFilter],
        queryFn: () => {
            const params = new URLSearchParams();
            params.append("page", page.toString());
            params.append("page_size", "50");
            if (statusFilter) {
                params.append("status_processamento", statusFilter);
            }
            return apiFetch<SyncStatusPaginatedResponse>(`/pecuaria/campo/sync-status?${params.toString()}`);
        },
        refetchInterval: 30000,
    });

    const reprocessMutation = useMutation({
        mutationFn: (tarefaId: string) => {
            return apiFetch(`/pecuaria/campo/tarefas/${tarefaId}/processar`, {
                method: "POST"
            });
        },
        onSuccess: () => {
            toast.success("Processamento concluído com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["campo-sync-status"] });
        },
        onError: (err: unknown) => {
            toast.error(err instanceof Error ? err.message : "Erro ao reprocessar tarefa");
        }
    });

    const handleReprocessar = (tarefaId: string) => {
        reprocessMutation.mutate(tarefaId);
    };

    const columns: ColumnDef<SyncStatusResponse>[] = [
        {
            id: "type",
            accessorKey: "type",
            header: "Atividade",
            cell: (_value, row) => (
                <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-sm bg-neutral-100 dark:bg-white/5 flex items-center justify-center">
                        <Smartphone size={16} className="text-neutral-500" />
                    </div>
                    <div>
                        <div className="font-bold">{row.type}</div>
                        <div className="text-xs text-foreground/50 truncate w-32" title={row.tarefa_campo_id}>
                            {row.tarefa_campo_id.split("-")[0]}...
                        </div>
                    </div>
                </div>
            )
        },
        {
            id: "status_processamento",
            accessorKey: "status_processamento",
            header: "Status Sincronização",
            cell: (status) => {
                if (status === "SUCCESS") return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle2 size={12} className="mr-1"/> Sincronizado</Badge>;
                if (status === "ERROR") return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200"><AlertCircle size={12} className="mr-1"/> Erro</Badge>;
                return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock size={12} className="mr-1"/> Pendente</Badge>;
            }
        },
        {
            id: "data_execucao",
            accessorKey: "data_execucao",
            header: "Data Execução",
            cell: (data) => {
                if (!data) return "-";
                return (
                    <div className="flex items-center text-sm">
                        <CalendarDays size={14} className="mr-2 text-foreground/40" />
                        {format(new Date(data), "dd/MM/yyyy HH:mm")}
                    </div>
                );
            }
        },
        {
            id: "resultados",
            header: "Resultados",
            accessorFn: (row) => row,
            cell: (_value, r) => {
                return (
                    <div className="text-sm">
                        <span className="text-green-600 font-medium">{r.total_processado} reg</span>
                        {r.total_erros > 0 && <span className="text-red-500 ml-2">{r.total_erros} erros</span>}
                        {r.mensagem_erro && <div className="text-red-500 text-xs max-w-[200px] truncate" title={r.mensagem_erro}>{r.mensagem_erro}</div>}
                    </div>
                );
            }
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            cell: (_value, row) => {
                const status = row.status_processamento;
                if (status === "SUCCESS") return null;
                
                return (
                    <div className="flex items-center gap-0 justify-end">
                        <Button 
                            variant="ghost" 
                            size="icon" 
                            className="size-7 rounded-sm text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                            onClick={() => handleReprocessar(row.tarefa_campo_id)}
                            disabled={reprocessMutation.isPending && reprocessMutation.variables === row.tarefa_campo_id}
                            title="Reprocessar"
                        >
                            <RefreshCcw size={14} className={reprocessMutation.isPending && reprocessMutation.variables === row.tarefa_campo_id ? "animate-spin" : ""} />
                        </Button>
                    </div>
                );
            }
        }
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader 
                title="Sync Campo"
                description="Monitoramento de tarefas pecuárias enviadas pelo aplicativo de campo"
                icon={<RefreshCcw size={22} className="text-primary" />}
                breadcrumbs={[
                    { label: "Pecuária", href: "/dashboard/pecuaria/rebanho" },
                    { label: "Sincronização do Campo" },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <div className="w-[200px]">
                            <Select 
                                value={statusFilter || "TODOS"} 
                                onValueChange={(val) => {
                                    setStatusFilter(val === "TODOS" ? "" : isStatusFilter(val) ? val : "");
                                }}
                            >
                                <SelectTrigger className="h-8 rounded-sm">
                                    <SelectValue placeholder="Todos os Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="TODOS">Todos os Status</SelectItem>
                                    <SelectItem value="SUCCESS">Sincronizados (Sucesso)</SelectItem>
                                    <SelectItem value="ERROR">Com Falha (Erro)</SelectItem>
                                    <SelectItem value="PENDENTE">Pendentes</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        
                        <Button variant="outline" size="sm" className="size-8 rounded-sm" onClick={() => queryClient.invalidateQueries({ queryKey: ["campo-sync-status"] })}>
                            <RefreshCcw size={14} className={isFetching ? "animate-spin" : ""} />
                        </Button>
                    </div>
                }
            />

            <Card className="shadow-sm">
                <CardHeader className="border-b">
                    <CardTitle>Lista de Tarefas</CardTitle>
                    <CardDescription>
                        Acompanhe o status das tarefas sincronizadas pelo campo.
                    </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                    <DataTable 
                        columns={columns} 
                        data={data?.items || []} 
                        isLoading={isLoading} 
                        searchable={true}
                        searchPlaceholder="Buscar tarefas..."
                        exportable={true}
                        exportFileName="tarefas_campo_export"
                        emptyMessage="Nenhuma tarefa encontrada."
                    />
                </CardContent>
            </Card>
        </div>
    );
}
