"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PackageSearch, Pencil, Lock, Eye } from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { toast } from "sonner";
import Link from "next/link";

interface LancamentoOrigemItem {
    lancamento_id: string;
    descricao: string;
    valor: number;
    origem: string;
    origem_id: string | null;
    data: string;
    categoria: string;
    gerado_automaticamente: boolean;
}

function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CATEGORIA_LABEL: Record<string, string> = {
    INSUMOS: "Insumos",
    MAO_OBRA: "Mão de obra",
    OPERACOES: "Operações",
    ADMINISTRATIVO: "Administrativo",
};

interface EditForm {
    descricao: string;
    valor: string;
    data: string;
    categoria: string;
}

interface Props {
    safraId: string;
}

export function LancamentosOrigemCard({ safraId }: Props) {
    const queryClient = useQueryClient();
    const [editItem, setEditItem] = useState<LancamentoOrigemItem | null>(null);
    const [form, setForm] = useState<EditForm>({ descricao: "", valor: "", data: "", categoria: "" });

    const { data: itens = [], isLoading } = useQuery<LancamentoOrigemItem[]>({
        queryKey: ["lancamentos-origens", safraId],
        queryFn: () => apiFetch(`/financeiro/lancamentos/origens?safra_id=${safraId}`),
        staleTime: 30_000,
    });

    const editMutation = useMutation({
        mutationFn: ({ id, body }: { id: string; body: object }) =>
            apiFetch(`/financeiro/lancamentos/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["lancamentos-origens", safraId] });
            queryClient.invalidateQueries({ queryKey: ["lancamentos-resumo"] });
            queryClient.invalidateQueries({ queryKey: ["lancamentos-insight"] });
            toast.success("Lançamento atualizado.");
            setEditItem(null);
        },
        onError: (err: Error) => toast.error(err.message),
    });

    function openEdit(item: LancamentoOrigemItem) {
        setEditItem(item);
        setForm({
            descricao: item.descricao,
            valor: String(item.valor),
            data: item.data,
            categoria: item.categoria,
        });
    }

    function submitEdit() {
        if (!editItem) return;
        const valor = parseFloat(form.valor.replace(",", "."));
        if (isNaN(valor) || valor <= 0) {
            toast.error("Valor inválido.");
            return;
        }
        editMutation.mutate({
            id: editItem.lancamento_id,
            body: { descricao: form.descricao, valor, data: form.data, categoria: form.categoria },
        });
    }

    if (isLoading) {
        return (
            <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full rounded-sm" />
                ))}
            </div>
        );
    }

    if (itens.length === 0) {
        return (
            <p className="text-sm text-muted-foreground text-center py-6">
                Nenhum lançamento registrado para esta safra.
            </p>
        );
    }

    const automaticos = itens.filter((i) => i.gerado_automaticamente).length;
    const manuais = itens.length - automaticos;

    return (
        <TooltipProvider>
            <div className="space-y-3">
                {/* Resumo */}
                <div className="flex gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <PackageSearch className="size-3 text-blue-600" />
                        <strong className="text-foreground">{automaticos}</strong> automático{automaticos !== 1 ? "s" : ""}
                    </span>
                    <span className="flex items-center gap-1">
                        <Pencil className="size-3 text-muted-foreground" />
                        <strong className="text-foreground">{manuais}</strong> manual{manuais !== 1 ? "is" : ""}
                    </span>
                </div>

                {/* Lista */}
                <div className="space-y-1.5">
                    {itens.map((item) => (
                        <div
                            key={item.lancamento_id}
                            className="flex items-center gap-3 rounded-sm border border-border bg-card px-3 py-2 text-sm"
                        >
                            {/* Badge origem */}
                            <div className="shrink-0">
                                {item.gerado_automaticamente ? (
                                    <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-blue-500/40 text-blue-700 bg-blue-500/5"
                                    >
                                        <PackageSearch className="size-2.5" />
                                        {item.origem === "ESTOQUE" ? "Estoque" : item.origem}
                                    </Badge>
                                ) : (
                                    <Badge
                                        variant="outline"
                                        className="text-[10px] gap-1 border-muted-foreground/30 text-muted-foreground"
                                    >
                                        <Pencil className="size-2.5" />
                                        Manual
                                    </Badge>
                                )}
                            </div>

                            {/* Descrição */}
                            <span className="flex-1 truncate text-foreground">{item.descricao}</span>

                            {/* Categoria */}
                            <span className="shrink-0 text-xs text-muted-foreground hidden sm:block">
                                {CATEGORIA_LABEL[item.categoria] ?? item.categoria}
                            </span>

                            {/* Data */}
                            <span className="shrink-0 text-xs text-muted-foreground">
                                {format(parseISO(item.data), "dd/MM/yy", { locale: ptBR })}
                            </span>

                            {/* Valor */}
                            <span className="shrink-0 font-semibold text-amber-700 tabular-nums">
                                {moeda(item.valor)}
                            </span>

                            {/* Ação editar ou ver movimentação */}
                            <div className="shrink-0">
                                {item.gerado_automaticamente ? (
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <span className="inline-flex">
                                                {item.origem === "ESTOQUE" && item.origem_id ? (
                                                    <Link href={`/estoque/movimentacoes/${item.origem_id}`}>
                                                        <Button
                                                            size="icon"
                                                            variant="ghost"
                                                            className="size-7 text-primary hover:bg-primary/10"
                                                            aria-label="Ver movimentação"
                                                        >
                                                            <Eye className="size-3.5" />
                                                        </Button>
                                                    </Link>
                                                ) : (
                                                    <Button
                                                        size="icon"
                                                        variant="ghost"
                                                        className="size-7 text-muted-foreground/40 cursor-not-allowed"
                                                        disabled
                                                        aria-label="Edição bloqueada"
                                                    >
                                                        <Lock className="size-3.5" />
                                                    </Button>
                                                )}
                                            </span>
                                        </TooltipTrigger>
                                        <TooltipContent side="left" className="max-w-52 text-xs">
                                            {item.origem === "ESTOQUE" 
                                                ? "Este custo foi gerado automaticamente pelo estoque. Ajuste na movimentação correspondente."
                                                : "Lançamento gerado automaticamente. Edição bloqueada."}
                                        </TooltipContent>
                                    </Tooltip>
                                ) : (
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        className="size-7 text-primary hover:text-primary"
                                        aria-label="Editar lançamento"
                                        onClick={() => openEdit(item)}
                                    >
                                        <Pencil className="size-3.5" />
                                    </Button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Dialog de edição */}
            <Dialog open={!!editItem} onOpenChange={(v) => !v && setEditItem(null)}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-base">
                            <Pencil className="size-4 text-primary" />
                            Editar lançamento manual
                        </DialogTitle>
                    </DialogHeader>

                    <div className="space-y-3 py-2">
                        <div className="space-y-1">
                            <Label>Descrição</Label>
                            <Input
                                value={form.descricao}
                                onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
                                maxLength={200}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <Label>Valor (R$)</Label>
                                <Input
                                    value={form.valor}
                                    onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
                                    inputMode="decimal"
                                />
                            </div>
                            <div className="space-y-1">
                                <Label>Data</Label>
                                <Input
                                    type="date"
                                    value={form.data}
                                    onChange={(e) => setForm((f) => ({ ...f, data: e.target.value }))}
                                />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label>Categoria</Label>
                            <Select value={form.categoria} onValueChange={(v) => setForm((f) => ({ ...f, categoria: v }))}>
                                <SelectTrigger>
                                    <span className="truncate">
                                        {CATEGORIA_LABEL[form.categoria as keyof typeof CATEGORIA_LABEL] ?? "Selecione a categoria"}
                                    </span>
                                </SelectTrigger>
                                <SelectContent>
                                    {Object.entries(CATEGORIA_LABEL).map(([k, v]) => (
                                        <SelectItem key={k} value={k}>{v}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditItem(null)}>Cancelar</Button>
                        <Button onClick={submitEdit} disabled={editMutation.isPending}>
                            {editMutation.isPending ? "Salvando..." : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </TooltipProvider>
    );
}
