"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Clock3, HardHat, Plus, SearchX, Trash2, UsersRound, WalletCards, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogBody,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ColaboradorCombobox } from "@/components/shared/colaborador-combobox";
import { toast } from "sonner";

interface Apontamento {
    id: string;
    pessoa_id: string;
    data: string;
    turno: string;
    horas_trabalhadas: number;
    quantidade_pessoas: number;
    tipo_operacao: string | null;
    custo_total: number | null;
    observacoes: string | null;
}

function SummaryCard({ label, value, icon: Icon, loading, tone = "primary" }: { label: string; value: number | string; icon: LucideIcon; loading: boolean; tone?: "primary" | "emerald" | "blue" | "amber" }) {
    const tones = {
        primary: "bg-primary/10 text-primary",
        emerald: "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30",
        blue: "bg-blue-100 text-blue-600 dark:bg-blue-900/30",
        amber: "bg-amber-100 text-amber-600 dark:bg-amber-900/30",
    } as const;

    return <Card className="rounded-sm shadow-sm"><CardContent className="flex items-start gap-4 p-5"><div className={`flex size-10 shrink-0 items-center justify-center rounded-sm ${tones[tone]}`}><Icon className="size-5" /></div><div className="min-w-0"><p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</p>{loading ? <Skeleton className="mt-1 h-7 w-20" /> : <p className="mt-0.5 text-xl font-black tracking-tight tabular-nums">{value}</p>}</div></CardContent></Card>;
}

function ApontamentosSkeleton() {
    return <Card className="rounded-sm shadow-sm"><CardContent className="space-y-3 p-4">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-10 w-full rounded-sm" />)}</CardContent></Card>;
}

const TURNOS = [
    { value: "MANHA", label: "Manhã" },
    { value: "TARDE", label: "Tarde" },
    { value: "INTEGRAL", label: "Integral" },
];

const apontamentoSchema = z.object({
    pessoa_id: z.string().uuid("Selecione um colaborador"),
    data: z.string().min(1, "Data obrigatória"),
    turno: z.string().min(1),
    horas_trabalhadas: z.coerce.number().positive("Horas devem ser maiores que zero"),
    quantidade_pessoas: z.coerce.number().int().min(1, "Mínimo 1 pessoa"),
    tipo_operacao: z.string().optional(),
    custo_hora_snapshot: z.coerce.number().min(0).optional().or(z.literal("")),
    observacoes: z.string().optional(),
});

type ApontamentoFormData = z.infer<typeof apontamentoSchema>;

export default function ApontamentosMaoObraPage() {
    const queryClient = useQueryClient();
    const [novoOpen, setNovoOpen] = useState(false);
    const [removerId, setRemoverId] = useState<string | null>(null);
    const [dataInicio, setDataInicio] = useState("");
    const [dataFim, setDataFim] = useState("");

    const {
        register, handleSubmit, control, reset, formState: { errors },
    } = useForm<ApontamentoFormData>({
        resolver: zodResolver(apontamentoSchema),
        defaultValues: { turno: "INTEGRAL", quantidade_pessoas: 1 },
    });

    const params = new URLSearchParams();
    if (dataInicio) params.set("data_inicio", dataInicio);
    if (dataFim) params.set("data_fim", dataFim);

    const { data: apontamentos = [], isLoading } = useQuery<Apontamento[]>({
        queryKey: ["mao-obra-apontamentos", dataInicio, dataFim],
        queryFn: () => apiFetch(`/mao-obra/apontamentos?${params.toString()}`),
    });

    const { data: colaboradores = [] } = useQuery<{ id: string; pessoa_id: string; nome: string }[]>({
        queryKey: ["colaboradores-nomes"],
        queryFn: () => apiFetch(`/rh/colaboradores?q=`),
        staleTime: 30_000,
    });

    const nomeColaborador = (pessoaId: string) =>
        colaboradores.find((c) => c.pessoa_id === pessoaId)?.nome ?? pessoaId;

    const criarMutation = useMutation({
        mutationFn: (dados: ApontamentoFormData) =>
            apiFetch("/mao-obra/apontamentos", {
                method: "POST",
                body: JSON.stringify({
                    pessoa_id: dados.pessoa_id,
                    data: new Date(dados.data).toISOString(),
                    turno: dados.turno,
                    horas_trabalhadas: dados.horas_trabalhadas,
                    quantidade_pessoas: dados.quantidade_pessoas,
                    tipo_operacao: dados.tipo_operacao || null,
                    custo_hora_snapshot: dados.custo_hora_snapshot === "" || dados.custo_hora_snapshot === undefined
                        ? null : Number(dados.custo_hora_snapshot),
                    observacoes: dados.observacoes || null,
                }),
            }),
        onSuccess: () => {
            toast.success("Apontamento registrado.");
            queryClient.invalidateQueries({ queryKey: ["mao-obra-apontamentos"] });
            setNovoOpen(false);
            reset({ turno: "INTEGRAL", quantidade_pessoas: 1, pessoa_id: "", data: "", horas_trabalhadas: undefined, tipo_operacao: "", custo_hora_snapshot: "", observacoes: "" });
        },
        onError: () => toast.error("Erro ao registrar apontamento."),
    });

    const removerMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/mao-obra/apontamentos/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Apontamento removido.");
            queryClient.invalidateQueries({ queryKey: ["mao-obra-apontamentos"] });
            setRemoverId(null);
        },
        onError: () => toast.error("Erro ao remover apontamento."),
    });

    const totalHoras = apontamentos.reduce((total, item) => total + item.horas_trabalhadas * item.quantidade_pessoas, 0);
    const totalCusto = apontamentos.reduce((total, item) => total + (item.custo_total ?? 0), 0);
    const colaboradoresAtendidos = new Set(apontamentos.map((item) => item.pessoa_id)).size;

    const columns: ColumnDef<Apontamento>[] = [
        {
            id: "data", header: "Data", accessorKey: "data", sortable: true,
            cell: (_value, item) => <span className="text-sm tabular-nums">{new Date(item.data).toLocaleDateString("pt-BR")}</span>,
            exportFormat: (_value, item) => new Date(item.data).toLocaleDateString("pt-BR"),
        },
        {
            id: "colaborador", header: "Colaborador", accessorFn: (item) => nomeColaborador(item.pessoa_id), sortable: true, filterable: true,
            cell: (_value, item) => <span className="font-medium">{nomeColaborador(item.pessoa_id)}</span>,
            exportFormat: (_value, item) => nomeColaborador(item.pessoa_id),
        },
        {
            id: "turno", header: "Turno", accessorKey: "turno", filterable: true,
            cell: (_value, item) => <Badge variant="outline" className="rounded-sm text-xs font-medium">{TURNOS.find((turno) => turno.value === item.turno)?.label ?? item.turno}</Badge>,
            exportFormat: (_value, item) => TURNOS.find((turno) => turno.value === item.turno)?.label ?? item.turno,
        },
        { id: "horas", header: "Horas", accessorKey: "horas_trabalhadas", sortable: true, cell: (value) => <span className="block text-right tabular-nums">{Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span> },
        { id: "pessoas", header: "Pessoas", accessorKey: "quantidade_pessoas", sortable: true, cell: (value) => <span className="block text-right tabular-nums">{value}</span> },
        { id: "operacao", header: "Operação", accessorKey: "tipo_operacao", filterable: true, cell: (value) => value || "—" },
        { id: "custo", header: "Custo total", accessorKey: "custo_total", sortable: true, cell: (value) => <span className="block text-right tabular-nums">{value != null ? Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}</span>, exportFormat: (value) => value != null ? Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—" },
        {
            id: "actions", header: "", exportable: false, sortable: false, filterable: false, isActionColumn: true,
            cell: (_value, item) => (
                <AlertDialog open={removerId === item.id} onOpenChange={(open) => !open && setRemoverId(null)}>
                    <AlertDialogTrigger asChild>
                        <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label={`Remover apontamento de ${nomeColaborador(item.pessoa_id)}`} onClick={() => setRemoverId(item.id)}>
                            <Trash2 className="size-3.5" />
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader><AlertDialogTitle>Remover apontamento?</AlertDialogTitle><AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription></AlertDialogHeader>
                        <AlertDialogFooter><AlertDialogCancel>Voltar</AlertDialogCancel><AlertDialogAction disabled={removerMutation.isPending} onClick={() => removerMutation.mutate(item.id)}>Remover</AlertDialogAction></AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
            ),
        },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader title="Apontamentos de mão de obra" description="Registre e acompanhe as horas trabalhadas pela equipe." icon={<HardHat className="size-5 text-primary" />} breadcrumbs={[{ label: "Operacional", href: "/operacional" }, { label: "Mão de obra" }, { label: "Apontamentos" }]} actions={<Button size="sm" onClick={() => setNovoOpen(true)}><Plus data-icon="inline-start" className="size-3.5" /> Novo apontamento</Button>} />

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <SummaryCard label="Apontamentos" value={apontamentos.length} icon={HardHat} loading={isLoading} />
                <SummaryCard label="Colaboradores" value={colaboradoresAtendidos} icon={UsersRound} loading={isLoading} tone="emerald" />
                <SummaryCard label="Horas apontadas" value={totalHoras.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} icon={Clock3} loading={isLoading} tone="blue" />
                <SummaryCard label="Custo total" value={totalCusto.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} icon={WalletCards} loading={isLoading} tone="amber" />
            </div>

            <Card className="rounded-sm shadow-sm">
                <CardContent className="flex flex-wrap items-end gap-3 p-4">
                    <div className="space-y-1.5"><Label htmlFor="data-inicio" className="text-xs">Data inicial</Label><Input id="data-inicio" type="date" className="h-9 w-[170px] text-sm" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} /></div>
                    <div className="space-y-1.5"><Label htmlFor="data-fim" className="text-xs">Data final</Label><Input id="data-fim" type="date" className="h-9 w-[170px] text-sm" value={dataFim} onChange={(event) => setDataFim(event.target.value)} /></div>
                    {(dataInicio || dataFim) && <Button variant="ghost" size="sm" className="h-9" onClick={() => { setDataInicio(""); setDataFim(""); }}>Limpar período</Button>}
                </CardContent>
            </Card>

            {isLoading ? <ApontamentosSkeleton /> : apontamentos.length === 0 ? (
                <div className="rounded-sm border-2 border-dashed bg-muted/20 py-14 text-center"><SearchX className="mx-auto mb-3 size-9 text-primary opacity-40" /><p className="text-sm font-medium">Nenhum apontamento encontrado</p><p className="mt-1 text-xs text-muted-foreground">Ajuste o período ou registre o primeiro apontamento.</p><Button size="sm" variant="outline" className="mt-4" onClick={() => setNovoOpen(true)}><Plus data-icon="inline-start" className="size-3.5" /> Registrar apontamento</Button></div>
            ) : <DataTable columns={columns} data={apontamentos} searchable searchPlaceholder="Buscar colaborador ou operação..." exportable exportFileName="apontamentos-mao-de-obra" emptyMessage="Nenhum apontamento encontrado." />}

            <Dialog open={novoOpen} onOpenChange={setNovoOpen}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Novo apontamento de mão de obra</DialogTitle>
                    </DialogHeader>
                    <DialogBody className="grid md:grid-cols-2 gap-4 max-h-[65vh] overflow-y-auto px-6">
                        <div className="space-y-2 md:col-span-2">
                            <Label>Colaborador *</Label>
                            <Controller
                                name="pessoa_id"
                                control={control}
                                render={({ field }) => (
                                    <ColaboradorCombobox value={field.value ?? ""} onChange={field.onChange} valueKey="pessoa_id" />
                                )}
                            />
                            {errors.pessoa_id && <p className="text-xs text-destructive">{errors.pessoa_id.message}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label>Data *</Label>
                            <Input type="date" {...register("data")} />
                            {errors.data && <p className="text-xs text-destructive">{errors.data.message}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label>Turno</Label>
                            <Controller
                                name="turno"
                                control={control}
                                render={({ field }) => (
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            {TURNOS.map((t) => (
                                                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                )}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Horas trabalhadas *</Label>
                            <Input type="number" step="0.01" min="0" {...register("horas_trabalhadas")} placeholder="0,00" />
                            {errors.horas_trabalhadas && <p className="text-xs text-destructive">{errors.horas_trabalhadas.message}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label>Quantidade de pessoas</Label>
                            <Input type="number" min="1" step="1" {...register("quantidade_pessoas")} />
                            {errors.quantidade_pessoas && <p className="text-xs text-destructive">{errors.quantidade_pessoas.message}</p>}
                        </div>

                        <div className="space-y-2">
                            <Label>Tipo de operação</Label>
                            <Input {...register("tipo_operacao")} placeholder="Ex: capina, colheita manual" />
                        </div>

                        <div className="space-y-2">
                            <Label>Custo/hora (override)</Label>
                            <Input type="number" step="0.01" min="0" {...register("custo_hora_snapshot")} placeholder="Deixe vazio para usar o valor do colaborador" />
                        </div>

                        <div className="space-y-2 md:col-span-2">
                            <Label>Observações</Label>
                            <Textarea {...register("observacoes")} placeholder="Observações adicionais" />
                        </div>
                    </DialogBody>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={() => setNovoOpen(false)}>Cancelar</Button>
                        <Button disabled={criarMutation.isPending} onClick={handleSubmit((d) => criarMutation.mutate(d))}>
                            Salvar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
