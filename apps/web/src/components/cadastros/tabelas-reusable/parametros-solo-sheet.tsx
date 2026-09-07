"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, Pencil, FlaskConical, Save } from "lucide-react";

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

interface Cultura {
    id: string;
    nome: string;
    sistema: boolean;
}

interface SoloParam {
    id: string;
    cultura_id: string;
    tenant_id: string | null;
    regiao: string | null;
    parametro: string;
    faixa_min: number;
    faixa_max: number | null;
    classificacao: string;
    rec_dose_kg_ha: number | null;
    obs: string | null;
}

const PARAMETROS = [
    { value: "FOSFORO",   label: "Fósforo (P₂O₅)" },
    { value: "POTASSIO",  label: "Potássio (K₂O)" },
    { value: "PH",        label: "pH" },
    { value: "NITROGENIO",label: "Nitrogênio (N)" },
    { value: "CALCARIO",  label: "Calagem" },
];

const CLASSIFICACOES = [
    { value: "MUITO_BAIXO", label: "Muito Baixo" },
    { value: "BAIXO",       label: "Baixo" },
    { value: "MEDIO",       label: "Médio" },
    { value: "ALTO",        label: "Alto" },
    { value: "MUITO_ALTO",  label: "Muito Alto" },
    { value: "PADRAO",      label: "Padrão (único)" },
];

const REGIOES = [
    { value: "",        label: "Sistema (padrão)" },
    { value: "CERRADO", label: "Cerrado" },
    { value: "SUL",     label: "Sul" },
    { value: "NORDESTE",label: "Nordeste" },
    { value: "SUDESTE", label: "Sudeste" },
    { value: "NORTE",   label: "Norte" },
];

const NIVEL_COLORS: Record<string, string> = {
    MUITO_BAIXO: "bg-red-100 text-red-700",
    BAIXO:       "bg-orange-100 text-orange-700",
    MEDIO:       "bg-amber-100 text-amber-700",
    ALTO:        "bg-blue-100 text-blue-700",
    MUITO_ALTO:  "bg-purple-100 text-purple-700",
    PADRAO:      "bg-muted text-muted-foreground",
};

const PARAM_LABELS: Record<string, string> = {
    FOSFORO:    "Fósforo",
    POTASSIO:   "Potássio",
    PH:         "pH",
    NITROGENIO: "Nitrogênio",
    CALCARIO:   "Calagem",
};

const EMPTY_FORM = {
    parametro: "FOSFORO",
    regiao: "",
    faixa_min: 0,
    faixa_max: "" as number | "",
    classificacao: "BAIXO",
    rec_dose_kg_ha: "" as number | "",
    obs: "",
};

interface Props {
    cultura: Cultura | null;
    open: boolean;
    onClose: () => void;
    isBackoffice?: boolean;
}

export function ParametrosSoloSheet({ cultura, open, onClose, isBackoffice = false }: Props) {
    const qc = useQueryClient();
    const [editingId, setEditingId] = useState<string | null>(null);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({ ...EMPTY_FORM });
    const [regiaoFiltro, setRegiaoFiltro] = useState<string>("");

    const baseUrl = isBackoffice ? "/backoffice/tabelas/culturas" : "/cadastros/culturas";

    const { data: params = [], isLoading } = useQuery<SoloParam[]>({
        queryKey: ["solo-params", cultura?.id, isBackoffice],
        queryFn: () => apiFetch(`${baseUrl}/${cultura!.id}/parametros-solo`),
        enabled: !!cultura?.id && open,
    });

    const createMut = useMutation({
        mutationFn: (data: any) =>
            apiFetch(`${baseUrl}/${cultura!.id}/parametros-solo`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["solo-params", cultura?.id, isBackoffice] });
            qc.invalidateQueries({ queryKey: ["culturas-disponiveis-solo"] });
            toast.success("Parâmetro criado");
            resetForm();
        },
        onError: () => toast.error("Erro ao criar parâmetro"),
    });

    // Pré-preenche o form com valores do sistema para o parâmetro selecionado
    function preencherComPadrao(parametro: string) {
        const padrao = params.find(p => p.tenant_id === null && p.parametro === parametro);
        if (padrao) {
            setForm(f => ({
                ...f,
                parametro,
                faixa_min: padrao.faixa_min,
                faixa_max: padrao.faixa_max ?? "",
                classificacao: padrao.classificacao,
                rec_dose_kg_ha: padrao.rec_dose_kg_ha ?? "",
                obs: padrao.obs ?? "",
            }));
        } else {
            setForm(f => ({ ...f, parametro }));
        }
    }

    const updateMut = useMutation({
        mutationFn: (data: any) =>
            apiFetch(`${baseUrl}/${cultura!.id}/parametros-solo/${editingId}`, {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["solo-params", cultura?.id, isBackoffice] });
            qc.invalidateQueries({ queryKey: ["culturas-disponiveis-solo"] });
            toast.success("Parâmetro atualizado");
            resetForm();
        },
        onError: () => toast.error("Erro ao atualizar parâmetro"),
    });

    const deleteMut = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`${baseUrl}/${cultura!.id}/parametros-solo/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["solo-params", cultura?.id, isBackoffice] });
            qc.invalidateQueries({ queryKey: ["culturas-disponiveis-solo"] });
            toast.success("Parâmetro removido");
            setDeleteId(null);
        },
        onError: () => toast.error("Erro ao remover parâmetro"),
    });

    function resetForm() {
        setForm({ ...EMPTY_FORM });
        setEditingId(null);
        setShowForm(false);
    }

    function openEdit(p: SoloParam) {
        setForm({
            parametro: p.parametro,
            regiao: p.regiao ?? "",
            faixa_min: p.faixa_min,
            faixa_max: p.faixa_max ?? "",
            classificacao: p.classificacao,
            rec_dose_kg_ha: p.rec_dose_kg_ha ?? "",
            obs: p.obs ?? "",
        });
        setEditingId(p.id);
        setShowForm(true);
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        const payload = {
            parametro: form.parametro,
            regiao: form.regiao || null,
            faixa_min: Number(form.faixa_min),
            faixa_max: form.faixa_max !== "" ? Number(form.faixa_max) : null,
            classificacao: form.classificacao,
            rec_dose_kg_ha: form.rec_dose_kg_ha !== "" ? Number(form.rec_dose_kg_ha) : null,
            obs: form.obs || null,
        };
        if (editingId) updateMut.mutate(payload);
        else createMut.mutate(payload);
    }

    // Verifica se a região selecionada tem ao menos um parâmetro customizado pelo tenant
    const regiaoTemCustom = regiaoFiltro
        ? params.some(p => p.tenant_id !== null && p.regiao === regiaoFiltro)
        : true;

    // Hierarquia: tenant+região > sistema(geral). Só aplica fallback se região tiver ao menos um custom.
    const paramsFiltrados = (() => {
        if (isBackoffice) {
            // Em backoffice, mostramos tudo conforme o filtro de região, sem lógica de override
            return params
                .filter(p => !regiaoFiltro || p.regiao === regiaoFiltro)
                .map(p => ({ ...p, _override: false } as any));
        }

        if (!regiaoFiltro) {
            // "Sistema": mostrar apenas parâmetros globais (tenant_id === null, regiao === null)
            return params
                .filter(p => p.tenant_id === null && p.regiao === null)
                .map(p => ({ ...p, _override: false } as any));
        }
        if (!regiaoTemCustom) return [];
        const resultado: SoloParam[] = [];
        const chaves = Array.from(new Set(params.map(p => `${p.parametro}|${p.faixa_min}`)));
        for (const chave of chaves) {
            const [parametro, faixa_min_str] = chave.split("|");
            const faixa_min = parseFloat(faixa_min_str);
            const tenantRegiao = params.find(p =>
                p.parametro === parametro && p.faixa_min === faixa_min &&
                p.tenant_id !== null && p.regiao === regiaoFiltro
            );
            const sistema = params.find(p =>
                p.parametro === parametro && p.faixa_min === faixa_min &&
                p.tenant_id === null && p.regiao === null
            );
            const escolhido = tenantRegiao ?? sistema;
            if (escolhido) resultado.push({ ...escolhido, _override: !!tenantRegiao } as any);
        }
        return resultado;
    })();

    // Agrupar por parâmetro
    const grupos = PARAMETROS.map(p => ({
        ...p,
        faixas: paramsFiltrados.filter(r => r.parametro === p.value),
    })).filter(g => g.faixas.length > 0);

    return (
        <>
            <Sheet open={open} onOpenChange={o => { if (!o) { setRegiaoFiltro(""); setShowForm(false); onClose(); } }}>
                <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
                    <SheetHeader className="px-5 sm:px-6 pt-6 pb-4 border-b border-border/40">
                        <div>
                            <SheetTitle className="flex items-center gap-2 text-sm">
                                <FlaskConical size={16} className="text-primary" />
                                Parâmetros de Solo — {cultura?.nome}
                            </SheetTitle>
                            <SheetDescription className="text-xs mt-1">
                                Faixas de interpretação e doses de adubação por região.
                            </SheetDescription>
                        </div>
                    </SheetHeader>

                    <div className="py-6 px-5 sm:px-6 space-y-4 pb-12">
                        {/* Seletor de região */}
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground shrink-0">Região:</span>
                            <Select
                                value={regiaoFiltro || "__sistema__"}
                                onValueChange={(v: string) => { setRegiaoFiltro(v === "__sistema__" ? "" : v); setShowForm(false); }}
                            >
                                <SelectTrigger className="h-7 text-xs rounded-sm flex-1">
                                    <SelectValue placeholder={REGIOES.find(r => r.value === regiaoFiltro)?.label ?? "Sistema (padrão)"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {REGIOES.map(r => (
                                        <SelectItem key={r.value || "__sistema__"} value={r.value || "__sistema__"} className="text-xs">
                                            {r.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Botão adicionar */}
                        {!showForm && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="w-full rounded-sm"
                                onClick={() => {
                                    const padrao = params.find(p => p.tenant_id === null && p.regiao === (regiaoFiltro || null));
                                    const fallbackPadrao = padrao ?? params.find(p => p.tenant_id === null);
                                    if (fallbackPadrao) {
                                        setForm({
                                            parametro: fallbackPadrao.parametro,
                                            regiao: regiaoFiltro,
                                            faixa_min: fallbackPadrao.faixa_min,
                                            faixa_max: fallbackPadrao.faixa_max ?? "",
                                            classificacao: fallbackPadrao.classificacao,
                                            rec_dose_kg_ha: fallbackPadrao.rec_dose_kg_ha ?? "",
                                            obs: fallbackPadrao.obs ?? "",
                                        });
                                    } else {
                                        setForm({ ...EMPTY_FORM, regiao: regiaoFiltro });
                                    }
                                    setShowForm(true);
                                }}
                            >
                                <Plus className="mr-1.5 size-3.5" /> Adicionar Parâmetro Personalizado
                            </Button>
                        )}

                        {/* Formulário */}
                        {showForm && (
                            <form onSubmit={handleSubmit} className="border border-border/40 rounded-sm p-4 space-y-3 bg-muted/20">
                                <div className="flex items-center justify-between">
                                    <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">
                                        {editingId ? "Editar Parâmetro" : "Novo Parâmetro"}
                                    </p>
                                    {!editingId && (
                                        <span className="text-[9px] text-muted-foreground italic">
                                            Valores pré-preenchidos com o padrão do sistema — ajuste conforme sua região
                                        </span>
                                    )}
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Nutriente *</label>
                                        <Select value={form.parametro} onValueChange={preencherComPadrao}>
                                            <SelectTrigger><SelectValue placeholder={form.parametro ? PARAMETROS.find(p => p.value === form.parametro)?.label || "Selecione..." : "Selecione..."} /></SelectTrigger>
                                            <SelectContent>
                                                {PARAMETROS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Região</label>
                                        <Select value={form.regiao} onValueChange={(v: string) => setForm(f => ({ ...f, regiao: v }))}>
                                            <SelectTrigger><SelectValue placeholder={form.regiao ? REGIOES.find(r => r.value === form.regiao)?.label || "Geral" : "Geral"} /></SelectTrigger>
                                            <SelectContent>
                                                {REGIOES.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Faixa Mín *</label>
                                        <Input type="number" step="0.01"
                                            value={form.faixa_min}
                                            onChange={e => setForm(f => ({ ...f, faixa_min: Number(e.target.value) }))}
                                            required />
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Faixa Máx</label>
                                        <Input type="number" step="0.01"
                                            placeholder="vazio = sem limite"
                                            value={form.faixa_max}
                                            onChange={e => setForm(f => ({ ...f, faixa_max: e.target.value === "" ? "" : Number(e.target.value) }))} />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Classificação *</label>
                                        <Select value={form.classificacao} onValueChange={(v: string) => setForm(f => ({ ...f, classificacao: v }))}>
                                            <SelectTrigger><SelectValue placeholder={form.classificacao ? CLASSIFICACOES.find(c => c.value === form.classificacao)?.label || "Selecione..." : "Selecione..."} /></SelectTrigger>
                                            <SelectContent>
                                                {CLASSIFICACOES.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-xs font-medium">Dose (kg/ha)</label>
                                        <Input type="number" step="0.1"
                                            placeholder="Ex: 100"
                                            value={form.rec_dose_kg_ha}
                                            onChange={e => setForm(f => ({ ...f, rec_dose_kg_ha: e.target.value === "" ? "" : Number(e.target.value) }))} />
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-medium">Observação técnica</label>
                                    <Input
                                        placeholder="Ex: Aplicar parcelado em 2x..."
                                        value={form.obs}
                                        onChange={e => setForm(f => ({ ...f, obs: e.target.value }))} />
                                </div>

                                <div className="flex gap-2 justify-end pt-1">
                                    <Button type="button" variant="outline" size="sm" className="rounded-sm text-xs" onClick={resetForm}>
                                        Cancelar
                                    </Button>
                                    <Button type="submit" variant="outline" size="sm" className="rounded-sm text-xs"
                                        disabled={createMut.isPending || updateMut.isPending}>
                                        <Save className="mr-1.5 size-3" />
                                        {editingId ? "Atualizar" : "Salvar"}
                                    </Button>
                                </div>
                            </form>
                        )}

                        {/* Lista agrupada por parâmetro */}
                        {isLoading ? (
                            <div className="space-y-2">
                                <Skeleton className="h-16 w-full rounded-sm" />
                                <Skeleton className="h-16 w-full rounded-sm" />
                            </div>
                        ) : grupos.length === 0 ? (
                            <div className="text-center py-8 text-xs text-muted-foreground">
                                {regiaoFiltro && !regiaoTemCustom
                                    ? `Nenhum parâmetro personalizado para a região "${regiaoFiltro}".`
                                    : "Nenhum parâmetro cadastrado ainda."}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {grupos.map(grupo => (
                                    <div key={grupo.value}>
                                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest mb-2">
                                            {grupo.label}
                                        </p>
                                        <div className="space-y-1.5">
                                            {grupo.faixas.map(p => {
                                                const isOverride = (p as any)._override === true;
                                                const isSystem = regiaoFiltro
                                                    ? !isOverride
                                                    : p.tenant_id === null;
                                                return (
                                                    <div key={p.id}
                                                        className={`flex items-center justify-between p-2 rounded-sm border text-xs ${isSystem ? "bg-muted/30 border-border/30 opacity-70" : "bg-background border-border/40"}`}>
                                                        <div className="flex items-center gap-2 flex-1 min-w-0">
                                                            <Badge className={`${NIVEL_COLORS[p.classificacao] ?? "bg-muted"}`}>
                                                                {p.classificacao.replace("_", " ")}
                                                            </Badge>
                                                            <span className="font-mono text-[10px] shrink-0">
                                                                {p.faixa_min} – {p.faixa_max ?? "∞"}
                                                            </span>
                                                            {p.rec_dose_kg_ha && (
                                                                <span className="text-primary font-bold shrink-0">{p.rec_dose_kg_ha} kg/ha</span>
                                                            )}
                                                            {isOverride && regiaoFiltro && (
                                                                <Badge variant="default">personalizado</Badge>
                                                            )}
                                                            {isSystem && regiaoFiltro && (
                                                                <Badge variant="secondary">padrão sistema</Badge>
                                                            )}
                                                            {!regiaoFiltro && p.tenant_id === null && (
                                                                <Badge variant="secondary">sistema</Badge>
                                                            )}
                                                            {!isSystem && !isBackoffice && (
                                                                <div className="flex items-center gap-0 shrink-0">
                                                                    <Button size="icon" variant="ghost" className="size-6 text-primary hover:text-primary"
                                                                        onClick={() => openEdit(p)}>
                                                                        <Pencil className="size-3" />
                                                                    </Button>
                                                                    <Button size="icon" variant="ghost" className="size-6 text-destructive hover:text-destructive"
                                                                        onClick={() => setDeleteId(p.id)}>
                                                                        <Trash2 className="size-3" />
                                                                    </Button>
                                                                </div>
                                                            )}
                                                            {isBackoffice && (
                                                                <div className="flex items-center gap-0 shrink-0">
                                                                    <Button size="icon" variant="ghost" className="size-6 text-primary hover:text-primary"
                                                                        onClick={() => openEdit(p)}>
                                                                        <Pencil className="size-3" />
                                                                    </Button>
                                                                    <Button size="icon" variant="ghost" className="size-6 text-destructive hover:text-destructive"
                                                                        onClick={() => setDeleteId(p.id)}>
                                                                        <Trash2 className="size-3" />
                                                                    </Button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </SheetContent>
            </Sheet>

            <AlertDialog open={!!deleteId} onOpenChange={open => !open && setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Remover parâmetro?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter className="sm:justify-end gap-2">
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={() => deleteId && deleteMut.mutate(deleteId)}
                        >
                            Remover
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
