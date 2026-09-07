"use client";

import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { HardHat, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
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

    return (
        <div className="p-8 space-y-6 max-w-6xl mx-auto w-full">
            <PageHeader
                title="Apontamento de Mão de Obra"
                description="Registro manual de horas trabalhadas por colaborador, sem vínculo com equipamento."
                icon={<HardHat className="size-5" />}
            />

            <Card className="shadow-sm">
                <CardContent className="p-4 space-y-4">
                    <div className="flex items-end justify-between gap-3 flex-wrap">
                        <div className="flex items-end gap-3">
                            <div className="space-y-2">
                                <Label className="text-xs">Data início</Label>
                                <Input type="date" className="h-8 text-xs" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-xs">Data fim</Label>
                                <Input type="date" className="h-8 text-xs" value={dataFim} onChange={(e) => setDataFim(e.target.value)} />
                            </div>
                        </div>
                        <Button size="sm" className="gap-1.5 h-8" onClick={() => setNovoOpen(true)}>
                            <Plus size={14} /> Novo Apontamento
                        </Button>
                    </div>

                    <Table>
                        <TableHeader>
                            <TableRow className="text-xs">
                                <TableHead>Data</TableHead>
                                <TableHead>Colaborador</TableHead>
                                <TableHead>Turno</TableHead>
                                <TableHead className="text-right">Horas</TableHead>
                                <TableHead className="text-right">Qtd. Pessoas</TableHead>
                                <TableHead>Tipo de Operação</TableHead>
                                <TableHead className="text-right">Custo Total</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {!isLoading && apontamentos.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground text-sm">
                                        Nenhum apontamento registrado.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                apontamentos.map((ap) => (
                                    <TableRow key={ap.id}>
                                        <TableCell className="text-xs py-2.5">
                                            {new Date(ap.data).toLocaleDateString("pt-BR")}
                                        </TableCell>
                                        <TableCell className="text-xs">{nomeColaborador(ap.pessoa_id)}</TableCell>
                                        <TableCell className="text-xs">
                                            {TURNOS.find((t) => t.value === ap.turno)?.label ?? ap.turno}
                                        </TableCell>
                                        <TableCell className="text-right text-xs tabular-nums">
                                            {ap.horas_trabalhadas.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                                        </TableCell>
                                        <TableCell className="text-right text-xs tabular-nums">{ap.quantidade_pessoas}</TableCell>
                                        <TableCell className="text-xs">{ap.tipo_operacao ?? "—"}</TableCell>
                                        <TableCell className="text-right text-xs tabular-nums">
                                            {ap.custo_total != null
                                                ? `R$ ${ap.custo_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                                                : "—"}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex items-center gap-0 justify-end">
                                                <AlertDialog open={removerId === ap.id} onOpenChange={(open) => !open && setRemoverId(null)}>
                                                    <AlertDialogTrigger asChild>
                                                        <Button
                                                            size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                                            aria-label="Remover" onClick={() => setRemoverId(ap.id)}
                                                        >
                                                            <Trash2 className="size-3.5" />
                                                        </Button>
                                                    </AlertDialogTrigger>
                                                    <AlertDialogContent>
                                                        <AlertDialogHeader>
                                                            <AlertDialogTitle>Remover apontamento?</AlertDialogTitle>
                                                            <AlertDialogDescription>
                                                                Esta ação não pode ser desfeita.
                                                            </AlertDialogDescription>
                                                        </AlertDialogHeader>
                                                        <AlertDialogFooter>
                                                            <AlertDialogCancel>Voltar</AlertDialogCancel>
                                                            <AlertDialogAction onClick={() => removerMutation.mutate(ap.id)}>
                                                                Remover
                                                            </AlertDialogAction>
                                                        </AlertDialogFooter>
                                                    </AlertDialogContent>
                                                </AlertDialog>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

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
