"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Syringe, Plus, FlaskConical, AlertTriangle,
    CheckCircle2, Clock, Layers, Search, ArrowRight, ShieldAlert, XCircle, Save, MoreHorizontal,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

const schema = z.object({
    safra_id: z.string().min(1, "Safra obrigatória"),
    talhao_id: z.string().min(1, "Talhão obrigatório"),
    data_avaliacao: z.string().min(1, "Data obrigatória"),
    tipo: z.string().optional(),
    nome_popular: z.string().optional(),
    nivel_infestacao: z.number().optional(),
    unidade_medida: z.string().optional(),
    acao_tomada: z.string().optional(),
    observacoes: z.string().optional(),
});
type FormData = z.infer<typeof schema>;

interface Safra { id: string; ano_safra: string; cultura: string; status: string; }
interface AreaRural { id: string; nome: string; area_ha: number; }

const STATUS_COLORS: Record<string, string> = {
    PENDENTE: "bg-yellow-500/10 text-yellow-600 border-yellow-200",
    EM_ANDAMENTO: "bg-blue-500/10 text-blue-600 border-blue-200",
    CONCLUIDO: "bg-green-500/10 text-green-600 border-green-200",
    CANCELADO: "bg-red-500/10 text-red-600 border-red-200",
};

const TIPO_ICONS: Record<string, React.ReactNode> = {
    DOENCA: <AlertTriangle size={14} className="text-red-500" />,
    PRAGA: <Syringe size={14} className="text-orange-500" />,
    ERVA_DANINHA: <Layers size={14} className="text-green-700" />,
};

export default function DefensivosPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState("");
    const [isOpen, setIsOpen] = useState(false);

    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch("/safras"),
    });

    const { data: talhoes = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais", "talhoes", activeFazendaId],
        queryFn: () => {
            const params = new URLSearchParams({ tipo: "TALHAO" });
            if (activeFazendaId) params.set("unidade_produtiva_id", activeFazendaId);
            return apiFetch(`/cadastros/areas-rurais?${params}`);
        },
    });

    const form = useForm<FormData>({
        resolver: zodResolver(schema),
        defaultValues: {
            safra_id: "", talhao_id: "",
            data_avaliacao: new Date().toISOString().split("T")[0],
            tipo: "", nome_popular: "", unidade_medida: "", acao_tomada: "", observacoes: "",
        },
    });

    const createMutation = useMutation({
        mutationFn: (data: FormData) => apiFetch("/monitoramentos/", {
            method: "POST",
            body: JSON.stringify({
                ...data,
                nivel_infestacao: data.nivel_infestacao || null,
                tipo: data.tipo || null,
                nome_popular: data.nome_popular || null,
                unidade_medida: data.unidade_medida || null,
                acao_tomada: data.acao_tomada || null,
                observacoes: data.observacoes || null,
            }),
        }),
        onSuccess: () => {
            toast.success("Monitoramento registrado!");
            queryClient.invalidateQueries({ queryKey: ["monitoramentos"] });
            setIsOpen(false);
            form.reset();
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao registrar"),
    });

    const activeSafras = safras.filter((s) => !["ENCERRADA", "CANCELADA"].includes(s.status));

    const { data: monitoramentos = [], isLoading } = useQuery({
        queryKey: ["monitoramentos", activeFazendaId],
        queryFn: () => apiFetch<any[]>(`/monitoramentos/`),
        enabled: !!activeFazendaId,
    });

    const columns: ColumnDef<any>[] = [
        {
            id: "tipo",
            header: "Tipo",
            accessorFn: (row) => row.tipo_praga || "Ocorrência",
            cell: (value, row) => (
                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-sm bg-muted flex items-center justify-center shrink-0">
                        {TIPO_ICONS[row.tipo_praga] || <Syringe size={14} />}
                    </div>
                    <div>
                        <p className="font-bold text-sm truncate">{value}</p>
                        <p className="text-xs text-muted-foreground truncate">{row.descricao || "Sem descrição"}</p>
                    </div>
                </div>
            ),
        },
        {
            id: "safra",
            header: "Safra / Talhão",
            accessorFn: (row) => `${row.safra?.ano_safra || ""} ${row.talhao?.nome || ""}`,
            cell: (value, row) => (
                <div>
                    <p className="font-bold text-xs">{row.safra?.ano_safra || "N/A"}</p>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-widest">{row.talhao?.nome || "Sem talhão"}</p>
                </div>
            )
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => (
                <Badge className={`text-[10px] font-black border uppercase ${STATUS_COLORS[value as string] || "bg-muted"}`}>
                    {value as string}
                </Badge>
            ),
        },
        {
            id: "acoes",
            header: "",
            isActionColumn: true,
            cell: (value, row) => (
                <div className="flex justify-end gap-0">
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        className="size-7 text-primary hover:text-primary hover:bg-primary/10 rounded-sm"
                        onClick={() => toast.info("Em breve: Detalhes")}
                    >
                        <Search className="size-3.5" />
                    </Button>
                    <Button 
                        variant="ghost" 
                        size="icon" 
                        className="size-7 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-sm"
                        onClick={() => toast.info("Em breve: Cancelar")}
                    >
                        <XCircle className="size-3.5" />
                    </Button>
                </div>
            ),
        }
    ];

    const stats = {
        total: monitoramentos.length,
        pendentes: monitoramentos.filter((m: any) => m.status === "PENDENTE").length,
        concluidos: monitoramentos.filter((m: any) => m.status === "CONCLUIDO").length,
    };

    return (
        <>
        <div className="flex-1 p-6 space-y-6 max-w-6xl w-full">
            <PageHeader
                title="Fitossanitário"
                description="Monitoramento de pragas, doenças e herbicidas."
                icon={<ShieldAlert className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Fitossanitário" }]}
                actions={
                    <Button variant="outline" size="sm" onClick={() => setIsOpen(true)}>
                        <Plus className="size-3.5 mr-1.5" /> Novo Monitoramento
                    </Button>
                }
            />

            {/* KPI Cards */}
            <div className="grid gap-4 sm:grid-cols-3">
                {[
                    { label: "Ocorrências Totais", value: stats.total, sub: "todos registrados", icon: FlaskConical, color: "text-purple-600", bg: "bg-purple-100 dark:bg-purple-900/30" },
                    { label: "Pendentes de Ação", value: stats.pendentes, sub: "aguardando", icon: Clock, color: "text-amber-600", bg: "bg-amber-100 dark:bg-amber-900/30" },
                    { label: "Concluídos", value: stats.concluidos, sub: "resolvidos", icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-100 dark:bg-emerald-900/30" },
                ].map((k) => (
                    <Card key={k.label} className="shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className={`size-10 rounded-sm flex items-center justify-center shrink-0 ${k.bg}`}>
                                <k.icon className={`size-5 ${k.color}`} />
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">{k.label}</p>
                                <p className="text-2xl font-bold tabular-nums leading-tight mt-0.5">{k.value}</p>
                                <p className="text-xs text-muted-foreground mt-1">{k.sub}</p>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Table */}
            <DataTable
                data={monitoramentos}
                columns={columns}
                exportFileName="fitossanitario"
            />
        </div>
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogContent className="max-w-lg p-0 rounded-sm overflow-hidden">
                <form onSubmit={form.handleSubmit((d: FormData) => createMutation.mutate(d))} className="flex flex-col max-h-[85vh]">
                    <DialogHeader className="px-5 py-4 border-b bg-muted/20">
                        <DialogTitle className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                <ShieldAlert className="size-4 text-primary" />
                            </div>
                            Novo Monitoramento
                        </DialogTitle>
                    </DialogHeader>
                    <DialogBody className="grid gap-4 px-5 py-5 overflow-y-auto">
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label className="text-xs">Safra *</Label>
                                <Controller name="safra_id" control={form.control} render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            {activeSafras.map((s) => (
                                                <SelectItem key={s.id} value={s.id}>{s.cultura} — {s.ano_safra}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )} />
                                {form.formState.errors.safra_id && <p className="text-xs text-destructive">{form.formState.errors.safra_id.message}</p>}
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs">Talhão *</Label>
                                <Controller name="talhao_id" control={form.control} render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            {talhoes.map((t) => (
                                                <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )} />
                                {form.formState.errors.talhao_id && <p className="text-xs text-destructive">{form.formState.errors.talhao_id.message}</p>}
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label className="text-xs">Data da Avaliação *</Label>
                                <Input type="date" className="h-8 rounded-sm text-xs" {...form.register("data_avaliacao")} />
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs">Tipo</Label>
                                <Controller name="tipo" control={form.control} render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="PRAGA">Praga</SelectItem>
                                            <SelectItem value="DOENCA">Doença</SelectItem>
                                            <SelectItem value="ERVA_DANINHA">Erva Daninha</SelectItem>
                                        </SelectContent>
                                    </Select>
                                )} />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label className="text-xs">Nome Popular</Label>
                                <Input className="h-8 rounded-sm text-xs" placeholder="Ex: Lagarta-do-cartucho" {...form.register("nome_popular")} />
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs">Ação Tomada</Label>
                                <Controller name="acao_tomada" control={form.control} render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="CONTROLE">Controle</SelectItem>
                                            <SelectItem value="MONITORAR">Monitorar</SelectItem>
                                            <SelectItem value="NENHUMA">Nenhuma</SelectItem>
                                        </SelectContent>
                                    </Select>
                                )} />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1.5">
                                <Label className="text-xs">Nível de Infestação</Label>
                                <Input type="number" step="0.01" className="h-8 rounded-sm text-xs" placeholder="0.00" {...form.register("nivel_infestacao", { valueAsNumber: true })} />
                            </div>
                            <div className="space-y-1.5">
                                <Label className="text-xs">Unidade</Label>
                                <Input className="h-8 rounded-sm text-xs" placeholder="insetos/m², %" {...form.register("unidade_medida")} />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label className="text-xs">Observações</Label>
                            <Input className="h-8 rounded-sm text-xs" placeholder="Detalhes adicionais..." {...form.register("observacoes")} />
                        </div>
                    </DialogBody>
                    <DialogFooter className="px-5 py-4 border-t bg-muted/20 sm:justify-end">
                        <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setIsOpen(false)} disabled={createMutation.isPending}>
                            <XCircle className="size-3.5 mr-1.5" /> Cancelar
                        </Button>
                        <Button type="submit" variant="outline" size="sm" className="rounded-sm border-primary/50 text-primary hover:bg-primary/5" disabled={createMutation.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {createMutation.isPending ? "Salvando..." : "Registrar"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
        </>
    );
}
