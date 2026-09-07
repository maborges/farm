"use client";

import { useState } from "react";
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ProdutoCombobox } from "@/components/shared/produto-combobox";
import { TipoServicoCombobox } from "@/components/shared/tiposervico-combobox";
import { ColaboradorCombobox } from "@/components/shared/colaborador-combobox";
import { EquipamentoCombobox } from "@/components/shared/equipamento-combobox";
import { cn } from "@/lib/utils";
import { useForm } from "react-hook-form";
import {
    Plus, Trash2, ClipboardCheck, CalendarDays, PackageSearch,
    Users2, ShoppingCart, Lock, Unlock, RotateCw, CheckCircle2, XCircle, Save,
    Scale, TrendingUp, TrendingDown, MapPin, AlertTriangle, Layers, FlaskConical,
    Pencil, Ban, Eye, Tractor, HelpCircle, Package,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlanoOperacional {
    id: string;
    nome: string;
    descricao: string | null;
    data_inicio_prevista: string;
    data_fim_prevista: string | null;
    status: string;
    versao: number;
}

interface PlanoItem {
    id: string;
    safra_tarefa_id: string;
    status_planejamento: string;
    data_programada: string | null;
    ordem_execucao: number | null;
}

interface Insumo {
    id: string;
    produto_id: string;
    unidade_dose: string;
    quantidade_planejada: number;
    quantidade_disponivel_snapshot: number | null;
    quantidade_reservada: number | null;
    quantidade_faltante: number | null;
    custo_unitario_snapshot: number | null;
    custo_total_estimado: number | null;
    fonte_custo: string | null;
    reserva_estoque_id: string | null;
}

interface MaoObra {
    id: string;
    tipo_servico_id: string;
    pessoa_id: string | null;
    funcao: string | null;
    quantidade_pessoas: number;
    horas_estimadas: number | null;
    custo_hora_snapshot: number | null;
    custo_total_estimado: number | null;
    fonte_custo: string | null;
}

interface SafraTarefa {
    id: string;
    descricao: string;
    status: string;
    fase?: string | null;
    talhao_id?: string | null;
    custo_estimado?: number | null;
}

interface AreaRural {
    id: string;
    nome: string;
}

interface Deposito {
    id: string;
    nome: string;
}

interface ProdutoResumo {
    id: string;
    nome: string;
}

interface ReceitaAplicacao {
    id: string;
    nome: string;
    tipo_operacao: string | null;
    insumos: { produto_id: string; dose_ha: number; unidade_dose: string }[];
    mao_obra: { tipo_servico_id: string; funcao: string | null }[];
}

const STATUS_PLANO_LABEL: Record<string, string> = {
    RASCUNHO: "Rascunho",
    EM_ANALISE: "Em análise",
    PARCIALMENTE_PRONTO: "Parcialmente pronto",
    PRONTO: "Pronto",
    APROVADO: "Aprovado",
    EM_EXECUCAO: "Em execução",
    CONCLUIDO: "Concluído",
    CANCELADO: "Cancelado",
};

const TRANSICOES_PLANO: Record<string, string[]> = {
    RASCUNHO: ["EM_ANALISE", "CANCELADO"],
    EM_ANALISE: ["PARCIALMENTE_PRONTO", "PRONTO", "RASCUNHO", "CANCELADO"],
    PARCIALMENTE_PRONTO: ["PRONTO", "APROVADO", "CANCELADO"],
    PRONTO: ["APROVADO", "CANCELADO"],
    APROVADO: ["EM_EXECUCAO", "CANCELADO"],
    EM_EXECUCAO: ["CONCLUIDO", "CANCELADO"],
    CONCLUIDO: [],
    CANCELADO: [],
};

const STATUS_ITEM_LABEL: Record<string, string> = {
    NAO_ANALISADA: "Não analisada",
    AGUARDANDO_DEFINICAO: "Aguardando definição",
    PRONTA: "Pronta",
    AGUARDANDO_COMPRA: "Aguardando compra",
    PARCIALMENTE_ATENDIDA: "Parcialmente atendida",
    PROGRAMADA: "Programada",
    REMOVIDA: "Removida",
    CANCELADA: "Cancelada",
};

function brl(v: number | null | undefined) {
    if (v == null) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function ComparativoCustoBadge({ agronomico, planejado }: { agronomico: number | null | undefined; planejado: number }) {
    if (agronomico == null) return null;
    const delta = agronomico > 0 ? ((planejado - agronomico) / agronomico) * 100 : 0;
    const divergente = Math.abs(delta) >= 15;
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[11px] font-medium",
                divergente ? "border-amber-500/40 bg-amber-500/10 text-amber-600" : "border-muted-foreground/20 text-muted-foreground"
            )}
            title="Comparação entre a estimativa agronômica (análise de solo) e o custo planejado (insumos + mão de obra)"
        >
            <Scale className="size-3" />
            Agronômico: {brl(agronomico)} · Planejado: {brl(planejado)}
            {divergente && (delta > 0 ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />)}
        </span>
    );
}

function statusBadgeVariant(status: string): "default" | "secondary" | "destructive" | "outline" | "warning" {
    if (status === "CANCELADO" || status === "CANCELADA") return "destructive";
    if (status === "APROVADO" || status === "EM_EXECUCAO" || status === "CONCLUIDO" || status === "PROGRAMADA") return "default";
    if (status === "PRONTO" || status === "PRONTA") return "secondary";
    return "outline";
}

// ── Criar/Editar Plano ──────────────────────────────────────────────────────

function CreatePlanoDialog({ open, onClose, safraId, plano }: { open: boolean; onClose: () => void; safraId: string; plano?: PlanoOperacional }) {
    const qc = useQueryClient();
    const editando = !!plano;
    const { register, handleSubmit, reset } = useForm({
        defaultValues: {
            nome: plano?.nome ?? "",
            descricao: plano?.descricao ?? "",
            data_inicio_prevista: plano?.data_inicio_prevista ?? "",
            data_fim_prevista: plano?.data_fim_prevista ?? "",
        },
    });

    const save = useMutation({
        mutationFn: (data: { nome: string; descricao: string; data_inicio_prevista: string; data_fim_prevista: string }) =>
            editando
                ? apiFetch(`/agricola/planejamento-operacional/${plano!.id}`, {
                    method: "PATCH",
                    body: JSON.stringify({
                        nome: data.nome,
                        descricao: data.descricao || null,
                        data_inicio_prevista: data.data_inicio_prevista,
                        data_fim_prevista: data.data_fim_prevista || null,
                    }),
                })
                : apiFetch(`/agricola/planejamento-operacional/`, {
                    method: "POST",
                    body: JSON.stringify({
                        safra_id: safraId,
                        nome: data.nome,
                        descricao: data.descricao || null,
                        data_inicio_prevista: data.data_inicio_prevista,
                        data_fim_prevista: data.data_fim_prevista || null,
                    }),
                }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["planos-operacionais", safraId] });
            reset();
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <form onSubmit={handleSubmit((data) => save.mutate(data))}>
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                {editando ? <Pencil className="size-4 text-primary" /> : <ClipboardCheck className="size-4 text-primary" />}
                            </div>
                            <div className="space-y-0.5">
                                <DialogTitle>{editando ? "Editar planejamento operacional" : "Novo planejamento operacional"}</DialogTitle>
                                <DialogDescription>
                                    {editando
                                        ? "Altere nome, período ou observações deste plano."
                                        : "Agrupe tarefas já aprovadas para planejar insumos e mão de obra em lote."}
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-4">
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Nome do plano</Label>
                            <Input {...register("nome", { required: true })} placeholder="Ex: Pulverização — Talhões 1 a 4" />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Início previsto</Label>
                                <Input type="date" {...register("data_inicio_prevista", { required: true })} />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Fim previsto (opcional)</Label>
                                <Input type="date" {...register("data_fim_prevista")} />
                            </div>
                        </div>
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Observações (opcional)</Label>
                            <Textarea {...register("descricao")} rows={2} />
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={onClose} type="button">
                            <XCircle className="size-3.5 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={save.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {save.isPending ? "Salvando…" : editando ? "Salvar alterações" : "Criar plano"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ── Adicionar Tarefa ao Plano ─────────────────────────────────────────────────

function AddTarefaDialog({ open, onClose, safraId, planoId }: { open: boolean; onClose: () => void; safraId: string; planoId: string }) {
    const qc = useQueryClient();
    const [tarefaId, setTarefaId] = useState("");

    const { data: tarefas = [], isLoading: loadingTarefas, isError: erroTarefas, error: erroTarefasObj } = useQuery<SafraTarefa[]>({
        queryKey: ["safra-tarefas", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/tarefas`),
        enabled: open,
    });

    const { data: itensAtuais = [], isLoading: loadingItens, isError: erroItens } = useQuery<PlanoItem[]>({
        queryKey: ["plano-itens", planoId],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas`),
        enabled: open,
    });

    const { data: areasRurais = [] } = useQuery<AreaRural[]>({
        queryKey: ["cadastros-areas-rurais"],
        queryFn: () => apiFetch(`/cadastros/areas-rurais`),
        enabled: open,
    });
    const nomeTalhao = (talhaoId: string | null | undefined) =>
        talhaoId ? areasRurais.find((a) => a.id === talhaoId)?.nome ?? null : null;

    const jaAdicionadas = new Set(itensAtuais.map((i) => i.safra_tarefa_id));
    const aprovadas = tarefas.filter((t) => t.status === "APROVADA");
    const elegiveis = aprovadas.filter((t) => !jaAdicionadas.has(t.id));
    const isLoading = loadingTarefas || loadingItens;
    const isError = erroTarefas || erroItens;

    const add = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas`, {
                method: "POST",
                body: JSON.stringify({ safra_tarefa_id: tarefaId }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-itens", planoId] });
            setTarefaId("");
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Adicionar tarefa ao plano</DialogTitle>
                    <DialogDescription>
                        Somente tarefas já aprovadas e ainda não incluídas em outro plano ativo aparecem aqui.
                    </DialogDescription>
                </DialogHeader>
                <DialogBody className="flex flex-col gap-3">
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground text-center py-4">Carregando tarefas…</p>
                    ) : isError ? (
                        <p className="text-sm text-destructive text-center py-4">
                            Não foi possível carregar as tarefas desta safra.
                            {erroTarefasObj instanceof Error ? ` ${erroTarefasObj.message}` : " Verifique sua permissão de acesso a Tarefas de Campo."}
                        </p>
                    ) : aprovadas.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            Nenhuma tarefa aprovada nesta safra. Aprove as tarefas na tela de Tarefas de Campo antes de incluí-las no plano.
                        </p>
                    ) : elegiveis.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            Todas as {aprovadas.length} tarefa(s) aprovada(s) já estão neste plano ou em outro plano ativo.
                        </p>
                    ) : (
                        <Select value={tarefaId} onValueChange={setTarefaId}>
                            <SelectTrigger>
                                <SelectValue placeholder="Selecione a tarefa" />
                            </SelectTrigger>
                            <SelectContent>
                                {elegiveis.map((t) => {
                                    const talhao = nomeTalhao(t.talhao_id);
                                    return (
                                        <SelectItem key={t.id} value={t.id}>
                                            {t.descricao}
                                            {talhao ? ` — ${talhao}` : ""}
                                        </SelectItem>
                                    );
                                })}
                            </SelectContent>
                        </Select>
                    )}
                </DialogBody>
                <DialogFooter>
                    <Button variant="outline" size="sm" onClick={onClose} type="button">
                        Cancelar
                    </Button>
                    <Button size="sm" disabled={!tarefaId || add.isPending} onClick={() => add.mutate()}>
                        <Plus className="size-3.5 mr-1.5" />
                        {add.isPending ? "Adicionando…" : "Adicionar"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ── Adicionar Insumo ──────────────────────────────────────────────────────────

interface Necessidade {
    id: string;
    categoria: string;
    unidade_referencia: string;
    quantidade_tecnica: number | null;
    dose_tecnica: number | null;
    area_referencia_ha: number | null;
}

interface SugestaoProduto {
    item_orcamento_id: string;
    produto_id: string;
    produto_nome: string;
    unidade: string;
    custo_unitario_efetivo: number;
}

function AddInsumoDialog({ open, onClose, planoId, itemId, safraTarefaId }: { open: boolean; onClose: () => void; planoId: string; itemId: string; safraTarefaId: string }) {
    const qc = useQueryClient();
    const [produtoId, setProdutoId] = useState("");
    const [necessidadeId, setNecessidadeId] = useState("");
    const { register, handleSubmit, reset, setValue } = useForm({
        defaultValues: { unidade_dose: "L", quantidade_planejada: 0 },
    });

    const { data: necessidades = [] } = useQuery<Necessidade[]>({
        queryKey: ["tarefa-necessidades", safraTarefaId],
        queryFn: () => apiFetch(`/tarefas/${safraTarefaId}/necessidades`),
        enabled: open && !!safraTarefaId,
    });

    const { data: sugestoes = [] } = useQuery<SugestaoProduto[]>({
        queryKey: ["sugestoes-produto-orcamento", necessidadeId],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/necessidades/${necessidadeId}/sugestoes-produto`),
        enabled: open && !!necessidadeId,
    });

    function selecionarNecessidade(id: string) {
        setNecessidadeId(id);
        const nec = necessidades.find((n) => n.id === id);
        if (nec) {
            if (nec.quantidade_tecnica != null) setValue("quantidade_planejada", nec.quantidade_tecnica);
            setValue("unidade_dose", nec.unidade_referencia);
        }
    }

    const save = useMutation({
        mutationFn: (data: { unidade_dose: string; quantidade_planejada: number }) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${itemId}/insumos`, {
                method: "POST",
                body: JSON.stringify({
                    safra_tarefa_necessidade_id: necessidadeId || null,
                    produto_id: produtoId,
                    unidade_dose: data.unidade_dose,
                    quantidade_planejada: Number(data.quantidade_planejada),
                }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-insumos", itemId] });
            reset();
            setProdutoId("");
            setNecessidadeId("");
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md">
                <form onSubmit={handleSubmit((data) => save.mutate(data))}>
                    <DialogHeader>
                        <DialogTitle>Adicionar insumo</DialogTitle>
                        <DialogDescription>
                            O sistema verifica a disponibilidade em estoque e estima o custo automaticamente.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-4">
                        {necessidades.length > 0 && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">
                                    Necessidade técnica <span className="text-[10px] text-muted-foreground">(opcional — pré-preenche quantidade/unidade)</span>
                                </Label>
                                <Select value={necessidadeId} onValueChange={selecionarNecessidade}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Escolher necessidade da tarefa..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {necessidades.map((n) => (
                                            <SelectItem key={n.id} value={n.id}>
                                                {n.categoria} — {n.quantidade_tecnica ?? "?"} {n.unidade_referencia} total
                                                {n.dose_tecnica != null && n.area_referencia_ha != null
                                                    ? ` (${n.dose_tecnica}/ha × ${n.area_referencia_ha} ha)`
                                                    : ""}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}
                        {necessidadeId && sugestoes.length > 0 && (
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">
                                    Produto já usado no orçamento <span className="text-[10px] text-muted-foreground">(clique para preencher)</span>
                                </Label>
                                <div className="flex flex-wrap gap-1.5">
                                    {sugestoes.map((s) => (
                                        <Button
                                            key={s.item_orcamento_id}
                                            type="button"
                                            size="sm"
                                            variant={produtoId === s.produto_id ? "default" : "outline"}
                                            className="h-7 text-xs"
                                            onClick={() => setProdutoId(s.produto_id)}
                                        >
                                            {s.produto_nome}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Produto</Label>
                            <ProdutoCombobox value={produtoId} onChange={setProdutoId} />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Quantidade planejada</Label>
                                <Input type="number" step="0.01" {...register("quantidade_planejada", { valueAsNumber: true, required: true })} />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Unidade</Label>
                                <Input {...register("unidade_dose", { required: true })} placeholder="L, kg, sc..." />
                            </div>
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={onClose} type="button">
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={!produtoId || save.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {save.isPending ? "Salvando…" : "Adicionar"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ── Adicionar Mão de Obra ─────────────────────────────────────────────────────

function AddMaoObraDialog({ open, onClose, planoId, itemId }: { open: boolean; onClose: () => void; planoId: string; itemId: string }) {
    const qc = useQueryClient();
    const [tipoServicoId, setTipoServicoId] = useState("");
    const [pessoaId, setPessoaId] = useState("");
    const { register, handleSubmit, reset } = useForm({
        defaultValues: { funcao: "", quantidade_pessoas: 1, horas_estimadas: 0 },
    });

    const save = useMutation({
        mutationFn: (data: { funcao: string; quantidade_pessoas: number; horas_estimadas: number }) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${itemId}/mao-obra`, {
                method: "POST",
                body: JSON.stringify({
                    tipo_servico_id: tipoServicoId,
                    pessoa_id: pessoaId || null,
                    funcao: data.funcao || null,
                    quantidade_pessoas: Number(data.quantidade_pessoas) || 1,
                    horas_estimadas: Number(data.horas_estimadas) || null,
                }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-mao-obra", itemId] });
            reset();
            setTipoServicoId("");
            setPessoaId("");
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md">
                <form onSubmit={handleSubmit((data) => save.mutate(data))}>
                    <DialogHeader>
                        <DialogTitle>Adicionar mão de obra</DialogTitle>
                        <DialogDescription>
                            Estime a equipe necessária para executar a tarefa neste plano.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody className="flex flex-col gap-4">
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Tipo de serviço</Label>
                            <TipoServicoCombobox value={tipoServicoId} onChange={setTipoServicoId} />
                        </div>
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Pessoa <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                            <ColaboradorCombobox value={pessoaId} onChange={setPessoaId} valueKey="pessoa_id" />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Qtd. pessoas</Label>
                                <Input type="number" min={1} {...register("quantidade_pessoas", { valueAsNumber: true })} />
                            </div>
                            <div className="grid gap-1.5 col-span-2">
                                <Label className="text-xs font-medium">Horas estimadas</Label>
                                <Input type="number" step="0.5" {...register("horas_estimadas", { valueAsNumber: true })} placeholder="0" />
                            </div>
                        </div>
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Função (opcional)</Label>
                            <Input {...register("funcao")} placeholder="Ex: Tratorista" />
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={onClose} type="button">
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={!tipoServicoId || save.isPending}>
                            <Save className="size-3.5 mr-1.5" />
                            {save.isPending ? "Salvando…" : "Adicionar"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// ── Item (tarefa dentro do plano): insumos + mão de obra ─────────────────────

function PlanoItemPanel({
    planoId, item, tarefa, talhaoNome, selecionado, onToggleSelecionado, somenteLeitura,
}: {
    planoId: string;
    item: PlanoItem;
    tarefa: SafraTarefa | undefined;
    talhaoNome?: string | null;
    selecionado: boolean;
    onToggleSelecionado: (checked: boolean) => void;
    somenteLeitura: boolean;
}) {
    const qc = useQueryClient();
    // Uma vez que a OS já foi gerada para este item, ele sai do domínio de
    // simulação/planejamento — o backend já rejeita qualquer edição de insumo/mão
    // de obra/maquinário/receita nesse estado (_validar_plano_editavel_para_insumo).
    const itemBloqueado = item.status_planejamento === "PROGRAMADA";
    const [showInsumo, setShowInsumo] = useState(false);
    const [showMaoObra, setShowMaoObra] = useState(false);
    const [removerInsumoId, setRemoverInsumoId] = useState<string | null>(null);
    const [removerMaoObraId, setRemoverMaoObraId] = useState<string | null>(null);

    const { data: insumos = [] } = useQuery<Insumo[]>({
        queryKey: ["plano-insumos", item.id],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos`),
    });

    const { data: produtos = [] } = useQuery<ProdutoResumo[]>({
        queryKey: ["cadastros-produtos-nomes"],
        queryFn: () => apiFetch(`/cadastros/produtos?incluir_sistema=true`),
        enabled: insumos.length > 0,
    });

    const { data: maoObra = [] } = useQuery<MaoObra[]>({
        queryKey: ["plano-mao-obra", item.id],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/mao-obra`),
    });

    const aprovarItem = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/aprovar`, { method: "POST" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-itens", planoId] });
            qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] });
        },
        onError: (error: Error) => {
            toast.error("Não foi possível aprovar o item.", {
                description: error.message,
            });
        },
    });

    const reservar = useMutation({
        mutationFn: (insumoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos/${insumoId}/reservar`, { method: "POST" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] }),
    });

    const liberarReserva = useMutation({
        mutationFn: (insumoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos/${insumoId}/reserva`, { method: "DELETE" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] }),
    });

    const recalcular = useMutation({
        mutationFn: (insumoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos/${insumoId}/recalcular`, { method: "POST" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] }),
    });

    const solicitarCompra = useMutation({
        mutationFn: (insumoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos/${insumoId}/solicitar-compra`, { method: "POST" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] }),
    });

    const removerInsumo = useMutation({
        mutationFn: (insumoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/insumos/${insumoId}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-insumos", item.id] });
            setRemoverInsumoId(null);
        },
    });

    const removerMaoObra = useMutation({
        mutationFn: (maoObraId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/tarefas/${item.id}/mao-obra/${maoObraId}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["plano-mao-obra", item.id] });
            setRemoverMaoObraId(null);
        },
    });

    const custoPlanejado =
        insumos.reduce((s, i) => s + (i.custo_total_estimado ?? 0), 0) +
        maoObra.reduce((s, m) => s + (m.custo_total_estimado ?? 0), 0);

    const insumoSemSaldo = insumos.some((i) => (i.quantidade_disponivel_snapshot ?? 0) < i.quantidade_planejada);
    const bloquearAprovacao = insumos.length === 0 || insumoSemSaldo;
    const nomeProduto = (produtoId: string) => produtos.find((produto) => produto.id === produtoId)?.nome ?? produtoId;

    return (
        <AccordionItem value={item.id} className="border rounded-sm px-3">
            <div className="flex items-center gap-2">
                {!somenteLeitura && !itemBloqueado && (
                    <Checkbox
                        checked={selecionado}
                        onCheckedChange={onToggleSelecionado}
                        aria-label="Selecionar tarefa para aplicar receita em lote"
                        onClick={(e) => e.stopPropagation()}
                    />
                )}
                <AccordionTrigger className="hover:no-underline py-3 flex-1">
                    <div className="flex flex-1 items-center justify-between gap-3 pr-2">
                        <div className="flex flex-col items-start gap-0.5 text-left">
                            <span className="text-sm font-medium">{tarefa?.descricao ?? "Tarefa"}</span>
                            {talhaoNome && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                    <MapPin className="size-3" /> {talhaoNome}
                                </span>
                            )}
                        </div>
                        <Badge variant={statusBadgeVariant(item.status_planejamento)}>
                            {STATUS_ITEM_LABEL[item.status_planejamento] ?? item.status_planejamento}
                        </Badge>
                    </div>
                </AccordionTrigger>
            </div>
            <AccordionContent className="flex flex-col gap-5 pb-4">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <ComparativoCustoBadge agronomico={tarefa?.custo_estimado} planejado={custoPlanejado} />
                    {!somenteLeitura && !itemBloqueado && (
                        <div className="flex flex-col items-end gap-1">
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => aprovarItem.mutate()}
                                disabled={aprovarItem.isPending || bloquearAprovacao}
                                title={bloquearAprovacao ? "Sem saldo disponível suficiente para reservar todos os insumos desta tarefa." : undefined}
                            >
                                <CheckCircle2 className="size-3.5 mr-1.5" />
                                {aprovarItem.isPending ? "Aprovando…" : "Aprovar item (reservar disponível)"}
                            </Button>
                            {bloquearAprovacao && (
                                <span className="text-[11px] text-destructive flex items-center gap-1">
                                    <AlertTriangle className="size-3" />
                                    {insumos.length === 0 ? "Adicione ao menos um insumo antes de aprovar." : "Saldo insuficiente para algum insumo — solicite compra antes de aprovar."}
                                </span>
                            )}
                        </div>
                    )}
                </div>

                <div className="flex flex-col gap-5">
                    <div className="flex flex-col gap-2 min-w-0">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium flex items-center gap-1.5"><PackageSearch className="size-3.5" /> Insumos</h4>
                            {!somenteLeitura && !itemBloqueado && (
                                <Button size="sm" variant="outline" onClick={() => setShowInsumo(true)}>
                                    <Plus className="size-4 mr-1.5" /> Adicionar
                                </Button>
                            )}
                        </div>
                        {insumos.length === 0 ? (
                            <p className="text-xs text-muted-foreground py-2">Nenhum insumo planejado.</p>
                        ) : (
                            <div className="overflow-x-auto rounded-sm border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Produto</TableHead>
                                            <TableHead>Qtd.</TableHead>
                                            <TableHead>Disponível</TableHead>
                                            <TableHead>Faltante</TableHead>
                                            <TableHead className="text-right">Custo total</TableHead>
                                            {!somenteLeitura && !itemBloqueado && <TableHead className="text-right w-32">Ações</TableHead>}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {insumos.map((i) => (
                                            <TableRow key={i.id}>
                                                <TableCell className="min-w-48 font-medium">{nomeProduto(i.produto_id)}</TableCell>
                                                <TableCell>{i.quantidade_planejada} {i.unidade_dose}</TableCell>
                                                <TableCell className={cn((i.quantidade_disponivel_snapshot ?? 0) < i.quantidade_planejada && "text-amber-600")}>
                                                    {i.quantidade_disponivel_snapshot ?? "—"}
                                                </TableCell>
                                                <TableCell className={cn((i.quantidade_faltante ?? 0) > 0 && "text-destructive")}>
                                                    {i.quantidade_faltante ?? 0}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    {brl(i.custo_total_estimado)}
                                                    {i.fonte_custo === "CUSTO_INCOMPLETO" && (
                                                        <Badge variant="outline" className="ml-1.5 text-[10px]">custo incompleto</Badge>
                                                    )}
                                                </TableCell>
                                                {!somenteLeitura && !itemBloqueado && (
                                                    <TableCell className="text-right">
                                                        <div className="flex items-center justify-end gap-0.5">
                                                            <TooltipProvider>
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Button
                                                                            size="icon" variant="ghost" className="size-7"
                                                                            aria-label="Recalcular"
                                                                            onClick={() => recalcular.mutate(i.id)}
                                                                        >
                                                                            <RotateCw className="size-3.5" />
                                                                        </Button>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>Recalcular disponibilidade e custo com os dados atuais de estoque/preço.</TooltipContent>
                                                                </Tooltip>
                                                            </TooltipProvider>
                                                            {i.reserva_estoque_id ? (
                                                                <TooltipProvider>
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <Button
                                                                                size="icon" variant="ghost" className="size-7"
                                                                                aria-label="Liberar reserva"
                                                                                onClick={() => liberarReserva.mutate(i.id)}
                                                                            >
                                                                                <Unlock className="size-3.5" />
                                                                            </Button>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent>Liberar a reserva de estoque deste insumo (devolve o saldo reservado).</TooltipContent>
                                                                    </Tooltip>
                                                                </TooltipProvider>
                                                            ) : (
                                                                <TooltipProvider>
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <Button
                                                                                size="icon" variant="ghost" className="size-7"
                                                                                aria-label="Reservar em estoque"
                                                                                onClick={() => reservar.mutate(i.id)}
                                                                            >
                                                                                <Lock className="size-3.5" />
                                                                            </Button>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent>Reservar em estoque a quantidade planejada deste insumo.</TooltipContent>
                                                                    </Tooltip>
                                                                </TooltipProvider>
                                                            )}
                                                            {(i.quantidade_faltante ?? 0) > 0 && (
                                                                <TooltipProvider>
                                                                    <Tooltip>
                                                                        <TooltipTrigger asChild>
                                                                            <Button
                                                                                size="icon" variant="ghost" className="size-7"
                                                                                aria-label="Solicitar compra da falta"
                                                                                onClick={() => solicitarCompra.mutate(i.id)}
                                                                            >
                                                                                <ShoppingCart className="size-3.5" />
                                                                            </Button>
                                                                        </TooltipTrigger>
                                                                        <TooltipContent>Solicitar compra da quantidade que falta em estoque para este insumo.</TooltipContent>
                                                                    </Tooltip>
                                                                </TooltipProvider>
                                                            )}
                                                            <TooltipProvider>
                                                                <Tooltip>
                                                                    <TooltipTrigger asChild>
                                                                        <Button
                                                                            size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                                                            aria-label="Remover insumo"
                                                                            onClick={() => setRemoverInsumoId(i.id)}
                                                                        >
                                                                            <Trash2 className="size-3.5" />
                                                                        </Button>
                                                                    </TooltipTrigger>
                                                                    <TooltipContent>Remover este insumo do planejamento da tarefa.</TooltipContent>
                                                                </Tooltip>
                                                            </TooltipProvider>
                                                        </div>
                                                    </TableCell>
                                                )}
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </div>

                    <div className="flex flex-col gap-2 min-w-0">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium flex items-center gap-1.5"><Users2 className="size-3.5" /> Mão de obra</h4>
                            {!somenteLeitura && !itemBloqueado && (
                                <Button size="sm" variant="ghost" onClick={() => setShowMaoObra(true)}>
                                    <Plus className="size-3.5 mr-1" /> Adicionar
                                </Button>
                            )}
                        </div>
                        {maoObra.length === 0 ? (
                            <p className="text-xs text-muted-foreground py-2">Nenhuma necessidade de mão de obra estimada.</p>
                        ) : (
                            <div className="overflow-x-auto rounded-sm border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Função</TableHead>
                                            <TableHead>Qtd.</TableHead>
                                            <TableHead>Horas</TableHead>
                                            <TableHead className="text-right">Custo total</TableHead>
                                            {!somenteLeitura && !itemBloqueado && <TableHead className="text-right w-16">Ações</TableHead>}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {maoObra.map((m) => (
                                            <TableRow key={m.id}>
                                                <TableCell>{m.funcao ?? "—"}</TableCell>
                                                <TableCell>{m.quantidade_pessoas}</TableCell>
                                                <TableCell>{m.horas_estimadas ?? "—"}</TableCell>
                                                <TableCell className="text-right">
                                                    {brl(m.custo_total_estimado)}
                                                    {m.fonte_custo === "CUSTO_INCOMPLETO" && (
                                                        <Badge variant="outline" className="ml-1.5 text-[10px]">custo incompleto</Badge>
                                                    )}
                                                </TableCell>
                                                {!somenteLeitura && !itemBloqueado && (
                                                    <TableCell className="text-right">
                                                        <Button
                                                            size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive"
                                                            aria-label="Remover necessidade de mão de obra"
                                                            onClick={() => setRemoverMaoObraId(m.id)}
                                                        >
                                                            <Trash2 className="size-3.5" />
                                                        </Button>
                                                    </TableCell>
                                                )}
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        )}
                    </div>
                </div>
            </AccordionContent>

            {showInsumo && (
                <AddInsumoDialog open={showInsumo} onClose={() => setShowInsumo(false)} planoId={planoId} itemId={item.id} safraTarefaId={item.safra_tarefa_id} />
            )}
            {showMaoObra && (
                <AddMaoObraDialog open={showMaoObra} onClose={() => setShowMaoObra(false)} planoId={planoId} itemId={item.id} />
            )}

            <AlertDialog open={!!removerInsumoId} onOpenChange={() => setRemoverInsumoId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remover insumo?</AlertDialogTitle>
                        <AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setRemoverInsumoId(null)}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => removerInsumoId && removerInsumo.mutate(removerInsumoId)}
                            disabled={removerInsumo.isPending}
                        >
                            Remover
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog open={!!removerMaoObraId} onOpenChange={() => setRemoverMaoObraId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remover necessidade de mão de obra?</AlertDialogTitle>
                        <AlertDialogDescription>Esta ação não pode ser desfeita.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setRemoverMaoObraId(null)}>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => removerMaoObraId && removerMaoObra.mutate(removerMaoObraId)}
                            disabled={removerMaoObra.isPending}
                        >
                            Remover
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </AccordionItem>
    );
}

// ── Consolidar compras (agrupar insumos por produto) ───────────────────────────

interface ConsolidadoInsumo {
    produto_id: string;
    unidade: string;
    quantidade: number;
}

interface InsumoConsolidado {
    chave_grupo: string;
    categoria: string;
    titulo: string;
    unidade: string;
    quantidade_total: number;
    quantidade_tarefas: number;
    quantidade_pendentes: number;
    necessidade_ids_pendentes: string[];
    tipo_recurso: "INSUMO" | "MAQUINARIO" | "MAO_DE_OBRA";
}

function ConfigurarGrupoDialog({
    open,
    onClose,
    planoId,
    grupo,
}: {
    open: boolean;
    onClose: () => void;
    planoId: string;
    grupo: InsumoConsolidado;
}) {
    const qc = useQueryClient();
    const [produtoId, setProdutoId] = useState("");
    const [depositoId, setDepositoId] = useState("");
    const [maquinaId, setMaquinaId] = useState("");
    const [implementoId, setImplementoId] = useState("");
    const [tipoServicoId, setTipoServicoId] = useState("");
    const [pessoaId, setPessoaId] = useState("");
    const [quantidadePessoas, setQuantidadePessoas] = useState(1);

    const isInsumo = grupo.tipo_recurso === "INSUMO";
    const isMaquinario = grupo.tipo_recurso === "MAQUINARIO";
    const isMaoObra = grupo.tipo_recurso === "MAO_DE_OBRA";

    const { data: depositos = [] } = useQuery<Deposito[]>({
        queryKey: ["estoque-depositos"],
        queryFn: () => apiFetch(`/estoque/depositos`),
        enabled: open && isInsumo,
    });

    const { data: sugestoes = [] } = useQuery<{ item_orcamento_id: string; produto_id: string; produto_nome: string }[]>({
        queryKey: ["sugestoes-produto-orcamento", grupo.necessidade_ids_pendentes[0]],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/necessidades/${grupo.necessidade_ids_pendentes[0]}/sugestoes-produto`),
        enabled: open && isInsumo && grupo.necessidade_ids_pendentes.length > 0,
    });

    const invalidar = () => {
        qc.invalidateQueries({ queryKey: ["plano-insumos-consolidados", planoId] });
        qc.invalidateQueries({ queryKey: ["plano-itens", planoId] });
    };

    const aplicarInsumo = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/insumos-consolidados/aplicar`, {
                method: "POST",
                body: JSON.stringify({
                    necessidade_ids: grupo.necessidade_ids_pendentes,
                    produto_id: produtoId,
                    deposito_id: depositoId || null,
                }),
            }),
        onSuccess: (resultado: { quantidade_aplicada: number; quantidade_ignorada: number }) => {
            invalidar();
            toast.success(`Produto aplicado a ${resultado.quantidade_aplicada} tarefa(s).`);
            onClose();
        },
    });

    const aplicarMaquinario = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/insumos-consolidados/aplicar-maquinario`, {
                method: "POST",
                body: JSON.stringify({
                    necessidade_ids: grupo.necessidade_ids_pendentes,
                    maquina_id: maquinaId || null,
                    implemento_id: implementoId || null,
                }),
            }),
        onSuccess: (resultado: { quantidade_aplicada: number; quantidade_ignorada: number }) => {
            invalidar();
            toast.success(`Máquina aplicada a ${resultado.quantidade_aplicada} tarefa(s).`);
            onClose();
        },
    });

    const aplicarMaoObra = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/insumos-consolidados/aplicar-mao-obra`, {
                method: "POST",
                body: JSON.stringify({
                    necessidade_ids: grupo.necessidade_ids_pendentes,
                    tipo_servico_id: tipoServicoId,
                    pessoa_id: pessoaId || null,
                    quantidade_pessoas: quantidadePessoas,
                }),
            }),
        onSuccess: (resultado: { quantidade_aplicada: number; quantidade_ignorada: number }) => {
            invalidar();
            toast.success(`Mão de obra aplicada a ${resultado.quantidade_aplicada} tarefa(s).`);
            onClose();
        },
    });

    const podeAplicar = isInsumo ? !!produtoId : isMaquinario ? !!(maquinaId || implementoId) : !!tipoServicoId;
    const aplicando = aplicarInsumo.isPending || aplicarMaquinario.isPending || aplicarMaoObra.isPending;
    const handleAplicar = () => {
        if (isInsumo) aplicarInsumo.mutate();
        else if (isMaquinario) aplicarMaquinario.mutate();
        else aplicarMaoObra.mutate();
    };

    const descricaoRecurso = isInsumo ? "produto" : isMaquinario ? "máquina/implemento" : "mão de obra";

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>{grupo.titulo}</DialogTitle>
                    <DialogDescription>
                        {grupo.quantidade_total.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} {grupo.unidade} no total,
                        distribuído entre {grupo.quantidade_tarefas} tarefa(s) — {grupo.quantidade_pendentes} ainda sem {descricaoRecurso} definido(a).
                        {isMaoObra && (
                            <span className="block mt-1 text-[10px] text-amber-600">
                                Confira a unidade ({grupo.unidade}) antes de aplicar — o campo abaixo espera horas estimadas.
                            </span>
                        )}
                    </DialogDescription>
                </DialogHeader>
                <DialogBody className="flex flex-col gap-4">
                    {isInsumo && (
                        <>
                            {sugestoes.length > 0 && (
                                <div className="grid gap-1.5">
                                    <Label className="text-xs font-medium">
                                        Produto já usado no orçamento <span className="text-[10px] text-muted-foreground">(clique para preencher)</span>
                                    </Label>
                                    <div className="flex flex-wrap gap-1.5">
                                        {sugestoes.map((s) => (
                                            <Button
                                                key={s.item_orcamento_id}
                                                type="button"
                                                size="sm"
                                                variant={produtoId === s.produto_id ? "default" : "outline"}
                                                className="h-7 text-xs"
                                                onClick={() => setProdutoId(s.produto_id)}
                                            >
                                                {s.produto_nome}
                                            </Button>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Produto</Label>
                                <ProdutoCombobox value={produtoId} onChange={setProdutoId} />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Depósito <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                <Select value={depositoId} onValueChange={setDepositoId}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Selecione o depósito" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {depositos.map((d) => (
                                            <SelectItem key={d.id} value={d.id}>{d.nome}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </>
                    )}
                    {isMaquinario && (
                        <>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Máquina <span className="text-[10px] text-muted-foreground">(ao menos uma das duas)</span></Label>
                                <EquipamentoCombobox value={maquinaId} onChange={setMaquinaId} tiposPermitidos={TIPOS_MAQUINA} placeholder="Buscar máquina por nome" />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Implemento</Label>
                                <EquipamentoCombobox value={implementoId} onChange={setImplementoId} tiposPermitidos={TIPOS_IMPLEMENTO} placeholder="Buscar implemento por nome" />
                            </div>
                        </>
                    )}
                    {isMaoObra && (
                        <>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Tipo de serviço</Label>
                                <TipoServicoCombobox value={tipoServicoId} onChange={setTipoServicoId} />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Pessoa <span className="text-[10px] text-muted-foreground">(opcional)</span></Label>
                                <ColaboradorCombobox value={pessoaId} onChange={setPessoaId} valueKey="pessoa_id" />
                            </div>
                            <div className="grid gap-1.5">
                                <Label className="text-xs font-medium">Quantidade de pessoas</Label>
                                <Input type="number" min={1} value={quantidadePessoas} onChange={(e) => setQuantidadePessoas(Number(e.target.value) || 1)} />
                            </div>
                        </>
                    )}
                </DialogBody>
                <DialogFooter>
                    <Button variant="outline" size="sm" onClick={onClose} type="button">
                        Cancelar
                    </Button>
                    <Button size="sm" disabled={!podeAplicar || aplicando} onClick={handleAplicar}>
                        <Save className="size-3.5 mr-1.5" />
                        {aplicando ? "Aplicando…" : `Aplicar a ${grupo.quantidade_pendentes} tarefa(s)`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function InsumosConsolidadosDialog({
    open,
    onClose,
    planoId,
}: {
    open: boolean;
    onClose: () => void;
    planoId: string;
}) {
    const [grupoSelecionado, setGrupoSelecionado] = useState<InsumoConsolidado | null>(null);

    const { data: grupos = [], isLoading } = useQuery<InsumoConsolidado[]>({
        queryKey: ["plano-insumos-consolidados", planoId],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/${planoId}/insumos-consolidados`),
        enabled: open,
    });

    return (
        <>
            <Dialog open={open} onOpenChange={onClose}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Package className="size-4" /> Insumos consolidados do plano
                        </DialogTitle>
                        <DialogDescription>
                            Necessidades técnicas somadas entre todas as tarefas do plano. Configure o produto uma vez e aplique a todas as tarefas pendentes de uma vez.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody>
                        {isLoading ? (
                            <p className="text-sm text-muted-foreground text-center py-6">Carregando…</p>
                        ) : grupos.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-6">Nenhuma necessidade técnica encontrada nas tarefas deste plano.</p>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Insumo</TableHead>
                                        <TableHead className="text-right">Quantidade total</TableHead>
                                        <TableHead className="text-right">Tarefas</TableHead>
                                        <TableHead className="text-right">Status</TableHead>
                                        <TableHead />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {grupos.map((g) => (
                                        <TableRow key={g.chave_grupo}>
                                            <TableCell>
                                                <div className="font-medium text-sm">{g.titulo}</div>
                                                <div className="text-[10px] text-muted-foreground uppercase">{g.categoria}</div>
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">
                                                {g.quantidade_total.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} {g.unidade}
                                            </TableCell>
                                            <TableCell className="text-right tabular-nums">{g.quantidade_tarefas}</TableCell>
                                            <TableCell className="text-right">
                                                {g.quantidade_pendentes === 0 ? (
                                                    <Badge variant="secondary" className="gap-1"><CheckCircle2 className="size-3" /> Completo</Badge>
                                                ) : (
                                                    <Badge variant="outline">{g.quantidade_pendentes} pendente(s)</Badge>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {g.quantidade_pendentes > 0 && (
                                                    <Button size="sm" variant="outline" onClick={() => setGrupoSelecionado(g)}>
                                                        Configurar
                                                    </Button>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={onClose}>Fechar</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
            {grupoSelecionado && (
                <ConfigurarGrupoDialog
                    open={!!grupoSelecionado}
                    onClose={() => setGrupoSelecionado(null)}
                    planoId={planoId}
                    grupo={grupoSelecionado}
                />
            )}
        </>
    );
}

function ConsolidarComprasDialog({
    open,
    onClose,
    planoId,
    consolidados,
}: {
    open: boolean;
    onClose: () => void;
    planoId: string;
    consolidados: ConsolidadoInsumo[];
}) {
    const qc = useQueryClient();
    const [depositoId, setDepositoId] = useState("");

    const { data: depositos = [] } = useQuery<Deposito[]>({
        queryKey: ["estoque-depositos"],
        queryFn: () => apiFetch(`/estoque/depositos`),
        enabled: open,
    });

    const { data: produtos = [] } = useQuery<{ id: string; nome: string }[]>({
        queryKey: ["cadastros-produtos-nomes"],
        queryFn: () => apiFetch(`/cadastros/produtos?incluir_sistema=true`),
        enabled: open,
    });
    const nomeProduto = (id: string) => produtos.find((p) => p.id === id)?.nome ?? id;

    const gerar = useMutation({
        mutationFn: () =>
            apiFetch(`/compras/solicitacoes`, {
                method: "POST",
                body: JSON.stringify({
                    itens: consolidados.map((c) => ({
                        produto_id: c.produto_id,
                        deposito_id: depositoId,
                        quantidade_solicitada: c.quantidade,
                        unidade: c.unidade,
                    })),
                    origem: "PLANO_OPERACIONAL",
                    origem_id: planoId,
                }),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Layers className="size-4" /> Consolidar e solicitar compra
                    </DialogTitle>
                    <DialogDescription>
                        Soma a quantidade de cada produto entre todas as tarefas do plano e gera uma única solicitação de compra por produto.
                    </DialogDescription>
                </DialogHeader>
                <DialogBody className="flex flex-col gap-4">
                    <div className="overflow-hidden rounded-sm border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Produto</TableHead>
                                    <TableHead className="text-right">Quantidade total</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {consolidados.map((c) => (
                                    <TableRow key={c.produto_id}>
                                        <TableCell>{nomeProduto(c.produto_id)}</TableCell>
                                        <TableCell className="text-right">
                                            {c.quantidade.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} {c.unidade}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="grid gap-1.5">
                        <Label className="text-xs font-medium">Depósito de destino</Label>
                        <Select value={depositoId} onValueChange={setDepositoId}>
                            <SelectTrigger>
                                <SelectValue placeholder="Selecione o depósito" />
                            </SelectTrigger>
                            <SelectContent>
                                {depositos.map((d) => (
                                    <SelectItem key={d.id} value={d.id}>
                                        {d.nome}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </DialogBody>
                <DialogFooter>
                    <Button variant="outline" size="sm" onClick={onClose} type="button">
                        Cancelar
                    </Button>
                    <Button size="sm" disabled={!depositoId || gerar.isPending} onClick={() => gerar.mutate()}>
                        <ShoppingCart className="size-3.5 mr-1.5" />
                        {gerar.isPending ? "Gerando…" : "Gerar solicitação de compra"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ── Aplicar Receita em Lote ────────────────────────────────────────────────────

function AplicarReceitaDialog({
    open,
    onClose,
    planoId,
    safraId,
    itensSelecionados,
}: {
    open: boolean;
    onClose: () => void;
    planoId: string;
    safraId: string;
    itensSelecionados: { itemId: string; descricao: string; talhaoNome: string | null }[];
}) {
    const qc = useQueryClient();
    const [receitaId, setReceitaId] = useState("");

    const { data: receitas = [], isLoading } = useQuery<ReceitaAplicacao[]>({
        queryKey: ["receitas-aplicacao"],
        queryFn: () => apiFetch(`/agricola/cadastros/receitas-aplicacao/`),
        enabled: open,
    });

    const receitaSelecionada = receitas.find((r) => r.id === receitaId);

    const aplicar = useMutation({
        mutationFn: () =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/aplicar-receita`, {
                method: "POST",
                body: JSON.stringify({
                    receita_id: receitaId,
                    plano_operacional_tarefa_ids: itensSelecionados.map((i) => i.itemId),
                }),
            }),
        onSuccess: () => {
            for (const item of itensSelecionados) {
                qc.invalidateQueries({ queryKey: ["plano-insumos", item.itemId] });
                qc.invalidateQueries({ queryKey: ["plano-mao-obra", item.itemId] });
            }
            // aplicar_receita também resincroniza SafraTarefa.custo_estimado
            // ("Agronômico") com o custo real da receita — sem isso o card de
            // comparação continuaria mostrando o valor antigo até um refresh manual.
            qc.invalidateQueries({ queryKey: ["safra-tarefas", safraId] });
            setReceitaId("");
            onClose();
        },
    });

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FlaskConical className="size-4" /> Aplicar receita em lote
                    </DialogTitle>
                    <DialogDescription>
                        Cria os insumos (quantidade = dose/ha × área do talhão) e a mão de obra da receita em todas as tarefas selecionadas.
                    </DialogDescription>
                </DialogHeader>
                <DialogBody className="flex flex-col gap-4">
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground text-center py-4">Carregando receitas…</p>
                    ) : receitas.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                            Nenhuma receita cadastrada. Crie uma em Cadastros → Receitas de Aplicação.
                        </p>
                    ) : (
                        <div className="grid gap-1.5">
                            <Label className="text-xs font-medium">Receita</Label>
                            <Select value={receitaId} onValueChange={setReceitaId}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Selecione a receita" />
                                </SelectTrigger>
                                <SelectContent>
                                    {receitas.map((r) => (
                                        <SelectItem key={r.id} value={r.id}>
                                            {r.nome}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}

                    {receitaSelecionada && (
                        <div className="rounded-sm border p-3 text-xs text-muted-foreground flex flex-col gap-1">
                            <span>{receitaSelecionada.insumos.length} insumo(s) · {receitaSelecionada.mao_obra.length} mão de obra</span>
                        </div>
                    )}

                    <div className="flex flex-col gap-1">
                        <Label className="text-xs font-medium">Tarefas selecionadas ({itensSelecionados.length})</Label>
                        <div className="rounded-sm border divide-y max-h-40 overflow-y-auto">
                            {itensSelecionados.map((item) => (
                                <div key={item.itemId} className="flex items-center justify-between px-3 py-1.5 text-xs">
                                    <span>{item.descricao}</span>
                                    {item.talhaoNome && <span className="text-muted-foreground">{item.talhaoNome}</span>}
                                </div>
                            ))}
                        </div>
                    </div>
                </DialogBody>
                <DialogFooter>
                    <Button variant="outline" size="sm" onClick={onClose} type="button">
                        Cancelar
                    </Button>
                    <Button size="sm" disabled={!receitaId || aplicar.isPending} onClick={() => aplicar.mutate()}>
                        <FlaskConical className="size-3.5 mr-1.5" />
                        {aplicar.isPending ? "Aplicando…" : `Aplicar a ${itensSelecionados.length} tarefa(s)`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ── Gerar OS em Lote ────────────────────────────────────────────────────────

interface GerarOSLinha {
    itemId: string;
    descricao: string;
    talhaoNome: string | null;
    data_prevista: string;
    operador_id: string;
    maquina_id: string;
    implemento_id: string;
}

const TIPOS_MAQUINA = ["TRATOR", "COLHEDORA", "PULVERIZADOR", "PLANTADEIRA"];
const TIPOS_IMPLEMENTO = ["IMPLEMENTO", "PULVERIZADOR", "PLANTADEIRA"];

interface GerarOSResultado {
    plano_operacional_tarefa_id: string;
    sucesso: boolean;
    operacao_agricola_id: string | null;
    erro: string | null;
}

function ImplementoHelp() {
    return (
        <TooltipProvider>
            <Tooltip>
                <TooltipTrigger tabIndex={-1} className="outline-none">
                    <HelpCircle className="size-3.5 shrink-0 cursor-help text-muted-foreground" aria-hidden />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs">
                    Selecione o implemento ou acessório acoplado à máquina para executar a OS, como plantadeira, pulverizador, grade, carreta ou plataforma. Deixe em branco quando não se aplicar.
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}

function GerarOSLoteDialog({
    open,
    onClose,
    planoId,
    safraId,
    itensSelecionados,
}: {
    open: boolean;
    onClose: () => void;
    planoId: string;
    safraId: string;
    itensSelecionados: { itemId: string; descricao: string; talhaoNome: string | null; statusPlanejamento: string }[];
}) {
    const qc = useQueryClient();
    const elegiveis = itensSelecionados.filter((i) => i.statusPlanejamento === "PRONTA");
    const naoElegiveis = itensSelecionados.filter((i) => i.statusPlanejamento !== "PRONTA");

    const [dataPadrao, setDataPadrao] = useState("");
    const [operadorPadrao, setOperadorPadrao] = useState("");
    const [maquinaPadrao, setMaquinaPadrao] = useState("");
    const [implementoPadrao, setImplementoPadrao] = useState("");
    const [linhas, setLinhas] = useState<GerarOSLinha[]>(
        elegiveis.map((i) => ({
            itemId: i.itemId, descricao: i.descricao, talhaoNome: i.talhaoNome,
            data_prevista: "", operador_id: "", maquina_id: "", implemento_id: "",
        }))
    );
    const [resultados, setResultados] = useState<GerarOSResultado[] | null>(null);

    const aplicarPadraoATodos = () => {
        setLinhas(linhas.map((l) => ({
            ...l,
            data_prevista: dataPadrao || l.data_prevista,
            operador_id: operadorPadrao || l.operador_id,
            maquina_id: maquinaPadrao || l.maquina_id,
            implemento_id: implementoPadrao || l.implemento_id,
        })));
    };

    const gerar = useMutation({
        mutationFn: () =>
            apiFetch<{ resultados: GerarOSResultado[] }>(`/agricola/planejamento-operacional/${planoId}/gerar-os`, {
                method: "POST",
                body: JSON.stringify({
                    itens: linhas
                        .filter((l) => l.data_prevista)
                        .map((l) => ({
                            plano_operacional_tarefa_id: l.itemId,
                            data_prevista: l.data_prevista,
                            operador_id: l.operador_id || null,
                            maquina_id: l.maquina_id || null,
                            implemento_id: l.implemento_id || null,
                        })),
                }),
            }),
        onSuccess: (data) => {
            setResultados(data.resultados);
            for (const item of elegiveis) {
                qc.invalidateQueries({ queryKey: ["plano-itens", planoId] });
                qc.invalidateQueries({ queryKey: ["plano-insumos", item.itemId] });
            }
            qc.invalidateQueries({ queryKey: ["safra-tarefas", safraId] });
        },
    });

    const fechar = () => {
        setResultados(null);
        onClose();
    };

    const podeSubmeter = linhas.length > 0 && linhas.every((l) => l.data_prevista);

    return (
        <Dialog open={open} onOpenChange={fechar}>
            <DialogContent className="max-w-screen-sm">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Tractor className="size-4" /> Gerar Ordem de Serviço em lote
                    </DialogTitle>
                    <DialogDescription>
                        Cria a OS de cada tarefa pronta (insumos já reservados) de uma vez, vinculando ao módulo Campo.
                    </DialogDescription>
                </DialogHeader>
                <DialogBody className="flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
                    {resultados ? (
                        <div className="flex flex-col gap-2">
                            <p className="text-sm font-medium">
                                {resultados.filter((r) => r.sucesso).length} de {resultados.length} OS geradas com sucesso.
                            </p>
                            <div className="rounded-sm border divide-y">
                                {resultados.map((r) => {
                                    const linha = linhas.find((l) => l.itemId === r.plano_operacional_tarefa_id);
                                    return (
                                        <div key={r.plano_operacional_tarefa_id} className="flex items-center justify-between gap-3 px-3 py-2 text-xs">
                                            <span>{linha?.descricao ?? r.plano_operacional_tarefa_id}</span>
                                            {r.sucesso ? (
                                                <span className="text-emerald-600 flex items-center gap-1"><CheckCircle2 className="size-3.5" /> Gerada</span>
                                            ) : (
                                                <span className="text-destructive flex items-center gap-1"><AlertTriangle className="size-3.5" /> {r.erro}</span>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ) : (
                        <>
                            {naoElegiveis.length > 0 && (
                                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                                    <AlertTriangle className="size-3.5 shrink-0" />
                                    {naoElegiveis.length} tarefa(s) selecionada(s) não está(ão) com status PRONTA e foi(ram) ignorada(s).
                                </p>
                            )}
                            {elegiveis.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">
                                    Nenhuma das tarefas selecionadas está pronta (insumos reservados) para gerar OS.
                                </p>
                            ) : (
                                <>
                                    <div className="rounded-sm border p-3 flex flex-col gap-3">
                                        <p className="text-xs font-medium text-muted-foreground">Valor padrão (aplicar a todas as linhas abaixo)</p>
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="grid gap-1.5">
                                                <Label className="text-[11px] text-muted-foreground">Data prevista</Label>
                                                <Input type="date" value={dataPadrao} onChange={(e) => setDataPadrao(e.target.value)} />
                                            </div>
                                            <div className="grid gap-1.5">
                                                <Label className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                                    Implemento <ImplementoHelp />
                                                </Label>
                                                <EquipamentoCombobox
                                                    value={implementoPadrao}
                                                    onChange={setImplementoPadrao}
                                                    tiposPermitidos={TIPOS_IMPLEMENTO}
                                                    placeholder="Buscar implemento por nome"
                                                />
                                            </div>
                                            <div className="grid gap-1.5">
                                                <Label className="text-[11px] text-muted-foreground">Operador</Label>
                                                <ColaboradorCombobox value={operadorPadrao} onChange={setOperadorPadrao} valueKey="pessoa_id" />
                                            </div>
                                            <div className="grid gap-1.5">
                                                <Label className="text-[11px] text-muted-foreground">Máquina</Label>
                                                <EquipamentoCombobox
                                                    value={maquinaPadrao}
                                                    onChange={setMaquinaPadrao}
                                                    tiposPermitidos={TIPOS_MAQUINA}
                                                    placeholder="Buscar máquina por nome"
                                                />
                                            </div>
                                        </div>
                                        <Button type="button" size="sm" variant="outline" onClick={aplicarPadraoATodos}>
                                            Aplicar a todas as linhas
                                        </Button>
                                    </div>

                                    <div className="flex flex-col gap-2 max-h-[40vh] overflow-y-auto">
                                        {linhas.map((linha, idx) => (
                                            <div key={linha.itemId} className="rounded-sm border p-2 flex flex-col gap-2">
                                                <div className="flex items-center gap-1.5 text-xs font-medium">
                                                    <span>{linha.descricao}</span>
                                                    {linha.talhaoNome && <span className="text-muted-foreground flex items-center gap-1"><MapPin className="size-3" /> {linha.talhaoNome}</span>}
                                                </div>
                                                <div className="grid grid-cols-2 gap-2">
                                                    <div className="grid gap-1">
                                                        <Label className="text-[10px] text-muted-foreground">Data prevista</Label>
                                                        <Input
                                                            type="date"
                                                            value={linha.data_prevista}
                                                            onChange={(e) => setLinhas(linhas.map((l, j) => (j === idx ? { ...l, data_prevista: e.target.value } : l)))}
                                                        />
                                                    </div>
                                                    <div className="grid gap-1">
                                                        <Label className="flex items-center gap-1 text-[10px] text-muted-foreground">
                                                            Implemento <ImplementoHelp />
                                                        </Label>
                                                        <EquipamentoCombobox
                                                            value={linha.implemento_id}
                                                            onChange={(id) => setLinhas(linhas.map((l, j) => (j === idx ? { ...l, implemento_id: id } : l)))}
                                                            tiposPermitidos={TIPOS_IMPLEMENTO}
                                                            placeholder="Buscar implemento por nome"
                                                        />
                                                    </div>
                                                    <div className="grid gap-1">
                                                        <Label className="text-[10px] text-muted-foreground">Operador</Label>
                                                        <ColaboradorCombobox
                                                            value={linha.operador_id}
                                                            valueKey="pessoa_id"
                                                            onChange={(id) => setLinhas(linhas.map((l, j) => (j === idx ? { ...l, operador_id: id } : l)))}
                                                        />
                                                    </div>
                                                    <div className="grid gap-1">
                                                        <Label className="text-[10px] text-muted-foreground">Máquina</Label>
                                                        <EquipamentoCombobox
                                                            value={linha.maquina_id}
                                                            onChange={(id) => setLinhas(linhas.map((l, j) => (j === idx ? { ...l, maquina_id: id } : l)))}
                                                            tiposPermitidos={TIPOS_MAQUINA}
                                                            placeholder="Buscar máquina por nome"
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </DialogBody>
                <DialogFooter>
                    {resultados ? (
                        <Button size="sm" onClick={fechar}>Fechar</Button>
                    ) : (
                        <>
                            <Button variant="outline" size="sm" onClick={fechar} type="button">
                                Cancelar
                            </Button>
                            <Button size="sm" disabled={!podeSubmeter || gerar.isPending} onClick={() => gerar.mutate()}>
                                <Tractor className="size-3.5 mr-1.5" />
                                {gerar.isPending ? "Gerando…" : `Gerar OS (${linhas.length})`}
                            </Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ── Detalhe do Plano (Sheet) ──────────────────────────────────────────────────

function PlanoDetailSheet({ open, onClose, safraId, plano }: { open: boolean; onClose: () => void; safraId: string; plano: PlanoOperacional }) {
    const qc = useQueryClient();
    const [showAddTarefa, setShowAddTarefa] = useState(false);
    const [showConsolidar, setShowConsolidar] = useState(false);
    const [showInsumosLote, setShowInsumosLote] = useState(false);
    const [showAplicarReceita, setShowAplicarReceita] = useState(false);
    const [showGerarOS, setShowGerarOS] = useState(false);
    const [selecionados, setSelecionados] = useState<Set<string>>(new Set());
    const [avisoPendentes, setAvisoPendentes] = useState(false);

    const { data: tarefasSafra = [] } = useQuery<SafraTarefa[]>({
        queryKey: ["safra-tarefas", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/tarefas`),
        enabled: open,
    });

    const { data: areasRurais = [] } = useQuery<AreaRural[]>({
        queryKey: ["cadastros-areas-rurais"],
        queryFn: () => apiFetch(`/cadastros/areas-rurais`),
        enabled: open,
    });
    const nomeTalhao = (talhaoId: string | null | undefined) =>
        talhaoId ? areasRurais.find((a) => a.id === talhaoId)?.nome ?? null : null;

    const { data: itens = [], isLoading } = useQuery<PlanoItem[]>({
        queryKey: ["plano-itens", plano.id],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/${plano.id}/tarefas`),
        enabled: open,
    });

    const avancar = useMutation({
        mutationFn: (novoStatus: string) =>
            apiFetch(`/agricola/planejamento-operacional/${plano.id}/avancar?novo_status=${novoStatus}`, { method: "POST" }),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["planos-operacionais", safraId] }),
    });

    const findTarefa = (safraTarefaId: string) => tarefasSafra.find((t) => t.id === safraTarefaId);

    const insumosPorItem = useQueries({
        queries: itens.map((item) => ({
            queryKey: ["plano-insumos", item.id],
            queryFn: () => apiFetch<Insumo[]>(`/agricola/planejamento-operacional/${plano.id}/tarefas/${item.id}/insumos`),
            enabled: open,
        })),
    });
    const maoObraPorItem = useQueries({
        queries: itens.map((item) => ({
            queryKey: ["plano-mao-obra", item.id],
            queryFn: () => apiFetch<MaoObra[]>(`/agricola/planejamento-operacional/${plano.id}/tarefas/${item.id}/mao-obra`),
            enabled: open,
        })),
    });

    const totalAgronomico = itens.reduce((s, item) => s + (findTarefa(item.safra_tarefa_id)?.custo_estimado ?? 0), 0);
    const totalPlanejado =
        insumosPorItem.reduce((s, q) => s + (q.data ?? []).reduce((si, i) => si + (i.custo_total_estimado ?? 0), 0), 0) +
        maoObraPorItem.reduce((s, q) => s + (q.data ?? []).reduce((sm, m) => sm + (m.custo_total_estimado ?? 0), 0), 0);

    const consolidados: ConsolidadoInsumo[] = (() => {
        const mapa = new Map<string, ConsolidadoInsumo>();
        for (const q of insumosPorItem) {
            for (const i of q.data ?? []) {
                const chave = `${i.produto_id}__${i.unidade_dose}`;
                const atual = mapa.get(chave);
                if (atual) {
                    atual.quantidade += i.quantidade_planejada;
                } else {
                    mapa.set(chave, { produto_id: i.produto_id, unidade: i.unidade_dose, quantidade: i.quantidade_planejada });
                }
            }
        }
        return Array.from(mapa.values());
    })();

    const transicoesPossiveis = TRANSICOES_PLANO[plano.status] ?? [];
    const somenteLeitura = plano.status === "CANCELADO";

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent
                side="right"
                className="w-full overflow-hidden flex flex-col p-0"
                style={{ maxWidth: "min(96vw, 68rem)" }}
            >
                <SheetHeader className="px-6 pt-6">
                    <div className="flex items-center gap-2">
                        <SheetTitle>{plano.nome}</SheetTitle>
                        <Badge variant={statusBadgeVariant(plano.status)}>
                            {STATUS_PLANO_LABEL[plano.status] ?? plano.status}
                        </Badge>
                    </div>
                    <SheetDescription className="flex items-center gap-1.5">
                        <CalendarDays className="size-3.5" />
                        Início previsto: {new Date(plano.data_inicio_prevista).toLocaleDateString("pt-BR")}
                        {plano.data_fim_prevista ? ` · Fim: ${new Date(plano.data_fim_prevista).toLocaleDateString("pt-BR")}` : ""}
                    </SheetDescription>
                    {somenteLeitura && (
                        <span className="inline-flex w-fit items-center gap-1.5 rounded-sm border border-muted-foreground/20 bg-muted px-2 py-1 text-xs text-muted-foreground">
                            <Lock className="size-3" /> Plano cancelado — somente leitura
                        </span>
                    )}
                    {transicoesPossiveis.filter((s) => s !== "CANCELADO").length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-1">
                            {transicoesPossiveis.filter((s) => s !== "CANCELADO").map((s) => (
                                <Button
                                    key={s}
                                    size="sm"
                                    onClick={() => avancar.mutate(s)}
                                    disabled={avancar.isPending}
                                >
                                    {STATUS_PLANO_LABEL[s] ?? s}
                                </Button>
                            ))}
                        </div>
                    )}
                </SheetHeader>

                <ScrollArea className="flex-1 px-6 py-4">
                    {itens.length > 0 && (
                        <Card className="mb-4">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm flex items-center gap-1.5">
                                    <Scale className="size-3.5" /> Estimativa agronômica × Planejamento
                                </CardTitle>
                                <CardDescription>Soma do custo estimado na análise de solo contra o custo real planejado (insumos + mão de obra).</CardDescription>
                            </CardHeader>
                            <CardContent className="flex items-center gap-6 pt-0">
                                <div>
                                    <p className="text-xs text-muted-foreground">Agronômico</p>
                                    <p className="text-lg font-semibold">{brl(totalAgronomico)}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground">Planejado</p>
                                    <p className="text-lg font-semibold">{brl(totalPlanejado)}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground">Diferença</p>
                                    <p className={cn("text-lg font-semibold flex items-center gap-1", totalPlanejado > totalAgronomico ? "text-amber-600" : "text-emerald-600")}>
                                        {totalAgronomico > 0 ? `${(((totalPlanejado - totalAgronomico) / totalAgronomico) * 100).toFixed(1)}%` : "—"}
                                        {totalPlanejado > totalAgronomico ? <TrendingUp className="size-4" /> : <TrendingDown className="size-4" />}
                                    </p>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                    <div className="flex items-center justify-between mb-1 gap-2 flex-wrap">
                        <h3 className="text-sm font-medium">Tarefas do plano ({itens.length})</h3>
                        {!somenteLeitura && (
                            <div className="flex items-center gap-2">
                                {selecionados.size > 0 && (
                                    <Button size="sm" variant="outline" onClick={() => setShowAplicarReceita(true)}>
                                        <FlaskConical className="size-3.5 mr-1.5" /> Aplicar receita ({selecionados.size})
                                    </Button>
                                )}
                                {selecionados.size > 0 && (
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => {
                                            const temPendente = itens.some(
                                                (item) => selecionados.has(item.id) && item.status_planejamento !== "PRONTA"
                                            );
                                            if (temPendente) {
                                                setAvisoPendentes(true);
                                            } else {
                                                setShowGerarOS(true);
                                            }
                                        }}
                                    >
                                        <Tractor className="size-3.5 mr-1.5" />
                                        Gerar OS em lote ({itens.filter((item) => selecionados.has(item.id) && item.status_planejamento === "PRONTA").length})
                                    </Button>
                                )}
                                {consolidados.length > 0 && (
                                    <Button size="sm" variant="outline" onClick={() => setShowConsolidar(true)}>
                                        <Layers className="size-3.5 mr-1.5" /> Consolidar e solicitar compra
                                    </Button>
                                )}
                                {itens.length > 0 && (
                                    <Button size="sm" variant="outline" onClick={() => setShowInsumosLote(true)}>
                                        <Package className="size-3.5 mr-1.5" /> Configurar insumos em lote
                                    </Button>
                                )}
                                <Button size="sm" variant="outline" onClick={() => setShowAddTarefa(true)}>
                                    <Plus className="size-3.5 mr-1.5" /> Adicionar tarefa
                                </Button>
                            </div>
                        )}
                    </div>

                    {itens.length > 0 && (() => {
                        const prontos = itens.filter((i) => i.status_planejamento === "PRONTA").length;
                        const programados = itens.filter((i) => i.status_planejamento === "PROGRAMADA").length;
                        const pendentes = itens.length - prontos - programados;
                        return (
                            <p className="text-xs text-muted-foreground mb-3">
                                {programados > 0 && <span className="text-emerald-600 font-medium">{programados} com OS gerada</span>}
                                {programados > 0 && (prontos > 0 || pendentes > 0) && " · "}
                                {prontos > 0 && <span className="font-medium">{prontos} pronta(s) para gerar OS</span>}
                                {prontos > 0 && pendentes > 0 && " · "}
                                {pendentes > 0 && (
                                    <span className="text-amber-600 font-medium">
                                        {pendentes} pendente(s) de aprovação/reserva de insumo
                                    </span>
                                )}
                            </p>
                        );
                    })()}

                    {itens.length > 0 && !["CONCLUIDO", "CANCELADO"].includes(plano.status) && (() => {
                        const ativos = itens.filter((i) => !["REMOVIDA", "CANCELADA"].includes(i.status_planejamento));
                        const todasConcluidas =
                            ativos.length > 0 &&
                            ativos.every((i) => findTarefa(i.safra_tarefa_id)?.status === "CONCLUIDA");
                        if (!todasConcluidas) return null;
                        return (
                            <div className="mb-4 flex items-center justify-between gap-3 rounded-sm border border-emerald-500/30 bg-emerald-500/10 px-3 py-2">
                                <span className="flex items-center gap-1.5 text-sm text-emerald-700">
                                    <CheckCircle2 className="size-4 shrink-0" />
                                    Todas as tarefas deste plano já foram concluídas no campo.
                                </span>
                                {plano.status === "EM_EXECUCAO" ? (
                                    <Button size="sm" onClick={() => avancar.mutate("CONCLUIDO")} disabled={avancar.isPending}>
                                        Marcar plano como concluído
                                    </Button>
                                ) : (
                                    <span className="text-xs text-emerald-700/80 whitespace-nowrap">
                                        Avance o status acima até "Em execução" para poder concluir o plano.
                                    </span>
                                )}
                            </div>
                        );
                    })()}

                    {isLoading ? (
                        <p className="text-sm text-muted-foreground text-center py-6">Carregando…</p>
                    ) : itens.length === 0 ? (
                        <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed px-6 py-10 text-center">
                            <ClipboardCheck className="size-8 text-muted-foreground/50" />
                            <p className="text-sm font-medium">Nenhuma tarefa incluída neste plano</p>
                            {!somenteLeitura && (
                                <Button variant="outline" size="sm" onClick={() => setShowAddTarefa(true)}>
                                    <Plus className="size-4 mr-1.5" /> Adicionar primeira tarefa
                                </Button>
                            )}
                        </div>
                    ) : (
                        <Accordion type="multiple" className="flex flex-col gap-2">
                            {itens.map((item) => {
                                const tarefa = findTarefa(item.safra_tarefa_id);
                                return (
                                    <PlanoItemPanel
                                        key={item.id}
                                        planoId={plano.id}
                                        item={item}
                                        tarefa={tarefa}
                                        talhaoNome={nomeTalhao(tarefa?.talhao_id)}
                                        somenteLeitura={somenteLeitura}
                                        selecionado={selecionados.has(item.id)}
                                        onToggleSelecionado={(checked) => {
                                            setSelecionados((prev) => {
                                                const next = new Set(prev);
                                                if (checked) next.add(item.id);
                                                else next.delete(item.id);
                                                return next;
                                            });
                                        }}
                                    />
                                );
                            })}
                        </Accordion>
                    )}
                </ScrollArea>
            </SheetContent>

            {showAddTarefa && (
                <AddTarefaDialog open={showAddTarefa} onClose={() => setShowAddTarefa(false)} safraId={safraId} planoId={plano.id} />
            )}
            {showConsolidar && (
                <ConsolidarComprasDialog
                    open={showConsolidar}
                    onClose={() => setShowConsolidar(false)}
                    planoId={plano.id}
                    consolidados={consolidados}
                />
            )}
            {showInsumosLote && (
                <InsumosConsolidadosDialog
                    open={showInsumosLote}
                    onClose={() => setShowInsumosLote(false)}
                    planoId={plano.id}
                />
            )}
            <AlertDialog open={avisoPendentes} onOpenChange={setAvisoPendentes}>
                <AlertDialogContent className="max-w-md">
                    {(() => {
                        const pendentesSelecionados = itens.filter(
                            (item) => selecionados.has(item.id) && item.status_planejamento !== "PRONTA"
                        );
                        const prontosSelecionados = itens.filter(
                            (item) => selecionados.has(item.id) && item.status_planejamento === "PRONTA"
                        ).length;
                        return (
                            <>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Itens selecionados não estão prontos</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        {pendentesSelecionados.length} de {selecionados.size} tarefa(s) selecionada(s) ainda não
                                        {" "}tiveram os insumos aprovados/reservados e não vão gerar Ordem de Serviço agora.{" "}
                                        {prontosSelecionados > 0
                                            ? `Apenas ${prontosSelecionados} tarefa(s) pronta(s) vai(vão) gerar OS se você continuar.`
                                            : "Nenhuma tarefa selecionada está pronta — aprove os insumos antes de gerar OS."}
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <div className="max-h-48 overflow-y-auto space-y-1 rounded-sm border p-2">
                                    {pendentesSelecionados.map((item) => {
                                        const tarefa = findTarefa(item.safra_tarefa_id);
                                        return (
                                            <div key={item.id} className="flex items-center justify-between gap-2 text-xs">
                                                <span className="truncate">{nomeTalhao(tarefa?.talhao_id) ?? tarefa?.descricao ?? "Tarefa"}</span>
                                                <Badge variant={statusBadgeVariant(item.status_planejamento)} className="shrink-0">
                                                    {STATUS_ITEM_LABEL[item.status_planejamento] ?? item.status_planejamento}
                                                </Badge>
                                            </div>
                                        );
                                    })}
                                </div>
                                <AlertDialogFooter>
                                    <AlertDialogCancel onClick={() => setAvisoPendentes(false)}>Voltar e aprovar itens</AlertDialogCancel>
                                    <AlertDialogAction
                                        disabled={prontosSelecionados === 0}
                                        onClick={() => {
                                            setAvisoPendentes(false);
                                            setShowGerarOS(true);
                                        }}
                                    >
                                        Continuar só com as prontas
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </>
                        );
                    })()}
                </AlertDialogContent>
            </AlertDialog>

            {showAplicarReceita && (
                <AplicarReceitaDialog
                    open={showAplicarReceita}
                    onClose={() => { setShowAplicarReceita(false); setSelecionados(new Set()); }}
                    planoId={plano.id}
                    safraId={safraId}
                    itensSelecionados={itens
                        .filter((item) => selecionados.has(item.id))
                        .map((item) => {
                            const tarefa = findTarefa(item.safra_tarefa_id);
                            return {
                                itemId: item.id,
                                descricao: tarefa?.descricao ?? "Tarefa",
                                talhaoNome: nomeTalhao(tarefa?.talhao_id),
                            };
                        })}
                />
            )}
            {showGerarOS && (
                <GerarOSLoteDialog
                    open={showGerarOS}
                    onClose={() => { setShowGerarOS(false); setSelecionados(new Set()); }}
                    planoId={plano.id}
                    safraId={safraId}
                    itensSelecionados={itens
                        .filter((item) => selecionados.has(item.id))
                        .map((item) => {
                            const tarefa = findTarefa(item.safra_tarefa_id);
                            return {
                                itemId: item.id,
                                descricao: tarefa?.descricao ?? "Tarefa",
                                talhaoNome: nomeTalhao(tarefa?.talhao_id),
                                statusPlanejamento: item.status_planejamento,
                            };
                        })}
                />
            )}
        </Sheet>
    );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export function PlanejamentoOperacionalSafra({ safraId }: { safraId: string }) {
    const qc = useQueryClient();
    const [showCreate, setShowCreate] = useState(false);
    const [selectedPlano, setSelectedPlano] = useState<PlanoOperacional | null>(null);
    const [editandoPlano, setEditandoPlano] = useState<PlanoOperacional | null>(null);
    const [cancelandoPlano, setCancelandoPlano] = useState<PlanoOperacional | null>(null);

    const { data: planos = [], isLoading, isError, error } = useQuery<PlanoOperacional[]>({
        queryKey: ["planos-operacionais", safraId],
        queryFn: () => apiFetch(`/agricola/planejamento-operacional/?safra_id=${safraId}`),
    });

    const cancelarPlano = useMutation({
        mutationFn: (planoId: string) =>
            apiFetch(`/agricola/planejamento-operacional/${planoId}/avancar?novo_status=CANCELADO`, { method: "POST" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["planos-operacionais", safraId] });
            setCancelandoPlano(null);
        },
    });

    if (isLoading) {
        return <p className="text-sm text-muted-foreground py-6 text-center">Carregando planejamentos…</p>;
    }

    if (isError) {
        return (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-6 text-center">
                <p className="text-sm font-medium text-destructive">Não foi possível carregar os planejamentos desta safra.</p>
                <p className="mt-1 text-sm text-muted-foreground">{error instanceof Error ? error.message : "Erro desconhecido."}</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                    Agrupe tarefas aprovadas para planejar insumos, mão de obra e disparar compras em lote.
                </p>
                <Button size="sm" onClick={() => setShowCreate(true)}>
                    <Plus className="size-4 mr-1.5" /> Novo plano
                </Button>
            </div>

            {planos.length === 0 ? (
                <div className="flex flex-col items-center gap-3 rounded-sm border border-dashed px-6 py-10 text-center">
                    <ClipboardCheck className="size-8 text-muted-foreground/50" />
                    <div className="space-y-1">
                        <p className="text-sm font-medium">Nenhum planejamento operacional criado</p>
                        <p className="text-sm text-muted-foreground">
                            Crie um plano para agrupar tarefas e organizar a execução com antecedência.
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setShowCreate(true)}>
                        <Plus className="size-4 mr-1.5" /> Criar primeiro plano
                    </Button>
                </div>
            ) : (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {planos.map((p) => {
                        const podeEditar = ["RASCUNHO", "EM_ANALISE"].includes(p.status);
                        const podeCancelar = (TRANSICOES_PLANO[p.status] ?? []).includes("CANCELADO");
                        return (
                            <Card key={p.id}>
                                <CardHeader className="pb-2">
                                    <div className="flex items-start justify-between gap-2">
                                        <CardTitle className="text-base text-balance">{p.nome}</CardTitle>
                                        <div className="flex items-center gap-2 shrink-0">
                                            <div className="flex gap-1">
                                                <Button
                                                    size="icon-sm"
                                                    variant="outline"
                                                    onClick={() => setSelectedPlano(p)}
                                                    aria-label="Editar itens do planejamento"
                                                    title="Editar itens do planejamento"
                                                >
                                                    <Eye className="size-3.5" />
                                                </Button>
                                                {podeEditar && (
                                                    <Button
                                                        size="icon-sm"
                                                        variant="outline"
                                                        onClick={() => setEditandoPlano(p)}
                                                        aria-label="Editar planejamento"
                                                        title="Editar planejamento"
                                                    >
                                                        <Pencil className="size-3.5" />
                                                    </Button>
                                                )}
                                                {podeCancelar && (
                                                    <Button
                                                        size="icon-sm"
                                                        variant="outline"
                                                        className="text-destructive hover:text-destructive"
                                                        onClick={() => setCancelandoPlano(p)}
                                                        aria-label="Cancelar planejamento"
                                                        title="Cancelar planejamento"
                                                    >
                                                        <Ban className="size-3.5" />
                                                    </Button>
                                                )}
                                            </div>
                                            <Badge variant={statusBadgeVariant(p.status)}>{STATUS_PLANO_LABEL[p.status] ?? p.status}</Badge>
                                        </div>
                                    </div>
                                    <CardDescription className="flex items-center gap-1.5">
                                        <CalendarDays className="size-3.5" />
                                        {new Date(p.data_inicio_prevista).toLocaleDateString("pt-BR")}
                                    </CardDescription>
                                </CardHeader>
                                {p.descricao && (
                                    <CardContent className="pt-0">
                                        <p className="text-sm text-muted-foreground line-clamp-2 text-pretty">{p.descricao}</p>
                                    </CardContent>
                                )}
                            </Card>
                        );
                    })}
                </div>
            )}

            {showCreate && <CreatePlanoDialog open={showCreate} onClose={() => setShowCreate(false)} safraId={safraId} />}

            {editandoPlano && (
                <CreatePlanoDialog
                    open={!!editandoPlano}
                    onClose={() => setEditandoPlano(null)}
                    safraId={safraId}
                    plano={editandoPlano}
                />
            )}

            <AlertDialog open={!!cancelandoPlano} onOpenChange={() => setCancelandoPlano(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Cancelar planejamento operacional?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. Todas as reservas de estoque ativas dos insumos de
                            "{cancelandoPlano?.nome}" serão liberadas automaticamente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setCancelandoPlano(null)}>Voltar</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => cancelandoPlano && cancelarPlano.mutate(cancelandoPlano.id)}
                            disabled={cancelarPlano.isPending}
                        >
                            Cancelar plano
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {selectedPlano && (
                <PlanoDetailSheet
                    open={!!selectedPlano}
                    onClose={() => setSelectedPlano(null)}
                    safraId={safraId}
                    plano={selectedPlano}
                />
            )}
        </div>
    );
}
