"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
    AlertTriangle,
    CheckCircle2,
    Clock,
    Play,
    Plus,
    Search,
    Target,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";

interface PlanoAcaoViabilidade {
    vpl: number;
    tir_aa: number | null;
    payback_simples_anos: number | null;
    payback_descontado_anos: number | null;
    veredito_final: "VIAVEL" | "INVIAVEL" | "ATENCAO_LIQUIDEZ";
    resumo_executivo: string;
}

interface PlanoAcao {
    id: string;
    titulo: string;
    descricao: string | null;
    origem_indicador: string | null;
    responsavel_nome: string | null;
    meta: string | null;
    prazo: string | null;
    status: "ABERTO" | "EM_ANDAMENTO" | "CONCLUIDO" | "ATRASADO";
    resultado_obtido: string | null;
    investimento_estimado?: number | null;
    retorno_anual_estimado?: number | null;
    horizonte_anos?: number | null;
    tma_aa?: number | null;
    prazo_maximo_payback_anos?: number | null;
    viabilidade?: PlanoAcaoViabilidade | null;
}

const VEREDITO_CAPEX_BADGE: Record<PlanoAcaoViabilidade["veredito_final"], { label: string; className: string }> = {
    VIAVEL: { label: "Viável", className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30" },
    ATENCAO_LIQUIDEZ: { label: "Liquidez", className: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30" },
    INVIAVEL: { label: "Inviável", className: "bg-destructive/15 text-destructive border-destructive/30" },
};

function formatBrl(v: number): string {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const STATUS_BADGE: Record<PlanoAcao["status"], { label: string; className: string }> = {
    ABERTO: { label: "Aberto", className: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20" },
    EM_ANDAMENTO: { label: "Em andamento", className: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20" },
    ATRASADO: { label: "Atrasado", className: "bg-destructive/10 text-destructive border-destructive/20" },
    CONCLUIDO: { label: "Concluído", className: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20" },
};

function formatDateBr(iso: string | null): string {
    if (!iso) return "—";
    const [y, m, d] = iso.split("-");
    return y && m && d ? `${d}/${m}/${y}` : iso;
}

export function PlanosAcaoClient() {
    const qc = useQueryClient();
    const [busca, setBusca] = useState("");
    const [statusFiltro, setStatusFiltro] = useState<string>("TODOS");
    const [openNew, setOpenNew] = useState(false);
    const [concluirItem, setConcluirItem] = useState<PlanoAcao | null>(null);
    const [resultadoObtido, setResultadoObtido] = useState("");
    const [form, setForm] = useState({
        titulo: "",
        responsavel_nome: "",
        meta: "",
        prazo: "",
        descricao: "",
        investimento_estimado: "",
        retorno_anual_estimado: "",
        horizonte_anos: "5",
        tma_aa: "12",
        prazo_maximo_payback_anos: "4",
    });

    const { data: planos = [], isLoading } = useQuery<PlanoAcao[]>({
        queryKey: ["planos-acao"],
        queryFn: () => apiFetch("/planos-acao/"),
    });

    const criar = useMutation({
        mutationFn: (body: Record<string, unknown>) =>
            apiFetch("/planos-acao/", { method: "POST", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Plano de ação criado.");
            qc.invalidateQueries({ queryKey: ["planos-acao"] });
            setOpenNew(false);
            setForm({
                titulo: "",
                responsavel_nome: "",
                meta: "",
                prazo: "",
                descricao: "",
                investimento_estimado: "",
                retorno_anual_estimado: "",
                horizonte_anos: "5",
                tma_aa: "12",
                prazo_maximo_payback_anos: "4",
            });
        },
        onError: () => toast.error("Erro ao criar plano de ação."),
    });

    const atualizar = useMutation({
        mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
            apiFetch(`/planos-acao/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Plano de ação atualizado.");
            qc.invalidateQueries({ queryKey: ["planos-acao"] });
            setConcluirItem(null);
            setResultadoObtido("");
        },
        onError: () => toast.error("Erro ao atualizar plano de ação."),
    });

    const contadores = useMemo(() => {
        return {
            abertos: planos.filter((p) => p.status === "ABERTO").length,
            emAndamento: planos.filter((p) => p.status === "EM_ANDAMENTO").length,
            atrasados: planos.filter((p) => p.status === "ATRASADO").length,
            concluidos: planos.filter((p) => p.status === "CONCLUIDO").length,
        };
    }, [planos]);

    const filtrados = useMemo(() => {
        const termo = busca.trim().toLowerCase();
        return planos.filter((p) => {
            if (statusFiltro !== "TODOS" && p.status !== statusFiltro) return false;
            if (!termo) return true;
            return (
                p.titulo.toLowerCase().includes(termo) ||
                (p.responsavel_nome ?? "").toLowerCase().includes(termo) ||
                (p.origem_indicador ?? "").toLowerCase().includes(termo)
            );
        });
    }, [planos, busca, statusFiltro]);

    function handleCriar() {
        if (form.titulo.trim().length < 3) {
            toast.error("Informe um título com pelo menos 3 caracteres.");
            return;
        }
        const invest = Number(form.investimento_estimado);
        const retorno = Number(form.retorno_anual_estimado);
        const temCapex = Number.isFinite(invest) && invest > 0 && Number.isFinite(retorno) && retorno > 0;
        criar.mutate({
            titulo: form.titulo.trim(),
            responsavel_nome: form.responsavel_nome.trim() || null,
            meta: form.meta.trim() || null,
            prazo: form.prazo || null,
            descricao: form.descricao.trim() || null,
            ...(temCapex
                ? {
                      investimento_estimado: invest,
                      retorno_anual_estimado: retorno,
                      horizonte_anos: Math.max(1, Number(form.horizonte_anos) || 5),
                      tma_aa: Math.max(0, Number(form.tma_aa) || 12),
                      prazo_maximo_payback_anos: Math.max(0.5, Number(form.prazo_maximo_payback_anos) || 4),
                  }
                : {}),
        });
    }

    if (isLoading) {
        return (
            <div className="flex flex-1 flex-col gap-6 p-6">
                <PageHeader
                    title="Planos de Ação Gerenciais"
                    description="Transforme gargalos e indicadores negativos em ações acompanháveis com responsável, prazo e meta."
                    icon={<Target className="text-primary" size={22} />}
                    breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Planos de Ação" }]}
                />
                <Skeleton className="h-64 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="flex flex-1 flex-col gap-6 p-6">
            <PageHeader
                title="Planos de Ação Gerenciais"
                description="Transforme gargalos e indicadores negativos em ações acompanháveis com responsável, prazo e meta."
                icon={<Target className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Planos de Ação" }]}
                actions={
                    <Button
                        variant="outline"
                        size="sm"
                        className="rounded-sm"
                        onClick={() => setOpenNew(true)}
                    >
                        <Plus className="mr-1.5 size-3.5" /> Novo Plano
                    </Button>
                }
            />
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Abertos</span>
                            <Target className="size-3.5 text-blue-600" />
                        </div>
                        <p className="text-2xl font-bold mt-1">{contadores.abertos}</p>
                    </CardContent>
                </Card>
                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Em Andamento</span>
                            <Clock className="size-3.5 text-amber-600" />
                        </div>
                        <p className="text-2xl font-bold mt-1">{contadores.emAndamento}</p>
                    </CardContent>
                </Card>
                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Atrasados</span>
                            <AlertTriangle className="size-3.5 text-destructive" />
                        </div>
                        <p className="text-2xl font-bold mt-1 text-destructive">{contadores.atrasados}</p>
                    </CardContent>
                </Card>
                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Concluídos</span>
                            <CheckCircle2 className="size-3.5 text-emerald-600" />
                        </div>
                        <p className="text-2xl font-bold mt-1 text-emerald-700 dark:text-emerald-400">
                            {contadores.concluidos}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card className="rounded-sm">
                <CardContent className="pt-4 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                            <div className="relative w-64">
                                <Search className="size-3.5 text-muted-foreground absolute left-2.5 top-2.5" />
                                <Input
                                    value={busca}
                                    onChange={(e) => setBusca(e.target.value)}
                                    placeholder="Buscar plano ou responsável..."
                                    className="h-8 pl-8 text-xs rounded-sm"
                                />
                            </div>
                            <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                                <SelectTrigger className="h-8 w-44 text-xs rounded-sm">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="TODOS">Todos os status</SelectItem>
                                    <SelectItem value="ABERTO">Aberto</SelectItem>
                                    <SelectItem value="EM_ANDAMENTO">Em andamento</SelectItem>
                                    <SelectItem value="ATRASADO">Atrasado</SelectItem>
                                    <SelectItem value="CONCLUIDO">Concluído</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {filtrados.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            Nenhum plano de ação encontrado.
                        </p>
                    ) : (
                        <div className="rounded-sm border overflow-x-auto">
                            <Table className="text-xs">
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="h-8">Plano de Ação</TableHead>
                                        <TableHead className="h-8">Origem</TableHead>
                                        <TableHead className="h-8">Responsável</TableHead>
                                        <TableHead className="h-8">Meta</TableHead>
                                        <TableHead className="h-8">Viabilidade CapEx</TableHead>
                                        <TableHead className="h-8">Prazo</TableHead>
                                        <TableHead className="h-8">Status</TableHead>
                                        <TableHead className="h-8 text-right" />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filtrados.map((item) => {
                                        const badge = STATUS_BADGE[item.status] ?? STATUS_BADGE.ABERTO;
                                        return (
                                            <TableRow key={item.id}>
                                                <TableCell className="font-medium">
                                                    <div>{item.titulo}</div>
                                                    {item.resultado_obtido && (
                                                        <p className="text-[11px] text-emerald-700 dark:text-emerald-400">
                                                            Resultado: {item.resultado_obtido}
                                                        </p>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {item.origem_indicador ?? "Manual"}
                                                </TableCell>
                                                <TableCell>{item.responsavel_nome ?? "—"}</TableCell>
                                                <TableCell>{item.meta ?? "—"}</TableCell>
                                                <TableCell>
                                                    {item.viabilidade ? (
                                                        <div className="space-y-0.5">
                                                            <div className="flex items-center gap-1.5">
                                                                <Badge className={`rounded-sm text-[10px] ${VEREDITO_CAPEX_BADGE[item.viabilidade.veredito_final].className}`}>
                                                                    {VEREDITO_CAPEX_BADGE[item.viabilidade.veredito_final].label}
                                                                </Badge>
                                                                <span className="tabular-nums font-medium">
                                                                    VPL {formatBrl(item.viabilidade.vpl)}
                                                                </span>
                                                            </div>
                                                            <p className="text-[10px] text-muted-foreground tabular-nums">
                                                                {item.viabilidade.tir_aa !== null ? `TIR ${item.viabilidade.tir_aa.toFixed(1)}%` : "TIR —"}
                                                                {item.viabilidade.payback_descontado_anos !== null
                                                                    ? ` • Payback ${item.viabilidade.payback_descontado_anos.toFixed(1)}a`
                                                                    : ""}
                                                            </p>
                                                        </div>
                                                    ) : (
                                                        <span className="text-muted-foreground">—</span>
                                                    )}
                                                </TableCell>
                                                <TableCell>{formatDateBr(item.prazo)}</TableCell>
                                                <TableCell>
                                                    <Badge className={`rounded-sm text-[11px] ${badge.className}`}>
                                                        {badge.label}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        {item.status === "ABERTO" && (
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                className="rounded-sm h-7 text-xs"
                                                                onClick={() =>
                                                                    atualizar.mutate({
                                                                        id: item.id,
                                                                        body: { status: "EM_ANDAMENTO" },
                                                                    })
                                                                }
                                                            >
                                                                <Play className="size-3 mr-1" /> Iniciar
                                                            </Button>
                                                        )}
                                                        {item.status !== "CONCLUIDO" && (
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                className="rounded-sm h-7 text-xs"
                                                                onClick={() => setConcluirItem(item)}
                                                            >
                                                                <CheckCircle2 className="size-3 mr-1" /> Concluir
                                                            </Button>
                                                        )}
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={openNew} onOpenChange={setOpenNew}>
                <DialogContent className="sm:max-w-lg rounded-sm">
                    <DialogHeader>
                        <DialogTitle>Novo Plano de Ação</DialogTitle>
                        <DialogDescription>Defina responsável, meta e prazo para acompanhamento.</DialogDescription>
                    </DialogHeader>
                    <div className="px-6 space-y-3">
                        <div className="space-y-1">
                            <Label>Título</Label>
                            <Input
                                value={form.titulo}
                                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                                placeholder="Ex.: Reduzir custo de suplementação do Lote 02"
                                className="h-8 text-xs rounded-sm"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <Label>Responsável</Label>
                                <Input
                                    value={form.responsavel_nome}
                                    onChange={(e) => setForm({ ...form, responsavel_nome: e.target.value })}
                                    placeholder="Nome do responsável"
                                    className="h-8 text-xs rounded-sm"
                                />
                            </div>
                            <div className="space-y-1">
                                <Label>Prazo</Label>
                                <Input
                                    type="date"
                                    value={form.prazo}
                                    onChange={(e) => setForm({ ...form, prazo: e.target.value })}
                                    className="h-8 text-xs rounded-sm"
                                />
                            </div>
                        </div>
                        <div className="space-y-1">
                            <Label>Meta</Label>
                            <Input
                                value={form.meta}
                                onChange={(e) => setForm({ ...form, meta: e.target.value })}
                                placeholder="Ex.: Reduzir 10% do custo/ha"
                                className="h-8 text-xs rounded-sm"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Descrição</Label>
                            <Textarea
                                value={form.descricao}
                                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                                className="text-xs rounded-sm"
                            />
                        </div>
                        <div className="rounded-sm border bg-muted/20 p-3 space-y-2.5">
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                Viabilidade Financeira (Opcional — CapEx)
                            </p>
                            <div className="grid grid-cols-2 gap-2.5">
                                <div className="space-y-1">
                                    <Label className="text-xs">Investimento (R$)</Label>
                                    <Input
                                        type="number"
                                        min="0"
                                        step="1000"
                                        placeholder="Ex.: 500000"
                                        value={form.investimento_estimado}
                                        onChange={(e) => setForm({ ...form, investimento_estimado: e.target.value })}
                                        className="h-8 text-xs rounded-sm tabular-nums"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">Retorno Anual (R$)</Label>
                                    <Input
                                        type="number"
                                        min="0"
                                        step="1000"
                                        placeholder="Ex.: 180000"
                                        value={form.retorno_anual_estimado}
                                        onChange={(e) => setForm({ ...form, retorno_anual_estimado: e.target.value })}
                                        className="h-8 text-xs rounded-sm tabular-nums"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">Horizonte (anos)</Label>
                                    <Input
                                        type="number"
                                        min="1"
                                        max="25"
                                        value={form.horizonte_anos}
                                        onChange={(e) => setForm({ ...form, horizonte_anos: e.target.value })}
                                        className="h-8 text-xs rounded-sm tabular-nums"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-xs">TMA (% a.a.) / Payback Máx.</Label>
                                    <div className="grid grid-cols-2 gap-1.5">
                                        <Input
                                            type="number"
                                            min="0"
                                            step="0.5"
                                            value={form.tma_aa}
                                            onChange={(e) => setForm({ ...form, tma_aa: e.target.value })}
                                            className="h-8 text-xs rounded-sm tabular-nums"
                                            title="TMA (% a.a.)"
                                        />
                                        <Input
                                            type="number"
                                            min="0.5"
                                            step="0.5"
                                            value={form.prazo_maximo_payback_anos}
                                            onChange={(e) => setForm({ ...form, prazo_maximo_payback_anos: e.target.value })}
                                            className="h-8 text-xs rounded-sm tabular-nums"
                                            title="Payback Máximo (anos)"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpenNew(false)}>
                            Cancelar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            disabled={criar.isPending}
                            onClick={handleCriar}
                        >
                            Salvar Plano
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!concluirItem} onOpenChange={(open) => !open && setConcluirItem(null)}>
                <DialogContent className="sm:max-w-md rounded-sm">
                    <DialogHeader>
                        <DialogTitle>Concluir Plano de Ação</DialogTitle>
                        <DialogDescription>{concluirItem?.titulo}</DialogDescription>
                    </DialogHeader>
                    <div className="px-6 space-y-2">
                        <Label>Resultado Obtido</Label>
                        <Textarea
                            value={resultadoObtido}
                            onChange={(e) => setResultadoObtido(e.target.value)}
                            placeholder="Descreva o resultado alcançado..."
                            className="text-xs rounded-sm"
                        />
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={() => setConcluirItem(null)}
                        >
                            Cancelar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            disabled={atualizar.isPending || !concluirItem}
                            onClick={() =>
                                concluirItem &&
                                atualizar.mutate({
                                    id: concluirItem.id,
                                    body: {
                                        status: "CONCLUIDO",
                                        resultado_obtido: resultadoObtido.trim() || null,
                                    },
                                })
                            }
                        >
                            Confirmar Conclusão
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
