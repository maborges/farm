"use client";

import { useState, useCallback, useEffect } from "react";
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
    useDroppable,
    type DragStartEvent,
    type DragEndEvent,
} from "@dnd-kit/core";
import {
    SortableContext,
    useSortable,
    arrayMove,
    rectSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
    Shield, Plus, Pencil, Trash2, Lock, GripVertical,
    ChevronDown, ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogDescription,
    DialogHeader, DialogTitle, DialogTrigger, DialogBody, DialogFooter,
} from "@/components/ui/dialog";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Separator } from "@/components/ui/separator";
import { PermissionGuard } from "@/components/auth/permission-guard";
import {
    PERMISSION_CATALOG,
    ACTION_LABELS,
    ACTION_COLORS,
    isGranted,
    buildGrantedSet,
    revokeGranted,
    type PermAction,
} from "@/lib/permission-catalog";
import type { TenantRoleProfile } from "@/types/global";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getGranted(permissoes: Record<string, unknown> | null | undefined): string[] {
    if (!permissoes) return [];
    const granted = (permissoes.granted ?? permissoes.permissions) as string[] | undefined;
    if (granted) return granted;
    // Formato legado {"agricola": "write"} → converter
    const result: string[] = [];
    for (const [mod, level] of Object.entries(permissoes)) {
        if (level === "write" || level === "*") result.push(`${mod}:*`);
        else if (level === "read") result.push(`${mod}:*:view`, `${mod}:*:list`, `${mod}:*:export`);
    }
    return result;
}

function countGranted(granted: string[]): number {
    // Contar permissões individuais expandindo wildcards
    if (granted.includes("*")) return 999;
    let total = 0;
    for (const p of granted) {
        if (!p.includes("*")) total++;
        else total += 3; // estimativa para wildcards
    }
    return total;
}

// ─── Componente de árvore de permissões ───────────────────────────────────────

function PermissionTree({
    granted,
    onChange,
    readonly = false,
}: {
    granted: string[];
    onChange?: (granted: string[]) => void;
    readonly?: boolean;
}) {
    const [expanded, setExpanded] = useState<Set<string>>(() => new Set([PERMISSION_CATALOG[0]?.key]));
    const grantedSet = buildGrantedSet(granted);

    const toggleExpand = (key: string) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            next.has(key) ? next.delete(key) : next.add(key);
            return next;
        });
    };

    const toggle = (permission: string) => {
        if (readonly || !onChange) return;
        if (isGranted(grantedSet, permission)) {
            onChange(revokeGranted(granted, permission));
        } else {
            onChange([...granted, permission]);
        }
    };

    // Toggle todos os recursos de um módulo
    const toggleModule = (moduleKey: string) => {
        if (readonly || !onChange) return;
        const mod = PERMISSION_CATALOG.find((m) => m.key === moduleKey);
        if (!mod) return;
        const allPerms = mod.resources.flatMap((r) => r.actions.map((a) => `${r.key}:${a}`));
        const allChecked = allPerms.every((p) => isGranted(grantedSet, p));
        if (allChecked) {
            onChange(allPerms.reduce((acc, p) => revokeGranted(acc, p), granted));
        } else {
            const toAdd = allPerms.filter((p) => !isGranted(grantedSet, p));
            onChange([...granted, ...toAdd]);
        }
    };

    // Toggle todas as ações de um recurso
    const toggleResource = (resourceKey: string, actions: PermAction[]) => {
        if (readonly || !onChange) return;
        const allPerms = actions.map((a) => `${resourceKey}:${a}`);
        const allChecked = allPerms.every((p) => isGranted(grantedSet, p));
        if (allChecked) {
            onChange(allPerms.reduce((acc, p) => revokeGranted(acc, p), granted));
        } else {
            const toAdd = allPerms.filter((p) => !isGranted(grantedSet, p));
            onChange([...granted, ...toAdd]);
        }
    };

    return (
        <div className="space-y-1">
            {PERMISSION_CATALOG.map((mod) => {
                const isOpen = expanded.has(mod.key);
                const allModPerms = mod.resources.flatMap((r) => r.actions.map((a) => `${r.key}:${a}`));
                const checkedCount = allModPerms.filter((p) => isGranted(grantedSet, p)).length;
                const modChecked = checkedCount === allModPerms.length;
                const modIndeterminate = checkedCount > 0 && !modChecked;

                return (
                    <div key={mod.key} className="border rounded-lg overflow-hidden">
                        {/* Header do módulo */}
                        <div
                            className="flex items-center gap-2 px-3 py-2 bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors select-none"
                            onClick={() => toggleExpand(mod.key)}
                        >
                            {isOpen ? <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                            {!readonly && (
                                <Checkbox
                                    checked={modChecked}
                                    data-indeterminate={modIndeterminate}
                                    onCheckedChange={() => toggleModule(mod.key)}
                                    onClick={(e) => e.stopPropagation()}
                                    className="shrink-0"
                                />
                            )}
                            <span className="text-sm">{mod.icon}</span>
                            <span className="text-sm font-semibold flex-1">{mod.label}</span>
                            <Badge variant="outline" className="text-[10px] font-normal">
                                {checkedCount}/{allModPerms.length}
                            </Badge>
                        </div>

                        {/* Recursos do módulo */}
                        {isOpen && (
                            <div className="divide-y">
                                {mod.resources.map((res) => {
                                    const resPerms = res.actions.map((a) => `${res.key}:${a}`);
                                    const resChecked = resPerms.every((p) => isGranted(grantedSet, p));
                                    const resIndeterminate = resPerms.some((p) => isGranted(grantedSet, p)) && !resChecked;

                                    return (
                                        <div key={res.key} className="px-3 py-2">
                                            <div className="flex items-center gap-2 mb-1.5">
                                                {!readonly && (
                                                    <Checkbox
                                                        checked={resChecked}
                                                        data-indeterminate={resIndeterminate}
                                                        onCheckedChange={() => toggleResource(res.key, res.actions)}
                                                        className="shrink-0"
                                                    />
                                                )}
                                                <span className="text-xs font-medium text-foreground">{res.label}</span>
                                            </div>
                                            <div className="flex flex-wrap gap-1.5 pl-5">
                                                {res.actions.map((action) => {
                                                    const perm = `${res.key}:${action}`;
                                                    const checked = isGranted(grantedSet, perm);
                                                    return (
                                                        <label
                                                            key={action}
                                                            className={cn(
                                                                "flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded border cursor-pointer transition-colors",
                                                                checked
                                                                    ? "bg-primary/8 border-primary/30 text-primary"
                                                                    : "border-muted text-muted-foreground hover:border-muted-foreground/40",
                                                                readonly && "cursor-default"
                                                            )}
                                                        >
                                                            <Checkbox
                                                                checked={checked}
                                                                onCheckedChange={() => toggle(perm)}
                                                                disabled={readonly}
                                                                className="h-3 w-3"
                                                            />
                                                            <span className={cn("font-medium", checked && ACTION_COLORS[action])}>
                                                                {ACTION_LABELS[action]}
                                                            </span>
                                                        </label>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

// ─── Formulário de criação/edição ─────────────────────────────────────────────

function RoleForm({ role, onSuccess }: { role?: TenantRoleProfile; onSuccess: () => void }) {
    const isEditing = !!role;

    const buildInitial = useCallback((): string[] => {
        return getGranted(role?.permissoes as Record<string, unknown> | undefined);
    }, [role]);

    const [nome, setNome] = useState(role?.nome ?? "");
    const [descricao, setDescricao] = useState(role?.descricao ?? "");
    const [nomeError, setNomeError] = useState("");
    const [granted, setGranted] = useState<string[]>(buildInitial);

    const mutation = useMutation({
        mutationFn: () => {
            const payload = { nome, descricao: descricao || null, permissoes: { granted } };
            const url = isEditing ? `/team/roles/${role.id}` : "/team/roles";
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

    return (
        <form onSubmit={handleSubmit}>
            <DialogBody className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="rf-nome">Nome do Perfil *</Label>
                        <Input
                            id="rf-nome"
                            value={nome}
                            onChange={(e) => setNome(e.target.value)}
                            placeholder="Ex: Auditor Externo"
                        />
                        {nomeError && <p className="text-xs text-red-500">{nomeError}</p>}
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="rf-desc">Descrição</Label>
                        <Textarea
                            id="rf-desc"
                            value={descricao}
                            onChange={(e) => setDescricao(e.target.value)}
                            placeholder="Finalidade deste perfil..."
                            rows={2}
                            className="resize-none"
                        />
                    </div>
                </div>

                <div>
                    <div className="flex items-center justify-between mb-2">
                        <Label>Permissões por Módulo / Recurso / Ação</Label>
                        <span className="text-[10px] text-muted-foreground">
                            {countGranted(granted)} permissão(ões) selecionada(s)
                        </span>
                    </div>
                    <div className="max-h-[50vh] overflow-y-auto border rounded-lg p-2 space-y-1">
                        <PermissionTree granted={granted} onChange={setGranted} />
                    </div>
                </div>
            </DialogBody>

            <DialogFooter>
                <Button
                    type="submit"
                    variant="outline"
                    size="sm"
                    disabled={mutation.isPending}
                    className="bg-primary border-primary text-primary-foreground hover:bg-primary/90"
                >
                    {mutation.isPending ? "Salvando..." : isEditing ? "Salvar Alterações" : "Criar Perfil"}
                </Button>
            </DialogFooter>
        </form>
    );
}

// ─── Cards de perfil ──────────────────────────────────────────────────────────

function RoleCardContent({ role, onClone }: { role: TenantRoleProfile; onClone?: () => void }) {
    const granted = getGranted(role.permissoes as Record<string, unknown> | undefined);
    const total = countGranted(granted);
    const isFullAccess = granted.includes("*");

    return (
        <>
            {role.descricao && (
                <CardDescription className="text-[11px] leading-snug mt-0.5">{role.descricao}</CardDescription>
            )}
            <div className="mt-2 text-[11px] text-muted-foreground">
                {isFullAccess ? (
                    <span className="font-medium text-primary">Acesso total</span>
                ) : total === 0 ? (
                    <span className="italic">Sem permissões</span>
                ) : (
                    <span><b className="text-foreground">{total}</b> permissão(ões)</span>
                )}
            </div>
            {onClone && (
                <PermissionGuard permission="tenant:permissions:create" fallback={null}>
                    <Button variant="outline" size="sm" className="w-full h-7 text-xs gap-1.5 mt-2" onClick={onClone}>
                        <Plus size={11} />
                        Usar como base
                    </Button>
                </PermissionGuard>
            )}
        </>
    );
}

function SystemRoleCard({ role, isDragging, onClone }: { role: TenantRoleProfile; isDragging?: boolean; onClone?: () => void }) {
    return (
        <Card className={`border-muted transition-all ${isDragging ? "" : "hover:shadow-sm"}`}>
            <CardHeader className="pb-1 pt-4 px-4">
                <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm leading-tight">{role.nome}</CardTitle>
                    <Lock size={11} className="text-muted-foreground/50 mt-0.5 shrink-0" />
                </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
                <RoleCardContent role={role} onClone={onClone} />
            </CardContent>
        </Card>
    );
}

function SortableRoleCard({
    role, onEdit, onDelete, isDeleting,
}: {
    role: TenantRoleProfile;
    onEdit: () => void;
    onDelete: () => void;
    isDeleting: boolean;
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: role.id });
    const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 };

    return (
        <div ref={setNodeRef} style={style}>
            <Card className="border-cyan-500/20 hover:shadow-md transition-all group">
                <CardHeader className="pb-1 pt-4 px-4">
                    <div className="flex items-start justify-between gap-1">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                            <button
                                {...attributes}
                                {...listeners}
                                className="text-muted-foreground/40 hover:text-muted-foreground cursor-grab active:cursor-grabbing touch-none shrink-0"
                                aria-label="Arrastar para reordenar"
                            >
                                <GripVertical size={14} />
                            </button>
                            <CardTitle className="text-sm truncate">{role.nome}</CardTitle>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                            <PermissionGuard permission="tenant:permissions:update">
                                <Button
                                    variant="ghost" size="sm"
                                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={onEdit}
                                >
                                    <Pencil size={11} />
                                </Button>
                            </PermissionGuard>
                            <PermissionGuard permission="tenant:permissions:delete">
                                <AlertDialog>
                                    <AlertDialogTrigger render={<Button variant="ghost" size="sm" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-red-400 hover:text-red-500" disabled={isDeleting} />}>
                                        <Trash2 size={11} />
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>Excluir &quot;{role.nome}&quot;?</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                {role.em_uso && role.em_uso > 0
                                                    ? `Este perfil está em uso por ${role.em_uso} membro(s). Reatribua-os antes de excluir.`
                                                    : "Esta ação não pode ser desfeita."}
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                            <AlertDialogAction
                                                onClick={onDelete}
                                                className="bg-red-500 hover:bg-red-600"
                                                disabled={!!(role.em_uso && role.em_uso > 0)}
                                            >
                                                Excluir
                                            </AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            </PermissionGuard>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                    <RoleCardContent role={role} />
                    {role.em_uso !== undefined && role.em_uso > 0 && (
                        <p className="text-[10px] text-muted-foreground mt-1">
                            {role.em_uso} membro{role.em_uso > 1 ? "s" : ""} usando este perfil
                        </p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

// ─── Zona de exclusão por drag ────────────────────────────────────────────────

function TrashZone() {
    const { setNodeRef, isOver } = useDroppable({ id: "__trash__" });
    return (
        <div
            ref={setNodeRef}
            className={cn(
                "fixed bottom-8 left-1/2 -translate-x-1/2 z-50",
                "flex items-center gap-2 px-6 py-3 rounded-full border-2",
                "pointer-events-none select-none transition-colors",
                isOver
                    ? "border-destructive bg-destructive text-destructive-foreground shadow-lg"
                    : "border-destructive/40 bg-background text-destructive shadow-md"
            )}
        >
            <Trash2 size={15} aria-hidden />
            <span className="text-sm font-medium">Solte para excluir</span>
        </div>
    );
}

// ─── Página principal ─────────────────────────────────────────────────────────

export function RolesClient({ initialRoles }: { initialRoles: TenantRoleProfile[] }) {
    const queryClient = useQueryClient();
    const [createOpen, setCreateOpen] = useState(false);
    const [editTarget, setEditTarget] = useState<TenantRoleProfile | null>(null);
    const [cloneTarget, setCloneTarget] = useState<TenantRoleProfile | null>(null);
    const [cloneName, setCloneName] = useState("");
    const [orderedCustomIds, setOrderedCustomIds] = useState<string[]>([]);
    const [activeCardId, setActiveCardId] = useState<string | null>(null);
    const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

    const { data: roles, isLoading } = useQuery<TenantRoleProfile[]>({
        queryKey: ["team", "roles"],
        queryFn: () => apiFetch("/team/roles"),
        initialData: initialRoles,
    });

    // Sincroniza a ordem manual de reordenação com os perfis customizados
    // vindos do servidor — roda em effect (não durante o render) para não
    // duplicar IDs quando o componente renderiza mais de uma vez por update.
    useEffect(() => {
        const customIds = (roles ?? []).filter((r) => r.is_custom).map((r) => r.id);
        setOrderedCustomIds((prev) => {
            const known = new Set(prev);
            const stillValid = prev.filter((id) => customIds.includes(id));
            const novos = customIds.filter((id) => !known.has(id));
            return [...stillValid, ...novos];
        });
    }, [roles]);

    const deleteMutation = useMutation({
        mutationFn: (roleId: string) => apiFetch(`/team/roles/${roleId}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Perfil removido!");
            queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const cloneMutation = useMutation({
        mutationFn: ({ id, nome }: { id: string; nome: string }) =>
            apiFetch(`/team/roles/${id}/clone`, { method: "POST", body: JSON.stringify({ nome }) }),
        onSuccess: () => {
            toast.success("Perfil criado com base no padrão!");
            queryClient.invalidateQueries({ queryKey: ["team", "roles"] });
            setCloneTarget(null);
            setCloneName("");
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const systemRoles = roles?.filter((r) => !r.is_custom) ?? [];
    const customRolesMap = Object.fromEntries((roles ?? []).filter((r) => r.is_custom).map((r) => [r.id, r]));

    // Set() como defesa extra contra duplicidade — orderedCustomIds já deveria
    // vir sem repetição do effect acima, mas mapear via Set garante que uma
    // eventual regressão nunca produza `key` duplicada nos cards.
    const customRoles = Array.from(new Set(orderedCustomIds))
        .map((id) => customRolesMap[id])
        .filter(Boolean) as TenantRoleProfile[];

    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

    function handleDragEnd(event: DragEndEvent) {
        const { active, over } = event;
        setActiveCardId(null);
        if (over?.id === "__trash__") { setPendingDeleteId(String(active.id)); return; }
        if (over && active.id !== over.id) {
            setOrderedCustomIds((ids) => {
                const oldIndex = ids.indexOf(String(active.id));
                const newIndex = ids.indexOf(String(over.id));
                return arrayMove(ids, oldIndex, newIndex);
            });
        }
    }

    const activeCard = activeCardId ? customRolesMap[activeCardId] : null;

    if (isLoading) {
        return (
            <div className="p-8 space-y-6">
                <Skeleton className="h-10 w-64" />
                <div className="grid gap-4 md:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-48 rounded-sm" />)}
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Perfis e Permissões"
                description="Configure acesso granular por módulo, recurso e ação para cada membro da equipe."
                icon={<Shield size={20} />}
                breadcrumbs={[
                    { label: "Configurações", href: "/dashboard/settings" },
                    { label: "Perfis e Permissões" },
                ]}
                actions={
                    <PermissionGuard permission="tenant:permissions:create">
                        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                            <DialogTrigger render={<Button variant="outline" size="sm" className="gap-2" />}>
                                <Plus size={14} />
                                Novo Perfil
                            </DialogTrigger>
                            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                                <DialogHeader className="border-b">
                                    <DialogTitle>Criar Perfil Customizado</DialogTitle>
                                    <DialogDescription>
                                        Selecione as permissões granulares por módulo, recurso e ação.
                                    </DialogDescription>
                                </DialogHeader>
                                <RoleForm onSuccess={() => { setCreateOpen(false); queryClient.invalidateQueries({ queryKey: ["team", "roles"] }); }} />
                            </DialogContent>
                        </Dialog>
                    </PermissionGuard>
                }
            />

            {/* Perfis do Sistema */}
            <section>
                <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-4 flex items-center gap-2">
                    <Lock size={13} />
                    Perfis do Sistema
                    <Badge variant="outline" className="text-[9px] font-normal normal-case">somente leitura</Badge>
                </h2>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {systemRoles.map((role) => (
                        <SystemRoleCard
                            key={role.id}
                            role={role}
                            onClone={() => { setCloneTarget(role); setCloneName(`${role.nome} (cópia)`); }}
                        />
                    ))}
                </div>
            </section>

            <Separator />

            {/* Perfis Customizados */}
            <section>
                <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-1 flex items-center gap-2">
                    <Shield size={13} className="text-cyan-500" />
                    Perfis Customizados
                </h2>
                <p className="text-xs text-muted-foreground mb-4">Arraste para reordenar.</p>

                {customRoles.length === 0 ? (
                    <Card className="border-dashed">
                        <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <Shield size={40} className="mb-4 opacity-20" />
                            <p className="text-sm font-medium">Nenhum perfil customizado ainda</p>
                            <p className="text-xs mt-1">Clique em &quot;Usar como base&quot; num perfil padrão ou crie um do zero.</p>
                        </CardContent>
                    </Card>
                ) : (
                    <>
                        <DndContext
                            sensors={sensors}
                            collisionDetection={closestCenter}
                            autoScroll={false}
                            onDragStart={(e: DragStartEvent) => setActiveCardId(String(e.active.id))}
                            onDragEnd={handleDragEnd}
                        >
                            <SortableContext items={orderedCustomIds} strategy={rectSortingStrategy}>
                                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                                    {customRoles.map((role) => (
                                        <SortableRoleCard
                                            key={role.id}
                                            role={role}
                                            onEdit={() => setEditTarget(role)}
                                            onDelete={() => deleteMutation.mutate(role.id)}
                                            isDeleting={deleteMutation.isPending}
                                        />
                                    ))}
                                </div>
                            </SortableContext>

                            {activeCardId && <TrashZone />}

                            <DragOverlay dropAnimation={null}>
                                {activeCard && (
                                    <div className="opacity-90 shadow-xl">
                                        <SystemRoleCard role={activeCard} isDragging />
                                    </div>
                                )}
                            </DragOverlay>
                        </DndContext>

                        <AlertDialog open={!!pendingDeleteId} onOpenChange={(open) => !open && setPendingDeleteId(null)}>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Excluir perfil?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        {(() => {
                                            const role = pendingDeleteId ? customRolesMap[pendingDeleteId] : null;
                                            return role?.em_uso && role.em_uso > 0
                                                ? `"${role?.nome}" está em uso por ${role.em_uso} membro(s). Reatribua-os antes de excluir.`
                                                : `"${role?.nome}" será removido permanentemente.`;
                                        })()}
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                                    <AlertDialogAction
                                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        disabled={(() => { const r = pendingDeleteId ? customRolesMap[pendingDeleteId] : null; return !!(r?.em_uso && r.em_uso > 0); })()}
                                        onClick={() => { if (pendingDeleteId) deleteMutation.mutate(pendingDeleteId); setPendingDeleteId(null); }}
                                    >
                                        Excluir
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </>
                )}
            </section>

            {/* Dialog de Clone */}
            <Dialog open={!!cloneTarget} onOpenChange={(open) => !open && setCloneTarget(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader className="border-b">
                        <DialogTitle>Usar como base: {cloneTarget?.nome}</DialogTitle>
                        <DialogDescription>Cria uma cópia editável com as mesmas permissões.</DialogDescription>
                    </DialogHeader>
                    <DialogBody>
                        <Label>Nome do novo perfil</Label>
                        <Input className="mt-1.5" value={cloneName} onChange={(e) => setCloneName(e.target.value)} />
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setCloneTarget(null)}>Cancelar</Button>
                        <Button
                            size="sm"
                            disabled={cloneMutation.isPending || !cloneName.trim()}
                            onClick={() => cloneTarget && cloneMutation.mutate({ id: cloneTarget.id, nome: cloneName.trim() })}
                            className="bg-primary border-primary text-primary-foreground hover:bg-primary/90"
                        >
                            {cloneMutation.isPending ? "Criando..." : "Criar cópia"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog de Edição */}
            <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader className="border-b">
                        <DialogTitle>Editar Perfil</DialogTitle>
                        <DialogDescription>Atualize as permissões de &quot;{editTarget?.nome}&quot;.</DialogDescription>
                    </DialogHeader>
                    {editTarget && (
                        <RoleForm
                            role={editTarget}
                            onSuccess={() => { setEditTarget(null); queryClient.invalidateQueries({ queryKey: ["team", "roles"] }); }}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>
    );
}
