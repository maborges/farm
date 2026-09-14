"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
    Plus, X, Loader2,
    Tag, Hash, Scale, CalendarDays, Edit, Trash2, Beef, Weight
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface LoteBovino {
    id: string;
    identificacao: string;
}

interface AnimalBase {
    numero_brinco?: string;
    numero_sisbov?: string;
    microchip?: string;
    nome?: string;
    especie: string;
    categoria: string;
    raca?: string;
    sexo: string;
    pelagem?: string;
    data_nascimento?: string;
    data_entrada?: string;
    peso_atual_kg?: number;
    valor_aquisicao?: number;
    status: string;
    lote_id?: string;
    fornecedor?: string;
    numero_nf?: string;
    serie_nf?: string;
    chave_nfe?: string;
    dados_extras?: {
        compra?: {
            fornecedor?: string;
            numero_nf?: string;
            serie_nf?: string;
            chave_nfe?: string;
            evento_compra_id?: string;
            despesa_compra_id?: string;
        };
    } | null;
}

interface Animal extends AnimalBase {
    id: string;
    unidade_produtiva_id: string;
}

type AnimalSubmitPayload = {
    [key: string]: string | number | null | undefined;
};

interface AnimalListResponse {
    items: Animal[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
}

const CATEGORIAS = [
    "BEZERRO", "BEZERRA", "GARROTE", "NOVILHA", "BOI",
    "VACA_CORTE", "TOURO", "VACA_LEITE", "NOVILHA_LEITE", "REPRODUTOR", "OUTRO"
];
const RACAS = ["Nelore", "Angus", "Brahman", "Gir", "Girolando", "Simental", "Brangus", "Mestiço", "Outros"];
const SEXOS = ["MACHO", "FEMEA", "CASTRADO"];
const STATUS = ["ATIVO", "VENDIDO", "ABATIDO", "MORTO", "TRANSFERIDO"];
const ESPECIES = ["BOVINO", "SUINO", "OVINO", "CAPRINO", "EQUINO", "AVES", "OUTRO"];

function AnimalModal({
    fazendaId,
    animal,
    onClose
}: {
    fazendaId: string;
    animal?: Animal;
    onClose: () => void;
}) {
    const queryClient = useQueryClient();
    const isEditing = !!animal;

    const [form, setForm] = useState<AnimalBase>({
        numero_brinco: animal?.numero_brinco || "",
        numero_sisbov: animal?.numero_sisbov || "",
        microchip: animal?.microchip || "",
        nome: animal?.nome || "",
        especie: animal?.especie || "BOVINO",
        categoria: animal?.categoria || "BEZERRO",
        raca: animal?.raca || "",
        sexo: animal?.sexo || "MACHO",
        data_nascimento: animal?.data_nascimento ? animal.data_nascimento.split("T")[0] : "",
        data_entrada: animal?.data_entrada ? animal.data_entrada.split("T")[0] : new Date().toISOString().split("T")[0],
        peso_atual_kg: animal?.peso_atual_kg || 0,
        valor_aquisicao: animal?.valor_aquisicao || 0,
        status: animal?.status || "ATIVO",
        lote_id: animal?.lote_id || "",
        fornecedor: animal?.dados_extras?.compra?.fornecedor || "",
        numero_nf: animal?.dados_extras?.compra?.numero_nf || "",
        serie_nf: animal?.dados_extras?.compra?.serie_nf || "",
        chave_nfe: animal?.dados_extras?.compra?.chave_nfe || "",
    });

    // Buscar lotes para o select
    const { data: lotes = [] } = useQuery({
        queryKey: ["lotes", fazendaId],
        queryFn: () => apiFetch<LoteBovino[]>(`/pecuaria/lotes?unidade_produtiva_id=${fazendaId}`),
        enabled: !!fazendaId,
    });

    const mutation = useMutation({
        mutationFn: (payload: AnimalSubmitPayload) => {
            if (isEditing) {
                return apiFetch(`/pecuaria/animais/${animal.id}`, { method: "PATCH", body: JSON.stringify(payload) });
            }
            return apiFetch("/pecuaria/animais", { method: "POST", body: JSON.stringify(payload) });
        },
        onSuccess: () => {
            toast.success(`Animal ${isEditing ? "atualizado" : "cadastrado"} com sucesso!`);
            queryClient.invalidateQueries({ queryKey: ["animais"] });
            onClose();
        },
        onError: (err: Error) => {
            toast.error(err.message || "Erro ao salvar animal.");
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!fazendaId) return toast.error("Selecione uma fazenda primeiro.");
        if (!form.numero_brinco && !form.numero_sisbov && !form.microchip) {
            return toast.error("Informe pelo menos um identificador (Brinco, SISBOV ou Microchip).");
        }

        const { dados_extras: _dadosExtras, ...formPayload } = form;
        const payload = {
            ...formPayload,
            peso_atual_kg: Number(form.peso_atual_kg) || null,
            valor_aquisicao: Number(form.valor_aquisicao) || null,
            data_nascimento: form.data_nascimento || null,
            lote_id: form.lote_id || null,
            fornecedor: form.fornecedor || null,
            numero_nf: form.numero_nf || null,
            serie_nf: form.serie_nf || null,
            chave_nfe: form.chave_nfe || null,
            ...(!isEditing ? { unidade_produtiva_id: fazendaId } : {})
        };

        mutation.mutate(payload);
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
            <div className="bg-surface w-full max-w-2xl rounded-sm shadow-2xl border border-border-subtle animate-in fade-in duration-200 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between px-6 py-5 border-b border-border-subtle sticky top-0 bg-surface z-10">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-sm bg-primary/10 flex items-center justify-center">
                            <Beef size={18} className="text-primary" />
                        </div>
                        <div>
                            <h2 className="font-bold text-foreground text-[15px]">{isEditing ? "Editar Animal" : "Novo Animal"}</h2>
                            <p className="text-xs text-foreground/50">Cadastro individualizado</p>
                        </div>
                    </div>
                    <button type="button" onClick={onClose} className="h-8 w-8 rounded-sm hover:bg-neutral-100 dark:hover:bg-white/10 flex items-center justify-center transition-colors">
                        <X size={16} className="text-foreground/60" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                    {/* Seção Identificação */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-bold border-b pb-1">Identificação</h3>
                        <div className="grid grid-cols-3 gap-4">
                            {field("Nº Brinco", "brinco", (
                                <div className="relative">
                                    <Tag size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                    <Input id="brinco" className="h-8 text-sm pl-9" value={form.numero_brinco} onChange={e => setForm(f => ({ ...f, numero_brinco: e.target.value }))} />
                                </div>
                            ))}
                            {field("SISBOV", "sisbov", (
                                <Input id="sisbov" className="h-8 text-sm" value={form.numero_sisbov} onChange={e => setForm(f => ({ ...f, numero_sisbov: e.target.value }))} />
                            ))}
                            {field("Nome", "nome", (
                                <Input id="nome" className="h-8 text-sm" placeholder="Opcional" value={form.nome} onChange={e => setForm(f => ({ ...f, nome: e.target.value }))} />
                            ))}
                        </div>
                    </div>

                    {/* Seção Classificação */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-bold border-b pb-1">Classificação</h3>
                        <div className="grid grid-cols-4 gap-4">
                            {field("Espécie", "especie", (
                                <select id="especie" required className={selectClass} value={form.especie} onChange={e => setForm(f => ({ ...f, especie: e.target.value }))}>
                                    {ESPECIES.map(c => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
                                </select>
                            ), true)}
                            {field("Categoria", "categoria", (
                                <select id="categoria" required className={selectClass} value={form.categoria} onChange={e => setForm(f => ({ ...f, categoria: e.target.value }))}>
                                    {CATEGORIAS.map(c => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
                                </select>
                            ), true)}
                            {field("Sexo", "sexo", (
                                <select id="sexo" required className={selectClass} value={form.sexo} onChange={e => setForm(f => ({ ...f, sexo: e.target.value }))}>
                                    {SEXOS.map(c => <option key={c} value={c}>{c.replace("_", " ")}</option>)}
                                </select>
                            ), true)}
                            {field("Raça", "raca", (
                                <select id="raca" className={selectClass} value={form.raca} onChange={e => setForm(f => ({ ...f, raca: e.target.value }))}>
                                    <option value="">Nenhuma</option>
                                    {RACAS.map(r => <option key={r} value={r}>{r}</option>)}
                                </select>
                            ))}
                        </div>
                    </div>

                    {/* Seção Detalhes */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-bold border-b pb-1">Detalhes e Manejo</h3>
                        <div className="grid grid-cols-3 gap-4">
                            {field("Peso Atual (kg)", "peso", (
                                <div className="relative">
                                    <Scale size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                    <Input id="peso" type="number" min={0} step={0.1} className="h-8 text-sm pl-9" value={form.peso_atual_kg} onChange={e => setForm(f => ({ ...f, peso_atual_kg: Number(e.target.value) }))} />
                                </div>
                            ))}
                            {field("Data Nasc.", "data_nasc", (
                                <div className="relative">
                                    <CalendarDays size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground/40" />
                                    <Input id="data_nasc" type="date" className="h-8 text-sm pl-9" value={form.data_nascimento} onChange={e => setForm(f => ({ ...f, data_nascimento: e.target.value }))} />
                                </div>
                            ))}
                            {field("Status", "status", (
                                <select id="status" required className={selectClass} value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
                                    {STATUS.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                                </select>
                            ), true)}

                            {field("Lote Atual", "lote", (
                                <select id="lote" className={selectClass} value={form.lote_id} onChange={e => setForm(f => ({ ...f, lote_id: e.target.value }))}>
                                    <option value="">Sem Lote</option>
                                    {lotes.map(l => <option key={l.id} value={l.id}>{l.identificacao}</option>)}
                                </select>
                            ))}
                            {field("Val. Aquisição (R$)", "valor", (
                                <Input id="valor" type="number" min={0} step={0.01} className="h-8 text-sm" value={form.valor_aquisicao} onChange={e => setForm(f => ({ ...f, valor_aquisicao: Number(e.target.value) }))} />
                            ))}
                            {field("Data Entrada", "data_ent", (
                                <Input id="data_ent" type="date" className="h-8 text-sm" value={form.data_entrada} onChange={e => setForm(f => ({ ...f, data_entrada: e.target.value }))} required />
                            ), true)}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h3 className="text-sm font-bold border-b pb-1">Compra</h3>
                        <div className="grid grid-cols-3 gap-4">
                            {field("Fornecedor", "fornecedor", (
                                <Input id="fornecedor" className="h-8 text-sm" placeholder="Nome do fornecedor" value={form.fornecedor} onChange={e => setForm(f => ({ ...f, fornecedor: e.target.value }))} />
                            ))}
                            {field("Nota Fiscal", "nf", (
                                <Input id="nf" className="h-8 text-sm" placeholder="Número da NF" value={form.numero_nf} onChange={e => setForm(f => ({ ...f, numero_nf: e.target.value }))} />
                            ))}
                            {field("Chave NFe", "chave_nfe", (
                                <Input id="chave_nfe" className="h-8 text-sm" placeholder="Chave de acesso" value={form.chave_nfe} onChange={e => setForm(f => ({ ...f, chave_nfe: e.target.value }))} />
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-border-subtle sticky bottom-0 bg-surface">
                        <Button type="button" variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
                        <Button type="submit" size="sm" disabled={mutation.isPending}>
                            {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={16} className="mr-2" />}
                            {mutation.isPending ? "Salvando..." : isEditing ? "Atualizar" : "Salvar"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}

const getCategoriaBadge = (categoria: string) => {
    if (categoria.includes("VACA") || categoria.includes("MATRIZ")) return "bg-pink-50 text-pink-700 border-pink-200";
    if (categoria.includes("BEZERR")) return "bg-blue-50 text-blue-700 border-blue-200";
    if (categoria.includes("TOURO") || categoria.includes("REPRODUTOR")) return "bg-orange-50 text-orange-700 border-orange-200";
    if (categoria.includes("NOVILH") || categoria.includes("GARROTE")) return "bg-purple-50 text-purple-700 border-purple-200";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
};

const getStatusBadge = (status: string) => {
    if (status === "ATIVO") return "bg-green-50 text-green-700 border-green-200";
    if (status === "VENDIDO" || status === "TRANSFERIDO") return "bg-amber-50 text-amber-700 border-amber-200";
    if (status === "MORTO" || status === "ABATIDO") return "bg-red-50 text-red-700 border-red-200";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
};

export default function AnimaisPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();

    const [showModal, setShowModal] = useState(false);
    const [editingAnimal, setEditingAnimal] = useState<Animal | undefined>(undefined);
    const [animalToDelete, setAnimalToDelete] = useState<Animal | null>(null);

    // Filtros de API (para simplificar, na UI fetchamos os últimos 200 por enquanto,
    // pois o DataTable nativo faz paginação no cliente).
    const { data: response, isLoading } = useQuery({
        queryKey: ["animais", activeFazendaId],
        queryFn: () => apiFetch<AnimalListResponse>(`/pecuaria/animais?unidade_produtiva_id=${activeFazendaId}&page=1&page_size=200`),
        enabled: !!activeFazendaId,
    });

    const animais = response?.items || [];

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/pecuaria/animais/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Animal removido com sucesso");
            queryClient.invalidateQueries({ queryKey: ["animais"] });
        },
        onError: () => toast.error("Erro ao remover animal")
    });

    const solicitarPesagemMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/pecuaria/animais/${id}/pesagens/solicitar-balanca`, { method: "POST" }),
        onSuccess: () => {
            toast.success("Pesagem solicitada à balança!");
            queryClient.invalidateQueries({ queryKey: ["animais"] });
        },
        onError: (e: any) => toast.error(e?.message || "Erro ao solicitar pesagem"),
    });

    const handleDelete = (animal: Animal) => {
        setAnimalToDelete(animal);
    };

    const handleEdit = (animal: Animal) => {
        setEditingAnimal(animal);
        setShowModal(true);
    };

    const columns: ColumnDef<Animal>[] = [
        {
            id: "identificacao",
            header: "Brinco / SISBOV",
            accessorFn: (row) => row.numero_brinco || row.numero_sisbov || row.microchip || "-",
            cell: (value, row) => (
                <div>
                    <p className="font-semibold text-foreground">{value}</p>
                    {row.nome && <p className="text-xs text-foreground/60 font-medium mt-0.5">{row.nome}</p>}
                </div>
            ),
            sortable: true,
            filterable: true,
        },
        {
            id: "categoria",
            header: "Categoria",
            accessorKey: "categoria",
            cell: (value) => (
                <Badge className={`inline-flex items-center shadow-sm ${getCategoriaBadge(value)}`} variant="outline">
                    {value.replace("_", " ")}
                </Badge>
            ),
            sortable: true,
            filterable: true,
            filterOptions: CATEGORIAS.map(c => ({ label: c.replace("_", " "), value: c }))
        },
        {
            id: "sexo",
            header: "Sexo",
            accessorKey: "sexo",
            cell: (value) => <span className="text-xs font-semibold text-foreground/80">{value}</span>,
            sortable: true,
            filterable: true,
            filterOptions: SEXOS.map(s => ({ label: s, value: s }))
        },
        {
            id: "peso_atual_kg",
            header: "Peso (kg)",
            accessorKey: "peso_atual_kg",
            cell: (value) => <span className="text-foreground/70 block">{value ? `${value} kg` : "-"}</span>,
            sortable: true,
        },
        {
            id: "status",
            header: "Status",
            accessorKey: "status",
            cell: (value) => (
                <Badge className={`inline-flex items-center shadow-sm ${getStatusBadge(value)}`} variant="outline">
                    {value}
                </Badge>
            ),
            sortable: true,
            filterable: true,
            filterOptions: STATUS.map(s => ({ label: s, value: s }))
        },
        {
            id: "acoes",
            header: "",
            isActionColumn: true,
            cell: (_, row) => (
                <div className="flex items-center gap-0 justify-end">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 rounded-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        title="Solicitar pesagem na balança"
                        disabled={solicitarPesagemMutation.isPending}
                        onClick={(e) => { e.stopPropagation(); solicitarPesagemMutation.mutate(row.id); }}
                    >
                        <Weight className="size-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="size-7 rounded-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={(e) => { e.stopPropagation(); handleEdit(row); }}>
                        <Edit className="size-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="size-7 rounded-sm text-rose-600 hover:text-rose-700 hover:bg-rose-50" onClick={(e) => { e.stopPropagation(); handleDelete(row); }}>
                        <Trash2 className="size-3.5" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Rebanho Individual"
                description="Gerencie seus animais de forma detalhada e individualizada"
                icon={<Beef size={22} className="text-primary" />}
                breadcrumbs={[
                    { label: "Pecuária", href: "/dashboard/pecuaria" },
                    { label: "Animais" },
                ]}
                actions={
                    <Button onClick={() => { setEditingAnimal(undefined); setShowModal(true); }} size="sm" variant="outline" className="rounded-sm">
                        <Plus className="size-3.5 mr-1.5" />
                        Novo Animal
                    </Button>
                }
            />

            <Card className="shadow-sm">
                <CardHeader className="border-b">
                    <CardTitle>Lista de Animais</CardTitle>
                    <CardDescription>
                        Consulte, edite e exporte os animais do rebanho da sua fazenda.
                    </CardDescription>
                </CardHeader>
                <CardContent className="pt-4">
                    <DataTable
                        columns={columns}
                        data={animais}
                        isLoading={isLoading}
                        searchPlaceholder="Buscar por brinco, SISBOV ou nome..."
                        exportFileName="animais-export"
                        emptyMessage="Nenhum animal encontrado nesta fazenda."
                    />
                </CardContent>
            </Card>

            {showModal && (
                <AnimalModal
                    fazendaId={activeFazendaId!}
                    animal={editingAnimal}
                    onClose={() => setShowModal(false)}
                />
            )}

            <ConfirmDialog
                open={!!animalToDelete}
                title="Remover animal?"
                description={animalToDelete ? `O animal "${animalToDelete.numero_brinco || animalToDelete.numero_sisbov || animalToDelete.nome || animalToDelete.id}" será removido. Esta ação é irreversível.` : undefined}
                confirmText="Remover"
                destructive
                onCancel={() => setAnimalToDelete(null)}
                onConfirm={() => {
                    if (!animalToDelete) return;
                    deleteMutation.mutate(animalToDelete.id, {
                        onSettled: () => setAnimalToDelete(null),
                    });
                }}
            />
        </div>
    );
}
