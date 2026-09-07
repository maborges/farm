"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { DollarSign, TrendingUp, Users, Wrench, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";

export interface DashboardRH {
    total_colaboradores_ativos: number; total_diaristas: number; total_empreiteiros: number;
    gasto_diarias_mes: number; gasto_empreitadas_mes: number;
}
export interface Diaria {
    id: string; colaborador_id: string; data: string; atividade: string;
    horas_trabalhadas: number; valor_diaria: number; status: string;
}
export interface Empreitada {
    id: string; colaborador_id: string; descricao: string; unidade: string;
    quantidade: number; valor_unitario: number; valor_total: number;
    status: string; data_inicio: string; data_fim: string | null;
}
export interface Colaborador { id: string; nome: string; }


function toBRL(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

export function FolhaPagamentoClient({ 
    initialDash, initialDiarias, initialEmpreitadas, initialColaboradores 
}: { 
    initialDash: DashboardRH, initialDiarias: Diaria[], initialEmpreitadas: Empreitada[], initialColaboradores: Colaborador[] 
}) {
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: dashboard, isLoading: loadingDash } = useQuery<DashboardRH>({
        queryKey: ["rh", "dashboard"],
        queryFn: () => apiFetch("/rh/dashboard"),
        initialData: initialDash,
    });
    const { data: diarias = [], isLoading: loadingD } = useQuery<Diaria[]>({
        queryKey: ["rh", "diarias", activeFazendaId],
        queryFn: () => apiFetch(`/rh/diarias${qs}`),
        initialData: initialDiarias,
    });
    const { data: empreitadas = [], isLoading: loadingE } = useQuery<Empreitada[]>({
        queryKey: ["rh", "empreitadas", activeFazendaId],
        queryFn: () => apiFetch(`/rh/empreitadas${qs}`),
        initialData: initialEmpreitadas,
    });
    const { data: colaboradores = [] } = useQuery<Colaborador[]>({
        queryKey: ["rh", "colaboradores", activeFazendaId],
        queryFn: () => apiFetch(`/rh/colaboradores${qs}`),
        initialData: initialColaboradores,
    });

    const nomeColaborador = (id: string) => colaboradores.find(c => c.id === id)?.nome || "—";

    const diariasCols: ColumnDef<Diaria>[] = [
        { id: "colaborador", header: "Colaborador", accessorKey: "colaborador_id", cell: (_v, d) => nomeColaborador(d.colaborador_id) },
        { id: "data", header: "Data", accessorKey: "data", cell: (_v, d) => new Date(d.data).toLocaleDateString("pt-BR") },
        { id: "atividade", header: "Atividade", accessorKey: "atividade" },
        { id: "horas", header: "Horas", accessorKey: "horas_trabalhadas", cell: (_v, d) => `${d.horas_trabalhadas}h` },
        { id: "valor", header: "Valor", accessorKey: "valor_diaria", cell: (_v, d) => toBRL(d.valor_diaria) },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, d) => <WorkflowStatusBadge status={d.status} /> },
    ];

    const empreitadasCols: ColumnDef<Empreitada>[] = [
        { id: "colaborador", header: "Colaborador", accessorKey: "colaborador_id", cell: (_v, e) => nomeColaborador(e.colaborador_id) },
        { id: "descricao", header: "Descrição", accessorKey: "descricao" },
        { id: "quantidade", header: "Qtd", accessorKey: "quantidade", cell: (_v, e) => `${e.quantidade} ${e.unidade}` },
        { id: "valor_total", header: "Total", accessorKey: "valor_total", cell: (_v, e) => toBRL(e.valor_total) },
        { id: "data_inicio", header: "Início", accessorKey: "data_inicio", cell: (_v, e) => new Date(e.data_inicio).toLocaleDateString("pt-BR") },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, e) => <WorkflowStatusBadge status={e.status} /> },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Folha de Pagamento"
                description="Consolidação de diárias e empreitadas por período"
                icon={<Wallet className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Pessoas & RH", href: "/dashboard/rh" },
                    { label: "Folha de Pagamento" }
                ]}
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Colaboradores Ativos", value: dashboard?.total_colaboradores_ativos ?? 0, icon: <Users className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                    { label: "Diaristas", value: dashboard?.total_diaristas ?? 0, icon: <Users className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                    { label: "Gasto Diárias (mês)", value: dashboard ? toBRL(dashboard.gasto_diarias_mes) : toBRL(0), icon: <DollarSign className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                    { label: "Gasto Empreitadas (mês)", value: dashboard ? toBRL(dashboard.gasto_empreitadas_mes) : toBRL(0), icon: <Wrench className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                ].map((k, i) => (
                    <Card key={i} className={`rounded-sm border-l-[3px] ${k.border} shadow-sm transition-all hover:shadow-md`}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{k.label}</CardTitle>
                            {k.icon}
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-black tabular-nums text-foreground">
                                {loadingDash ? <Skeleton className="h-6 w-14" /> : k.value}
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Tabs defaultValue="diarias">
                <TabsList>
                    <TabsTrigger value="diarias"><DollarSign className="size-3.5 mr-1" />Diárias ({diarias.length})</TabsTrigger>
                    <TabsTrigger value="empreitadas"><Wrench className="size-3.5 mr-1" />Empreitadas ({empreitadas.length})</TabsTrigger>
                </TabsList>
                <TabsContent value="diarias" className="mt-4">
                    {loadingD ? <Skeleton className="h-40 w-full" /> :
                        diarias.length === 0
                            ? <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10 rounded-lg border border-dashed"><div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4"><DollarSign className="size-6 text-primary" /></div><h3 className="text-lg font-semibold mb-1">Nenhuma diária registrada</h3><p className="text-sm text-muted-foreground max-w-sm">Os lançamentos de diárias aparecerão aqui.</p></div>
                            : <DataTable columns={diariasCols} data={diarias} />}
                </TabsContent>
                <TabsContent value="empreitadas" className="mt-4">
                    {loadingE ? <Skeleton className="h-40 w-full" /> :
                        empreitadas.length === 0
                            ? <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10 rounded-lg border border-dashed"><div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4"><Wrench className="size-6 text-primary" /></div><h3 className="text-lg font-semibold mb-1">Nenhuma empreitada registrada</h3><p className="text-sm text-muted-foreground max-w-sm">Os lançamentos de empreitadas aparecerão aqui.</p></div>
                            : <DataTable columns={empreitadasCols} data={empreitadas} />}
                </TabsContent>
            </Tabs>
        </div>
    );
}
