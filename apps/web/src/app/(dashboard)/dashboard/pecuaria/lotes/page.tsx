"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
    Plus, X, Loader2,
    List, Hash, Scale, CalendarDays, ClipboardList, Beef, BarChart3
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoteIndicadoresDrawer } from "@/components/pecuaria/lote-indicadores-drawer";

interface LoteBovinoCreate {
    unidade_produtiva_id: string;
    area_id?: string;
    identificacao: string;
    categoria: string;
    raca: string;
    quantidade_cabecas: number;
    peso_medio_kg: number;
    data_formacao?: string;
}

interface LoteBovino extends LoteBovinoCreate {
    id: string;
}

const CATEGORIAS = ["Bezerros", "Bezerras", "Novilhas", "Novilhos", "Vacas", "Touros", "Matrizes", "Recria"];
const RACAS = ["Nelore", "Angus", "Brahman", "Gir", "Girolando", "Simental", "Brangus", "Mestiço", "Outros"];

function NovoLoteModal({ fazendaId, onClose }: { fazendaId: string; onClose: () => void }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState<Omit<LoteBovinoCreate, "unidade_produtiva_id">>({
        identificacao: "",
        categoria: "",
        raca: "",
        quantidade_cabecas: 1,
        peso_medio_kg: 0,
        data_formacao: new Date().toISOString().split("T")[0],
    });

    const mutation = useMutation({
        mutationFn: (payload: LoteBovinoCreate) =>
            apiFetch("/pecuaria/lotes", { method: "POST", body: JSON.stringify(payload) }),
        onSuccess: () => {
            toast.success("Lote criado com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["lotes"] });
            onClose();
        },
        onError: (err: Error) => {
            toast.error(err.message || "Erro ao criar lote.");
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!fazendaId) return toast.error("Selecione uma fazenda primeiro.");
        mutation.mutate({ ...form, unidade_produtiva_id: fazendaId });
    };

    const field = (label: string, id: string, input: React.ReactNode, required = false) => (
        <div className="flex flex-col gap-1.5">
            <label htmlFor={id} className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                {label} {required && <span className="text-red-500">*</span>}
            </label>
            {input}
        </div>
    );

    const selectClass = "flex h-8 w-full rounded-sm border border-primary/20 bg-background px-3 py-1 text-sm transition-all focus-visible:border-primary/60 focus-visible:ring-4 focus-visible:ring-primary/5 outline-none";

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-surface w-full max-w-lg rounded-sm shadow-2xl border border-border-subtle animate-in fade-in duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-border-subtle">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-sm bg-primary/10 flex items-center justify-center">
                            <Beef size={18} className="text-primary" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-[15px]">Novo Lote Bovino</h2>
                            <p className="text-xs text-foreground/50">Fundação de novo lote de animais</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="h-8 w-8 rounded-sm hover:bg-neutral-100 dark:hover:bg-white/10 flex items-center justify-center transition-colors">
                        <X size={16} className="text-foreground/60" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        {field("Identificação do Lote", "ident", (
                            <div className="relative">
                                <List size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                <Input
                                    id="ident"
                                    required
                                    placeholder="Ex: Lote A - Nelore 2024"
                                    className="pl-9"
                                    value={form.identificacao}
                                    onChange={e => setForm(f => ({ ...f, identificacao: e.target.value }))}
                                />
                            </div>
                        ), true)}

                        {field("Categoria", "categoria", (
                            <select
                                id="categoria"
                                required
                                className={selectClass}
                                value={form.categoria}
                                onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))}
                            >
                                <option value="">Selecione...</option>
                                {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
                            </select>
                        ), true)}
                    </div>

                    {field("Raça principal", "raca", (
                        <select
                            id="raca"
                            required
                            className={selectClass}
                            value={form.raca}
                            onChange={e => setForm(f => ({ ...f, raca: e.target.value }))}
                        >
                            <option value="">Selecione...</option>
                            {RACAS.map(r => <option key={r}>{r}</option>)}
                        </select>
                    ), true)}

                    <div className="grid grid-cols-2 gap-4">
                        {field("Qtd. de Cabeças", "cabecas", (
                            <div className="relative">
                                <Hash size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                <Input
                                    id="cabecas"
                                    type="number"
                                    required
                                    min={1}
                                    className="pl-9"
                                    value={form.quantidade_cabecas}
                                    onChange={e => setForm(f => ({ ...f, quantidade_cabecas: Number(e.target.value) }))}
                                />
                            </div>
                        ), true)}

                        {field("Peso Médio (kg)", "peso", (
                            <div className="relative">
                                <Scale size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                <Input
                                    id="peso"
                                    type="number"
                                    min={0}
                                    step={0.1}
                                    className="pl-9"
                                    value={form.peso_medio_kg}
                                    onChange={e => setForm(f => ({ ...f, peso_medio_kg: Number(e.target.value) }))}
                                />
                            </div>
                        ))}
                    </div>

                    {field("Data de Formação", "data", (
                        <div className="relative">
                            <CalendarDays size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                            <Input
                                id="data"
                                type="date"
                                className="pl-9"
                                value={form.data_formacao}
                                onChange={e => setForm(f => ({ ...f, data_formacao: e.target.value }))}
                            />
                        </div>
                    ))}

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-2">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={onClose}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="submit"
                            size="sm"
                            disabled={mutation.isPending}
                        >
                            {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={16} className="mr-2" />}
                            {mutation.isPending ? "Salvando..." : "Criar Lote"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}

const getCategoriaStyle = (categoria: string) => {
    switch (categoria.toLowerCase()) {
        case "bezerros":
        case "bezerras":
            return "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-400 border-blue-200 dark:border-blue-900/50";
        case "vacas":
        case "matrizes":
            return "bg-pink-50 text-pink-700 dark:bg-pink-950/50 dark:text-pink-400 border-pink-200 dark:border-pink-900/50";
        case "touros":
            return "bg-orange-50 text-orange-700 dark:bg-orange-950/50 dark:text-orange-400 border-orange-200 dark:border-orange-900/50";
        case "novilhas":
        case "novilhos":
        case "recria":
            return "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-400 border-purple-200 dark:border-purple-900/50";
        default:
            return "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700";
    }
};

export default function LotesBovinosPage() {
    const { activeFazendaId, isVisaoGrupo } = useAppStore();
    const [showModal, setShowModal] = useState(false);
    const [selectedLoteIndicadores, setSelectedLoteIndicadores] = useState<LoteBovino | null>(null);

    const { data: lotes = [], isLoading } = useQuery({
        queryKey: ["lotes", activeFazendaId, isVisaoGrupo],
        queryFn: () =>
            apiFetch<LoteBovino[]>(isVisaoGrupo ? "/pecuaria/lotes" : `/pecuaria/lotes?unidade_produtiva_id=${activeFazendaId}`),
        enabled: isVisaoGrupo || !!activeFazendaId,
    });

    const columns: ColumnDef<LoteBovino>[] = [
        {
            id: "categoria",
            header: "Categoria",
            accessorKey: "categoria",
            cell: (value) => (
                <Badge
                    className={`inline-flex items-center gap-1.5 shadow-sm ${getCategoriaStyle(value)}`}
                    variant="outline"
                >
                    {value}
                </Badge>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar categoria...",
            exportFormat: (value) => value,
        },
        {
            id: "identificacao",
            header: "Identificação",
            accessorKey: "identificacao",
            cell: (value, row) => (
                <div>
                    <p className="font-semibold text-foreground">{value}</p>
                    <p className="text-xs text-foreground/60 font-medium mt-0.5">Raça: {row.raca}</p>
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar identificação...",
            exportFormat: (value, row) => `${value} (${row.raca})`,
        },
        {
            id: "quantidade_cabecas",
            header: "Cabeças",
            accessorKey: "quantidade_cabecas",
            cell: (value) => (
                <span className="font-bold text-foreground text-right block">{value}</span>
            ),
            sortable: true,
            exportFormat: (value) => value?.toString() || "0",
        },
        {
            id: "peso_medio_kg",
            header: "Peso Médio",
            accessorKey: "peso_medio_kg",
            cell: (value) => (
                <span className="text-foreground/70 text-right block">
                    {value?.toFixed(1)} kg
                </span>
            ),
            sortable: true,
            exportFormat: (value) => value ? `${value.toFixed(1)} kg` : "-",
        },
        {
            id: "data_formacao",
            header: "Fundação",
            accessorKey: "data_formacao",
            cell: (value) => (
                <span className="text-foreground/70 text-right block">
                    {new Date(value).toLocaleDateString("pt-BR")}
                </span>
            ),
            sortable: true,
            exportFormat: (value) => new Date(value).toLocaleDateString("pt-BR"),
        },
        {
            id: "acoes",
            header: "",
            cell: (_, row) => (
                <div className="flex items-center gap-0 justify-end">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 rounded-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        title="Indicadores"
                        onClick={(event) => {
                            event.stopPropagation();
                            setSelectedLoteIndicadores(row);
                        }}
                    >
                        <BarChart3 className="size-3.5" />
                    </Button>
                </div>
            ),
            sortable: false,
            filterable: false,
            exportable: false,
            isActionColumn: true,
        },
    ];

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-200">
            {/* Header */}
            <PageHeader
                title="Rebanho: Lotes"
                description="Gerencie a quantidade de cabeças, pesagem e movimentação entre pastos."
                icon={<ClipboardList size={22} className="text-primary" />}
                breadcrumbs={[
                    { label: "Pecuária", href: "/dashboard/pecuaria" },
                    { label: "Lotes" }
                ]}
                actions={
                    <Button
                        size="sm"
                        variant="outline"
                        className="rounded-sm"
                        onClick={() => {
                            if (!activeFazendaId) return toast.error("Selecione uma fazenda para adicionar lotes.");
                            setShowModal(true);
                        }}
                    >
                        <Plus className="size-3.5 mr-1.5" />
                        Novo Lote
                    </Button>
                }
            />

            {/* DataTable */}
            <Card className="shadow-sm">
                <CardHeader className="border-b">
                    <CardTitle>Lista de Lotes</CardTitle>
                    <CardDescription>
                        Consulte, crie e acompanhe o desempenho dos lotes de animais.
                    </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                    <DataTable
                        data={lotes}
                        columns={columns}
                        searchable
                        searchPlaceholder="Buscar por identificação, raça ou categoria..."
                        exportable
                        exportFileName="lotes-bovinos"
                        emptyMessage="Nenhum lote registrado nesta fazenda."
                    />
                </CardContent>
            </Card>

            {showModal && activeFazendaId && (
                <NovoLoteModal fazendaId={activeFazendaId} onClose={() => setShowModal(false)} />
            )}
            <LoteIndicadoresDrawer
                open={Boolean(selectedLoteIndicadores)}
                loteId={selectedLoteIndicadores?.id ?? null}
                loteNome={selectedLoteIndicadores?.identificacao ?? null}
                onOpenChange={(open) => {
                    if (!open) {
                        setSelectedLoteIndicadores(null);
                    }
                }}
            />
        </div>
    );
}
