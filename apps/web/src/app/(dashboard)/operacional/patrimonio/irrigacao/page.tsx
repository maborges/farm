"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Droplets, Plus, ArrowLeft, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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

interface SistemaIrrigacao {
    id: string;
    imovel_id: string;
    unidade_produtiva_id: string | null;
    nome: string;
    tipo: string;
    fonte_agua: string | null;
    area_irrigada_ha: number | null;
    vazao_m3h: number | null;
    pressao_bar: number | null;
    potencia_motor_cv: number | null;
    status: "ATIVO" | "INATIVO" | "MANUTENCAO";
    data_instalacao: string | null;
    observacoes: string | null;
}

const TIPO_LABEL: Record<string, string> = {
    PIVO_CENTRAL: "Pivô central",
    GOTEJAMENTO: "Gotejamento",
    ASPERSAO: "Aspersão",
    MICROASPERSAO: "Microaspersão",
    SULCO: "Sulco",
    OUTRO: "Outro",
};

const STATUS_CONFIG: Record<SistemaIrrigacao["status"], { label: string; color: string }> = {
    ATIVO: { label: "Ativo", color: "bg-green-100 text-green-700 border-green-200" },
    INATIVO: { label: "Inativo", color: "bg-gray-100 text-gray-600 border-gray-200" },
    MANUTENCAO: { label: "Manutenção", color: "bg-amber-100 text-amber-700 border-amber-200" },
};

const FORM_INICIAL = {
    imovel_id: "",
    nome: "",
    tipo: "PIVO_CENTRAL",
    fonte_agua: "",
    area_irrigada_ha: "",
    vazao_m3h: "",
    status: "ATIVO",
    observacoes: "",
};

export default function IrrigacaoPage() {
    const queryClient = useQueryClient();
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editandoId, setEditandoId] = useState<string | null>(null);
    const [form, setForm] = useState(FORM_INICIAL);
    const [excluirId, setExcluirId] = useState<string | null>(null);

    const { data: imoveis = [] } = useQuery<Imovel[]>({
        queryKey: ["imoveis"],
        queryFn: () => apiFetch("/imoveis/"),
    });

    const { data: sistemas = [], isLoading } = useQuery<SistemaIrrigacao[]>({
        queryKey: ["irrigacao-sistemas"],
        queryFn: () => apiFetch("/imoveis/irrigacao/"),
    });

    const salvarMutation = useMutation({
        mutationFn: () => {
            const payload = {
                imovel_id: form.imovel_id,
                nome: form.nome,
                tipo: form.tipo,
                fonte_agua: form.fonte_agua || null,
                area_irrigada_ha: form.area_irrigada_ha ? Number(form.area_irrigada_ha) : null,
                vazao_m3h: form.vazao_m3h ? Number(form.vazao_m3h) : null,
                status: form.status,
                observacoes: form.observacoes || null,
            };
            return editandoId
                ? apiFetch(`/imoveis/irrigacao/${editandoId}`, { method: "PATCH", body: JSON.stringify(payload) })
                : apiFetch("/imoveis/irrigacao/", { method: "POST", body: JSON.stringify(payload) });
        },
        onSuccess: () => {
            toast.success(editandoId ? "Sistema de irrigação atualizado." : "Sistema de irrigação criado.");
            queryClient.invalidateQueries({ queryKey: ["irrigacao-sistemas"] });
            fecharDialog();
        },
        onError: () => toast.error("Erro ao salvar sistema de irrigação."),
    });

    const excluirMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/imoveis/irrigacao/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Sistema de irrigação removido.");
            queryClient.invalidateQueries({ queryKey: ["irrigacao-sistemas"] });
            setExcluirId(null);
        },
        onError: () => toast.error("Erro ao remover sistema de irrigação."),
    });

    function abrirNovo() {
        setEditandoId(null);
        setForm(FORM_INICIAL);
        setDialogOpen(true);
    }

    function abrirEdicao(s: SistemaIrrigacao) {
        setEditandoId(s.id);
        setForm({
            imovel_id: s.imovel_id,
            nome: s.nome,
            tipo: s.tipo,
            fonte_agua: s.fonte_agua ?? "",
            area_irrigada_ha: s.area_irrigada_ha != null ? String(s.area_irrigada_ha) : "",
            vazao_m3h: s.vazao_m3h != null ? String(s.vazao_m3h) : "",
            status: s.status,
            observacoes: s.observacoes ?? "",
        });
        setDialogOpen(true);
    }

    function fecharDialog() {
        setDialogOpen(false);
        setEditandoId(null);
        setForm(FORM_INICIAL);
    }

    const imoveisPorId = Object.fromEntries(imoveis.map((i) => [i.id, i.nome]));

    return (
        <div className="p-8 space-y-6 max-w-6xl mx-auto w-full">
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" asChild>
                    <Link href="/cadastros/imoveis"><ArrowLeft size={18} /></Link>
                </Button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Droplets className="text-primary" size={22} /> Irrigação
                    </h1>
                    <p className="text-muted-foreground text-sm">Sistemas de irrigação cadastrados no patrimônio (pivôs, gotejamento, aspersão e demais infraestruturas de água).</p>
                </div>
                <Button size="sm" className="gap-1.5 h-8" onClick={abrirNovo}>
                    <Plus size={14} /> Novo sistema
                </Button>
            </div>

            <Card className="shadow-sm">
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow className="text-xs">
                                <TableHead>Nome</TableHead>
                                <TableHead>Tipo</TableHead>
                                <TableHead>Imóvel</TableHead>
                                <TableHead className="text-right">Área irrigada</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {!isLoading && sistemas.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground text-sm">
                                        Nenhum sistema de irrigação cadastrado.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                sistemas.map((s) => (
                                    <TableRow key={s.id}>
                                        <TableCell className="text-xs font-medium py-2.5">{s.nome}</TableCell>
                                        <TableCell className="text-xs">{TIPO_LABEL[s.tipo] ?? s.tipo}</TableCell>
                                        <TableCell className="text-xs">{imoveisPorId[s.imovel_id] ?? "—"}</TableCell>
                                        <TableCell className="text-right text-xs tabular-nums">
                                            {s.area_irrigada_ha != null ? `${s.area_irrigada_ha.toLocaleString("pt-BR")} ha` : "—"}
                                        </TableCell>
                                        <TableCell>
                                            <Badge className={STATUS_CONFIG[s.status].color + " border text-[10px] font-normal"}>
                                                {STATUS_CONFIG[s.status].label}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex items-center gap-0 justify-end">
                                                <Button
                                                    size="icon" variant="ghost" className="size-7 text-primary hover:text-primary"
                                                    aria-label="Editar"
                                                    onClick={() => abrirEdicao(s)}
                                                >
                                                    <Pencil className="size-3.5" />
                                                </Button>
                                                <AlertDialog open={excluirId === s.id} onOpenChange={(open) => !open && setExcluirId(null)}>
                                                    <AlertDialogTrigger asChild>
                                                        <Button
                                                            size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                                            aria-label="Excluir"
                                                            onClick={() => setExcluirId(s.id)}
                                                        >
                                                            <Trash2 className="size-3.5" />
                                                        </Button>
                                                    </AlertDialogTrigger>
                                                    <AlertDialogContent>
                                                        <AlertDialogHeader>
                                                            <AlertDialogTitle>Remover sistema de irrigação?</AlertDialogTitle>
                                                            <AlertDialogDescription>
                                                                O sistema "{s.nome}" será removido permanentemente. Esta ação não pode ser desfeita.
                                                            </AlertDialogDescription>
                                                        </AlertDialogHeader>
                                                        <AlertDialogFooter>
                                                            <AlertDialogCancel>Voltar</AlertDialogCancel>
                                                            <AlertDialogAction onClick={() => excluirMutation.mutate(s.id)}>Remover</AlertDialogAction>
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

            <Dialog open={dialogOpen} onOpenChange={(open) => !open && fecharDialog()}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>{editandoId ? "Editar sistema de irrigação" : "Novo sistema de irrigação"}</DialogTitle>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <div className="space-y-2">
                            <Label>Imóvel *</Label>
                            <Select value={form.imovel_id} onValueChange={(v) => setForm((f) => ({ ...f, imovel_id: v }))}>
                                <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Selecione o imóvel" /></SelectTrigger>
                                <SelectContent>
                                    {imoveis.map((i) => (
                                        <SelectItem key={i.id} value={i.id}>{i.nome}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Nome *</Label>
                            <Input
                                value={form.nome}
                                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                                placeholder="Ex: Pivô 1 - Talhão Norte"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Tipo *</Label>
                                <Select value={form.tipo} onValueChange={(v) => setForm((f) => ({ ...f, tipo: v }))}>
                                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        {Object.entries(TIPO_LABEL).map(([value, label]) => (
                                            <SelectItem key={value} value={value}>{label}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Fonte de água</Label>
                                <Select value={form.fonte_agua} onValueChange={(v) => setForm((f) => ({ ...f, fonte_agua: v }))}>
                                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Selecione" /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="POCO">Poço</SelectItem>
                                        <SelectItem value="RIO">Rio</SelectItem>
                                        <SelectItem value="ACUDE">Açude</SelectItem>
                                        <SelectItem value="ACUDE_PARTICULAR">Açude particular</SelectItem>
                                        <SelectItem value="REDE_PUBLICA">Rede pública</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Área irrigada (ha)</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    value={form.area_irrigada_ha}
                                    onChange={(e) => setForm((f) => ({ ...f, area_irrigada_ha: e.target.value }))}
                                    placeholder="0,00"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Vazão (m³/h)</Label>
                                <Input
                                    type="number" step="0.01" min="0"
                                    value={form.vazao_m3h}
                                    onChange={(e) => setForm((f) => ({ ...f, vazao_m3h: e.target.value }))}
                                    placeholder="0,00"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Status</Label>
                            <Select value={form.status} onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}>
                                <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ATIVO">Ativo</SelectItem>
                                    <SelectItem value="INATIVO">Inativo</SelectItem>
                                    <SelectItem value="MANUTENCAO">Manutenção</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Observações</Label>
                            <Textarea
                                value={form.observacoes}
                                onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))}
                                placeholder="Observações adicionais"
                            />
                        </div>
                    </DialogBody>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={fecharDialog}>Cancelar</Button>
                        <Button
                            disabled={!form.imovel_id || !form.nome || salvarMutation.isPending}
                            onClick={() => salvarMutation.mutate()}
                        >
                            {editandoId ? "Salvar alterações" : "Criar sistema"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
