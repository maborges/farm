"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { MapPin, Plus, LandPlot, Building2, FileText, Globe, Search, ArrowRight, ShieldCheck, Wrench, Droplets } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface Imovel {
    id: string;
    nome: string;
    area_total_ha: number;
    car_numero?: string;
    cidade?: string;
    estado?: string;
}

export default function PatrimonioPage() {
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);

    const { data: imoveis, isLoading } = useQuery<Imovel[]>({
        queryKey: ["imoveis"],
        queryFn: () => apiFetch("/imoveis/")
    });

    const createMutation = useMutation({
        mutationFn: (data: any) => apiFetch("/imoveis/", {
            method: "POST",
            body: JSON.stringify(data)
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["imoveis"] });
            toast.success("Imóvel cadastrado com sucesso!");
            setIsAddOpen(false);
            reset();
        }
    });

    const { register, handleSubmit, reset } = useForm();

    const onSubmit = (data: any) => {
        createMutation.mutate(data);
    };

    if (isLoading) {
        return <div className="p-8 space-y-6"><Skeleton className="h-10 w-full" /><Skeleton className="h-64 w-full" /></div>;
    }

    return (
        <div className="p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto w-full">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <MapPin className="text-primary" /> Imóveis & Patrimônio
                    </h1>
                    <p className="text-muted-foreground mt-1">Gestão de propriedades rurais, matrículas, áreas legais e benfeitorias.</p>
                </div>

                <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                    <DialogTrigger>
                        <Button size="sm" variant="outline" className="gap-2">
                            <Plus size={16} /> Novo Imóvel
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[550px]">
                        <form onSubmit={handleSubmit(onSubmit)}>
                            <DialogHeader>
                                <DialogTitle>Cadastrar Propriedade Rural</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="space-y-2">
                                    <Label>Nome da Fazenda / Imóvel</Label>
                                    <Input placeholder="Fazenda Esperança - Sede" {...register("nome", { required: true })} />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Área Total (Hectares)</Label>
                                        <Input type="number" step="0.01" placeholder="0.00" {...register("area_total_ha", { required: true })} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Nº do CAR (Ambiental)</Label>
                                        <Input placeholder="MT-12345..." {...register("car_numero")} />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label>Cidade</Label>
                                        <Input placeholder="Primavera do Leste" {...register("cidade")} />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Estado (UF)</Label>
                                        <Input placeholder="MT" maxLength={2} {...register("estado")} />
                                    </div>
                                </div>
                            </div>
                            <DialogFooter>
                                <Button type="submit" disabled={createMutation.isPending} className="w-full">Salvar Propriedade</Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                <Card className="bg-primary/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs font-bold uppercase">Área Total Gerenciada</CardDescription>
                        <CardTitle className="text-2xl">
                            {imoveis?.reduce((acc, curr) => acc + curr.area_total_ha, 0).toLocaleString('pt-BR')} ha
                        </CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-emerald-500/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardDescription className="text-xs font-bold uppercase text-emerald-700">Propriedades Ativas</CardDescription>
                        <CardTitle className="text-2xl">{imoveis?.length || 0}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className="bg-blue-500/5 border-none shadow-none">
                    <CardHeader className="pb-2 flex flex-row items-start justify-between">
                        <div>
                            <CardDescription className="text-xs font-bold uppercase text-blue-700">Benfeitorias</CardDescription>
                            <CardTitle className="text-2xl">--</CardTitle>
                        </div>
                        <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs" asChild>
                            <Link href="/operacional/patrimonio/manutencao">
                                <Wrench size={12} /> Manutenção
                            </Link>
                        </Button>
                    </CardHeader>
                </Card>
                <Card className="bg-cyan-500/5 border-none shadow-none">
                    <CardHeader className="pb-2 flex flex-row items-start justify-between">
                        <div>
                            <CardDescription className="text-xs font-bold uppercase text-cyan-700">Irrigação</CardDescription>
                            <CardTitle className="text-2xl">--</CardTitle>
                        </div>
                        <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs" asChild>
                            <Link href="/operacional/patrimonio/irrigacao">
                                <Droplets size={12} /> Sistemas
                            </Link>
                        </Button>
                    </CardHeader>
                </Card>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
                {imoveis?.length === 0 && (
                    <Card className="lg:col-span-2 border-dashed border-2 bg-transparent">
                        <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <LandPlot size={48} className="mb-4 opacity-20" />
                            <p>Nenhuma propriedade rural cadastrada no seu patrimônio.</p>
                            <Button variant="link" onClick={() => setIsAddOpen(true)}>Clique aqui para começar</Button>
                        </CardContent>
                    </Card>
                )}

                {imoveis?.map((imovel) => (
                    <Card key={imovel.id} className="group hover:border-primary/50 transition-colors shadow-sm bg-surface overflow-hidden">
                        <CardHeader className="pb-2 flex flex-row items-start justify-between">
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <CardTitle className="text-xl font-bold">{imovel.nome}</CardTitle>
                                    <Badge variant="outline" className="bg-primary/5 border-primary/20 text-primary uppercase text-[10px]">
                                        Escriturada
                                    </Badge>
                                </div>
                                <CardDescription className="flex items-center gap-1">
                                    <Globe size={12} /> {imovel.cidade} - {imovel.estado}
                                </CardDescription>
                            </div>
                            <div className="p-3 bg-primary/10 rounded-sm group-hover:bg-primary group-hover:text-white transition-colors">
                                <LandPlot size={20} />
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 gap-4 mt-2">
                                <div className="p-3 rounded-sm bg-neutral-100 dark:bg-neutral-800/50">
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold">Área Nominal</p>
                                    <p className="text-lg font-mono font-bold">{imovel.area_total_ha} ha</p>
                                </div>
                                <div className="p-3 rounded-sm bg-neutral-100 dark:bg-neutral-800/50">
                                    <p className="text-[10px] text-muted-foreground uppercase font-bold">Registro CAR</p>
                                    <p className="text-sm font-medium truncate" title={imovel.car_numero}>{imovel.car_numero || 'Pendente'}</p>
                                </div>
                            </div>

                            <div className="mt-6 flex items-center gap-2">
                                <Button variant="outline" size="sm" className="w-full text-xs h-9 gap-2">
                                    <FileText size={14} /> Matrículas
                                </Button>
                                <Button variant="outline" size="sm" className="w-full text-xs h-9 gap-2" asChild>
                                    <Link href="/operacional/patrimonio/manutencao">
                                        <Building2 size={14} /> Benfeitorias
                                    </Link>
                                </Button>
                                <Button size="sm" className="h-9 px-3">
                                    <ArrowRight size={16} />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
