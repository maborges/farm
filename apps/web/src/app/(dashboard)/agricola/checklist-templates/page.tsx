"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Pencil, Trash2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface Template {
    id: string;
    cultura: string | null;
    fase: string;
    titulo: string;
    obrigatorio: boolean;
    is_system: boolean;
    ativo: boolean;
}

const FASES = [
    { key: "PLANEJADA", label: "Planejamento" },
    { key: "PREPARO_SOLO", label: "Preparo Solo" },
    { key: "PLANTIO", label: "Plantio" },
    { key: "DESENVOLVIMENTO", label: "Desenvolvimento" },
    { key: "COLHEITA", label: "Colheita" },
    { key: "POS_COLHEITA", label: "Pós-Colheita" },
];

const FASE_LABEL: Record<string, string> = Object.fromEntries(FASES.map(f => [f.key, f.label]));
const FASE_COR: Record<string, string> = {
    PLANEJADA: "bg-blue-100 text-blue-700",
    PREPARO_SOLO: "bg-amber-100 text-amber-700",
    PLANTIO: "bg-lime-100 text-lime-700",
    DESENVOLVIMENTO: "bg-emerald-100 text-emerald-700",
    COLHEITA: "bg-orange-100 text-orange-700",
    POS_COLHEITA: "bg-purple-100 text-purple-700",
};

const CULTURAS = ["SOJA", "MILHO", "TRIGO", "ALGODAO", "FEIJAO", "ARROZ", "CANA"];

export default function ChecklistTemplatesPage() {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [editando, setEditando] = useState<Template | null>(null);
    const [filtroFase, setFiltroFase] = useState("TODAS");
    const [filtroCultura, setFiltroCultura] = useState("TODAS");

    const [form, setForm] = useState({ titulo: "", fase: "", cultura: "", obrigatorio: false });

    const { data: templates = [], isLoading } = useQuery<Template[]>({
        queryKey: ["checklist-templates"],
        queryFn: () => apiFetch("/checklist/templates"),
    });

    const createMutation = useMutation({
        mutationFn: (body: object) =>
            apiFetch("/checklist/templates", { method: "POST", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Template criado.");
            qc.invalidateQueries({ queryKey: ["checklist-templates"] });
            handleClose();
        },
        onError: () => toast.error("Erro ao criar template."),
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, body }: { id: string; body: object }) =>
            apiFetch(`/checklist/templates/${id}`, { method: "PUT", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Template atualizado.");
            qc.invalidateQueries({ queryKey: ["checklist-templates"] });
            handleClose();
        },
        onError: () => toast.error("Erro ao atualizar template."),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/checklist/templates/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Template desativado.");
            qc.invalidateQueries({ queryKey: ["checklist-templates"] });
        },
    });

    function handleClose() {
        setOpen(false);
        setEditando(null);
        setForm({ titulo: "", fase: "", cultura: "", obrigatorio: false });
    }

    function handleEditar(t: Template) {
        setEditando(t);
        setForm({ titulo: t.titulo, fase: t.fase, cultura: t.cultura ?? "", obrigatorio: t.obrigatorio });
        setOpen(true);
    }

    function handleSalvar() {
        if (!form.titulo || !form.fase) {
            toast.error("Preencha título e fase.");
            return;
        }
        const body = {
            titulo: form.titulo,
            fase: form.fase,
            cultura: form.cultura || null,
            obrigatorio: form.obrigatorio,
        };
        if (editando) {
            updateMutation.mutate({ id: editando.id, body });
        } else {
            createMutation.mutate(body);
        }
    }

    const filtered = templates.filter(t => {
        if (!t.ativo) return false;
        if (filtroFase !== "TODAS" && t.fase !== filtroFase) return false;
        if (filtroCultura !== "TODAS" && t.cultura !== filtroCultura && t.cultura !== null) return false;
        return true;
    });

    // Agrupar por fase
    const porFase: Record<string, Template[]> = {};
    for (const t of filtered) {
        porFase[t.fase] = [...(porFase[t.fase] ?? []), t];
    }

    return (
        <div className="flex-1 flex flex-col gap-6 w-full max-w-screen-xl mx-auto px-4 md:px-8 py-8">
            <PageHeader
                title="Templates de Checklist"
                description="Configure atividades padrão por fase do ciclo agrícola. Os templates são copiados automaticamente ao avançar a safra de fase."
                breadcrumbs={[
                    { label: "Agrícola", href: "/agricola" },
                    { label: "Templates de Checklist" },
                ]}
                actions={
                    <Button size="sm" onClick={() => setOpen(true)}>
                        <Plus className="size-3.5 mr-1.5" /> Novo Template
                    </Button>
                }
            />

            {/* Filtros */}
            <div className="flex gap-2 flex-wrap">
                <Select value={filtroFase} onValueChange={setFiltroFase}>
                    <SelectTrigger className="w-44 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="TODAS">Todas as fases</SelectItem>
                        {FASES.map(f => <SelectItem key={f.key} value={f.key}>{f.label}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Select value={filtroCultura} onValueChange={setFiltroCultura}>
                    <SelectTrigger className="w-40 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="TODAS">Todas as culturas</SelectItem>
                        {CULTURAS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Badge variant="secondary" className="h-8 px-3 flex items-center">
                    {filtered.length} template{filtered.length !== 1 ? "s" : ""}
                </Badge>
            </div>

            {isLoading ? (
                <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-16" />)}</div>
            ) : filtered.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground text-sm">
                    Nenhum template encontrado. Crie o primeiro para começar.
                </div>
            ) : (
                <div className="space-y-4">
                    {FASES.filter(f => porFase[f.key]?.length > 0).map(fase => (
                        <Card key={fase.key} className="shadow-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm flex items-center gap-2">
                                    <Badge className={cn("text-xs", FASE_COR[fase.key])}>
                                        {fase.label}
                                    </Badge>
                                    <span className="text-muted-foreground font-normal">
                                        {porFase[fase.key].length} template{porFase[fase.key].length !== 1 ? "s" : ""}
                                    </span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0 space-y-1.5">
                                {porFase[fase.key].map(t => (
                                    <div
                                        key={t.id}
                                        className="flex items-center gap-3 px-3 py-2 rounded-lg border hover:bg-muted/40 text-sm group"
                                    >
                                        {t.obrigatorio && (
                                            <ShieldAlert className="size-3.5 text-red-500 shrink-0" />
                                        )}
                                        <span className="flex-1 truncate">{t.titulo}</span>
                                        {t.cultura && (
                                            <Badge variant="outline" className="text-xs shrink-0">{t.cultura}</Badge>
                                        )}
                                        {t.obrigatorio && (
                                            <Badge className="bg-red-100 text-red-700 border-red-200 text-xs shrink-0">Obrigatório</Badge>
                                        )}
                                        {t.is_system && (
                                            <Badge variant="secondary" className="text-xs shrink-0">System</Badge>
                                        )}
                                        {!t.is_system && (
                                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                                                <Button variant="ghost" size="icon" className="size-7" onClick={() => handleEditar(t)}>
                                                    <Pencil className="size-3.5" />
                                                </Button>
                                                <Button
                                                    variant="ghost" size="icon"
                                                    className="size-7 text-destructive hover:text-destructive"
                                                    onClick={() => deleteMutation.mutate(t.id)}
                                                >
                                                    <Trash2 className="size-3.5" />
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Dialog criar/editar */}
            <Dialog open={open} onOpenChange={o => { if (!o) handleClose(); else setOpen(true); }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>{editando ? "Editar Template" : "Novo Template"}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div>
                            <Label className="text-xs">Fase *</Label>
                            <Select value={form.fase} onValueChange={v => setForm(f => ({ ...f, fase: v }))}>
                                <SelectTrigger className="mt-1">
                                    <SelectValue placeholder="Selecione a fase" />
                                </SelectTrigger>
                                <SelectContent>
                                    {FASES.map(f => <SelectItem key={f.key} value={f.key}>{f.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Título da atividade *</Label>
                            <Input
                                className="mt-1"
                                placeholder="Ex: Verificar pH do solo"
                                value={form.titulo}
                                onChange={e => setForm(f => ({ ...f, titulo: e.target.value }))}
                            />
                        </div>
                        <div>
                            <Label className="text-xs">Cultura (deixe vazio para todas)</Label>
                            <Select value={form.cultura} onValueChange={v => setForm(f => ({ ...f, cultura: v === "_todas" ? "" : v }))}>
                                <SelectTrigger className="mt-1">
                                    <SelectValue placeholder="Todas as culturas" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="_todas">Todas as culturas</SelectItem>
                                    {CULTURAS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-center justify-between px-1">
                            <div>
                                <p className="text-sm font-medium">Atividade obrigatória</p>
                                <p className="text-xs text-muted-foreground">Bloqueia o avanço de fase se não concluída</p>
                            </div>
                            <Switch
                                checked={form.obrigatorio}
                                onCheckedChange={v => setForm(f => ({ ...f, obrigatorio: v }))}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={handleClose}>Cancelar</Button>
                        <Button onClick={handleSalvar} disabled={createMutation.isPending || updateMutation.isPending}>
                            {createMutation.isPending || updateMutation.isPending ? "Salvando…" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
