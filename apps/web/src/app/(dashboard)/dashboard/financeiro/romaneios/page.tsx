"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useTalhoesContexto } from "@/hooks/use-agricola";
import { useForm } from "react-hook-form";
import { FileText, Plus, Wheat } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface Romaneio {
    id: string; numero_romaneio: string | null; safra_id: string; talhao_id: string;
    data_colheita: string; turno: string | null; peso_bruto_kg: number;
    tara_kg: number | null; peso_liquido_kg: number | null;
    umidade_pct: number | null; impureza_pct: number | null;
    preco_saca: number | null; destino: string | null;
}
interface RomaneioKPIs {
    total_romaneios: number; total_sacas: number;
    receita_total: number; produtividade_sc_ha: number | null;
}
interface Safra { id: string; ano_safra: string; cultura: string; }

function toBRL(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

export default function RomaneiosPage() {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";
    const [showDialog, setShowDialog] = useState(false);

    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["agricola", "safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras/${qs}`),
    });
    const { data: kpis, isLoading: loadingKpis } = useQuery<RomaneioKPIs>({
        queryKey: ["romaneios", "kpis", activeFazendaId],
        queryFn: () => apiFetch(`/romaneios/kpis${qs}`),
    });
    const { data: romaneios = [], isLoading } = useQuery<Romaneio[]>({
        queryKey: ["romaneios", activeFazendaId],
        queryFn: () => apiFetch(`/romaneios/${qs}`),
    });

    const mut = useMutation({
        mutationFn: (d: any) => apiFetch("/romaneios/", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["romaneios"] }); setShowDialog(false); toast.success("Romaneio registrado."); },
        onError: (e: any) => toast.error(e.message || "Erro."),
    });

    const columns: ColumnDef<Romaneio>[] = [
        { id: "numero_romaneio", header: "Nº Romaneio", accessorKey: "numero_romaneio", cell: (_v, r) => r.numero_romaneio || "—" },
        { id: "data_colheita", header: "Data Colheita", accessorKey: "data_colheita", cell: (_v, r) => new Date(r.data_colheita).toLocaleDateString("pt-BR") },
        { id: "turno", header: "Turno", accessorKey: "turno", cell: (_v, r) => r.turno || "—" },
        { id: "peso_bruto", header: "Peso Bruto (kg)", accessorKey: "peso_bruto_kg", cell: (_v, r) => r.peso_bruto_kg.toLocaleString("pt-BR") },
        { id: "peso_liquido", header: "Peso Líq. (kg)", accessorKey: "peso_liquido_kg", cell: (_v, r) => r.peso_liquido_kg?.toLocaleString("pt-BR") ?? "—" },
        { id: "umidade", header: "Umidade %", accessorKey: "umidade_pct", cell: (_v, r) => r.umidade_pct != null ? `${r.umidade_pct}%` : "—" },
        { id: "preco_saca", header: "Preço/Saca", accessorKey: "preco_saca", cell: (_v, r) => r.preco_saca ? toBRL(r.preco_saca) : "—" },
        { id: "destino", header: "Destino", accessorKey: "destino", cell: (_v, r) => r.destino || "—" },
    ];

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Romaneios de Colheita"
                description="Registro e rastreabilidade de romaneios"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Romaneios de Colheita" },
                ]}
                icon={<Wheat className="text-primary" size={22} />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDialog(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                    >
                        <Plus className="size-4 mr-1.5" /> Novo Romaneio
                    </Button>
                }
            />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {loadingKpis
                    ? Array.from({ length: 4 }).map((_, i) => <Card key={i} className="rounded-sm"><CardHeader className="pb-1"><Skeleton className="h-4 w-24" /></CardHeader><CardContent><Skeleton className="h-7 w-20" /></CardContent></Card>)
                    : kpis ? [
                        { label: "Total Romaneios", value: kpis.total_romaneios },
                        { label: "Total Sacas", value: kpis.total_sacas.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) },
                        { label: "Receita Total", value: toBRL(kpis.receita_total) },
                        { label: "Produtividade (sc/ha)", value: kpis.produtividade_sc_ha != null ? kpis.produtividade_sc_ha.toFixed(1) : "—" },
                    ].map(k => (
                        <Card key={k.label} className="rounded-sm border-l-[3px] border-l-primary/60 shadow-sm transition-all hover:shadow-md">
                            <CardHeader className="pb-1">
                                <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">
                                    {k.label}
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-2xl font-black tabular-nums">{k.value}</p>
                            </CardContent>
                        </Card>
                    )) : null
                }
            </div>

            {isLoading ? <Skeleton className="h-40 w-full rounded-sm" /> :
                romaneios.length === 0
                    ? (
                        <div className="flex flex-col items-center justify-center py-16 px-4 text-center border border-dashed rounded-sm bg-muted/10">
                            <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                <Wheat className="size-6 text-primary" />
                            </div>
                            <h3 className="text-lg font-semibold mb-1">Nenhum romaneio registrado</h3>
                            <p className="text-sm text-muted-foreground max-w-sm mb-5">
                                Você ainda não possui registros de romaneios de colheita. Clique abaixo para começar.
                            </p>
                            <Button variant="outline" size="sm" onClick={() => setShowDialog(true)} className="rounded-sm">
                                <Plus className="size-4 mr-1.5" /> Registrar Romaneio
                            </Button>
                        </div>
                    )
                    : <DataTable columns={columns} data={romaneios} />
            }

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <RomaneioForm safras={safras} onClose={() => setShowDialog(false)} onSubmit={mut.mutate} loading={mut.isPending} />
            </Dialog>
        </div>
    );
}

function RomaneioForm({ safras, onClose, onSubmit, loading }: { safras: Safra[]; onClose: () => void; onSubmit: (d: any) => void; loading: boolean }) {
    const { register, handleSubmit, reset, setValue } = useForm<any>();
    const { activeFazendaId } = useAppStore();
    
    const [selectedSafraId, setSelectedSafraId] = useState<string>("");

    const { data: talhoesSafra = [] } = useQuery<{ area_id: string }[]>({
        queryKey: ["safra-talhoes", selectedSafraId],
        queryFn: async () => {
            try {
                return await apiFetch(`/safras/${selectedSafraId}/talhoes`) as { area_id: string }[];
            } catch {
                return [];
            }
        },
        enabled: !!selectedSafraId,
    });

    const { data: puSafra = [] } = useQuery<{ area_id: string; area_nome?: string }[]>({
        queryKey: ["safra-production-units", selectedSafraId],
        queryFn: async () => {
            try {
                return await apiFetch(`/safras/${selectedSafraId}/production-units`) as { area_id: string; area_nome?: string }[];
            } catch {
                return [];
            }
        },
        enabled: !!selectedSafraId,
    });

    const { data: todasAreas = [] } = useQuery<{ id: string; nome: string }[]>({
        queryKey: ["areas-rurais", activeFazendaId],
        queryFn: async () => {
            const qs = activeFazendaId ? `&unidade_produtiva_id=${activeFazendaId}` : "";
            return await apiFetch(`/cadastros/areas-rurais?tipo=TALHAO${qs}`) as { id: string; nome: string }[];
        },
        enabled: !!selectedSafraId,
    });

    const talhoes = (() => {
        const map = new Map<string, { id: string; nome: string }>();
        // Legado
        talhoesSafra.forEach(t => {
            const area = todasAreas.find(a => a.id === t.area_id);
            if (area) map.set(area.id, { id: area.id, nome: area.nome });
        });
        // Moderno (Production Units)
        puSafra.forEach(pu => {
            if (pu.area_id) {
                map.set(pu.area_id, { 
                    id: pu.area_id, 
                    nome: pu.area_nome || todasAreas.find(a => a.id === pu.area_id)?.nome || "Área Desconhecida" 
                });
            }
        });
        return Array.from(map.values());
    })();

    return (
        <DialogContent className="max-w-xl p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
            <DialogHeader className="px-6 pt-6 pb-2">
                <div className="flex items-center gap-2.5">
                    <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                        <FileText className="size-4 text-primary" />
                    </div>
                    <DialogTitle>Novo Romaneio de Colheita</DialogTitle>
                </div>
            </DialogHeader>
            <form onSubmit={handleSubmit(d => {
                onSubmit({
                    ...d,
                    peso_bruto_kg: Number(d.peso_bruto_kg),
                    tara_kg: d.tara_kg ? Number(d.tara_kg) : 0,
                    umidade_pct: d.umidade_pct ? Number(d.umidade_pct) : undefined,
                    impureza_pct: d.impureza_pct ? Number(d.impureza_pct) : undefined,
                    preco_saca: d.preco_saca ? Number(d.preco_saca) : undefined,
                });
                reset();
            })} className="flex flex-col">
                <DialogBody className="px-6 py-6 space-y-8">
                    
                    {/* Seção 1: Origem e Informações Gerais */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                            Origem e Informações Gerais
                        </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Safra *</Label>
                                <Select onValueChange={(v: string) => { setValue("safra_id", v); setSelectedSafraId(v); }}>
                                    <SelectTrigger className="h-8 rounded-sm">
                                        <SelectValue placeholder="Selecione..." />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {safras.map(s => <SelectItem key={s.id} value={s.id}>{s.ano_safra} — {s.cultura}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Talhão *</Label>
                                <Select onValueChange={(v: string) => setValue("talhao_id", v)} disabled={!selectedSafraId}>
                                    <SelectTrigger className="h-8 rounded-sm">
                                        <SelectValue placeholder={selectedSafraId ? "Selecione..." : "Selecione a safra"} />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {talhoes.map(t => <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Data Colheita *</Label>
                                <Input type="date" className="h-8 rounded-sm" {...register("data_colheita", { required: true })} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Turno</Label>
                                <Select onValueChange={(v: string) => setValue("turno", v)}>
                                    <SelectTrigger className="h-8 rounded-sm">
                                        <SelectValue placeholder="Selecione..." />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-sm">
                                        {["MANHA", "TARDE", "NOITE"].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2 col-span-2">
                                <Label className="text-sm font-medium">Destino</Label>
                                <Input className="h-8 rounded-sm" {...register("destino")} placeholder="Ex: Cooperativa, Armazém" />
                            </div>
                        </div>
                    </div>

                    {/* Seção 2: Pesagem e Qualidade */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                            Pesagem e Qualidade
                        </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Nº Romaneio</Label>
                                <Input className="h-8 rounded-sm" {...register("numero_romaneio")} placeholder="Opcional" />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Peso Bruto (kg) *</Label>
                                <Input type="number" step="0.1" className="h-8 rounded-sm" {...register("peso_bruto_kg", { required: true })} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Tara (kg)</Label>
                                <Input type="number" step="0.1" className="h-8 rounded-sm" defaultValue="0" {...register("tara_kg")} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Umidade (%)</Label>
                                <Input type="number" step="0.1" className="h-8 rounded-sm" {...register("umidade_pct")} />
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Impureza (%)</Label>
                                <Input type="number" step="0.1" className="h-8 rounded-sm" {...register("impureza_pct")} />
                            </div>
                        </div>
                    </div>

                    {/* Seção 3: Comercial (Opcional) */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                            Comercial (Opcional)
                        </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label className="text-sm font-medium">Preço/Saca (R$)</Label>
                                <Input type="number" step="0.01" className="h-8 rounded-sm" {...register("preco_saca")} />
                            </div>
                        </div>
                    </div>

                </DialogBody>
                
                <DialogFooter className="px-6 py-4 bg-muted/50 border-t border-border/40">
                    <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => { onClose(); reset(); }}>
                        Cancelar
                    </Button>
                    <Button type="submit" variant="outline" size="sm" className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm" disabled={loading}>
                        {loading ? "Salvando…" : "Registrar Romaneio"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
