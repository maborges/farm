"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, Bug, Leaf, Sprout, Plus, ChevronDown, ChevronRight, NotebookPen } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface CatalogoItem {
    id: string;
    tipo: string;
    nome_popular: string;
    nome_cientifico: string | null;
    nde_padrao: number | null;
    unidade_medida: string | null;
}

interface Monitoramento {
    id: string;
    talhao_id: string;
    data_avaliacao: string;
    tipo: string | null;
    nome_popular: string | null;
    nome_cientifico: string | null;
    nivel_infestacao: number | null;
    unidade_medida: string | null;
    nde_cultura: number | null;
    atingiu_nde: boolean;
    acao_tomada: string | null;
    estagio_fenologico_codigo: string | null;
    observacoes: string | null;
    catalogo_id: string | null;
}

interface Props {
    safraId: string;
    talhoes: { id: string; nome: string }[];
}

const TIPO_CONFIG: Record<string, { label: string; icon: React.ElementType; cor: string }> = {
    PRAGA:          { label: "Praga",          icon: Bug,           cor: "bg-red-100 text-red-700 border-red-200" },
    DOENCA:         { label: "Doença",         icon: AlertTriangle, cor: "bg-amber-100 text-amber-700 border-amber-200" },
    PLANTA_DANINHA: { label: "Planta Daninha", icon: Sprout,        cor: "bg-lime-100 text-lime-700 border-lime-200" },
    OBSERVACAO:     { label: "Observação",     icon: NotebookPen,   cor: "bg-sky-100 text-sky-700 border-sky-200" },
};

const ACAO_LABEL: Record<string, string> = {
    CONTROLE: "Controle aplicado",
    MONITORAR: "Monitorar",
    NENHUMA: "Sem ação",
};

function MonitoramentoCard({ m, talhaoNome }: { m: Monitoramento; talhaoNome: string }) {
    const cfg = m.tipo ? TIPO_CONFIG[m.tipo] : null;
    const Icon = cfg?.icon ?? Leaf;

    return (
        <div className={cn(
            "flex items-start gap-3 px-3 py-3 rounded-lg border text-sm",
            m.atingiu_nde ? "bg-red-50 border-red-200" : "bg-white border-border"
        )}>
            <div className={cn("mt-0.5 p-1.5 rounded-md", cfg?.cor ?? "bg-muted")}>
                <Icon className="size-3.5" />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{m.nome_popular ?? m.nome_cientifico ?? "—"}</span>
                    {m.atingiu_nde && (
                        <Badge className="bg-red-100 text-red-700 border-red-300 text-xs">NDE atingido</Badge>
                    )}
                    {m.estagio_fenologico_codigo && (
                        <Badge variant="outline" className="text-xs">{m.estagio_fenologico_codigo}</Badge>
                    )}
                </div>
                <div className="text-xs text-muted-foreground mt-0.5 flex flex-wrap gap-x-3">
                    <span>{talhaoNome}</span>
                    <span>{format(new Date(m.data_avaliacao + "T12:00:00"), "dd/MM/yy", { locale: ptBR })}</span>
                    {m.nivel_infestacao != null && (
                        <span>{m.nivel_infestacao} {m.unidade_medida ?? ""}</span>
                    )}
                    {m.acao_tomada && <span>{ACAO_LABEL[m.acao_tomada] ?? m.acao_tomada}</span>}
                </div>
                {m.observacoes && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{m.observacoes}</p>
                )}
            </div>
        </div>
    );
}

export function MonitoramentoRegistro({ safraId, talhoes }: Props) {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [filtroTipo, setFiltroTipo] = useState<string>("TODOS");
    const [filtroTalhao, setFiltroTalhao] = useState<string>("TODOS");
    const [expandido, setExpandido] = useState<Record<string, boolean>>({});

    const [form, setForm] = useState({
        talhao_id: "",
        data_avaliacao: new Date().toISOString().split("T")[0],
        tipo_manual: "",   // usado quando OBSERVACAO (sem catálogo)
        catalogo_id: "",
        nivel_infestacao: "",
        acao_tomada: "",
        observacoes: "",
    });

    const isObservacao = form.tipo_manual === "OBSERVACAO";

    const { data: registros = [], isLoading } = useQuery<Monitoramento[]>({
        queryKey: ["monitoramento", safraId, filtroTipo, filtroTalhao],
        queryFn: () => {
            const params = new URLSearchParams();
            if (filtroTipo !== "TODOS") params.set("tipo", filtroTipo);
            if (filtroTalhao !== "TODOS") params.set("talhao_id", filtroTalhao);
            return apiFetch(`/monitoramentos/safra/${safraId}?${params}`);
        },
    });

    const { data: catalogo = [] } = useQuery<CatalogoItem[]>({
        queryKey: ["monitoramento-catalogo"],
        queryFn: () => apiFetch("/monitoramentos/catalogo"),
    });

    const mutation = useMutation({
        mutationFn: (body: object) =>
            apiFetch("/monitoramentos/", { method: "POST", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Registro salvo.");
            qc.invalidateQueries({ queryKey: ["monitoramento", safraId] });
            setOpen(false);
            setForm({ talhao_id: "", data_avaliacao: new Date().toISOString().split("T")[0], tipo_manual: "", catalogo_id: "", nivel_infestacao: "", acao_tomada: "", observacoes: "" });
        },
        onError: () => toast.error("Erro ao salvar registro."),
    });

    const catalogoSelecionado = catalogo.find(c => c.id === form.catalogo_id);

    function handleSalvar() {
        if (!form.talhao_id || !form.data_avaliacao) {
            toast.error("Preencha talhão e data.");
            return;
        }
        if (!isObservacao && !form.catalogo_id) {
            toast.error("Selecione o organismo do catálogo ou escolha 'Observação'.");
            return;
        }
        if (isObservacao && !form.observacoes.trim()) {
            toast.error("Preencha o campo de observações.");
            return;
        }
        mutation.mutate({
            safra_id: safraId,
            talhao_id: form.talhao_id,
            data_avaliacao: form.data_avaliacao,
            tipo: isObservacao ? "OBSERVACAO" : undefined,
            catalogo_id: isObservacao ? null : form.catalogo_id,
            nivel_infestacao: !isObservacao && form.nivel_infestacao ? parseFloat(form.nivel_infestacao) : null,
            acao_tomada: !isObservacao ? (form.acao_tomada || null) : null,
            observacoes: form.observacoes || null,
        });
    }

    // Group by tipo
    const grupos = ["PRAGA", "DOENCA", "PLANTA_DANINHA", "OBSERVACAO"] as const;
    const porTipo: Record<string, Monitoramento[]> = {};
    for (const r of registros) {
        const k = r.tipo ?? "OUTROS";
        porTipo[k] = [...(porTipo[k] ?? []), r];
    }

    const talhaoMap = Object.fromEntries(talhoes.map(t => [t.id, t.nome]));

    return (
        <div className="space-y-4">
            {/* Toolbar */}
            <div className="flex items-center gap-2 flex-wrap">
                <Select value={filtroTipo} onValueChange={setFiltroTipo}>
                    <SelectTrigger className="w-40 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="TODOS">Todos os tipos</SelectItem>
                        <SelectItem value="PRAGA">Pragas</SelectItem>
                        <SelectItem value="DOENCA">Doenças</SelectItem>
                        <SelectItem value="PLANTA_DANINHA">Plantas Daninhas</SelectItem>
                        <SelectItem value="OBSERVACAO">Observações</SelectItem>
                    </SelectContent>
                </Select>
                <Select value={filtroTalhao} onValueChange={setFiltroTalhao}>
                    <SelectTrigger className="w-44 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="TODOS">Todos os talhões</SelectItem>
                        {talhoes.map(t => (
                            <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <Button size="sm" className="ml-auto h-8" onClick={() => setOpen(true)}>
                    <Plus className="size-3.5 mr-1.5" /> Registrar
                </Button>
            </div>

            {isLoading ? (
                <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-14" />)}</div>
            ) : registros.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground text-sm">
                    Nenhum registro de monitoramento encontrado.
                </div>
            ) : (
                <div className="space-y-3">
                    {grupos.map(tipo => {
                        const items = porTipo[tipo] ?? [];
                        if (items.length === 0) return null;
                        const cfg = TIPO_CONFIG[tipo];
                        const Icon = cfg.icon;
                        const isOpen = expandido[tipo] !== false; // default open
                        return (
                            <Card key={tipo} className="shadow-sm">
                                <CardHeader
                                    className="pb-2 cursor-pointer select-none"
                                    onClick={() => setExpandido(e => ({ ...e, [tipo]: !isOpen }))}
                                >
                                    <CardTitle className="text-sm flex items-center gap-2">
                                        <Icon className="size-4" />
                                        {cfg.label}
                                        <Badge variant="secondary" className="ml-1">{items.length}</Badge>
                                        {items.some(i => i.atingiu_nde) && (
                                            <Badge className="bg-red-100 text-red-700 border-red-200 text-xs ml-auto mr-2">
                                                NDE
                                            </Badge>
                                        )}
                                        {isOpen ? <ChevronDown className="size-3.5 ml-auto" /> : <ChevronRight className="size-3.5 ml-auto" />}
                                    </CardTitle>
                                </CardHeader>
                                {isOpen && (
                                    <CardContent className="pt-0 space-y-2">
                                        {items.map(m => (
                                            <MonitoramentoCard
                                                key={m.id}
                                                m={m}
                                                talhaoNome={talhaoMap[m.talhao_id] ?? m.talhao_id}
                                            />
                                        ))}
                                    </CardContent>
                                )}
                            </Card>
                        );
                    })}
                </div>
            )}

            {/* Dialog novo registro */}
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Novo Registro de Monitoramento</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3 py-2">
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <Label className="text-xs">Talhão *</Label>
                                <Select value={form.talhao_id} onValueChange={v => setForm(f => ({ ...f, talhao_id: v }))}>
                                    <SelectTrigger className="mt-1">
                                        <SelectValue placeholder="Selecione" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {talhoes.map(t => <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label className="text-xs">Data *</Label>
                                <Input
                                    type="date"
                                    className="mt-1"
                                    value={form.data_avaliacao}
                                    onChange={e => setForm(f => ({ ...f, data_avaliacao: e.target.value }))}
                                />
                            </div>
                        </div>

                        <div>
                            <Label className="text-xs">Tipo de registro *</Label>
                            <Select value={form.tipo_manual} onValueChange={v => setForm(f => ({ ...f, tipo_manual: v, catalogo_id: "" }))}>
                                <SelectTrigger className="mt-1">
                                    <SelectValue placeholder="Selecione o tipo" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="CATALOGO">Praga / Doença / Planta Daninha (catálogo)</SelectItem>
                                    <SelectItem value="OBSERVACAO">Observação livre</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {form.tipo_manual === "CATALOGO" && (
                            <>
                                <div>
                                    <Label className="text-xs">Organismo (catálogo) *</Label>
                                    <Select value={form.catalogo_id} onValueChange={v => setForm(f => ({ ...f, catalogo_id: v }))}>
                                        <SelectTrigger className="mt-1">
                                            <SelectValue placeholder="Selecione do catálogo" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {catalogo.map(c => (
                                                <SelectItem key={c.id} value={c.id}>
                                                    {c.nome_popular}
                                                    {c.nome_cientifico && ` (${c.nome_cientifico})`}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    {catalogoSelecionado?.nde_padrao && (
                                        <p className="text-xs text-muted-foreground mt-1">
                                            NDE padrão: {catalogoSelecionado.nde_padrao} {catalogoSelecionado.unidade_medida ?? ""}
                                        </p>
                                    )}
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <Label className="text-xs">Nível de infestação</Label>
                                        <Input
                                            type="number"
                                            step="0.01"
                                            className="mt-1"
                                            placeholder={`ex: 2.5 ${catalogoSelecionado?.unidade_medida ?? ""}`}
                                            value={form.nivel_infestacao}
                                            onChange={e => setForm(f => ({ ...f, nivel_infestacao: e.target.value }))}
                                        />
                                    </div>
                                    <div>
                                        <Label className="text-xs">Ação tomada</Label>
                                        <Select value={form.acao_tomada} onValueChange={v => setForm(f => ({ ...f, acao_tomada: v }))}>
                                            <SelectTrigger className="mt-1">
                                                <SelectValue placeholder="Selecione" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="CONTROLE">Controle aplicado</SelectItem>
                                                <SelectItem value="MONITORAR">Monitorar</SelectItem>
                                                <SelectItem value="NENHUMA">Sem ação</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </>
                        )}

                        <div>
                            <Label className="text-xs">Observações</Label>
                            <Textarea
                                className="mt-1 resize-none"
                                rows={2}
                                value={form.observacoes}
                                onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
                        <Button onClick={handleSalvar} disabled={mutation.isPending}>
                            {mutation.isPending ? "Salvando…" : "Salvar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
