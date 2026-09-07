"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm, useWatch } from "react-hook-form";
import { Plus, MoreHorizontal, X, BookmarkCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription, DialogClose } from "@/components/ui/dialog";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { ContratoFuturo } from "../types";
import {
    CultivoOption,
    CommodityOption,
    SafraOption,
    resolveCommodityFromCultivos,
    resolveCommodityFromSafra,
    resolveCommodityFromSelection,
} from "./commodity-resolution";

type ContratoPayload = {
    safra_id?: string;
    commodity_id?: string | null;
    commodity: string;
    mercado?: string;
    mes_vencimento: string;
    tipo_posicao: "COMPRA" | "VENDA";
    quantidade: number;
    preco_contratado: number | null;
};

export function ContratosClient({
    initialContratos, initialSafras, initialCommodities
}: {
    initialContratos: ContratoFuturo[], initialSafras: SafraOption[], initialCommodities: CommodityOption[]
}) {
    const qc = useQueryClient();
    const [showDialog, setShowDialog] = useState(false);

    const { data: contratos = [], isLoading } = useQuery<ContratoFuturo[]>({
        queryKey: ["financeiro", "hedge", "contratos"],
        queryFn: () => apiFetch("/financeiro/hedge/contratos"),
        initialData: initialContratos,
    });

    const { data: safras = [] } = useQuery<SafraOption[]>({
        queryKey: ["agricola", "safras"],
        queryFn: () => apiFetch("/safras"),
        initialData: initialSafras,
        staleTime: 0,
        refetchOnMount: "always",
    });

    const { data: commodities = [] } = useQuery<CommodityOption[]>({
        queryKey: ["cadastros", "commodities"],
        queryFn: () => apiFetch("/cadastros/commodities"),
        initialData: initialCommodities,
        staleTime: 0,
        refetchOnMount: "always",
    });

    const mut = useMutation({
        mutationFn: (d: ContratoPayload) => apiFetch("/financeiro/hedge/contratos", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { 
            qc.invalidateQueries({ queryKey: ["financeiro", "hedge", "contratos"] }); 
            setShowDialog(false); 
            toast.success("Contrato futuro criado com sucesso."); 
        },
        onError: (e: Error) => toast.error(e.message || "Erro ao criar contrato."),
    });

    const cols: ColumnDef<ContratoFuturo>[] = [
        { 
            id: "safra", header: "Safra", accessorKey: "safra_id", 
            cell: (_v, d) => {
                const s = safras.find(s => s.id === d.safra_id);
                if (!s) return "—";
                return s.cultura ? `${s.ano_safra} - ${s.cultura}` : s.ano_safra;
            }
        },
        { id: "commodity", header: "Commodity", accessorKey: "commodity" },
        { id: "mercado", header: "Mercado", accessorKey: "mercado", cell: (_v, d) => d.mercado || "—" },
        { id: "vencimento", header: "Vencimento", accessorKey: "mes_vencimento", cell: (_v, d) => d.mes_vencimento || "—" },
        { id: "quantidade", header: "Quantidade", accessorKey: "quantidade", cell: (_v, d) => `${d.quantidade.toLocaleString("pt-BR")} ${d.unidade || "sc"}` },
        { id: "posicao", header: "Posição", accessorKey: "tipo_posicao" },
        { id: "preco", header: "Preço", accessorKey: "preco_contratado", cell: (_v, d) => d.preco_contratado ? d.preco_contratado.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—" },
        { id: "status", header: "Status", accessorKey: "status", cell: (_v, d) => <WorkflowStatusBadge status={d.status} /> },
        {
            id: "actions",
            header: "",
            cell: () => (
                <div className="flex justify-end gap-0">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground rounded-sm">
                        <MoreHorizontal className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Contratos Futuros"
                description="Gestão de instrumentos de proteção de preço"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Contratos Futuros" }
                ]}
                icon={<BookmarkCheck className="text-primary" size={22} />}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowDialog(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                    >
                        <Plus className="size-4 mr-1.5" /> Novo Contrato
                    </Button>
                }
            />

            <Card className="rounded-sm">
                <CardContent className="p-0">
                    {isLoading ? <div className="p-4"><Skeleton className="h-64 w-full rounded-sm" /></div> :
                        contratos.length === 0
                            ? (
                                <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10">
                                    <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                        <BookmarkCheck className="size-6 text-primary" />
                                    </div>
                                    <h3 className="text-lg font-semibold mb-1">Nenhum contrato futuro registrado</h3>
                                    <p className="text-sm text-muted-foreground max-w-sm mb-5">
                                        Você ainda não possui registros de contratos de hedge. Clique abaixo para cadastrar.
                                    </p>
                                    <Button variant="outline" size="sm" onClick={() => setShowDialog(true)} className="rounded-sm">
                                        <Plus className="size-4 mr-1.5" /> Novo Contrato
                                    </Button>
                                </div>
                            )
                            : <DataTable columns={cols} data={contratos} searchable exportable />
                    }
                </CardContent>
            </Card>

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <ContratoForm
                    safras={safras}
                    commodities={commodities}
                    onClose={() => setShowDialog(false)}
                    onSubmit={mut.mutate}
                    loading={mut.isPending}
                />
            </Dialog>
        </div>
    );
}

function ContratoForm({
    safras,
    commodities,
    onClose,
    onSubmit,
    loading,
}: {
    safras: SafraOption[];
    commodities: CommodityOption[];
    onClose: () => void;
    onSubmit: (d: ContratoPayload) => void;
    loading: boolean;
}) {
    const form = useForm<{
        safra_id?: string;
        commodity_id?: string;
        mercado?: string;
        mes_vencimento: string;
        tipo_posicao: "COMPRA" | "VENDA";
        quantidade: string;
        preco_contratado?: string;
    }>({
        defaultValues: { tipo_posicao: "VENDA" }
    });

    const safraId = useWatch({ control: form.control, name: "safra_id" });
    const commodityId = useWatch({ control: form.control, name: "commodity_id" });
    const { data: safraCultivos = [] } = useQuery<CultivoOption[]>({
        queryKey: ["agricola", "safras", safraId ?? "sem-safra", "cultivos"],
        queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
        enabled: Boolean(safraId),
        staleTime: 0,
        refetchOnMount: "always",
    });
    const selectedSafra = useMemo(
        () => safras.find((safra) => safra.id === safraId),
        [safraId, safras],
    );
    const autoCommodity = useMemo(
        () => resolveCommodityFromCultivos(safraCultivos, commodities)
            ?? resolveCommodityFromSafra(selectedSafra, commodities),
        [commodities, safraCultivos, selectedSafra],
    );
    const derivedCommodity = useMemo(
        () => autoCommodity,
        [autoCommodity],
    );
    const selectedCommodity = useMemo(
        () => resolveCommodityFromSelection(commodityId, commodities),
        [commodityId, commodities],
    );
    const commodityReadOnly = Boolean(derivedCommodity);
    const commodityValue = derivedCommodity?.nome ?? selectedCommodity?.nome ?? "";
    const commodityHint = commodityReadOnly
        ? "Commodity definida automaticamente pela Safra."
        : safraId
            ? "Não foi possível identificar automaticamente a Commodity desta Safra. Selecione uma Commodity."
            : "Commodity obrigatória para contratos sem Safra.";
    const commodityRequired = !commodityReadOnly;
    const lastAutoCommodityId = useRef<string | null>(null);

    useEffect(() => {
        if (!safraId) {
            lastAutoCommodityId.current = null;
            if (commodityId) {
                form.setValue("commodity_id", undefined, { shouldValidate: true });
            }
            return;
        }

        if (derivedCommodity) {
            lastAutoCommodityId.current = derivedCommodity.id;
            if (commodityId !== derivedCommodity.id) {
                form.setValue("commodity_id", derivedCommodity.id, { shouldValidate: true });
            }
            return;
        }

        if (commodityId && commodityId === lastAutoCommodityId.current) {
            form.setValue("commodity_id", undefined, { shouldValidate: true });
        }
        lastAutoCommodityId.current = null;
    }, [commodityId, derivedCommodity, form, safraId]);

    return (
        <DialogContent className="sm:max-w-md">
            <DialogHeader>
                <DialogTitle>Novo Contrato Futuro</DialogTitle>
                <DialogDescription>
                    Registre um novo instrumento financeiro de proteção (Hedge)
                </DialogDescription>
            </DialogHeader>

            <Form {...form}>
                <form id="contrato-form" onSubmit={form.handleSubmit(d => { 
                    const commodity = derivedCommodity ?? selectedCommodity;
                    if (!commodity) {
                        toast.error("Selecione uma commodity.");
                        return;
                    }
                    onSubmit({
                        ...d,
                        commodity_id: commodity.id,
                        commodity: commodity.nome,
                        quantidade: parseFloat(d.quantidade),
                        preco_contratado: d.preco_contratado ? parseFloat(d.preco_contratado) : null
                    }); 
                    form.reset(); 
                })}>
                    <DialogBody className="space-y-4">
                        <FormField
                            control={form.control}
                            name="safra_id"
                            rules={{}}
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Safra *</FormLabel>
                                    <div className="flex items-center gap-2">
                                        <Select
                                            onValueChange={(v) => {
                                                field.onChange(v);
                                                if (!v) {
                                                    form.setValue("commodity_id", undefined, { shouldValidate: true });
                                                }
                                            }}
                                            value={field.value}
                                        >
                                            <FormControl>
                                                <SelectTrigger className="h-8 text-sm rounded-sm">
                                                    <SelectValue placeholder="Selecione a safra" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent className="rounded-sm">
                                                {safras.map(s => <SelectItem key={s.id} value={s.id} className="text-sm">{s.cultura ? `${s.ano_safra} - ${s.cultura}` : s.ano_safra}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                            {field.value ? (
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-8 w-8 rounded-sm text-muted-foreground"
                                                    aria-label="Limpar safra"
                                                    onClick={() => {
                                                        field.onChange(undefined);
                                                        form.setValue("commodity_id", undefined, { shouldValidate: true });
                                                    }}
                                                >
                                                <X className="h-4 w-4" />
                                            </Button>
                                        ) : null}
                                    </div>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="space-y-2">
                            <FormLabel>Commodity *</FormLabel>
                            {commodityReadOnly ? (
                                <div className="space-y-1">
                                    <Input
                                        className="h-8 text-sm rounded-sm"
                                        value={commodityValue}
                                        disabled
                                        readOnly
                                    />
                                    <CardDescription className="text-xs text-muted-foreground">
                                        {commodityHint}
                                    </CardDescription>
                                </div>
                            ) : (
                                <div className="space-y-1">
                                    <FormField
                                        control={form.control}
                                        name="commodity_id"
                                        rules={commodityRequired ? { required: "Obrigatório" } : {}}
                                        render={({ field }) => (
                                            <FormItem>
                                                <Select
                                                    onValueChange={(value) => field.onChange(value)}
                                                    value={field.value}
                                                    disabled={commodities.length === 0}
                                                >
                                                    <FormControl>
                                                        <SelectTrigger className="h-8 text-sm rounded-sm">
                                                            <SelectValue placeholder={commodities.length === 0 ? "Carregando commodities..." : "Selecione a commodity"} />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent className="rounded-sm">
                                                        {commodities.map((commodity) => (
                                                            <SelectItem key={commodity.id} value={commodity.id} className="text-sm">
                                                                {commodity.nome}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <CardDescription className="text-xs text-muted-foreground">
                                        {commodityHint}
                                    </CardDescription>
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="mercado"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Mercado</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" placeholder="Ex: B3" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="mes_vencimento"
                                rules={{ required: "Obrigatório" }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Mês Venc. *</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" placeholder="Ex: 2027-05" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="tipo_posicao"
                                rules={{ required: "Obrigatório" }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Posição *</FormLabel>
                                        <Select onValueChange={field.onChange} value={field.value}>
                                            <FormControl>
                                                <SelectTrigger className="h-8 text-sm rounded-sm">
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent className="rounded-sm">
                                                <SelectItem value="COMPRA" className="text-sm">COMPRA</SelectItem>
                                                <SelectItem value="VENDA" className="text-sm">VENDA</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="quantidade"
                                rules={{ required: "Obrigatório", min: { value: 0.01, message: "Valor inválido" } }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Quantidade *</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" type="number" step="0.01" min="0.01" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="preco_contratado"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Preço (R$)</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" type="number" step="0.01" min="0" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                    </DialogBody>

                    <DialogFooter>
                        <DialogClose asChild>
                            <Button size="sm" type="button" variant="outline" className="rounded-sm" onClick={() => form.reset()}>
                                Cancelar
                            </Button>
                        </DialogClose>
                        <Button size="sm" type="submit" className="rounded-sm" disabled={loading}>
                            {loading ? "Salvando…" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </form>
            </Form>
        </DialogContent>
    );
}
