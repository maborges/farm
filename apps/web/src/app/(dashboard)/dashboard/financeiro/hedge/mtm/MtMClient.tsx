"use client";

import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { TrendingUp, TrendingDown, Activity, DollarSign, Target, RefreshCw, AlertTriangle, Calculator } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { DataTable } from "@/components/ui/data-table";
import { columns, EnrichedSnapshot } from "./columns";
import { HedgePositionSnapshot } from "../types";

type SafraOption = {
    id: string;
    ano_safra: string;
    cultura?: string;
};

type ContratoOption = {
    id: string;
    commodity: string;
    mes_vencimento: string | null;
    tipo_posicao: string;
};

type NotificacaoHedge = {
    id: string;
    tipo: string;
    titulo: string;
    mensagem: string;
    nivel: "DANGER" | "WARNING" | "INFO" | string;
};

type ReprocessarResponse = {
    processados: number;
    atualizados: number;
    criados: number;
};

export function MtMClient({ 
    initialSnapshots, safras, contratos, initialSafraId 
}: { 
    initialSnapshots: HedgePositionSnapshot[], safras: SafraOption[], contratos: ContratoOption[], initialSafraId: string 
}) {
    const router = useRouter();
    const [safraId, setSafraId] = useState(initialSafraId);
    
    // Reprocessamento states
    const [isReprocessOpen, setIsReprocessOpen] = useState(false);
    const reprocessForm = useForm({
        defaultValues: { data_inicio: "", data_fim: "", motivo: "" }
    });
    const [isReprocessing, setIsReprocessing] = useState(false);
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const qs = safraId ? `?safra_id=${safraId}&limit=100` : "?limit=100";

    const { data: snapshots, isLoading } = useQuery<HedgePositionSnapshot[]>({
        queryKey: ["financeiro", "hedge", "snapshots", safraId],
        queryFn: () => apiFetch(`/financeiro/hedge/snapshots${qs}`),
        initialData: initialSnapshots || [],
    });

    const { data: notificacoes } = useQuery<NotificacaoHedge[]>({
        queryKey: ["notificacoes", "hedge_alertas"],
        queryFn: () => apiFetch("/notificacoes?lida=false&limit=50"),
    });

    const hedgeAlerts = useMemo(() => {
        if (!notificacoes) return [];
        return notificacoes.filter(n => n.tipo.startsWith("HEDGE_"));
    }, [notificacoes]);

    const handleSafraChange = (val: string) => {
        setSafraId(val === "all" ? "" : val);
        router.push(`/dashboard/financeiro/hedge/mtm${val === "all" ? "" : `?safra_id=${val}`}`);
    };

    const handleReprocess = async (data: { data_inicio: string; data_fim: string; motivo: string }) => {
        try {
            setIsReprocessing(true);
            const payload = {
                ...data,
                safra_id: safraId || null
            };
            const res = await apiFetch<ReprocessarResponse>("/financeiro/hedge/snapshots/reprocessar", {
                method: "POST",
                body: JSON.stringify(payload)
            });
            toast({
                title: "Sucesso!",
                description: `${res.processados} processados, ${res.atualizados} atualizados, ${res.criados} criados.`,
            });
            setIsReprocessOpen(false);
            reprocessForm.reset();
            queryClient.invalidateQueries({ queryKey: ["financeiro", "hedge", "snapshots"] });
        } catch (err: any) {
            toast({ title: "Erro", description: err.message || "Erro ao reprocessar.", variant: "destructive" });
        } finally {
            setIsReprocessing(false);
        }
    };

    // Enrich snapshots with names from related entities
    const enrichedData: EnrichedSnapshot[] = useMemo(() => {
        if (!snapshots) return [];
        return snapshots.map(snap => {
            const safra = safras.find(s => s.id === snap.safra_id);
            const contrato = contratos.find(c => c.id === snap.contrato_futuro_id);
            return {
                ...snap,
                nome_safra: safra ? (safra.cultura ? `${safra.ano_safra} - ${safra.cultura}` : safra.ano_safra) : "—",
                nome_contrato: contrato ? `${contrato.commodity} ${contrato.mes_vencimento || ""} ${contrato.tipo_posicao}` : "—",
                nome_commodity: contrato ? contrato.commodity : "—"
            };
        });
    }, [snapshots, safras, contratos]);

    const totalMtM = enrichedData.reduce((acc, curr) => acc + curr.mtm_valor, 0);
    const qtdAbertaTotal = enrichedData.reduce((acc, curr) => acc + curr.quantidade_aberta, 0);
    const mtmIsNegative = totalMtM < 0;

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-500">
            <PageHeader
                title="Mark-to-Market (MTM)"
                description="Acompanhamento diário do PnL não realizado da sua posição de Risco"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Mark-to-Market (MTM)" }
                ]}
                icon={<Calculator className="text-primary" size={22} />}
                actions={
                    <div className="flex items-center gap-2">
                        <Dialog open={isReprocessOpen} onOpenChange={setIsReprocessOpen}>
                            <DialogTrigger asChild>
                                <Button variant="outline" size="sm" className="h-8 rounded-sm font-bold border-primary text-primary hover:bg-primary/5">
                                    <RefreshCw className="mr-2 size-4" />
                                    Reprocessar MtM
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-md rounded-sm">
                                <DialogHeader>
                                    <DialogTitle>Reprocessar Mark-to-Market</DialogTitle>
                                </DialogHeader>
                                <Form {...reprocessForm}>
                                    <form onSubmit={reprocessForm.handleSubmit(handleReprocess)}>
                                        <DialogBody className="space-y-4">
                                            <div className="grid grid-cols-2 gap-4">
                                                <FormField
                                                    control={reprocessForm.control}
                                                    name="data_inicio"
                                                    rules={{ required: "Obrigatório" }}
                                                    render={({ field }) => (
                                                        <FormItem>
                                                            <FormLabel>Data Início *</FormLabel>
                                                            <FormControl>
                                                                <Input type="date" className="h-8 rounded-sm text-sm" {...field} />
                                                            </FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                                <FormField
                                                    control={reprocessForm.control}
                                                    name="data_fim"
                                                    rules={{ required: "Obrigatório" }}
                                                    render={({ field }) => (
                                                        <FormItem>
                                                            <FormLabel>Data Fim *</FormLabel>
                                                            <FormControl>
                                                                <Input type="date" className="h-8 rounded-sm text-sm" {...field} />
                                                            </FormControl>
                                                            <FormMessage />
                                                        </FormItem>
                                                    )}
                                                />
                                            </div>
                                            <FormField
                                                control={reprocessForm.control}
                                                name="motivo"
                                                rules={{ required: "Obrigatório", minLength: { value: 10, message: "Mínimo de 10 caracteres" } }}
                                                render={({ field }) => (
                                                    <FormItem>
                                                        <FormLabel>Motivo do Reprocessamento *</FormLabel>
                                                        <FormControl>
                                                            <Textarea 
                                                                className="rounded-sm text-sm"
                                                                placeholder="Descreva por que o reprocessamento é necessário..."
                                                                {...field}
                                                            />
                                                        </FormControl>
                                                        <FormMessage />
                                                    </FormItem>
                                                )}
                                            />
                                        </DialogBody>
                                        <DialogFooter>
                                            <Button type="submit" size="sm" className="rounded-sm" disabled={isReprocessing}>
                                                {isReprocessing ? "Processando..." : "Confirmar"}
                                            </Button>
                                        </DialogFooter>
                                    </form>
                                </Form>
                            </DialogContent>
                        </Dialog>
                        <div className="w-64">
                            <Select value={safraId || "all"} onValueChange={handleSafraChange}>
                                <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue placeholder="Filtrar por Safra" /></SelectTrigger>
                                <SelectContent className="rounded-sm">
                                    <SelectItem value="all" className="text-sm">Todas as Safras</SelectItem>
                                    {safras.map(s => <SelectItem key={s.id} value={s.id} className="text-sm">{s.cultura ? `${s.ano_safra} - ${s.cultura}` : s.ano_safra}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                }
            />

            {hedgeAlerts.length > 0 && (
                <Card className="rounded-sm border-l-4 border-l-destructive">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center text-destructive">
                            <AlertTriangle className="mr-2 h-4 w-4" />
                            Alertas de Risco Ativos ({hedgeAlerts.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {hedgeAlerts.map(alerta => (
                                <div key={alerta.id} className="flex items-start justify-between text-sm p-3 bg-muted/30 rounded-sm border">
                                    <div>
                                        <span className="font-semibold block">{alerta.titulo}</span>
                                        <span className="text-muted-foreground">{alerta.mensagem}</span>
                                    </div>
                                    <Badge variant={alerta.nivel === "DANGER" ? "destructive" : alerta.nivel === "WARNING" ? "default" : "secondary"}>
                                        {alerta.nivel}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">PnL Não Realizado (Total MTM)</CardTitle>
                        <DollarSign className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black tabular-nums flex items-center">
                            {isLoading ? <Skeleton className="h-8 w-24 rounded-sm" /> : (
                                <span className={mtmIsNegative ? "text-red-600" : "text-emerald-600"}>
                                    {totalMtM.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </span>
                            )}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Quantidade Aberta Exposta</CardTitle>
                        <Activity className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums text-neutral-800 dark:text-neutral-200">
                            {isLoading ? <Skeleton className="h-8 w-20 rounded-sm" /> : `${qtdAbertaTotal.toLocaleString("pt-BR")} sc`}
                        </div>
                    </CardContent>
                </Card>
                <Card className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">Projeções Consolidadas</CardTitle>
                        <Target className="size-4 text-muted-foreground opacity-50" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black tabular-nums">
                            {isLoading ? <Skeleton className="h-8 w-16 rounded-sm" /> : enrichedData.length}
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="mt-8 bg-white rounded-sm shadow-sm border p-4">
                {isLoading ? (
                    <div className="space-y-4">
                        <Skeleton className="h-10 w-full rounded-sm" />
                        <Skeleton className="h-10 w-full rounded-sm" />
                        <Skeleton className="h-10 w-full rounded-sm" />
                    </div>
                ) : (
                    <DataTable 
                        columns={columns} 
                        data={enrichedData} 
                    />
                )}
            </div>
        </div>
    );
}
