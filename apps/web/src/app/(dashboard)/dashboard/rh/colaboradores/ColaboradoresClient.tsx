"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import {
    Banknote,
    BriefcaseBusiness,
    CalendarDays,
    Check,
    Pencil,
    Plus,
    Search,
    UserCheck,
    Users,
    UserX,
    X,
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/shared/page-header";

export interface Colaborador {
    id: string;
    pessoa_id: string;
    nome: string | null;
    cpf: string | null;
    cargo: string | null;
    tipo_contrato: string;
    valor_diaria: number | null;
    valor_hora: number | null;
    data_admissao: string | null;
    unidade_produtiva_id?: string | null;
    observacoes?: string | null;
    ativo: boolean;
}

interface PessoaOpcao {
    id: string;
    nome_exibicao: string;
    tipo: string;
}

interface ColaboradorFormValues {
    cargo: string;
    tipo_contrato: string;
    valor_diaria: string;
    valor_hora: string;
    data_admissao: string;
    observacoes: string;
    ativo: boolean;
}

interface ColaboradorPayload {
    pessoa_id?: string;
    cargo?: string;
    tipo_contrato: string;
    valor_diaria?: number;
    valor_hora?: number;
    data_admissao?: string;
    unidade_produtiva_id?: string;
    observacoes?: string;
    ativo?: boolean;
}

const contratoLabel: Record<string, string> = {
    DIARISTA: "Diarista",
    CLT: "CLT",
    PJ: "PJ",
    EMPREITEIRO: "Empreiteiro",
    TERCEIRO: "Terceiro",
    TEMPORARIO: "Temporário",
};

const contratoOptions = Object.entries(contratoLabel);

function formatCurrency(value: number | null) {
    if (!value) return "—";
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
}

function colaboradoresUrl(activeFazendaId: string | null | undefined, ativo: boolean) {
    const params = new URLSearchParams({ ativo: String(ativo) });
    if (activeFazendaId) params.set("unidade_produtiva_id", activeFazendaId);
    return `/rh/colaboradores?${params.toString()}`;
}

async function fetchColaboradores(activeFazendaId: string | null | undefined) {
    const [ativos, inativos] = await Promise.all([
        apiFetch<Colaborador[]>(colaboradoresUrl(activeFazendaId, true)),
        apiFetch<Colaborador[]>(colaboradoresUrl(activeFazendaId, false)),
    ]);
    return [...ativos, ...inativos];
}

function colaboradorToPessoa(colaborador: Colaborador | null): PessoaOpcao | null {
    if (!colaborador) return null;
    return {
        id: colaborador.pessoa_id,
        nome_exibicao: colaborador.nome ?? "Pessoa sem nome",
        tipo: "PF",
    };
}

export function ColaboradoresClient({
    initialColaboradores,
    initialActiveFazendaId,
}: {
    initialColaboradores: Colaborador[];
    initialActiveFazendaId?: string;
}) {
    const qc = useQueryClient();
    const { activeFazendaId } = useAppStore();
    const [showDialog, setShowDialog] = useState(false);
    const [editando, setEditando] = useState<Colaborador | null>(null);
    const [apenasAtivos, setApenasAtivos] = useState(true);

    const { data: colaboradores = [], isLoading, isFetching } = useQuery<Colaborador[]>({
        queryKey: ["rh", "colaboradores", activeFazendaId],
        queryFn: () => fetchColaboradores(activeFazendaId),
        initialData: activeFazendaId === initialActiveFazendaId ? initialColaboradores : undefined,
    });

    const criarMut = useMutation({
        mutationFn: (payload: ColaboradorPayload) =>
            apiFetch<Colaborador>("/rh/colaboradores", { method: "POST", body: payload }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "colaboradores"] });
            setShowDialog(false);
            toast.success("Colaborador cadastrado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao cadastrar colaborador."),
    });

    const editarMut = useMutation({
        mutationFn: ({ id, payload }: { id: string; payload: ColaboradorPayload }) =>
            apiFetch<Colaborador>(`/rh/colaboradores/${id}`, { method: "PATCH", body: payload }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "colaboradores"] });
            setEditando(null);
            toast.success("Colaborador atualizado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao atualizar colaborador."),
    });

    const desativarMut = useMutation({
        mutationFn: (id: string) => apiFetch<{ message: string }>(`/rh/colaboradores/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "colaboradores"] });
            toast.success("Colaborador desativado.");
        },
        onError: (error: Error) => toast.error(error.message || "Erro ao desativar colaborador."),
    });

    const lista = apenasAtivos ? colaboradores.filter((c) => c.ativo) : colaboradores;
    const ativos = colaboradores.filter((c) => c.ativo).length;
    const inativos = colaboradores.filter((c) => !c.ativo).length;
    const diaristas = colaboradores.filter((c) => c.tipo_contrato === "DIARISTA" && c.ativo).length;
    const mensalistas = colaboradores.filter((c) => ["CLT", "PJ", "TERCEIRO"].includes(c.tipo_contrato) && c.ativo).length;
    const custoDiario = colaboradores
        .filter((c) => c.ativo)
        .reduce((sum, c) => sum + (c.valor_diaria ?? 0), 0);

    const columns: ColumnDef<Colaborador>[] = useMemo(() => [
        {
            id: "nome",
            header: "Colaborador",
            accessorKey: "nome",
            cell: (_value, row) => (
                <div className="min-w-[180px]">
                    <div className="font-medium leading-tight">{row.nome ?? "—"}</div>
                    <div className="text-[11px] text-muted-foreground">{row.cpf ?? "CPF não informado"}</div>
                </div>
            ),
            exportFormat: (_value, row) => row.nome ?? "",
        },
        {
            id: "cargo",
            header: "Cargo",
            accessorKey: "cargo",
            cell: (_value, row) => row.cargo ? row.cargo : <span className="text-muted-foreground">—</span>,
        },
        {
            id: "tipo_contrato",
            header: "Contrato",
            accessorKey: "tipo_contrato",
            filterOptions: contratoOptions.map(([value, label]) => ({ value, label })),
            cell: (_value, row) => (
                <Badge variant={row.tipo_contrato === "DIARISTA" ? "warning" : "metadata"} className="text-[10px]">
                    {contratoLabel[row.tipo_contrato] ?? row.tipo_contrato}
                </Badge>
            ),
            exportFormat: (_value, row) => contratoLabel[row.tipo_contrato] ?? row.tipo_contrato,
        },
        {
            id: "valor_diaria",
            header: "Diária",
            accessorKey: "valor_diaria",
            cell: (_value, row) => formatCurrency(row.valor_diaria),
            exportFormat: (_value, row) => row.valor_diaria?.toString() ?? "",
        },
        {
            id: "valor_hora",
            header: "Hora",
            accessorKey: "valor_hora",
            cell: (_value, row) => formatCurrency(row.valor_hora),
            exportFormat: (_value, row) => row.valor_hora?.toString() ?? "",
        },
        {
            id: "admissao",
            header: "Admissão",
            accessorKey: "data_admissao",
            cell: (_value, row) => formatDate(row.data_admissao),
        },
        {
            id: "ativo",
            header: "Status",
            accessorKey: "ativo",
            filterOptions: [
                { value: "true", label: "Ativo" },
                { value: "false", label: "Inativo" },
            ],
            cell: (_value, row) => <StatusBadge status={row.ativo ? "ativo" : "inativo"} />,
            exportFormat: (_value, row) => row.ativo ? "Ativo" : "Inativo",
        },
        {
            id: "acoes",
            header: "",
            exportable: false,
            sortable: false,
            filterable: false,
            isActionColumn: true,
            cell: (_value, row) => (
                <div className="flex items-center justify-end gap-1">
                    <Button
                        size="icon-sm"
                        variant="ghost"
                        title="Editar colaborador"
                        onClick={() => setEditando(row)}
                    >
                        <Pencil className="size-3.5" />
                    </Button>
                    {row.ativo && (
                        <Button
                            size="icon-sm"
                            variant="ghost"
                            title="Desativar colaborador"
                            disabled={desativarMut.isPending}
                            onClick={() => desativarMut.mutate(row.id)}
                            className="text-destructive hover:text-destructive"
                        >
                            <UserX className="size-3.5" />
                        </Button>
                    )}
                </div>
            ),
        },
    ], [desativarMut]);

    const openNovo = () => {
        setEditando(null);
        setShowDialog(true);
    };

    const closeDialog = () => {
        setShowDialog(false);
        setEditando(null);
    };

    const salvar = (payload: ColaboradorPayload) => {
        if (editando) {
            editarMut.mutate({ id: editando.id, payload });
            return;
        }
        criarMut.mutate(payload);
    };

    const dialogAberto = showDialog || !!editando;
    const isPending = criarMut.isPending || editarMut.isPending;

    return (
        <div className="flex flex-col gap-5 p-4 sm:p-6">
            <PageHeader
                title="Colaboradores"
                description="Cadastro operacional de equipe, contratos e valores usados em RH e operações de campo."
                icon={<Users className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Pessoas & RH", href: "/dashboard/rh" },
                    { label: "Colaboradores" }
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <div className="flex h-9 items-center gap-2 rounded-sm border bg-background px-3 text-xs text-muted-foreground">
                            <Switch
                                checked={!apenasAtivos}
                                onCheckedChange={(checked) => setApenasAtivos(!checked)}
                                aria-label="Exibir inativos"
                            />
                            <span>Inativos</span>
                        </div>
                        <Button
                            size="sm"
                            onClick={openNovo}
                            className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                            variant="outline"
                        >
                            <Plus className="size-4 mr-1.5" /> Colaborador
                        </Button>
                    </div>
                }
            />

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <MetricCard icon={<UserCheck className="size-4" />} label="Ativos" value={ativos} loading={isLoading} />
                <MetricCard icon={<UserX className="size-4" />} label="Inativos" value={inativos} loading={isLoading} muted />
                <MetricCard icon={<CalendarDays className="size-4" />} label="Diaristas" value={diaristas} loading={isLoading} />
                <MetricCard icon={<BriefcaseBusiness className="size-4" />} label="Mensalistas/PJ" value={mensalistas} loading={isLoading} />
                <MetricCard icon={<Banknote className="size-4" />} label="Diárias ativas" value={formatCurrency(custoDiario)} loading={isLoading} />
            </div>

            {isLoading ? (
                <div className="space-y-3">
                    <Skeleton className="h-12 w-full rounded-sm" />
                    <Skeleton className="h-64 w-full rounded-sm" />
                </div>
            ) : lista.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10 rounded-lg border border-dashed">
                    <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                        <Users className="size-6 text-primary" />
                    </div>
                    <h3 className="text-lg font-semibold mb-1">{apenasAtivos ? "Nenhum colaborador ativo" : "Nenhum colaborador cadastrado"}</h3>
                    <p className="text-sm text-muted-foreground max-w-sm mb-5">
                        Cadastre colaboradores a partir de uma Pessoa já existente no cadastro central.
                    </p>
                    <Button size="sm" variant="outline" onClick={openNovo} className="rounded-sm">
                        <Plus className="size-4 mr-1.5" /> Cadastrar colaborador
                    </Button>
                </div>
            ) : (
                <DataTable
                    columns={columns}
                    data={lista}
                    searchPlaceholder="Buscar por nome, CPF, cargo ou contrato..."
                    exportFileName="rh-colaboradores"
                    emptyMessage="Nenhum colaborador encontrado."
                    isLoading={isFetching && colaboradores.length === 0}
                />
            )}

            <Dialog open={dialogAberto} onOpenChange={(open) => { if (!open) closeDialog(); }}>
                <ColaboradorForm
                    key={editando?.id ?? "novo"}
                    colaborador={editando}
                    fazendaId={activeFazendaId}
                    onClose={closeDialog}
                    onSubmit={salvar}
                    loading={isPending}
                />
            </Dialog>
        </div>
    );
}

function MetricCard({
    icon,
    label,
    value,
    loading,
    muted = false,
}: {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    loading: boolean;
    muted?: boolean;
}) {
    const borderColor = muted ? "border-l-muted-foreground/60" : "border-l-primary/60";
    return (
        <Card className={`rounded-sm border-l-[3px] ${borderColor} shadow-sm transition-all hover:shadow-md`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{label}</CardTitle>
                <div className={`opacity-50 ${muted ? "text-muted-foreground" : "text-primary"}`}>
                    {icon}
                </div>
            </CardHeader>
            <CardContent>
                <div className={`text-2xl font-black tabular-nums ${muted ? "text-muted-foreground" : "text-foreground"}`}>
                    {loading ? <Skeleton className="h-6 w-14" /> : value}
                </div>
            </CardContent>
        </Card>
    );
}

function PessoaPicker({
    value,
    disabled,
    onSelect,
}: {
    value: PessoaOpcao | null;
    disabled?: boolean;
    onSelect: (pessoa: PessoaOpcao | null) => void;
}) {
    const [busca, setBusca] = useState("");
    const { data: pessoas = [], isFetching } = useQuery<PessoaOpcao[]>({
        queryKey: ["cadastros-pessoas-picker"],
        queryFn: () => apiFetch<PessoaOpcao[]>("/cadastros/pessoas?ativo=true"),
        staleTime: 60_000,
    });

    const filtradas = busca.trim()
        ? pessoas
            .filter((p) => p.nome_exibicao.toLowerCase().includes(busca.trim().toLowerCase()))
            .slice(0, 8)
        : [];

    if (value) {
        return (
            <div className="flex items-center gap-2">
                <Input
                    value={value.nome_exibicao}
                    readOnly
                    disabled={disabled}
                    className="font-medium"
                />
                {!disabled && (
                    <Button type="button" size="sm" variant="outline" onClick={() => onSelect(null)}>
                        <X className="size-3.5" /> Trocar
                    </Button>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-1.5">
            <div className="relative">
                <Search className="absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                    placeholder="Buscar pessoa pelo nome"
                    value={busca}
                    onChange={(e) => setBusca(e.target.value)}
                    className="pl-7"
                    disabled={disabled}
                />
            </div>
            {busca.trim() && (
                <div className="max-h-44 overflow-y-auto rounded-sm border bg-popover shadow-sm">
                    {isFetching ? (
                        <p className="px-3 py-2 text-xs text-muted-foreground">Buscando...</p>
                    ) : filtradas.length === 0 ? (
                        <p className="px-3 py-2 text-xs text-muted-foreground">
                            Nenhuma pessoa encontrada. Cadastre antes em Cadastros &gt; Pessoas.
                        </p>
                    ) : (
                        filtradas.map((pessoa) => (
                            <button
                                type="button"
                                key={pessoa.id}
                                onClick={() => {
                                    onSelect(pessoa);
                                    setBusca("");
                                }}
                                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-accent"
                            >
                                <span className="truncate">{pessoa.nome_exibicao}</span>
                                <Badge variant="outline" className="text-[10px]">{pessoa.tipo}</Badge>
                            </button>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}

function ColaboradorForm({
    colaborador,
    fazendaId,
    onClose,
    onSubmit,
    loading,
}: {
    colaborador: Colaborador | null;
    fazendaId: string | null | undefined;
    onClose: () => void;
    onSubmit: (payload: ColaboradorPayload) => void;
    loading: boolean;
}) {
    const isEditing = !!colaborador;
    const [pessoa, setPessoa] = useState<PessoaOpcao | null>(colaboradorToPessoa(colaborador));
    const { register, handleSubmit, reset, setValue, watch } = useForm<ColaboradorFormValues>({
        defaultValues: {
            cargo: colaborador?.cargo ?? "",
            tipo_contrato: colaborador?.tipo_contrato ?? "DIARISTA",
            valor_diaria: colaborador?.valor_diaria?.toString() ?? "",
            valor_hora: colaborador?.valor_hora?.toString() ?? "",
            data_admissao: colaborador?.data_admissao ?? "",
            observacoes: colaborador?.observacoes ?? "",
            ativo: colaborador?.ativo ?? true,
        },
    });

    const tipoContrato = watch("tipo_contrato");
    const ativo = watch("ativo");

    useEffect(() => {
        setValue("ativo", colaborador?.ativo ?? true);
    }, [colaborador, setValue]);

    const submit = (values: ColaboradorFormValues) => {
        if (!isEditing && !pessoa) {
            toast.error("Selecione uma pessoa para cadastrar o colaborador.");
            return;
        }

        const payload: ColaboradorPayload = {
            tipo_contrato: values.tipo_contrato,
            cargo: values.cargo.trim() || undefined,
            valor_diaria: values.valor_diaria ? Number(values.valor_diaria) : undefined,
            valor_hora: values.valor_hora ? Number(values.valor_hora) : undefined,
            data_admissao: values.data_admissao || undefined,
            unidade_produtiva_id: fazendaId || undefined,
            observacoes: values.observacoes.trim() || undefined,
            ativo: values.ativo,
        };

        if (!isEditing) payload.pessoa_id = pessoa?.id;
        onSubmit(payload);
    };

    const handleClose = () => {
        reset();
        setPessoa(null);
        onClose();
    };

    return (
        <DialogContent className="max-w-xl">
            <DialogHeader className="border-b">
                <DialogTitle>{isEditing ? "Editar colaborador" : "Novo colaborador"}</DialogTitle>
                <DialogDescription>
                    {isEditing ? "Atualize contrato, valores e vínculo operacional." : "Vincule uma pessoa cadastrada e defina os dados de RH."}
                </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit(submit)} className="flex min-h-0 flex-col">
                <div className="grid max-h-[65vh] gap-4 overflow-y-auto px-6 pb-2 md:grid-cols-2">
                    <div className="space-y-2 md:col-span-2">
                        <Label>Pessoa {!isEditing && <span className="text-destructive">*</span>}</Label>
                        <PessoaPicker value={pessoa} disabled={isEditing} onSelect={setPessoa} />
                    </div>

                    <div className="space-y-2">
                        <Label>Cargo</Label>
                        <Input {...register("cargo")} placeholder="Ex: Tratorista" />
                    </div>

                    <div className="space-y-2">
                        <Label>Tipo de contrato <span className="text-destructive">*</span></Label>
                        <Select value={tipoContrato} onValueChange={(value) => setValue("tipo_contrato", value, { shouldDirty: true })}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {contratoOptions.map(([value, label]) => (
                                    <SelectItem key={value} value={value}>{label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Valor diária</Label>
                        <Input {...register("valor_diaria")} type="number" min="0" step="0.01" inputMode="decimal" placeholder="0,00" />
                    </div>

                    <div className="space-y-2">
                        <Label>Valor hora</Label>
                        <Input {...register("valor_hora")} type="number" min="0" step="0.01" inputMode="decimal" placeholder="0,00" />
                    </div>

                    <div className="space-y-2">
                        <Label>Data de admissão</Label>
                        <Input {...register("data_admissao")} type="date" />
                    </div>

                    {isEditing && (
                        <div className="space-y-2">
                            <Label>Status</Label>
                            <div className="flex h-9 w-full items-center justify-between rounded-sm border bg-background px-3 text-sm">
                                <span className="flex items-center gap-2">
                                    {ativo ? <Check className="size-3.5 text-emerald-600" /> : <X className="size-3.5 text-muted-foreground" />}
                                    {ativo ? "Ativo" : "Inativo"}
                                </span>
                                <Switch checked={ativo} onCheckedChange={(checked) => setValue("ativo", checked, { shouldDirty: true })} />
                            </div>
                        </div>
                    )}

                    <div className="space-y-2 md:col-span-2">
                        <Label>Observações</Label>
                        <Textarea {...register("observacoes")} rows={3} placeholder="Informações internas sobre disponibilidade, função ou contrato." />
                    </div>
                </div>

                <DialogFooter className="border-t px-6 pb-6 pt-4">
                    <Button type="button" variant="outline" onClick={handleClose}>
                        Cancelar
                    </Button>
                    <Button type="submit" disabled={loading || (!isEditing && !pessoa)}>
                        {loading ? "Salvando..." : isEditing ? "Salvar alterações" : "Cadastrar"}
                    </Button>
                </DialogFooter>
            </form>
        </DialogContent>
    );
}
