"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import { PageHeader } from "@/components/shared/page-header";
import { Package, Calendar, Tag, ArrowLeft, Layers, Info, DollarSign, Settings2, AlertTriangle, CheckCircle2, History } from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Textarea } from "@/components/ui/textarea";

interface Movimentacao {
    id: string;
    produto_nome: string;
    deposito_nome: string;
    tipo: string;
    quantidade: number;
    custo_unitario: number;
    custo_total: number;
    data_movimentacao: string;
    motivo: string;
    origem_tipo: string;
    ajuste_de?: string;
    safra_id?: string;
    lote_id?: string;
}

interface LancamentoFinanceiroSimplificado {
    id: string;
    valor: number;
    categoria: string;
    data: string;
}

interface AjusteAuditoriaItem {
    id: string;
    tipo: string;
    quantidade: number;
    motivo: string;
    created_at: string;
    lancamento_financeiro?: LancamentoFinanceiroSimplificado;
}

interface AuditoriaMovimentacao {
    movimentacao_original: Movimentacao;
    ajustes: AjusteAuditoriaItem[];
}

function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function MovimentacaoDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const queryClient = useQueryClient();
    const [isAjusteOpen, setIsAjusteOpen] = useState(false);
    const [tipoAjuste, setTipoAjuste] = useState<"ENTRADA" | "SAIDA">("SAIDA");

    const { data: mov, isLoading, error } = useQuery<Movimentacao>({
        queryKey: ["estoque-movimentacao", id],
        queryFn: () => apiFetch(`/estoque/movimentacoes/${id}`),
        enabled: !!id,
    });

    const { data: audit, isLoading: isAuditLoading } = useQuery<AuditoriaMovimentacao>({
        queryKey: ["estoque-movimentacao-auditoria", id],
        queryFn: () => apiFetch(`/estoque/movimentacoes/${id}/auditoria`),
        enabled: !!id,
    });

    // Initialize tipoAjuste based on mov when it's first loaded
    const [hasInitialized, setHasInitialized] = useState(false);
    if (mov && !hasInitialized) {
        setTipoAjuste(mov.tipo === "ENTRADA" ? "SAIDA" : "ENTRADA");
        setHasInitialized(true);
    }

    const mutation = useMutation({
        mutationFn: (payload: { tipo_ajuste: "ENTRADA" | "SAIDA"; quantidade: number; motivo: string }) =>
            apiFetch(`/estoque/movimentacoes/${id}/ajustar`, {
                method: "POST",
                body: JSON.stringify(payload),
            }),
        onSuccess: () => {
            toast.success("Ajuste realizado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["estoque-movimentacao", id] });
            queryClient.invalidateQueries({ queryKey: ["estoque-movimentacao-auditoria", id] });
            setIsAjusteOpen(false);
        },
        onError: (err: any) => {
            toast.error(err.message || "Erro ao realizar ajuste.");
        },
    });

    const handleAjustar = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const payload = {
            tipo_ajuste: formData.get("tipo_ajuste") as "ENTRADA" | "SAIDA",
            quantidade: Number(formData.get("quantidade")),
            motivo: formData.get("motivo") as string,
        };

        if (!payload.quantidade || payload.quantidade <= 0) {
            toast.error("Informe uma quantidade válida.");
            return;
        }

        if (!payload.motivo || payload.motivo.length < 3) {
            toast.error("Informe um motivo válido (mínimo 3 caracteres).");
            return;
        }

        mutation.mutate(payload);
    };

    if (isLoading) {
        return (
            <div className="p-8 space-y-6">
                <Skeleton className="h-12 w-64" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                </div>
            </div>
        );
    }

    if (error || !mov) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="h-16 w-16 rounded-full bg-red-50 flex items-center justify-center text-red-600">
                    <Info size={32} />
                </div>
                <h1 className="text-xl font-bold">Movimentação não encontrada</h1>
                <p className="text-muted-foreground">Não foi possível carregar os detalhes desta movimentação.</p>
                <Button variant="outline" size="sm" onClick={() => router.back()}>
                    <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
                </Button>
            </div>
        );
    }

    const isEntrada = mov.tipo === "ENTRADA";
    const isAjuste = mov.tipo.startsWith("AJUSTE");

    return (
        <div className="max-w-[1400px] w-full pt-4 px-6 animate-in fade-in slide-in-from-bottom-2 duration-500 pb-12">
            <div className="mb-4">
                <button
                    onClick={() => router.back()}
                    className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-primary transition-colors uppercase tracking-widest"
                >
                    <ArrowLeft size={14} />
                    Voltar para lançamentos
                </button>
            </div>

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <PageHeader
                    title="Detalhe da Movimentação"
                    description="Rastreabilidade total do registro de estoque e seu impacto financeiro."
                    icon={<Package className="h-8 w-8 text-primary" />}
                />

                <div className="flex items-center gap-2">
                    <Dialog open={isAjusteOpen} onOpenChange={setIsAjusteOpen}>
                        <DialogTrigger asChild>
                            <Button variant="outline" size="sm" className="bg-primary/5 border-primary/20 text-primary hover:bg-primary/10">
                                <Settings2 className="mr-2 h-4 w-4" /> Solicitar Ajuste
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[425px] rounded-sm">
                            <form onSubmit={handleAjustar}>
                                <DialogHeader>
                                    <DialogTitle className="flex items-center gap-2">
                                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                                        Ajuste de Movimentação
                                    </DialogTitle>
                                    <DialogDescription>
                                        Esta ação não altera o registro original. Uma nova movimentação de correção será criada vinculada a esta.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid gap-4 py-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="tipo_ajuste" className="text-xs font-bold uppercase tracking-wider">Tipo de Ajuste</Label>
                                        <input type="hidden" name="tipo_ajuste" value={tipoAjuste} />
                                        <Select value={tipoAjuste} onValueChange={(v) => setTipoAjuste(v as "ENTRADA" | "SAIDA")}>
                                            <SelectTrigger id="tipo_ajuste" className="h-9 rounded-sm">
                                                <SelectValue placeholder="Selecione o tipo" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="ENTRADA">Entrada (Aumentar estoque)</SelectItem>
                                                <SelectItem value="SAIDA">Saída (Diminuir estoque)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <p className="text-[10px] text-muted-foreground italic">
                                            {isEntrada ? "* Geralmente se a entrada foi errada, você quer fazer uma SAÍDA de correção." : "* Se a saída foi excessiva, você quer fazer uma ENTRADA de correção."}
                                        </p>
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="quantidade" className="text-xs font-bold uppercase tracking-wider">Quantidade do Ajuste</Label>
                                        <Input
                                            id="quantidade"
                                            name="quantidade"
                                            type="number"
                                            step="0.01"
                                            placeholder="Ex: 10.5"
                                            className="h-9 rounded-sm"
                                            required
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="motivo" className="text-xs font-bold uppercase tracking-wider">Motivo da Correção</Label>
                                        <Textarea
                                            id="motivo"
                                            name="motivo"
                                            placeholder="Descreva o motivo deste ajuste..."
                                            className="min-h-[80px] rounded-sm resize-none"
                                            required
                                        />
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button type="submit" size="sm" className="rounded-sm" disabled={mutation.isPending}>
                                        {mutation.isPending ? "Processando..." : "Confirmar Ajuste"}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Coluna da Esquerda: Detalhes */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-card rounded-sm border border-border shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-border bg-muted/30 flex items-center justify-between">
                            <h3 className="text-xs font-bold flex items-center gap-2 uppercase tracking-widest text-foreground/70">
                                <Info size={14} className="text-primary" />
                                Informações do Registro
                            </h3>
                            {mov.ajuste_de && (
                                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] uppercase font-bold px-2 py-0 h-5">
                                    <History size={10} className="mr-1" /> Ajuste de Outro Registro
                                </Badge>
                            )}
                        </div>
                        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-12">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                    <Package size={12} /> Produto
                                </label>
                                <p className="text-sm font-semibold text-foreground">{mov.produto_nome}</p>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                    <Calendar size={12} /> Data do Movimento
                                </label>
                                <p className="text-sm font-semibold text-foreground">
                                    {format(parseISO(mov.data_movimentacao), "PPP", { locale: ptBR })}
                                </p>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                    <Tag size={12} /> Tipo / Operação
                                </label>
                                <div>
                                    <Badge className={`rounded-sm text-[10px] uppercase font-bold ${
                                        isEntrada 
                                        ? "bg-green-100 text-green-700 border-green-200" 
                                        : "bg-orange-100 text-orange-700 border-orange-200"
                                    }`}>
                                        {mov.tipo}
                                    </Badge>
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                    <Layers size={12} /> Depósito / Local
                                </label>
                                <p className="text-sm font-semibold text-foreground">{mov.deposito_nome}</p>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                    Origem do Dado
                                </label>
                                <p className="text-xs font-medium text-foreground/60">{mov.origem_tipo || "Lançamento Direto"}</p>
                            </div>

                            {mov.motivo && (
                                <div className="sm:col-span-2 space-y-1.5">
                                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
                                        Observações / Justificativa
                                    </label>
                                    <div className="text-xs text-foreground/80 bg-muted/40 p-4 rounded-sm border border-border/50 leading-relaxed italic">
                                        "{mov.motivo}"
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Auditoria de Ajustes */}
                    <div className="bg-card rounded-sm border border-border shadow-sm overflow-hidden mt-6">
                        <div className="px-6 py-4 border-b border-border bg-muted/30 flex items-center justify-between">
                            <h3 className="text-xs font-bold flex items-center gap-2 uppercase tracking-widest text-foreground/70">
                                <History size={14} className="text-primary" />
                                Auditoria de Ajustes
                            </h3>
                            <Badge variant="outline" className="text-[10px] uppercase font-bold h-5">
                                {audit?.ajustes.length || 0} Registros
                            </Badge>
                        </div>
                        <div className="p-0">
                            {isAuditLoading ? (
                                <div className="p-6 space-y-4">
                                    <Skeleton className="h-12 w-full" />
                                    <Skeleton className="h-12 w-full" />
                                </div>
                            ) : audit?.ajustes && audit.ajustes.length > 0 ? (
                                <div className="divide-y divide-border/40">
                                    {audit.ajustes.map((ajuste) => (
                                        <div key={ajuste.id} className="p-6 hover:bg-muted/10 transition-colors">
                                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-3">
                                                <div className="flex items-center gap-3">
                                                    <Badge className={`rounded-sm text-[9px] uppercase font-black px-1.5 h-4 ${
                                                        ajuste.tipo === "ENTRADA" 
                                                        ? "bg-green-100 text-green-700 border-green-200" 
                                                        : "bg-orange-100 text-orange-700 border-orange-200"
                                                    }`}>
                                                        {ajuste.tipo}
                                                    </Badge>
                                                    <span className="text-sm font-bold text-foreground">
                                                        {ajuste.quantidade.toLocaleString("pt-BR")} unidades
                                                    </span>
                                                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
                                                        • {format(parseISO(ajuste.created_at), "dd/MM/yyyy HH:mm")}
                                                    </span>
                                                </div>
                                                
                                                {ajuste.lancamento_financeiro && (
                                                    <div className="flex items-center gap-2 bg-green-50 px-2 py-1 rounded-sm border border-green-100">
                                                        <DollarSign size={12} className="text-green-600" />
                                                        <span className="text-[10px] font-bold text-green-700 uppercase tracking-tighter">
                                                            Impacto: {moeda(ajuste.lancamento_financeiro.valor)}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                            <p className="text-xs text-foreground/70 leading-relaxed italic border-l-2 border-primary/20 pl-3">
                                                "{ajuste.motivo || "Sem motivo informado"}"
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-12 flex flex-col items-center justify-center text-center space-y-3">
                                    <div className="h-12 w-12 rounded-full bg-muted/30 flex items-center justify-center text-muted-foreground/40">
                                        <History size={24} />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-foreground/60 uppercase tracking-tight">Sem ajustes registrados</p>
                                        <p className="text-xs text-muted-foreground max-w-[200px] mx-auto">
                                            Nenhuma correção foi solicitada para esta movimentação até o momento.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Timeline ou Histórico Simples se for ajuste */}
                    {mov.ajuste_de && (
                        <Alert variant="info">
                            <Info />
                            <AlertTitle className="text-xs font-bold uppercase tracking-tight">Vínculo de Auditoria</AlertTitle>
                            <AlertDescription className="text-xs leading-relaxed">
                                Este registro é uma correção vinculada à movimentação <span className="font-mono font-bold">#{mov.ajuste_de.substring(0, 8)}</span>.
                                Ambos os registros permanecem no sistema para fins de auditoria e integridade de saldo histórico.
                            </AlertDescription>
                        </Alert>
                    )}
                </div>

                {/* Coluna da Direita: Resumo Financeiro */}
                <div className="space-y-6">
                    <div className="bg-card rounded-sm border border-border shadow-sm overflow-hidden">
                        <div className="px-6 py-4 border-b border-border bg-primary/5 flex items-center justify-between">
                            <h3 className="text-xs font-bold flex items-center gap-2 uppercase tracking-widest text-primary">
                                <DollarSign size={14} /> Impacto Financeiro
                            </h3>
                            <CheckCircle2 size={14} className="text-green-500" />
                        </div>
                        <div className="p-6 space-y-6">
                            <div className="flex justify-between items-end border-b border-border/40 pb-4">
                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                        Quantidade
                                    </label>
                                    <p className="text-2xl font-black text-foreground tabular-nums">
                                        {mov.quantidade.toLocaleString("pt-BR")}
                                    </p>
                                </div>
                                <div className="text-right space-y-1">
                                    <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                        Custo Unitário
                                    </label>
                                    <p className="text-sm font-bold text-foreground/70 tabular-nums">
                                        {moeda(mov.custo_unitario)}
                                    </p>
                                </div>
                            </div>

                            <div className="pt-2">
                                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest block mb-1">
                                    Custo Total Gerado
                                </label>
                                <p className={`text-3xl font-black tabular-nums ${isEntrada ? "text-foreground" : "text-amber-600"}`}>
                                    {moeda(mov.custo_total)}
                                </p>
                                <p className="text-[10px] text-muted-foreground mt-1">
                                    {isEntrada 
                                        ? "Valor agregado ao patrimônio em estoque." 
                                        : "Custo apropriado diretamente ao centro de custo/safra."}
                                </p>
                            </div>
                        </div>
                        <div className="bg-muted/30 px-6 py-4 border-t border-border">
                            <p className="text-[10px] text-muted-foreground leading-relaxed">
                                <span className="font-bold">Nota de Integridade:</span> Este registro foi gerado pelo subsistema de estoque e não permite edição direta de valores financeiros para garantir a conciliação física.
                            </p>
                        </div>
                    </div>

                    {mov.safra_id && (
                        <div className="bg-card rounded-sm border border-border shadow-sm p-6 flex items-center gap-4">
                            <div className="h-10 w-10 rounded-sm bg-green-50 flex items-center justify-center text-green-600">
                                <CheckCircle2 size={20} />
                            </div>
                            <div>
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Safra Vinculada</p>
                                <p className="text-xs font-semibold">Apropriado em Safra Vigente</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
