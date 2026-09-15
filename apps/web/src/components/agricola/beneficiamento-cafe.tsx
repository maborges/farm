"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Plus, Pencil, TrendingDown, Package, Star, Layers, ShoppingCart, BarChart3, Archive } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useHasTier } from "@/hooks/use-has-tier";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Lock } from "lucide-react";
import Link from "next/link";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Talhao { id: string; nome: string; }

interface DetalheCafe {
    metodo: string;
    local_secagem: string | null;
    peneira_principal: string | null;
    bebida: string | null;
    pontuacao_scaa: number | null;
    defeitos_intrinsecos: number | null;
    defeitos_extrinsecos: number | null;
}

interface Lote {
    id: string;
    numero_lote: string;
    status: string;
    data_entrada: string;
    peso_entrada_kg: number;
    umidade_entrada_pct: number | null;
    data_saida: string | null;
    peso_saida_kg: number | null;
    umidade_saida_pct: number | null;
    fator_reducao: number | null;
    fator_esperado_manual: number | null;
    sacas_beneficiadas: number | null;
    perda_pct: number | null;
    perda_secagem_kg: number | null;
    perda_quebra_kg: number | null;
    perda_defeito_kg: number | null;
    talhao_id: string | null;
    lote_estoque_id: string | null;
    detalhe_cafe: DetalheCafe | null;
}

interface KPIs {
    total_lotes: number;
    peso_entrada_total_kg: number;
    peso_saida_total_kg: number;
    sacas_beneficiadas_total: number;
    fator_reducao_medio: number | null;
    lotes_em_processo: number;
    lotes_concluidos: number;
    pontuacao_media_scaa: number | null;
}

interface RendimentoPorMetodo {
    metodo: string;
    total_lotes: number;
    peso_entrada_kg: number;
    peso_saida_kg: number;
    sacas_beneficiadas: number;
    fator_reducao_real: number | null;
    fator_reducao_esperado: number;
    eficiencia_pct: number;
    perda_secagem_kg: number;
    perda_quebra_kg: number;
    perda_defeito_kg: number;
    perda_total_kg: number;
}

interface RelatorioRendimento {
    safra_id: string;
    total_lotes: number;
    peso_entrada_total_kg: number;
    peso_saida_total_kg: number;
    sacas_total: number;
    rendimento_medio_pct: number;
    por_metodo: RendimentoPorMetodo[];
}

interface BeneficiamentoMutacaoResult {
    id?: string;
    numero_contrato?: string;
    lote_estoque_id?: string;
    detail?: string;
    message?: string;
}

interface Props { safraId: string; talhoes: Talhao[]; }

const METODOS = ["NATURAL", "LAVADO", "HONEY", "DESCASCADO"];
const LOCAIS = ["TERREIRO_CIMENTO", "TERREIRO_SUSPENSO", "SECADOR_MECANICO", "MISTO"];
const STATUS_FLOW = ["RECEBIMENTO", "SECAGEM", "CLASSIFICACAO", "ARMAZENADO", "VENDIDO"];

const STATUS_COLOR: Record<string, string> = {
    RECEBIMENTO: "bg-blue-100 text-blue-700",
    SECAGEM: "bg-amber-100 text-amber-700",
    CLASSIFICACAO: "bg-purple-100 text-purple-700",
    ARMAZENADO: "bg-green-100 text-green-700",
    VENDIDO: "bg-gray-100 text-gray-700",
};

const METODO_COLOR: Record<string, string> = {
    NATURAL: "bg-orange-100 text-orange-700",
    LAVADO: "bg-cyan-100 text-cyan-700",
    HONEY: "bg-yellow-100 text-yellow-700",
    DESCASCADO: "bg-rose-100 text-rose-700",
    GENERICO: "bg-slate-100 text-slate-700",
};

function fmt(n: number | null | undefined, dec = 1) {
    if (n == null) return "—";
    return n.toLocaleString("pt-BR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

export function BeneficiamentoCafe({ safraId, talhoes }: Props) {
    const qc = useQueryClient();
    const [openNew, setOpenNew] = useState(false);
    const [editId, setEditId] = useState<string | null>(null);
    const hasProfessionalTier = useHasTier("PROFISSIONAL");

    const [ehCafe, setEhCafe] = useState(true);
    const [form, setForm] = useState({
        numero_lote: "", metodo: "NATURAL", data_entrada: new Date().toISOString().slice(0, 10),
        peso_entrada_kg: "", umidade_entrada_pct: "", talhao_id: "", local_secagem: "",
        fator_esperado_manual: "",
    });

    const [editForm, setEditForm] = useState<Record<string, string>>({});

    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.beneficiamento",
        surface: "agricola.beneficiamento.panel",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });

    const { data: lotes = [], isLoading } = useQuery<Lote[]>({
        queryKey: ["beneficiamento", safraId],
        queryFn: () => apiFetch(`/beneficiamento?safra_id=${safraId}`),
        enabled: hasProfessionalTier,
    });

    const { data: kpis } = useQuery<KPIs>({
        queryKey: ["beneficiamento-kpis", safraId],
        queryFn: () => apiFetch(`/beneficiamento/kpis?safra_id=${safraId}`),
        enabled: hasProfessionalTier,
    });

    const { data: relatorio } = useQuery<RelatorioRendimento>({
        queryKey: ["beneficiamento-relatorio", safraId],
        queryFn: () => apiFetch(`/beneficiamento/relatorio-rendimento?safra_id=${safraId}`),
        enabled: hasProfessionalTier,
    });

    const talhaoMap = Object.fromEntries(talhoes.map(t => [t.id, t.nome]));

    const criar = useMutation({
        mutationFn: (body: object) =>
            apiFetch("/beneficiamento/", { method: "POST", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Lote criado.");
            qc.invalidateQueries({ queryKey: ["beneficiamento", safraId] });
            qc.invalidateQueries({ queryKey: ["beneficiamento-kpis", safraId] });
            setOpenNew(false);
        },
        onError: () => toast.error("Erro ao criar lote."),
    });

    const atualizar = useMutation({
        mutationFn: ({ id, body }: { id: string; body: object }) =>
            apiFetch(`/beneficiamento/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Lote atualizado.");
            qc.invalidateQueries({ queryKey: ["beneficiamento", safraId] });
            qc.invalidateQueries({ queryKey: ["beneficiamento-kpis", safraId] });
            setEditId(null);
        },
        onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao atualizar."),
    });

    const gerarVenda = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/beneficiamento/${id}/gerar-venda`, { method: "POST" }),
        onSuccess: (data: BeneficiamentoMutacaoResult) => {
            toast.success(`Venda criada! Contrato: ${data.numero_contrato || data.id}`);
            qc.invalidateQueries({ queryKey: ["beneficiamento", safraId] });
            qc.invalidateQueries({ queryKey: ["beneficiamento-kpis", safraId] });
        },
        onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao gerar venda."),
    });

    const armazenar = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/beneficiamento/${id}/armazenar`, { method: "POST" }),
        onSuccess: (data: BeneficiamentoMutacaoResult) => {
            toast.success(`Lote enviado ao estoque! SKU: ${data.lote_estoque_id?.slice(0, 8) ?? "—"}`);
            qc.invalidateQueries({ queryKey: ["beneficiamento", safraId] });
            qc.invalidateQueries({ queryKey: ["beneficiamento-kpis", safraId] });
        },
        onError: (e: unknown) => toast.error(e instanceof Error ? e.message : "Erro ao armazenar."),
    });

    if (!hasProfessionalTier) {
        return (
            <Alert className="rounded-sm">
                <Lock className="size-4" />
                <AlertTitle>Beneficiamento avançado disponível no PROFISSIONAL</AlertTitle>
                <AlertDescription className="space-y-3">
                    <p>O plano atual mantém a operação de safra. Lotes de beneficiamento, KPIs e relatórios de rendimento exigem plano Profissional.</p>
                    <Button
                        asChild
                        size="sm"
                        className="rounded-sm"
                        onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                            feature: "agricola.beneficiamento",
                            surface: "agricola.beneficiamento.panel",
                            requiredTier: "PROFISSIONAL",
                            ctaLabel: "Ver planos",
                        })}
                    >
                        <Link href="/dashboard/settings/billing">Ver planos</Link>
                    </Button>
                </AlertDescription>
            </Alert>
        );
    }

    function handleCriar() {
        if (!form.numero_lote || !form.peso_entrada_kg) {
            toast.error("Número do lote e peso de entrada são obrigatórios.");
            return;
        }
        const body: Record<string, unknown> = {
            safra_id: safraId,
            numero_lote: form.numero_lote,
            data_entrada: form.data_entrada,
            peso_entrada_kg: parseFloat(form.peso_entrada_kg),
        };
        if (form.talhao_id) body.talhao_id = form.talhao_id;
        if (form.umidade_entrada_pct) body.umidade_entrada_pct = parseFloat(form.umidade_entrada_pct);
        if (ehCafe) {
            body.detalhe_cafe = {
                metodo: form.metodo,
                local_secagem: form.local_secagem || null,
            };
        } else if (form.fator_esperado_manual) {
            body.fator_esperado_manual = parseFloat(form.fator_esperado_manual);
        }
        criar.mutate(body);
    }

    function abrirEdit(lote: Lote) {
        setEditForm({
            status: lote.status,
            local_secagem: lote.detalhe_cafe?.local_secagem ?? "",
            data_saida: lote.data_saida ?? "",
            peso_saida_kg: lote.peso_saida_kg?.toString() ?? "",
            umidade_saida_pct: lote.umidade_saida_pct?.toString() ?? "",
            fator_esperado_manual: lote.fator_esperado_manual?.toString() ?? "",
            perda_secagem_kg: lote.perda_secagem_kg?.toString() ?? "",
            perda_quebra_kg: lote.perda_quebra_kg?.toString() ?? "",
            perda_defeito_kg: lote.perda_defeito_kg?.toString() ?? "",
            bebida: lote.detalhe_cafe?.bebida ?? "",
            pontuacao_scaa: lote.detalhe_cafe?.pontuacao_scaa?.toString() ?? "",
        });
        setEditId(lote.id);
    }

    function handleAtualizar() {
        if (!editId) return;
        const isCafe = !!editLote?.detalhe_cafe;
        const body: Record<string, unknown> = {};
        if (editForm.status) body.status = editForm.status;
        if (editForm.data_saida) body.data_saida = editForm.data_saida;
        if (editForm.peso_saida_kg) body.peso_saida_kg = parseFloat(editForm.peso_saida_kg);
        if (editForm.umidade_saida_pct) body.umidade_saida_pct = parseFloat(editForm.umidade_saida_pct);
        if (!isCafe && editForm.fator_esperado_manual) body.fator_esperado_manual = parseFloat(editForm.fator_esperado_manual);
        if (editForm.perda_secagem_kg) body.perda_secagem_kg = parseFloat(editForm.perda_secagem_kg);
        if (editForm.perda_quebra_kg) body.perda_quebra_kg = parseFloat(editForm.perda_quebra_kg);
        if (editForm.perda_defeito_kg) body.perda_defeito_kg = parseFloat(editForm.perda_defeito_kg);
        if (isCafe && (editForm.local_secagem || editForm.bebida || editForm.pontuacao_scaa)) {
            body.detalhe_cafe = {
                ...(editForm.local_secagem ? { local_secagem: editForm.local_secagem } : {}),
                ...(editForm.bebida ? { bebida: editForm.bebida } : {}),
                ...(editForm.pontuacao_scaa ? { pontuacao_scaa: parseFloat(editForm.pontuacao_scaa) } : {}),
            };
        }
        atualizar.mutate({ id: editId, body });
    }

    const editLote = lotes.find(l => l.id === editId);
    const editIsCafe = !!editLote?.detalhe_cafe;

    return (
        <div className="space-y-6">
            {/* KPIs */}
            {kpis && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <Card><CardContent className="pt-4">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><Package className="size-3.5" /> Lotes</div>
                        <p className="text-2xl font-bold">{kpis.total_lotes}</p>
                        <p className="text-xs text-muted-foreground">{kpis.lotes_em_processo} em processo · {kpis.lotes_concluidos} concluídos</p>
                    </CardContent></Card>
                    <Card><CardContent className="pt-4">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><Layers className="size-3.5" /> Sacas Beneficiadas</div>
                        <p className="text-2xl font-bold">{fmt(kpis.sacas_beneficiadas_total, 0)}</p>
                        <p className="text-xs text-muted-foreground">{fmt(kpis.peso_saida_total_kg, 0)} kg beneficiado</p>
                    </CardContent></Card>
                    <Card><CardContent className="pt-4">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><TrendingDown className="size-3.5" /> Fator Redução</div>
                        <p className="text-2xl font-bold">{kpis.fator_reducao_medio ? `${fmt(kpis.fator_reducao_medio)}:1` : "—"}</p>
                        <p className="text-xs text-muted-foreground">{fmt(kpis.peso_entrada_total_kg, 0)} kg entrada</p>
                    </CardContent></Card>
                    <Card><CardContent className="pt-4">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1"><Star className="size-3.5" /> Pontuação SCA</div>
                        <p className="text-2xl font-bold">{kpis.pontuacao_media_scaa ? fmt(kpis.pontuacao_media_scaa) : "—"}</p>
                        <p className="text-xs text-muted-foreground">{kpis.pontuacao_media_scaa && kpis.pontuacao_media_scaa >= 80 ? "Specialty ✓" : "Só lotes de café"}</p>
                    </CardContent></Card>
                </div>
            )}

            {/* Relatório de Rendimento */}
            {relatorio && relatorio.por_metodo.length > 0 && (
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-4">
                            <BarChart3 className="size-4 text-muted-foreground" />
                            <h3 className="font-semibold text-sm">Relatório de Rendimento por Método</h3>
                        </div>
                        <div className="rounded-md border overflow-x-auto">
                            <Table className="text-xs">
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="h-8">Método</TableHead>
                                        <TableHead className="h-8 text-right">Lotes</TableHead>
                                        <TableHead className="h-8 text-right">Entrada (kg)</TableHead>
                                        <TableHead className="h-8 text-right">Saída (kg)</TableHead>
                                        <TableHead className="h-8 text-right">Fator Real</TableHead>
                                        <TableHead className="h-8 text-right">Fator Esp.</TableHead>
                                        <TableHead className="h-8 text-right">Eficiência</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {relatorio.por_metodo.map(m => {
                                        const eff = m.eficiencia_pct;
                                        const effColor = eff >= 95 ? "bg-green-50" : eff >= 80 ? "bg-amber-50" : "bg-red-50";
                                        return (
                                            <TableRow key={m.metodo} className={effColor}>
                                                <TableCell className="font-medium">
                                                    <Badge className={cn("text-xs border-0", METODO_COLOR[m.metodo] ?? "bg-muted")}>
                                                        {m.metodo === "GENERICO" ? "Genérico" : m.metodo}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-right">{m.total_lotes}</TableCell>
                                                <TableCell className="text-right">{fmt(m.peso_entrada_kg, 0)}</TableCell>
                                                <TableCell className="text-right">{fmt(m.peso_saida_kg, 0)}</TableCell>
                                                <TableCell className="text-right">{m.fator_reducao_real ? `${fmt(m.fator_reducao_real)}:1` : "—"}</TableCell>
                                                <TableCell className="text-right">{m.fator_reducao_esperado}:1</TableCell>
                                                <TableCell className="text-right">
                                                    <Badge className={cn("text-xs", eff >= 95 ? "bg-green-100 text-green-700" : eff >= 80 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700")}>
                                                        {fmt(eff)}%
                                                    </Badge>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Rendimento geral: <strong>{fmt(relatorio.rendimento_medio_pct)}%</strong> ·
                            {fmt(relatorio.peso_entrada_total_kg, 0)} kg entrada → {fmt(relatorio.peso_saida_total_kg, 0)} kg saída
                        </p>
                    </CardContent>
                </Card>
            )}

            <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm">Lotes de Beneficiamento</h3>
                <Button size="sm" onClick={() => setOpenNew(true)}>
                    <Plus className="size-4 mr-1" /> Novo Lote
                </Button>
            </div>

            {isLoading ? <Skeleton className="h-32 w-full" /> : lotes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">Nenhum lote registrado.</p>
            ) : (
                <div className="rounded-md border overflow-x-auto">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Lote</TableHead>
                                <TableHead>Método</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Talhão</TableHead>
                                <TableHead className="text-right">Entrada (kg)</TableHead>
                                <TableHead className="text-right">Saída (kg)</TableHead>
                                <TableHead className="text-right">Sacas</TableHead>
                                <TableHead className="text-right">Fator</TableHead>
                                <TableHead className="text-right">SCA</TableHead>
                                <TableHead />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {lotes.map(l => (
                                <TableRow key={l.id}>
                                    <TableCell className="font-medium text-sm">{l.numero_lote}</TableCell>
                                    <TableCell>
                                        {l.detalhe_cafe ? (
                                            <Badge className={cn("text-xs border-0", METODO_COLOR[l.detalhe_cafe.metodo] ?? "bg-muted")}>{l.detalhe_cafe.metodo}</Badge>
                                        ) : (
                                            <Badge className={cn("text-xs border-0", METODO_COLOR.GENERICO)}>Genérico</Badge>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        <Badge className={cn("text-xs border-0", STATUS_COLOR[l.status] ?? "bg-muted")}>{l.status}</Badge>
                                    </TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {l.talhao_id ? (talhaoMap[l.talhao_id] ?? l.talhao_id.slice(0, 8)) : "—"}
                                    </TableCell>
                                    <TableCell className="text-right text-sm">{fmt(l.peso_entrada_kg, 0)}</TableCell>
                                    <TableCell className="text-right text-sm">{l.peso_saida_kg ? fmt(l.peso_saida_kg, 0) : "—"}</TableCell>
                                    <TableCell className="text-right text-sm font-medium">
                                        {l.sacas_beneficiadas ? fmt(l.sacas_beneficiadas) : "—"}
                                    </TableCell>
                                    <TableCell className="text-right text-sm">
                                        {l.fator_reducao ? `${fmt(l.fator_reducao)}:1` : "—"}
                                    </TableCell>
                                    <TableCell className="text-right text-sm">
                                        {l.detalhe_cafe?.pontuacao_scaa ? (
                                            <span className={cn(l.detalhe_cafe.pontuacao_scaa >= 80 ? "text-green-600 font-semibold" : "")}>
                                                {fmt(l.detalhe_cafe.pontuacao_scaa)}
                                            </span>
                                        ) : "—"}
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex gap-1 items-center justify-end">
                                            {l.status === "ARMAZENADO" && !l.lote_estoque_id && (
                                                <Button variant="ghost" size="icon" className="size-7 text-amber-600"
                                                    onClick={() => armazenar.mutate(l.id)} disabled={armazenar.isPending}
                                                    title="Armazenar em estoque">
                                                    <Archive className="size-3.5" />
                                                </Button>
                                            )}
                                            {l.status === "ARMAZENADO" && l.lote_estoque_id && (
                                                <Button variant="ghost" size="icon" className="size-7 text-green-600"
                                                    onClick={() => gerarVenda.mutate(l.id)} disabled={gerarVenda.isPending}
                                                    title="Gerar venda">
                                                    <ShoppingCart className="size-3.5" />
                                                </Button>
                                            )}
                                            <Button variant="ghost" size="icon" className="size-7" onClick={() => abrirEdit(l)}>
                                                <Pencil className="size-3.5" />
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}

            {/* Modal: Novo Lote */}
            <Dialog open={openNew} onOpenChange={setOpenNew}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Novo Lote de Beneficiamento</DialogTitle>
                    </DialogHeader>
                    <div className="grid max-h-[65vh] gap-4 overflow-y-auto px-6 pb-2 md:grid-cols-2">
                        <div className="space-y-2 md:col-span-2">
                            <Label>Número do Lote *</Label>
                            <Input placeholder="ex: LOT-001"
                                value={form.numero_lote} onChange={e => setForm(p => ({ ...p, numero_lote: e.target.value }))} />
                        </div>
                        <div className="flex items-center justify-between rounded-sm border px-3 py-2 md:col-span-2">
                            <Label>Lote de café?</Label>
                            <Switch checked={ehCafe} onCheckedChange={setEhCafe} />
                        </div>
                        {ehCafe ? (
                            <>
                                <div className="space-y-2">
                                    <Label>Método *</Label>
                                    <Select value={form.metodo} onValueChange={(value) => setForm(p => ({ ...p, metodo: value }))}>
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {METODOS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Local de Secagem</Label>
                                    <Select value={form.local_secagem ?? ""} onValueChange={(value) => setForm(p => ({ ...p, local_secagem: value }))}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="— não definido —" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {LOCAIS.map(l => <SelectItem key={l} value={l}>{l.replace(/_/g, " ")}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </>
                        ) : (
                            <div className="space-y-2 md:col-span-2">
                                <Label>Fator entrada/saída esperado</Label>
                                <Input type="number" step="0.01" placeholder="ex: 1.1 (opcional, usado para calcular perda)"
                                    value={form.fator_esperado_manual} onChange={e => setForm(p => ({ ...p, fator_esperado_manual: e.target.value }))} />
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label>Data Entrada *</Label>
                            <Input type="date"
                                value={form.data_entrada} onChange={e => setForm(p => ({ ...p, data_entrada: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Peso Entrada (kg) *</Label>
                            <Input type="number" placeholder="kg"
                                value={form.peso_entrada_kg} onChange={e => setForm(p => ({ ...p, peso_entrada_kg: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Umidade Entrada (%)</Label>
                            <Input type="number" step="0.1" placeholder="ex: 55"
                                value={form.umidade_entrada_pct} onChange={e => setForm(p => ({ ...p, umidade_entrada_pct: e.target.value }))} />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                            <Label>Talhão</Label>
                            <Select value={form.talhao_id} onValueChange={(value) => setForm(p => ({ ...p, talhao_id: value }))}>
                                <SelectTrigger>
                                    <SelectValue placeholder="— nenhum —" />
                                </SelectTrigger>
                                <SelectContent>
                                    {talhoes.map(t => <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={() => setOpenNew(false)}>Cancelar</Button>
                        <Button onClick={handleCriar} disabled={criar.isPending}>
                            {criar.isPending ? "Salvando…" : "Registrar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Modal: Atualizar Lote */}
            <Dialog open={!!editId} onOpenChange={v => !v && setEditId(null)}>
                <DialogContent className="max-w-xl">
                    <DialogHeader className="border-b">
                        <DialogTitle>Atualizar Lote {editLote?.numero_lote}</DialogTitle>
                    </DialogHeader>
                    <div className="grid max-h-[65vh] gap-4 overflow-y-auto px-6 pb-2 md:grid-cols-2">
                        <div className="space-y-2 md:col-span-2">
                            <Label>Status</Label>
                            <Select value={editForm.status ?? ""} onValueChange={(value) => setEditForm(p => ({ ...p, status: value }))}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {STATUS_FLOW.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Peso Saída (kg)</Label>
                            <Input type="number" placeholder="kg beneficiado"
                                value={editForm.peso_saida_kg ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, peso_saida_kg: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Umidade Saída (%)</Label>
                            <Input type="number" step="0.1" placeholder="ex: 12"
                                value={editForm.umidade_saida_pct ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, umidade_saida_pct: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Data Saída</Label>
                            <Input type="date"
                                value={editForm.data_saida ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, data_saida: e.target.value }))} />
                        </div>
                        {!editIsCafe && (
                            <div className="space-y-2">
                                <Label>Fator esperado</Label>
                                <Input type="number" step="0.01" placeholder="ex: 1.1"
                                    value={editForm.fator_esperado_manual ?? ""}
                                    onChange={e => setEditForm(p => ({ ...p, fator_esperado_manual: e.target.value }))} />
                            </div>
                        )}
                        <div className="md:col-span-2">
                            <p className="text-xs font-semibold text-muted-foreground">Perdas Detalhadas (kg)</p>
                        </div>
                        <div className="space-y-2">
                            <Label>Perda Secagem</Label>
                            <Input type="number" placeholder="kg"
                                value={editForm.perda_secagem_kg ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, perda_secagem_kg: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Perda Quebra</Label>
                            <Input type="number" placeholder="kg"
                                value={editForm.perda_quebra_kg ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, perda_quebra_kg: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Perda Defeito</Label>
                            <Input type="number" placeholder="kg"
                                value={editForm.perda_defeito_kg ?? ""}
                                onChange={e => setEditForm(p => ({ ...p, perda_defeito_kg: e.target.value }))} />
                        </div>
                        {editIsCafe && (
                            <>
                                <div className="space-y-2">
                                    <Label>Bebida (ABIC)</Label>
                                    <Input placeholder="ex: MOLE"
                                        value={editForm.bebida ?? ""}
                                        onChange={e => setEditForm(p => ({ ...p, bebida: e.target.value }))} />
                                </div>
                                <div className="space-y-2 md:col-span-2">
                                    <Label>Pontuação SCA (0–100)</Label>
                                    <Input type="number" step="0.25" placeholder="≥ 80 = specialty"
                                        value={editForm.pontuacao_scaa ?? ""}
                                        onChange={e => setEditForm(p => ({ ...p, pontuacao_scaa: e.target.value }))} />
                                </div>
                            </>
                        )}
                        {editForm.peso_saida_kg && editLote && (
                            <p className="text-xs text-muted-foreground md:col-span-2">
                                Fator estimado: {(editLote.peso_entrada_kg / parseFloat(editForm.peso_saida_kg)).toFixed(2)}:1 ·{" "}
                                {(parseFloat(editForm.peso_saida_kg) / 60).toFixed(1)} sacas
                            </p>
                        )}
                    </div>
                    <DialogFooter className="border-t px-6 pb-6 pt-4">
                        <Button variant="outline" onClick={() => setEditId(null)}>Cancelar</Button>
                        <Button onClick={handleAtualizar} disabled={atualizar.isPending}>
                            {atualizar.isPending ? "Salvando…" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
