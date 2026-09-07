"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    Tractor, Plus, Search, Settings2,
    MoreHorizontal, Edit, Trash2,
    CheckCircle2, AlertCircle, Wrench, X,
    Gauge, Calendar, Info, Box, Package
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription,
    DialogFooter, DialogHeader, DialogTitle, DialogTrigger
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Table, TableBody, TableCell,
    TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/shared/page-header";

interface PlanoManutencao {
    id: string;
    maquinario_id: string;
    descricao: string;
    frequencia_horas: number;
    ultimo_registro_horas: number;
}

interface Maquinario {
    id: string;
    nome: string;
    tipo: string;
    marca: string;
    modelo: string;
    ano: number;
    horimetro_atual: number;
    status: string;
    planos?: PlanoManutencao[];
}

export default function FrotaPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [isOSDialogOpen, setIsOSDialogOpen] = useState(false);
    const [isPlanDialogOpen, setIsPlanDialogOpen] = useState(false);
    const [selectedMaquinario, setSelectedMaquinario] = useState<Maquinario | null>(null);
    const [osItems, setOsItems] = useState<any[]>([]);
    const [osForm, setOsForm] = useState({ tipo: "PREVENTIVA", descricao_problema: "", horimetro_na_abertura: 0, tecnico_responsavel: "" });

    // Form state
    const [formData, setFormData] = useState({
        nome: "",
        tipo: "TRATOR",
        marca: "",
        modelo: "",
        ano: new Date().getFullYear(),
        placa_chassi: "",
        horimetro_atual: 0,
        status: "ATIVO"
    });

    const { data: maquinas, isLoading } = useQuery<Maquinario[]>({
        queryKey: ["frota", "maquinarios", activeFazendaId],
        queryFn: () => apiFetch(`/frota/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: produtos } = useQuery<any[]>({
        queryKey: ["estoque", "produtos", activeFazendaId],
        queryFn: () => apiFetch(`/cadastros/produtos?ativo=true&unidade_produtiva_id=${activeFazendaId}`),
        enabled: isOSDialogOpen
    });

    const mutation = useMutation({
        mutationFn: (data: any) => apiFetch("/frota/", {
            method: "POST",
            body: JSON.stringify({ ...data, unidade_produtiva_id: activeFazendaId })
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["frota"] });
            toast.success("Maquinário cadastrado com sucesso!");
            setIsDialogOpen(false);
            setFormData({
                nome: "", tipo: "TRATOR", marca: "", modelo: "",
                ano: new Date().getFullYear(), placa_chassi: "",
                horimetro_atual: 0, status: "ATIVO"
            });
        },
        onError: (err: any) => toast.error(`Erro: ${err.message}`)
    });

    const osMutation = useMutation({
        mutationFn: (data: any) => apiFetch("/oficina/os", {
            method: "POST",
            body: JSON.stringify(data)
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["frota"] });
            toast.success("Ordem de Serviço aberta!");
            setIsOSDialogOpen(false);
            setOsForm({ tipo: "PREVENTIVA", descricao_problema: "", horimetro_na_abertura: 0, tecnico_responsavel: "" });
        },
        onError: (err: any) => toast.error(`Erro: ${err.message}`)
    });

    const handleSave = () => {
        if (!formData.nome) return toast.error("Preencha o nome do maquinário.");
        mutation.mutate(formData);
    };

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Frota & Maquinários"
                description="Gestão de ativos, horímetros e manutenção preventiva."
                actions={
                    <Button size="sm" className="gap-2" onClick={() => setIsDialogOpen(true)}>
                        <Plus size={16} /> Novo Maquinário
                    </Button>
                }
            />

            {/* Quick Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-l-[3px] border-l-primary">
                    <CardContent className="p-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-primary/10 flex items-center justify-center text-primary">
                            <Tractor size={24} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black uppercase text-muted-foreground">Total de Ativos</p>
                            <p className="text-2xl font-black">{maquinas?.length || 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-amber-500">
                    <CardContent className="p-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-amber-500/10 flex items-center justify-center text-amber-600">
                            <Wrench size={24} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black uppercase text-muted-foreground">Em Manutenção</p>
                            <p className="text-2xl font-black">{maquinas?.filter(m => m.status !== 'ATIVO').length || 0}</p>
                        </div>
                    </CardContent>
                </Card>
                <Card className="border-l-[3px] border-l-blue-500">
                    <CardContent className="p-6 flex items-center gap-4">
                        <div className="h-12 w-12 rounded-sm bg-blue-500/10 flex items-center justify-center text-blue-600">
                            <Gauge size={24} />
                        </div>
                        <div>
                            <p className="text-[10px] font-black uppercase text-muted-foreground">Uso Acumulado</p>
                            <p className="text-2xl font-black">{(maquinas?.reduce((acc, m) => acc + m.horimetro_atual, 0) || 0).toLocaleString()} h</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* List Table */}
            <Card className="border-l-[3px] border-l-primary overflow-hidden">
                <CardContent className="p-0">
                    <Table>
                        <TableHeader className="bg-muted/10 border-none">
                            <TableRow className="border-none hover:bg-transparent text-muted-foreground/70 uppercase">
                                <TableHead className="px-8 py-5 text-[10px] font-black">Ativo / Tipo</TableHead>
                                <TableHead className="px-8 py-5 text-[10px] font-black">Marca / Modelo</TableHead>
                                <TableHead className="px-8 py-5 text-[10px] font-black">Uso Atual (h)</TableHead>
                                <TableHead className="px-8 py-5 text-[10px] font-black">Status</TableHead>
                                <TableHead className="px-8 py-5 text-[10px] font-black text-right"></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody className="font-medium">
                            {isLoading ? (
                                Array(3).fill(0).map((_, i) => (
                                    <TableRow key={i}><TableCell colSpan={5}><Skeleton className="h-16 w-full rounded-sm" /></TableCell></TableRow>
                                ))
                            ) : maquinas?.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="h-64 text-center">
                                        <div className="flex flex-col items-center gap-3 opacity-20">
                                            <Tractor size={48} />
                                            <p className="font-black uppercase text-xs">Nenhum maquinário cadastrado</p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                maquinas?.map((m) => (
                                    <TableRow key={m.id} className="group hover:bg-muted/10 border-b border-border/20 transition-all">
                                        <TableCell className="px-8 py-6">
                                            <div className="flex items-center gap-3">
                                                <div className="h-10 w-10 rounded-sm bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                                                    <Tractor size={18} />
                                                </div>
                                                <div>
                                                    <p className="font-black text-sm uppercase">{m.nome}</p>
                                                    <p className="text-[10px] text-muted-foreground font-bold uppercase">{m.tipo}</p>
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell className="px-8 py-6">
                                            <div className="space-y-0.5">
                                                <p className="text-sm font-bold text-foreground">{m.marca}</p>
                                                <p className="text-xs text-muted-foreground">{m.modelo} ({m.ano})</p>
                                            </div>
                                        </TableCell>
                                        <TableCell className="px-8 py-6">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2">
                                                    <Gauge size={14} className="text-muted-foreground" />
                                                    <span className="text-sm font-black">{m.horimetro_atual.toLocaleString()} h</span>
                                                </div>
                                                {m.planos?.some(p => (p.ultimo_registro_horas + p.frequencia_horas) - m.horimetro_atual < 50) && (
                                                    <Badge variant="ghost" className="text-[9px] font-black border-amber-500 text-amber-600 bg-amber-50 h-5 px-1 uppercase">
                                                        Revisão Próxima
                                                    </Badge>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell className="px-8 py-6">
                                            {m.status === 'ATIVO' ? (
                                                <Badge className="bg-green-500/10 text-green-700 border-none flex items-center gap-1 w-fit"><CheckCircle2 size={10} /> Ativo</Badge>
                                            ) : (
                                                <Badge className="bg-amber-500/10 text-amber-700 border-none flex items-center gap-1 w-fit"><AlertCircle size={10} /> Manutenção</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="px-8 py-6 text-right">
                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-8 px-3 rounded-sm text-primary font-bold gap-2 hover:bg-primary/10"
                                                    onClick={() => {
                                                        setSelectedMaquinario(m);
                                                        setIsOSDialogOpen(true);
                                                        setOsItems([]);
                                                    }}
                                                >
                                                    <Wrench size={14} /> Manutenção
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-8 px-3 rounded-sm text-muted-foreground font-bold gap-2 hover:bg-muted"
                                                    onClick={() => {
                                                        setSelectedMaquinario(m);
                                                        setIsPlanDialogOpen(true);
                                                    }}
                                                >
                                                    <Settings2 size={14} /> Planos
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Dialog Nova OS */}
            <Dialog open={isOSDialogOpen} onOpenChange={setIsOSDialogOpen}>
                <DialogContent className="sm:max-w-[500px] rounded-sm bg-surface border-none shadow-2xl p-0 overflow-hidden">
                    <DialogHeader className="p-6 bg-muted/20">
                        <DialogTitle className="text-2xl font-black flex items-center gap-2 text-foreground">
                            <Wrench className="text-primary" /> Abrir Ordem de Serviço
                        </DialogTitle>
                        <DialogDescription className="font-medium italic">Inicie um registro de manutenção para {selectedMaquinario?.nome}</DialogDescription>
                    </DialogHeader>

                    <div className="p-6 space-y-6">
                        <div className="space-y-4">
                            <div className="space-y-1">
                                <label className="text-[10px] font-black uppercase text-muted-foreground ml-1">Tipo da OS</label>
                                <Select defaultValue="PREVENTIVA">
                                    <SelectTrigger className="h-12 border-none bg-muted/50 rounded-sm font-bold">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="bg-surface border-border">
                                        <SelectItem value="PREVENTIVA">Preventiva (Plano)</SelectItem>
                                        <SelectItem value="CORRETIVA">Corretiva (Quebra)</SelectItem>
                                        <SelectItem value="REVISAO">Revisão Geral</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-black uppercase text-muted-foreground ml-1">Descrição do Problema / Serviço</label>
                                <Input placeholder="Descreva o que será feito..." className="h-12 border-none bg-muted/50 rounded-sm font-bold" />
                            </div>
                        </div>

                        <Separator className="bg-border/20" />

                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <label className="text-[10px] font-black uppercase text-muted-foreground flex items-center gap-2">
                                    <Package size={12} /> Peças e Insumos
                                </label>
                                <Badge variant="ghost" className="text-[9px] border-primary/30 text-primary">Baixa Automática</Badge>
                            </div>

                            <div className="flex gap-2">
                                <Select onValueChange={(v: string) => {
                                    const p = produtos?.find(x => x.id === v);
                                    if (p) setOsItems([...osItems, { ...p, quantidade: 1 }]);
                                }}>
                                    <SelectTrigger className="h-10 border-none bg-muted/30 rounded-sm font-bold flex-1">
                                        <SelectValue placeholder="Adicionar peça do estoque..." />
                                    </SelectTrigger>
                                    <SelectContent className="bg-surface border-border">
                                        {produtos?.map((p: any) => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2 max-h-32 overflow-y-auto pr-1">
                                {osItems.map((item, idx) => (
                                    <div key={idx} className="flex items-center justify-between p-2 bg-muted/20 rounded-sm border border-border/10">
                                        <div className="flex items-center gap-2">
                                            <Box size={14} className="text-muted-foreground" />
                                            <span className="text-xs font-bold">{item.nome}</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-[10px] font-black text-muted-foreground">1 {item.unidade_medida}</span>
                                            <button onClick={() => setOsItems(osItems.filter((_, i) => i !== idx))}><X size={12} className="text-red-500" /></button>
                                        </div>
                                    </div>
                                ))}
                                {osItems.length === 0 && <p className="text-[10px] text-center py-4 text-muted-foreground font-medium italic">Nenhuma peça adicionada ainda.</p>}
                            </div>
                        </div>
                    </div>

                    <DialogFooter className="p-6 pt-0">
                        <Button
                            className="w-full h-12 bg-primary text-white font-black rounded-sm uppercase shadow-lg shadow-primary/20"
                            disabled={osMutation.isPending || !osForm.descricao_problema}
                            onClick={() => osMutation.mutate({
                                maquinario_id: selectedMaquinario?.id,
                                tipo: osForm.tipo,
                                descricao_problema: osForm.descricao_problema,
                                horimetro_na_abertura: Number(osForm.horimetro_na_abertura),
                                tecnico_responsavel: osForm.tecnico_responsavel || undefined,
                            })}
                        >
                            {osMutation.isPending ? "Abrindo..." : "Abrir Ordem de Serviço"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog Planos de Manutenção */}
            <Dialog open={isPlanDialogOpen} onOpenChange={setIsPlanDialogOpen}>
                <DialogContent className="sm:max-w-[600px] rounded-sm bg-surface border-none shadow-2xl">
                    <DialogHeader>
                        <DialogTitle className="text-2xl font-black flex items-center gap-2">
                            <Settings2 className="text-primary" /> Planos de Manutenção
                        </DialogTitle>
                        <DialogDescription className="font-medium">Configure alertas de revisão por horas para {selectedMaquinario?.nome}</DialogDescription>
                    </DialogHeader>

                    <div className="space-y-6 py-4">
                        <div className="bg-muted/30 p-4 rounded-sm space-y-3">
                            <p className="text-[10px] font-black uppercase text-muted-foreground">Novo Plano</p>
                            <div className="flex gap-2">
                                <Input placeholder="Ex: Troca de Óleo Motor" className="h-10 border-none bg-background rounded-sm font-bold flex-1" />
                                <Input type="number" placeholder="250 h" className="h-10 border-none bg-background rounded-sm font-black w-24" />
                                <Button size="icon" className="bg-primary text-white h-10 w-10 rounded-sm"><Plus size={18} /></Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <p className="text-[10px] font-black uppercase text-muted-foreground">Planos Ativos</p>
                            <div className="space-y-2">
                                <div className="p-4 bg-muted/10 rounded-sm flex items-center justify-between border border-border/20">
                                    <div>
                                        <p className="font-bold text-sm">Troca de Filtros</p>
                                        <p className="text-[10px] text-muted-foreground font-medium uppercase">A cada 500 horas</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs font-black text-primary">Próximo: 1.250 h</p>
                                        <p className="text-[9px] text-muted-foreground font-bold">Faltam 84 h</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            {/* Dialog Novo Maquinário */}
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent className="sm:max-w-[700px] rounded-sm p-0 overflow-hidden border-none shadow-2xl bg-surface">
                    <div className="bg-[#1e2227] p-10 text-white relative">
                        <div className="absolute top-0 right-0 p-10 opacity-10">
                            <Tractor size={100} />
                        </div>
                        <DialogHeader>
                            <DialogTitle className="text-3xl font-black flex items-center gap-3">
                                <Plus className="size-8 text-primary" />
                                Cadastrar Ativo
                            </DialogTitle>
                            <DialogDescription className="text-gray-400 font-medium">Controle de frota, caminhões e implementos acoplados.</DialogDescription>
                        </DialogHeader>
                    </div>

                    <div className="p-10 grid grid-cols-2 gap-8">
                        <div className="space-y-4">
                            <div className="space-y-1">
                                <label className="text-[10px] font-black uppercase text-muted-foreground ml-1">Identificação</label>
                                <Input
                                    placeholder="Ex: Trator JD 8R - 01"
                                    className="h-12 border-none bg-muted/50 rounded-sm font-bold"
                                    value={formData.nome}
                                    onChange={e => setFormData({ ...formData, nome: e.target.value })}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-60 font-black ml-1 uppercase">Tipo</p>
                                    <Select value={formData.tipo} onValueChange={(v: string) => setFormData({ ...formData, tipo: v })}>
                                        <SelectTrigger className="h-12 border-none bg-muted/50 rounded-sm font-bold">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-surface border-border">
                                            <SelectItem value="TRATOR">Trator</SelectItem>
                                            <SelectItem value="COLHEITADEIRA">Colheitadeira</SelectItem>
                                            <SelectItem value="PULVERIZADOR">Pulverizador</SelectItem>
                                            <SelectItem value="VEICULO_LEVE">Veículo Leve</SelectItem>
                                            <SelectItem value="VEICULO_PESADO">Veículo Pesado</SelectItem>
                                            <SelectItem value="IMPLEMENTO">Implemento</SelectItem>
                                            <SelectItem value="OUTROS">Outros</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-60 font-black ml-1 uppercase">Ano</p>
                                    <Input
                                        type="number"
                                        className="h-12 border-none bg-muted/50 rounded-sm font-bold"
                                        value={formData.ano}
                                        onChange={e => setFormData({ ...formData, ano: Number(e.target.value) })}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-60 font-black ml-1 uppercase">Marca</p>
                                    <Input
                                        placeholder="Ex: John Deere"
                                        className="h-12 border-none bg-muted/50 rounded-sm font-bold"
                                        value={formData.marca}
                                        onChange={e => setFormData({ ...formData, marca: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-60 font-black ml-1 uppercase">Modelo</p>
                                    <Input
                                        placeholder="Ex: 8R 370"
                                        className="h-12 border-none bg-muted/50 rounded-sm font-bold"
                                        value={formData.modelo}
                                        onChange={e => setFormData({ ...formData, modelo: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] opacity-60 font-black ml-1 uppercase">Horímetro Inicial</p>
                                <div className="relative">
                                    <Gauge className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                                    <Input
                                        type="number"
                                        className="h-12 border-none bg-muted/50 rounded-sm font-black pl-11 text-lg"
                                        value={formData.horimetro_atual}
                                        onChange={e => setFormData({ ...formData, horimetro_atual: Number(e.target.value) })}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="p-10 pt-0 flex gap-4">
                        <Button variant="ghost" className="h-14 flex-1 rounded-sm font-black text-xs uppercase border-border/60" onClick={() => setIsDialogOpen(false)}>
                            Cancelar
                        </Button>
                        <Button
                            className="h-14 flex-[2] rounded-sm font-black text-lg shadow-2xl bg-primary text-white shadow-primary/20 uppercase"
                            onClick={handleSave}
                            disabled={mutation.isPending}
                        >
                            {mutation.isPending ? "Salvando..." : "Salvar Ativo"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
