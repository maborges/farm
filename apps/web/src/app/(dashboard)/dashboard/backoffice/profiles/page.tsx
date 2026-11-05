"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
    DndContext,
    DragOverlay,
    closestCenter,
    PointerSensor,
    useSensor,
    useSensors,
    type DragStartEvent,
    type DragEndEvent,
    type DragOverEvent,
    useDroppable,
} from "@dnd-kit/core";
import {
    SortableContext,
    useSortable,
    verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
    Shield, Plus, Pencil, Trash2, GripVertical,
    Eye, EyeOff, Check, Info, Users, Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import {
    Dialog, DialogContent, DialogDescription,
    DialogHeader, DialogTitle, DialogTrigger, DialogBody, DialogFooter,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

/* ─── Tipos ─── */

interface SystemProfile {
    id: string;
    nome: string;
    descricao: string | null;
    is_custom: boolean;
    permissoes: Record<string, string>;
    em_uso: number;
}

type PermCol = "none" | "read" | "write";

/* ─── Constantes ─── */

const PERMISSION_MODULES = [
    { key: "agricola", label: "Agricultura", icon: "🌱" },
    { key: "pecuaria", label: "Pecuária", icon: "🐄" },
    { key: "financeiro", label: "Financeiro", icon: "💰" },
    { key: "operacional", label: "Operacional", icon: "⚙️" },
    { key: "rh", label: "RH / Equipe", icon: "👥" },
    { key: "ambiental", label: "Ambiental", icon: "🌿" },
    { key: "relatorios", label: "Relatórios", icon: "📊" },
    { key: "configuracoes", label: "Configurações", icon: "🔧" },
] as const;

type PermKey = (typeof PERMISSION_MODULES)[number]["key"];

const COLUMNS: { id: PermCol; label: string; color: string; bg: string; border: string; accent: string }[] = [
    { id: "none", label: "Sem Acesso", color: "text-muted-foreground", bg: "bg-muted/20", border: "border-muted/40", accent: "bg-muted-foreground/20" },
    { id: "read", label: "Somente Leitura", color: "text-blue-700 dark:text-blue-100", bg: "bg-blue-500/5 dark:bg-blue-500/20", border: "border-blue-400/30", accent: "bg-blue-400" },
    { id: "write", label: "Escrita Completa", color: "text-emerald-700 dark:text-emerald-100", bg: "bg-emerald-500/5 dark:bg-emerald-500/20", border: "border-emerald-400/30", accent: "bg-emerald-500" },
];

/* ─── Página ─── */

export default function BackofficeProfilesPage() {
    const queryClient = useQueryClient();
    const [createOpen, setCreateOpen] = useState(false);
    const [editTarget, setEditTarget] = useState<SystemProfile | null>(null);

    const { data: profiles, isLoading } = useQuery<SystemProfile[]>({
        queryKey: ["backoffice", "profiles"],
        queryFn: () => apiFetch("/backoffice/profiles"),
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => apiFetch(`/backoffice/profiles/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Perfil padrão removido!");
            queryClient.invalidateQueries({ queryKey: ["backoffice", "profiles"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <div className="space-y-2">
                    <Skeleton className="h-8 w-72" />
                    <Skeleton className="h-4 w-96" />
                </div>
                <Skeleton className="h-12 w-full rounded-sm" />
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-44 rounded-sm" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <PageHeader
                title="Perfis Padrão do Sistema"
                description="Perfis globais disponíveis para todos os produtores. Alterações refletem imediatamente."
                icon={<Shield className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Perfis & Permissões" },
                ]}
                actions={
                    <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                        <DialogTrigger asChild>
                            <Button variant="outline" size="sm" className="gap-2">
                                <Plus size={14} aria-hidden />
                                Novo Perfil Padrão
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="w-[90vw] sm:max-w-5xl max-h-[90dvh] overflow-hidden p-0">
                            <DialogHeader className="border-b px-6 py-5">
                                <div className="flex items-start gap-3">
                                    <div className="rounded-sm border bg-primary/5 p-2 text-primary">
                                        <Shield size={18} aria-hidden />
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <DialogTitle>Criar Perfil Padrão</DialogTitle>
                                        <DialogDescription>
                                    Este perfil ficará disponível para todos os produtores da plataforma.
                                    Arraste os módulos entre as colunas para definir o nível de acesso.
                                        </DialogDescription>
                                    </div>
                                </div>
                            </DialogHeader>
                            <SystemProfileForm
                                submitLabel="Criar Perfil Padrão"
                                onCancel={() => setCreateOpen(false)}
                                onSuccess={() => {
                                    setCreateOpen(false);
                                    queryClient.invalidateQueries({ queryKey: ["backoffice", "profiles"] });
                                }}
                            />
                        </DialogContent>
                    </Dialog>
                }
            />

            {/* Info banner */}
            <div className="rounded-sm border border-amber-400/30 bg-amber-500/5 px-4 py-3 flex items-start gap-3">
                <Lock size={15} className="text-amber-500 mt-0.5 shrink-0" aria-hidden />
                <div>
                    <p className="text-sm font-medium text-amber-700 dark:text-amber-400">Atenção: impacto global</p>
                    <p className="text-xs text-muted-foreground mt-0.5 text-pretty">
                        Editar ou remover um perfil padrão afeta todos os produtores que o utilizam.
                        Perfis em uso não podem ser removidos sem reatribuição.
                    </p>
                </div>
            </div>

            {/* Grid de perfis */}
            {profiles?.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
                        <Shield size={40} className="opacity-20" aria-hidden />
                        <div className="text-center space-y-1">
                            <p className="text-sm font-medium text-foreground">Nenhum perfil padrão cadastrado</p>
                            <p className="text-xs text-pretty">Crie perfis que estarão disponíveis para todos os produtores.</p>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            className="gap-2 mt-2"
                            onClick={() => setCreateOpen(true)}
                        >
                            <Plus size={14} aria-hidden />
                            Criar primeiro perfil
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {profiles?.map((profile) => (
                        <SystemProfileCard
                            key={profile.id}
                            profile={profile}
                            onEdit={() => setEditTarget(profile)}
                            onDelete={() => deleteMutation.mutate(profile.id)}
                            isDeleting={deleteMutation.isPending}
                        />
                    ))}
                </div>
            )}

            {/* Dialog de Edição */}
            <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
                <DialogContent className="w-[90vw] sm:max-w-5xl max-h-[90dvh] overflow-hidden p-0">
                    <DialogHeader className="border-b px-6 py-5">
                        <div className="flex items-start gap-3">
                            <div className="rounded-sm border bg-primary/5 p-2 text-primary">
                                <Pencil size={18} aria-hidden />
                            </div>
                            <div className="flex flex-col gap-1">
                                <DialogTitle>Editar Perfil Padrão</DialogTitle>
                                <DialogDescription>
                            Alterações em &quot;{editTarget?.nome}&quot; refletem em todos os produtores que usam este perfil.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    {editTarget && (
                        <SystemProfileForm
                            profile={editTarget}
                            submitLabel="Salvar Alterações"
                            onCancel={() => setEditTarget(null)}
                            onSuccess={() => {
                                setEditTarget(null);
                                queryClient.invalidateQueries({ queryKey: ["backoffice", "profiles"] });
                            }}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}

/* ─── Card de Perfil Padrão ─── */

function SystemProfileCard({
    profile, onEdit, onDelete, isDeleting,
}: {
    profile: SystemProfile;
    onEdit: () => void;
    onDelete: () => void;
    isDeleting: boolean;
}) {
    const writeCount = Object.values(profile.permissoes).filter((v) => v === "write").length;
    const readCount = Object.values(profile.permissoes).filter((v) => v === "read").length;
    const noneCount = PERMISSION_MODULES.length - writeCount - readCount;

    return (
        <Card className="group border-border hover:shadow-sm transition-shadow border-l-[3px] border-l-primary">
            <CardHeader className="pb-2 pt-4 px-4">
                <div className="flex items-start justify-between gap-1">
                    <div className="flex-1 min-w-0">
                        <CardTitle className="text-sm truncate">{profile.nome}</CardTitle>
                        {profile.descricao && (
                            <CardDescription className="text-xs leading-snug mt-0.5 text-pretty line-clamp-2">
                                {profile.descricao}
                            </CardDescription>
                        )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                        <Button
                            variant="ghost"
                            size="sm"
                            aria-label={`Editar perfil ${profile.nome}`}
                            className="size-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={onEdit}
                        >
                            <Pencil size={11} aria-hidden />
                        </Button>
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    aria-label={`Remover perfil ${profile.nome}`}
                                    className="size-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive"
                                    disabled={isDeleting}
                                >
                                    <Trash2 size={11} aria-hidden />
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Remover &quot;{profile.nome}&quot;?</AlertDialogTitle>
                                    <AlertDialogDescription className="text-pretty">
                                        {profile.em_uso > 0
                                            ? `Este perfil está em uso por ${profile.em_uso} usuário(s). Reatribua-os antes de remover.`
                                            : "Esta ação remove o perfil de todos os produtores que o utilizam."}
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                    <AlertDialogAction
                                        onClick={onDelete}
                                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        disabled={profile.em_uso > 0}
                                    >
                                        Remover
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
                <div className="flex h-1.5 rounded-full overflow-hidden gap-px mb-2" role="img" aria-label={`${writeCount} escrita, ${readCount} leitura, ${noneCount} sem acesso`}>
                    {writeCount > 0 && <div className="bg-green-500 rounded-full" style={{ flex: writeCount }} />}
                    {readCount > 0 && <div className="bg-blue-400 rounded-full" style={{ flex: readCount }} />}
                    {noneCount > 0 && <div className="bg-muted rounded-full" style={{ flex: noneCount }} />}
                </div>
                <div className="flex items-center gap-3 text-xs tabular-nums">
                    <span className="flex items-center gap-1 text-green-600">
                        <Check size={10} aria-hidden /><b>{writeCount}</b>
                    </span>
                    <span className="flex items-center gap-1 text-blue-500">
                        <Eye size={10} aria-hidden /><b>{readCount}</b>
                    </span>
                    <span className="flex items-center gap-1 text-muted-foreground">
                        <EyeOff size={10} aria-hidden /><b>{noneCount}</b>
                    </span>
                </div>
                <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
                    <Users size={10} aria-hidden />
                    <span>{profile.em_uso} produtor{profile.em_uso !== 1 ? "es" : ""} usando</span>
                </div>
            </CardContent>
        </Card>
    );
}

/* ─── Formulário com DnD 3 colunas ─── */

function SystemProfileForm({
    profile,
    onSuccess,
    onCancel,
    submitLabel,
}: {
    profile?: SystemProfile;
    onSuccess: () => void;
    onCancel: () => void;
    submitLabel: string;
}) {
    const isEditing = !!profile;

    const buildInitial = useCallback((): Record<PermCol, PermKey[]> => {
        const initial: Record<PermCol, PermKey[]> = { none: [], read: [], write: [] };
        for (const mod of PERMISSION_MODULES) {
            const level = (profile?.permissoes?.[mod.key] ?? "none") as PermCol;
            initial[level].push(mod.key);
        }
        return initial;
    }, [profile]);

    const [nome, setNome] = useState(profile?.nome ?? "");
    const [descricao, setDescricao] = useState(profile?.descricao ?? "");
    const [nomeError, setNomeError] = useState("");
    const [columns, setColumns] = useState<Record<PermCol, PermKey[]>>(buildInitial);
    const [activeDragId, setActiveDragId] = useState<PermKey | null>(null);
    const [overCol, setOverCol] = useState<PermCol | null>(null);

    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

    function findColumn(key: PermKey): PermCol {
        for (const col of ["none", "read", "write"] as PermCol[]) {
            if (columns[col].includes(key)) return col;
        }
        return "none";
    }

    function handleDragStart(event: DragStartEvent) {
        setActiveDragId(event.active.id as PermKey);
    }

    function handleDragOver(event: DragOverEvent) {
        const overId = String(event.over?.id ?? "");
        if (["none", "read", "write"].includes(overId)) {
            setOverCol(overId as PermCol);
        } else {
            for (const col of ["none", "read", "write"] as PermCol[]) {
                if (columns[col].includes(overId as PermKey)) { setOverCol(col); break; }
            }
        }
    }

    function handleDragEnd(event: DragEndEvent) {
        const { active, over } = event;
        setActiveDragId(null);
        setOverCol(null);
        if (!over) return;
        const draggedKey = active.id as PermKey;
        const overId = String(over.id);
        const targetCol = (["none", "read", "write"].includes(overId)
            ? overId
            : findColumn(overId as PermKey)) as PermCol;
        const sourceCol = findColumn(draggedKey);
        if (sourceCol === targetCol) return;
        setColumns((prev) => {
            const next = { none: [...prev.none], read: [...prev.read], write: [...prev.write] };
            next[sourceCol] = next[sourceCol].filter((k) => k !== draggedKey);
            next[targetCol] = [...next[targetCol], draggedKey];
            return next;
        });
    }

    const mutation = useMutation({
        mutationFn: () => {
            const permissoes: Record<string, string> = {};
            for (const col of ["none", "read", "write"] as PermCol[]) {
                for (const key of columns[col]) permissoes[key] = col;
            }
            const payload = { nome, descricao: descricao || null, permissoes };
            const url = isEditing ? `/backoffice/profiles/${profile.id}` : "/backoffice/profiles";
            const method = isEditing ? "PATCH" : "POST";
            return apiFetch(url, { method, body: JSON.stringify(payload) });
        },
        onSuccess: () => {
            toast.success(isEditing ? "Perfil atualizado!" : "Perfil criado!");
            onSuccess();
        },
        onError: (err: Error) => toast.error(err.message),
    });

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!nome.trim() || nome.trim().length < 3) {
            setNomeError("Nome deve ter pelo menos 3 caracteres.");
            return;
        }
        setNomeError("");
        mutation.mutate();
    }

    const activeMod = activeDragId ? PERMISSION_MODULES.find((m) => m.key === activeDragId) : null;

    return (
        <form onSubmit={handleSubmit} className="flex max-h-[calc(90dvh-9rem)] flex-col">
            <DialogBody className="overflow-y-auto px-6 py-5">
                <div className="flex gap-6 items-start">
                {/* Esquerda: campos + salvar */}
                    <div className="flex w-64 shrink-0 flex-col gap-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="sp-nome">Nome do Perfil *</Label>
                        <Input
                            id="sp-nome"
                            value={nome}
                            onChange={(e) => setNome(e.target.value)}
                            placeholder="Ex: Operador de Campo"
                        />
                        {nomeError && (
                            <p className="text-xs text-destructive" role="alert">{nomeError}</p>
                        )}
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="sp-desc">Descrição</Label>
                        <Textarea
                            id="sp-desc"
                            value={descricao}
                            onChange={(e) => setDescricao(e.target.value)}
                            placeholder="Descreva brevemente o propósito deste perfil..."
                            rows={4}
                            className="resize-none text-sm"
                        />
                    </div>
                    </div>

                {/* Direita: DnD */}
                    <div className="min-w-0 flex-1">
                        <div className="mb-3 flex items-center gap-2">
                            <Label>Permissões por Módulo</Label>
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                <Info size={10} aria-hidden /> Arraste os módulos entre as colunas
                            </span>
                        </div>

                        <DndContext
                            sensors={sensors}
                            collisionDetection={closestCenter}
                            autoScroll={false}
                            onDragStart={handleDragStart}
                            onDragOver={handleDragOver}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="grid grid-cols-3 gap-3">
                                {COLUMNS.map((col) => (
                                    <DropZone
                                        key={col.id}
                                        col={col}
                                        keys={columns[col.id]}
                                        isOver={overCol === col.id}
                                    />
                                ))}
                            </div>
                            <DragOverlay dropAnimation={null}>
                                {activeMod && (
                                    <ModuleChip
                                        modKey={activeMod.key}
                                        label={activeMod.label}
                                        icon={activeMod.icon}
                                        level="none"
                                        isDragging
                                    />
                                )}
                            </DragOverlay>
                        </DndContext>
                    </div>
                </div>
            </DialogBody>
            <DialogFooter className="gap-2 border-t px-6 py-4">
                <Button type="button" variant="outline" size="sm" onClick={onCancel}>
                    Cancelar
                </Button>
                <Button type="submit" variant="outline" size="sm" disabled={mutation.isPending}>
                    {mutation.isPending ? "Salvando..." : submitLabel}
                </Button>
            </DialogFooter>
        </form>
    );
}

/* ─── Drop Zone ─── */

function DropZone({ col, keys, isOver }: {
    col: (typeof COLUMNS)[number];
    keys: PermKey[];
    isOver: boolean;
}) {
    const { setNodeRef } = useDroppable({ id: col.id });

    return (
        <div
            ref={setNodeRef}
            className={cn(
                "rounded-sm border-2 flex flex-col overflow-hidden",
                isOver
                    ? cn(col.border, col.bg, "shadow-sm")
                    : "border-muted/30 bg-muted/10"
            )}
        >
            {/* Header */}
            <div className={cn("px-3 pt-3 pb-2 border-b border-inherit", isOver && col.bg)}>
                <div className={cn("h-0.5 w-8 rounded-full mb-2", col.accent)} />
                <p className={cn("text-xs font-bold", col.color)}>{col.label}</p>
                <div className="flex items-center justify-between mt-0.5">
                    <p className="text-xs text-muted-foreground tabular-nums">
                        {keys.length} módulo{keys.length !== 1 ? "s" : ""}
                    </p>
                    {keys.length > 0 && (
                        <span className={cn(
                            "text-xs font-semibold px-1.5 py-0.5 rounded-full border",
                            col.border, col.color
                        )}>
                            {col.id === "write" ? "R+W" : col.id === "read" ? "R" : "—"}
                        </span>
                    )}
                </div>
            </div>

            {/* Chips em grid 2 colunas */}
            <SortableContext items={keys} strategy={verticalListSortingStrategy}>
                <div className="p-2 flex-1 grid grid-cols-2 gap-1.5 content-start min-h-40">
                    {keys.length === 0 && (
                        <div className="col-span-2 flex flex-col items-center justify-center py-6 text-muted-foreground/40 select-none gap-1">
                            <GripVertical size={16} aria-hidden />
                            <p className="text-xs">Arraste aqui</p>
                        </div>
                    )}
                    {keys.map((key) => {
                        const mod = PERMISSION_MODULES.find((m) => m.key === key)!;
                        return (
                            <SortableModuleChip
                                key={key}
                                modKey={key}
                                label={mod.label}
                                icon={mod.icon}
                                level={col.id}
                            />
                        );
                    })}
                </div>
            </SortableContext>
        </div>
    );
}

/* ─── Module Chips ─── */

function SortableModuleChip({ modKey, label, icon, level }: {
    modKey: PermKey;
    label: string;
    icon: string;
    level: PermCol;
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: modKey });
    const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.2 : 1 };
    return (
        <div ref={setNodeRef} style={style}>
            <ModuleChip
                modKey={modKey}
                label={label}
                icon={icon}
                level={level}
                dragProps={{ ...attributes, ...listeners }}
            />
        </div>
    );
}

function ModuleChip({ label, icon, level, isDragging, dragProps }: {
    modKey: PermKey;
    label: string;
    icon: string;
    level: PermCol;
    isDragging?: boolean;
    dragProps?: React.HTMLAttributes<HTMLDivElement>;
}) {
    return (
        <div
            {...dragProps}
            aria-label={`Módulo ${label}`}
            className={cn(
                "flex items-center gap-1.5 px-2 py-1.5 rounded-sm border text-xs font-medium",
                "cursor-grab active:cursor-grabbing select-none w-full",
                level === "write" && "border-green-400/40 bg-green-500/5 text-green-700",
                level === "read" && "border-blue-400/40 bg-blue-500/5 text-blue-700",
                level === "none" && "border-border text-muted-foreground bg-background",
                isDragging && "shadow-lg ring-1 ring-primary/20",
                !isDragging && "hover:shadow-sm",
            )}
        >
            <span className="text-sm leading-none shrink-0" aria-hidden>{icon}</span>
            <span className="truncate flex-1 leading-tight">{label}</span>
            <GripVertical size={9} className="opacity-30 shrink-0" aria-hidden />
        </div>
    );
}
