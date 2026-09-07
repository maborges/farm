"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useForm } from "react-hook-form";
import { Plus, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { HedgeRegistro, ContratoFuturo } from "../types";

type RegistroPayload = {
    contrato_futuro_id?: string;
    tipo: "ABERTURA" | "ROLAGEM" | "ENCERRAMENTO" | "AJUSTE";
    data_operacao: string;
    quantidade: number;
    preco: number;
    observacoes?: string;
};

export function RegistrosClient({ 
    initialRegistros, contratos 
}: { 
    initialRegistros: HedgeRegistro[], contratos: ContratoFuturo[] 
}) {
    const qc = useQueryClient();
    const [showDialog, setShowDialog] = useState(false);

    const { data: registros = [], isLoading } = useQuery<HedgeRegistro[]>({
        queryKey: ["financeiro", "hedge", "registros"],
        queryFn: () => apiFetch("/financeiro/hedge/registros"),
        initialData: initialRegistros,
    });

    const mut = useMutation({
        mutationFn: (d: RegistroPayload) => apiFetch("/financeiro/hedge/registros", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { 
            qc.invalidateQueries({ queryKey: ["financeiro", "hedge", "registros"] }); 
            setShowDialog(false); 
            toast.success("Operação registrada com sucesso."); 
        },
        onError: (e: Error) => toast.error(e.message || "Erro ao registrar operação."),
    });

    const cols: ColumnDef<HedgeRegistro>[] = [
        { id: "data", header: "Data", accessorKey: "data_operacao", cell: (_v, d) => new Date(d.data_operacao).toLocaleDateString("pt-BR") },
        { 
            id: "contrato", header: "Contrato", accessorKey: "contrato_futuro_id", 
            cell: (_v, d) => {
                const c = contratos.find(x => x.id === d.contrato_futuro_id);
                return c ? `${c.commodity} - ${c.mes_vencimento || c.mercado}` : "—";
            }
        },
        { id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (_v, d) => <Badge variant="outline">{d.tipo}</Badge> },
        { id: "quantidade", header: "Quantidade", accessorKey: "quantidade", cell: (_v, d) => d.quantidade.toLocaleString("pt-BR") },
        { id: "preco", header: "Preço", accessorKey: "preco", cell: (_v, d) => d.preco.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) },
        { id: "resultado", header: "Result. Papel", accessorKey: "resultado_papel", cell: (_v, d) => d.resultado_papel ? d.resultado_papel.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—" },
        {
            id: "actions",
            header: "",
            cell: () => (
                <div className="flex justify-end gap-0">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 rounded-sm">
                        <Plus className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    const contratosAbertos = contratos.filter(c => c.status === "ABERTO");

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-500">
            <PageHeader
                title="Registros de Operações"
                description="Aberturas, rolagens, ajustes e encerramentos"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Registros de Operações" }
                ]}
                icon={<ClipboardList className="text-primary" size={22} />}
                actions={
                    <Button variant="outline" size="sm" className="rounded-sm font-bold border-primary text-primary hover:bg-primary/5" onClick={() => setShowDialog(true)}>
                        <Plus className="size-4 mr-1" /> Registrar Operação
                    </Button>
                }
            />

            <DataTable 
                columns={cols} 
                data={registros} 
                isLoading={isLoading}
                emptyMessage="Nenhuma operação registrada."
                searchable 
                exportable 
            />

            <Dialog open={showDialog} onOpenChange={v => { if (!v) setShowDialog(false); }}>
                <RegistroForm contratos={contratosAbertos} onClose={() => setShowDialog(false)} onSubmit={mut.mutate} loading={mut.isPending} />
            </Dialog>
        </div>
    );
}

function RegistroForm({ contratos, onClose, onSubmit, loading }: { contratos: ContratoFuturo[]; onClose: () => void; onSubmit: (d: RegistroPayload) => void; loading: boolean }) {
    const form = useForm<{
        contrato_futuro_id?: string;
        tipo: "ABERTURA" | "ROLAGEM" | "ENCERRAMENTO" | "AJUSTE";
        data_operacao: string;
        quantidade: string;
        preco: string;
        observacoes?: string;
    }>({
        defaultValues: { tipo: "ABERTURA", data_operacao: new Date().toISOString().split("T")[0] }
    });

    const contratoId = form.watch("contrato_futuro_id");

    return (
        <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle>Registrar Operação</DialogTitle></DialogHeader>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(d => { 
                    onSubmit({
                        ...d,
                        quantidade: parseFloat(d.quantidade),
                        preco: parseFloat(d.preco)
                    }); 
                    form.reset(); 
                })}>
                    <DialogBody className="space-y-4">
                        <FormField
                            control={form.control}
                            name="contrato_futuro_id"
                            rules={{ required: "Selecione o contrato." }}
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Contrato Futuro *</FormLabel>
                                    <Select value={field.value} onValueChange={field.onChange}>
                                        <FormControl>
                                            <SelectTrigger className="h-8 text-sm rounded-sm">
                                                <SelectValue placeholder="Selecione o contrato aberto" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent className="rounded-sm">
                                            {contratos.length === 0 ? <SelectItem value="none" disabled className="text-sm">Nenhum contrato aberto</SelectItem> : null}
                                            {contratos.map(c => <SelectItem key={c.id} value={c.id} className="text-sm">{c.commodity} ({c.mes_vencimento}) - {c.tipo_posicao}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="tipo"
                                rules={{ required: "Obrigatório" }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Tipo Operação *</FormLabel>
                                        <Select value={field.value} onValueChange={field.onChange}>
                                            <FormControl>
                                                <SelectTrigger className="h-8 text-sm rounded-sm"><SelectValue /></SelectTrigger>
                                            </FormControl>
                                            <SelectContent className="rounded-sm">
                                                <SelectItem value="ABERTURA" className="text-sm">ABERTURA</SelectItem>
                                                <SelectItem value="ROLAGEM" className="text-sm">ROLAGEM</SelectItem>
                                                <SelectItem value="AJUSTE" className="text-sm">AJUSTE</SelectItem>
                                                <SelectItem value="ENCERRAMENTO" className="text-sm">ENCERRAMENTO</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="data_operacao"
                                rules={{ required: "Obrigatório" }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Data Operação *</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" {...field} type="date" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={form.control}
                                name="quantidade"
                                rules={{ required: "Obrigatório", min: { value: 0.01, message: "Mín. 0.01" } }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Quantidade *</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" {...field} type="number" step="0.01" min="0.01" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="preco"
                                rules={{ required: "Obrigatório", min: { value: 0.01, message: "Mín. 0.01" } }}
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Preço *</FormLabel>
                                        <FormControl>
                                            <Input className="h-8 text-sm rounded-sm" {...field} type="number" step="0.01" min="0.01" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                        
                        <FormField
                            control={form.control}
                            name="observacoes"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Observações</FormLabel>
                                    <FormControl>
                                        <Textarea className="text-sm rounded-sm" {...field} rows={2} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </DialogBody>

                    <DialogFooter>
                        <Button size="sm" type="button" variant="outline" className="rounded-sm" onClick={() => { onClose(); form.reset(); }}>Cancelar</Button>
                        <Button size="sm" type="submit" variant="outline" className="rounded-sm" disabled={loading || !contratoId || contratos.length === 0}>{loading ? "Salvando…" : "Registrar"}</Button>
                    </DialogFooter>
                </form>
            </Form>
        </DialogContent>
    );
}
