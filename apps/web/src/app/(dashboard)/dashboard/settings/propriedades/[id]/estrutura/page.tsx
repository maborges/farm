"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useAppStore } from "@/lib/stores/app-store";
import { ArrowLeft, Plus, Landmark, FolderTree } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { AreaTreeItem } from "@/components/shared/area-tree";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
    Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import type { AreaRuralTree } from "@farm/zod-schemas";
import Link from "next/link";

const CHILD_TYPES: Record<string, string[]> = {
    PROPRIEDADE: ["GLEBA", "TALHAO", "PASTAGEM", "APP", "RESERVA_LEGAL", "ARMAZEM", "SEDE", "INFRAESTRUTURA"],
    GLEBA: ["TALHAO", "PASTAGEM", "PIQUETE", "APP", "RESERVA_LEGAL"],
    UNIDADE_PRODUTIVA: ["TALHAO", "PASTAGEM", "PIQUETE"],
    TALHAO: [],
    PASTAGEM: ["PIQUETE"],
    PIQUETE: [],
};

const TIPO_LABELS: Record<string, string> = {
    GLEBA: "Gleba", TALHAO: "Talhão", PASTAGEM: "Pastagem",
    PIQUETE: "Piquete", APP: "APP", RESERVA_LEGAL: "Reserva Legal",
    ARMAZEM: "Armazém", SEDE: "Sede", INFRAESTRUTURA: "Infraestrutura",
};

const areaFormSchema = z.object({
    nome: z.string().min(2, "Mínimo 2 caracteres").max(150),
    tipo: z.string().min(1, "Selecione o tipo"),
    codigo: z.string().max(50).optional().or(z.literal("")),
    area_hectares: z.coerce.number().optional().or(z.literal(0)),
    descricao: z.string().max(500).optional().or(z.literal("")),
});

type AreaFormInput = z.infer<typeof areaFormSchema>;
type AreaFormValues = z.input<typeof areaFormSchema>;

/* ─── Página ─── */

export default function EstruturaPropPage() {
    const { id: fazendaId } = useParams<{ id: string }>();
    const router = useRouter();
    const queryClient = useQueryClient();

    const hasHydrated = useAppStore((s) => s._hasHydrated);
    const token = useAppStore((s) => s.token);
    const [isReady, setIsReady] = useState(false);
    useEffect(() => { if (hasHydrated) setIsReady(true); }, [hasHydrated]);

    const [selectedArea, setSelectedArea] = useState<AreaRuralTree | null>(null);
    const [sheetMode, setSheetMode] = useState<"add" | "edit" | null>(null);
    const [addParentId, setAddParentId] = useState<string | null>(null);
    const [addParentType, setAddParentType] = useState<string | null>(null);
    const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; area?: AreaRuralTree }>({ open: false });

    const { data: fazenda } = useQuery<{ id: string; nome: string }>({
        queryKey: ["fazenda", fazendaId],
        queryFn: () => apiFetch(`/fazendas/${fazendaId}`),
        enabled: isReady && !!token && !!fazendaId,
    });

    const { data: areas = [], isLoading } = useQuery<AreaRuralTree[]>({
        queryKey: ["areas-rurais", fazendaId],
        queryFn: async () => {
            const data = await apiFetch<AreaRuralTree[]>(`/cadastros/areas-rurais?unidade_produtiva_id=${fazendaId}`);
            
            // Se o backend retornou uma lista flat, transformamos em árvore localmente
            // caso não tenha vindo com a propriedade "filhos" populada
            if (Array.isArray(data) && data.length > 0 && !data[0].filhos) {
                const map = new Map<string, AreaRuralTree>();
                const roots: AreaRuralTree[] = [];

                data.forEach(item => {
                    map.set(item.id, { ...item, filhos: [] });
                });

                data.forEach(item => {
                    const node = map.get(item.id)!;
                    if (item.parent_id && map.has(item.parent_id)) {
                        map.get(item.parent_id)!.filhos!.push(node);
                    } else {
                        roots.push(node);
                    }
                });
                return roots;
            }
            
            return data;
        },
        enabled: isReady && !!token && !!fazendaId,
    });

    const createMutation = useMutation({
        mutationFn: (data: AreaFormInput & { unidade_produtiva_id: string; parent_id?: string }) =>
            apiFetch("/cadastros/areas-rurais", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            toast.success("Área criada com sucesso!");
            queryClient.invalidateQueries({ queryKey: ["areas-rurais", fazendaId] });
            setSheetMode(null);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao criar área"),
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: Partial<AreaFormInput> }) =>
            apiFetch(`/cadastros/areas-rurais/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        onSuccess: () => {
            toast.success("Área atualizada!");
            queryClient.invalidateQueries({ queryKey: ["areas-rurais", fazendaId] });
            setSheetMode(null);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao atualizar"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/cadastros/areas-rurais/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Área removida.");
            queryClient.invalidateQueries({ queryKey: ["areas-rurais", fazendaId] });
            setSelectedArea(null);
        },
        onError: (err: Error) => toast.error(err.message || "Erro ao remover"),
    });

    function handleAdd(parentId: string, parentType: string) {
        setAddParentId(parentId);
        setAddParentType(parentType);
        setSelectedArea(null);
        setSheetMode("add");
    }

    function handleEdit(area: AreaRuralTree) {
        setSelectedArea(area);
        setSheetMode("edit");
    }

    function handleDelete(area: AreaRuralTree) {
        setDeleteDialog({ open: true, area });
    }

    function handleSubmit(data: AreaFormInput) {
        if (sheetMode === "add") {
            createMutation.mutate({
                ...data,
                unidade_produtiva_id: fazendaId,
                parent_id: addParentId ?? undefined,
            });
        } else if (sheetMode === "edit" && selectedArea) {
            updateMutation.mutate({ id: selectedArea.id, data });
        }
    }

    const isPending = createMutation.isPending || updateMutation.isPending;

    return (
        <div className="p-8 space-y-6">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Button variant="ghost" size="sm" className="gap-1.5 -ml-2" asChild>
                    <Link href="/dashboard/settings/propriedades">
                        <ArrowLeft className="size-4" /> Propriedades
                    </Link>
                </Button>
            </div>

            <PageHeader
                title={fazenda ? `Estrutura — ${fazenda.nome}` : "Estrutura Territorial"}
                description="Gerencie a hierarquia de áreas da propriedade."
                icon={<FolderTree className="size-5" />}
                actions={
                    <Button
                        onClick={() => { setAddParentId(null); setAddParentType("PROPRIEDADE"); setSheetMode("add"); }}
                        className="gap-2"
                    >
                        <Plus className="size-4" /> Adicionar Área
                    </Button>
                }
            />

            {isLoading ? (
                <div className="space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-lg" />)}
                </div>
            ) : areas.length === 0 ? (
                <div className="border-dashed border rounded-lg p-10 text-center space-y-3">
                    <Landmark className="size-12 mx-auto text-muted-foreground opacity-30" />
                    <p className="text-muted-foreground text-sm">Nenhuma área cadastrada. Comece adicionando glebas ou talhões.</p>
                    <Button
                        onClick={() => { setAddParentId(null); setAddParentType("PROPRIEDADE"); setSheetMode("add"); }}
                        className="gap-2"
                    >
                        <Plus className="size-4" /> Adicionar primeira área
                    </Button>
                </div>
            ) : (
                <div className="border rounded-lg p-2 space-y-0.5">
                    {areas.map((area) => (
                        <AreaTreeItem
                            key={area.id}
                            area={area}
                            selectedId={selectedArea?.id}
                            onSelect={setSelectedArea}
                            onAdd={handleAdd}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                        />
                    ))}
                </div>
            )}

            {/* Sheet de add/edit */}
            <AreaFormSheet
                open={sheetMode !== null}
                onOpenChange={(v) => { if (!v) setSheetMode(null); }}
                mode={sheetMode ?? "add"}
                area={sheetMode === "edit" ? selectedArea ?? undefined : undefined}
                parentType={addParentType ?? undefined}
                isPending={isPending}
                onSubmit={handleSubmit}
            />

            <ConfirmDialog
                open={deleteDialog.open}
                title="Remover Área Rural"
                description={`Deseja remover "${deleteDialog.area?.nome}" e todas as áreas filhas? Esta ação não pode ser desfeita.`}
                confirmText="Remover"
                cancelText="Cancelar"
                destructive
                onConfirm={() => deleteDialog.area?.id && deleteMutation.mutate(deleteDialog.area.id)}
                onCancel={() => setDeleteDialog({ open: false })}
            />
        </div>
    );
}

/* ─── Sheet de formulário de área ─── */

function AreaFormSheet({
    open, onOpenChange, mode, area, parentType, isPending, onSubmit,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    mode: "add" | "edit";
    area?: AreaRuralTree;
    parentType?: string;
    isPending: boolean;
    onSubmit: (data: AreaFormInput) => void;
}) {
    const allowedTypes = parentType ? (CHILD_TYPES[parentType] ?? Object.keys(TIPO_LABELS)) : Object.keys(TIPO_LABELS);

    const { register, handleSubmit, setValue, watch, reset, formState: { errors } } = useForm<AreaFormValues, unknown, AreaFormInput>({
        resolver: zodResolver(areaFormSchema),
        defaultValues: area
            ? { nome: area.nome, tipo: area.tipo, codigo: area.codigo ?? "", area_hectares: area.area_hectares ?? 0, descricao: area.descricao ?? "" }
            : { nome: "", tipo: allowedTypes[0] ?? "", codigo: "", area_hectares: 0, descricao: "" },
    });

    useEffect(() => {
        if (open) {
            reset(area
                ? { nome: area.nome, tipo: area.tipo, codigo: area.codigo ?? "", area_hectares: area.area_hectares ?? 0, descricao: area.descricao ?? "" }
                : { nome: "", tipo: allowedTypes[0] ?? "", codigo: "", area_hectares: 0, descricao: "" }
            );
        }
    }, [open, area, reset, allowedTypes]);

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="w-full max-w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-md">
                <SheetHeader className="shrink-0 border-b px-4 py-4 pr-12">
                    <SheetTitle>{mode === "add" ? "Nova Área" : "Editar Área"}</SheetTitle>
                    <SheetDescription>
                        {mode === "add" ? "Adicione uma nova área à hierarquia territorial." : "Atualize os dados desta área."}
                    </SheetDescription>
                </SheetHeader>

                <form onSubmit={handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col overflow-hidden">
                    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
                        <div className="flex flex-col gap-1.5">
                            <Label>Tipo *</Label>
                            <Select
                                value={watch("tipo")}
                                onValueChange={(v: string) => setValue("tipo", v)}
                                disabled={isPending || mode === "edit"}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Selecione o tipo..." />
                                </SelectTrigger>
                                <SelectContent>
                                    {allowedTypes.map((t) => (
                                        <SelectItem key={t} value={t}>{TIPO_LABELS[t] ?? t}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            {errors.tipo && <p className="text-xs text-destructive">{errors.tipo.message}</p>}
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <Label>Nome *</Label>
                            <Input {...register("nome")} placeholder="Ex: Gleba Norte, Talhão 01..." disabled={isPending} />
                            {errors.nome && <p className="text-xs text-destructive">{errors.nome.message}</p>}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="flex flex-col gap-1.5">
                                <Label>Área (ha)</Label>
                                <Input
                                    type="number" step="0.0001"
                                    className="tabular-nums"
                                    {...register("area_hectares")}
                                    placeholder="0.0000"
                                    disabled={isPending}
                                />
                            </div>
                            <div className="flex flex-col gap-1.5">
                                <Label>Código / Sigla</Label>
                                <Input {...register("codigo")} placeholder="T01, G-A..." disabled={isPending} />
                            </div>
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <Label>Descrição</Label>
                            <Textarea
                                {...register("descricao")}
                                className="min-h-20 resize-y"
                                placeholder="Observações opcionais..."
                                disabled={isPending}
                            />
                        </div>
                    </div>

                    <SheetFooter className="shrink-0 border-t px-4 py-3 sm:flex-row sm:justify-end">
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending ? "Salvando..." : mode === "add" ? "Adicionar" : "Salvar"}
                        </Button>
                    </SheetFooter>
                </form>
            </SheetContent>
        </Sheet>
    );
}
