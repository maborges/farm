"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Wrench, Plus, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
import { toast } from "sonner";

interface Imovel {
    id: string;
    nome: string;
}

interface Benfeitoria {
    id: string;
    imovel_id: string;
    nome: string;
    tipo: string;
}

interface OrdemServico {
    id: string;
    benfeitoria_id: string;
    numero_os: string;
    tipo: string;
    status: "ABERTA" | "EM_EXECUCAO" | "CONCLUIDA" | "CANCELADA";
    descricao_problema: string;
    data_abertura: string;
    data_conclusao: string | null;
    custo_total: number;
}

const STATUS_CONFIG: Record<OrdemServico["status"], { label: string; color: string }> = {
    ABERTA: { label: "Aberta", color: "bg-blue-100 text-blue-700 border-blue-200" },
    EM_EXECUCAO: { label: "Em execução", color: "bg-amber-100 text-amber-700 border-amber-200" },
    CONCLUIDA: { label: "Concluída", color: "bg-green-100 text-green-700 border-green-200" },
    CANCELADA: { label: "Cancelada", color: "bg-gray-100 text-gray-600 border-gray-200" },
};

export default function ManutencaoBenfeitoriasPage() {
    const queryClient = useQueryClient();
    const [benfeitoriaId, setBenfeitoriaId] = useState("");
    const [novaOsOpen, setNovaOsOpen] = useState(false);
    const [novaOsForm, setNovaOsForm] = useState({ tipo: "CORRETIVA", descricao_problema: "" });
    const [concluirOsId, setConcluirOsId] = useState<string | null>(null);
    const [custoConcluir, setCustoConcluir] = useState("");

    const { data: imoveis = [] } = useQuery<Imovel[]>({
        queryKey: ["imoveis"],
        queryFn: () => apiFetch("/imoveis/"),
    });

    const { data: benfeitoriasPorImovel = [] } = useQuery<Benfeitoria[][]>({
        queryKey: ["benfeitorias-todas", imoveis.map((i) => i.id).join(",")],
        queryFn: () =>
            Promise.all(imoveis.map((i) => apiFetch<Benfeitoria[]>(`/imoveis/${i.id}/benfeitorias`))),
        enabled: imoveis.length > 0,
    });
    const benfeitorias = benfeitoriasPorImovel.flat();

    const { data: ordensServico = [], isLoading: loadingOs } = useQuery<OrdemServico[]>({
        queryKey: ["os-benfeitoria", benfeitoriaId],
        queryFn: () => apiFetch(`/imoveis/benfeitorias/manutencao/ordens-servico?benfeitoria_id=${benfeitoriaId}`),
        enabled: !!benfeitoriaId,
    });

    const abrirOsMutation = useMutation({
        mutationFn: () =>
            apiFetch("/imoveis/benfeitorias/manutencao/ordens-servico", {
                method: "POST",
                body: JSON.stringify({ benfeitoria_id: benfeitoriaId, ...novaOsForm }),
            }),
        onSuccess: () => {
            toast.success("Ordem de serviço aberta.");
            queryClient.invalidateQueries({ queryKey: ["os-benfeitoria", benfeitoriaId] });
            setNovaOsOpen(false);
            setNovaOsForm({ tipo: "CORRETIVA", descricao_problema: "" });
        },
        onError: () => toast.error("Erro ao abrir ordem de serviço."),
    });

    const concluirOsMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/imoveis/benfeitorias/manutencao/ordens-servico/${concluirOsId}/concluir`, {
                method: "POST",
                body: JSON.stringify({ custo_total: custoConcluir ? Number(custoConcluir) : 0 }),
            }),
        onSuccess: () => {
            toast.success("Ordem de serviço concluída.");
            queryClient.invalidateQueries({ queryKey: ["os-benfeitoria", benfeitoriaId] });
            setConcluirOsId(null);
            setCustoConcluir("");
        },
        onError: () => toast.error("Erro ao concluir ordem de serviço."),
    });

    const cancelarOsMutation = useMutation({
        mutationFn: (osId: string) =>
            apiFetch(`/imoveis/benfeitorias/manutencao/ordens-servico/${osId}/cancelar`, { method: "POST" }),
        onSuccess: () => {
            toast.success("Ordem de serviço cancelada.");
            queryClient.invalidateQueries({ queryKey: ["os-benfeitoria", benfeitoriaId] });
        },
        onError: () => toast.error("Erro ao cancelar ordem de serviço."),
    });

    return (
        <div className="p-8 space-y-6 max-w-6xl mx-auto w-full">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" asChild>
                    <Link href="/cadastros/imoveis"><ArrowLeft size={18} /></Link>
                </Button>
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Wrench className="text-primary" size={22} /> Manutenção de Benfeitorias
                    </h1>
                    <p className="text-muted-foreground text-sm">Ordens de serviço de manutenção para sedes, silos, currais, galpões e demais benfeitorias.</p>
                </div>
            </div>

            <Card className="shadow-sm">
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-3">
                        <div className="space-y-2 w-64">
                            <Label className="text-xs">Benfeitoria</Label>
                            <Select value={benfeitoriaId} onValueChange={setBenfeitoriaId}>
                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Selecione a benfeitoria" /></SelectTrigger>
                                <SelectContent>
                                    {benfeitorias.map((b) => (
                                        <SelectItem key={b.id} value={b.id}>{b.nome} ({b.tipo})</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <Button size="sm" className="gap-1.5 h-8 mt-5" disabled={!benfeitoriaId} onClick={() => setNovaOsOpen(true)}>
                            <Plus size={14} /> Abrir OS
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow className="text-xs">
                                <TableHead>Nº OS</TableHead>
                                <TableHead>Tipo</TableHead>
                                <TableHead>Problema</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Custo</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {!benfeitoriaId ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground text-sm">
                                        Selecione uma benfeitoria para ver as ordens de serviço.
                                    </TableCell>
                                </TableRow>
                            ) : !loadingOs && ordensServico.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground text-sm">
                                        Nenhuma ordem de serviço registrada para esta benfeitoria.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                ordensServico.map((os) => (
                                    <TableRow key={os.id}>
                                        <TableCell className="font-mono text-xs py-2.5">{os.numero_os}</TableCell>
                                        <TableCell className="text-xs">{os.tipo}</TableCell>
                                        <TableCell className="text-xs max-w-xs truncate" title={os.descricao_problema}>{os.descricao_problema}</TableCell>
                                        <TableCell>
                                            <Badge className={STATUS_CONFIG[os.status].color + " border text-[10px] font-normal"}>
                                                {STATUS_CONFIG[os.status].label}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right text-xs tabular-nums">
                                            {os.custo_total > 0 ? `R$ ${os.custo_total.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "—"}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {os.status === "ABERTA" && (
                                                <div className="flex items-center gap-1 justify-end">
                                                    <Button
                                                        size="sm" variant="outline" className="h-7 text-xs"
                                                        onClick={() => setConcluirOsId(os.id)}
                                                    >
                                                        Concluir
                                                    </Button>
                                                    <AlertDialog>
                                                        <AlertDialogTrigger asChild>
                                                            <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive">Cancelar</Button>
                                                        </AlertDialogTrigger>
                                                        <AlertDialogContent>
                                                            <AlertDialogHeader>
                                                                <AlertDialogTitle>Cancelar ordem de serviço?</AlertDialogTitle>
                                                                <AlertDialogDescription>
                                                                    A OS {os.numero_os} será marcada como cancelada. Esta ação não pode ser desfeita.
                                                                </AlertDialogDescription>
                                                            </AlertDialogHeader>
                                                            <AlertDialogFooter>
                                                                <AlertDialogCancel>Voltar</AlertDialogCancel>
                                                                <AlertDialogAction onClick={() => cancelarOsMutation.mutate(os.id)}>Cancelar OS</AlertDialogAction>
                                                            </AlertDialogFooter>
                                                        </AlertDialogContent>
                                                    </AlertDialog>
                                                </div>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <Dialog open={novaOsOpen} onOpenChange={setNovaOsOpen}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Nova ordem de serviço</DialogTitle>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <div className="space-y-2">
                            <Label>Tipo</Label>
                            <Select value={novaOsForm.tipo} onValueChange={(v) => setNovaOsForm((f) => ({ ...f, tipo: v }))}>
                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="PREVENTIVA">Preventiva</SelectItem>
                                    <SelectItem value="CORRETIVA">Corretiva</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Descrição do problema *</Label>
                            <Textarea
                                value={novaOsForm.descricao_problema}
                                onChange={(e) => setNovaOsForm((f) => ({ ...f, descricao_problema: e.target.value }))}
                                placeholder="Ex: Telhado do galpão com goteira na ala norte"
                            />
                        </div>
                    </DialogBody>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={() => setNovaOsOpen(false)}>Cancelar</Button>
                        <Button
                            disabled={!novaOsForm.descricao_problema || abrirOsMutation.isPending}
                            onClick={() => abrirOsMutation.mutate()}
                        >
                            Abrir OS
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!concluirOsId} onOpenChange={(open) => !open && setConcluirOsId(null)}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Concluir ordem de serviço</DialogTitle>
                    </DialogHeader>
                    <DialogBody className="space-y-2">
                        <Label>Custo total (peças + mão de obra)</Label>
                        <Input
                            type="number" step="0.01" min="0"
                            value={custoConcluir}
                            onChange={(e) => setCustoConcluir(e.target.value)}
                            placeholder="0,00"
                        />
                    </DialogBody>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={() => setConcluirOsId(null)}>Cancelar</Button>
                        <Button disabled={concluirOsMutation.isPending} onClick={() => concluirOsMutation.mutate()}>
                            Concluir OS
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
