"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    DndContext, DragEndEvent, DragOverEvent, DragStartEvent,
    PointerSensor, useSensor, useSensors, DragOverlay, closestCenter,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useState } from "react";
import { Plus, GripVertical, Trash2, Copy, Layers, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface Talhao {
    id: string;
    nome: string;
    area_ha?: number;
}

interface GrupoItem {
    id: string;
    talhao_id: string;
}

interface Grupo {
    id: string;
    nome: string;
    cor: string | null;
    ordem: number;
    itens: GrupoItem[];
}

const CORES_PRESET = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
];

function TalhaoCard({ talhao, isDragging }: { talhao: Talhao; isDragging?: boolean }) {
    const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: talhao.id });
    const style = { transform: CSS.Transform.toString(transform), transition };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "flex items-center gap-2 px-3 py-2 bg-background border rounded-lg text-sm select-none",
                isDragging && "opacity-40"
            )}
        >
            <span {...attributes} {...listeners} className="cursor-grab text-muted-foreground hover:text-foreground">
                <GripVertical className="size-4" />
            </span>
            <span className="flex-1 font-medium">{talhao.nome}</span>
            {talhao.area_ha && (
                <span className="text-xs text-muted-foreground tabular-nums">{talhao.area_ha} ha</span>
            )}
        </div>
    );
}

interface SafraGruposTalhoesProps {
    safraId: string;
    fazendaTalhoes: Talhao[];
}

export function SafraGruposTalhoes({ safraId, fazendaTalhoes }: SafraGruposTalhoesProps) {
    const queryClient = useQueryClient();
    const queryKey = ["grupos-talhoes", safraId];
    const [activeId, setActiveId] = useState<string | null>(null);
    const [isAddGrupoOpen, setIsAddGrupoOpen] = useState(false);
    const [novoNome, setNovoNome] = useState("");
    const [novaCor, setNovaCor] = useState(CORES_PRESET[0]);
    const [isCopiarOpen, setIsCopiarOpen] = useState(false);
    const [safraOrigemId, setSafraOrigemId] = useState("");

    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

    const { data: grupos = [] } = useQuery<Grupo[]>({
        queryKey,
        queryFn: () => apiFetch(`/safras/${safraId}/grupos-talhoes`),
    });

    const criarMutation = useMutation({
        mutationFn: (dados: any) => apiFetch(`/safras/${safraId}/grupos-talhoes`, {
            method: "POST", body: JSON.stringify(dados),
        }),
        onSuccess: () => { queryClient.invalidateQueries({ queryKey }); setIsAddGrupoOpen(false); setNovoNome(""); },
    });

    const excluirMutation = useMutation({
        mutationFn: (grupoId: string) => apiFetch(`/safras/${safraId}/grupos-talhoes/${grupoId}`, { method: "DELETE" }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey }),
    });

    const sincronizarMutation = useMutation({
        mutationFn: ({ grupoId, talhaoIds }: { grupoId: string; talhaoIds: string[] }) =>
            apiFetch(`/safras/${safraId}/grupos-talhoes/${grupoId}/talhoes`, {
                method: "PUT", body: JSON.stringify({ talhao_ids: talhaoIds }),
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey }),
    });

    const copiarMutation = useMutation({
        mutationFn: (origemId: string) => apiFetch(`/safras/${safraId}/grupos-talhoes/copiar`, {
            method: "POST", body: JSON.stringify({ safra_origem_id: origemId }),
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success("Grupos copiados com sucesso!");
            setIsCopiarOpen(false);
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao copiar grupos"),
    });

    // IDs de talhões já em algum grupo
    const talhoeEmGrupo = new Set(grupos.flatMap(g => g.itens.map(i => i.talhao_id)));
    const talhoesSemGrupo = fazendaTalhoes.filter(t => !talhoeEmGrupo.has(t.id));
    const activeTalhao = fazendaTalhoes.find(t => t.id === activeId);

    function handleDragStart(e: DragStartEvent) {
        setActiveId(e.active.id as string);
    }

    function handleDragEnd(e: DragEndEvent) {
        setActiveId(null);
        const { active, over } = e;
        if (!over) return;

        const talhaoId = active.id as string;
        const overId = over.id as string;

        // Verifica se "over" é um grupo
        const grupoDestino = grupos.find(g => g.id === overId || g.itens.some(i => i.talhao_id === overId));
        if (!grupoDestino) return;

        // Remove de qualquer grupo atual
        const grupoOrigem = grupos.find(g => g.itens.some(i => i.talhao_id === talhaoId));

        if (grupoOrigem?.id === grupoDestino.id) return; // mesmo grupo, sem mudança

        // Atualiza grupo destino
        const idsDestino = [...grupoDestino.itens.map(i => i.talhao_id), talhaoId];
        sincronizarMutation.mutate({ grupoId: grupoDestino.id, talhaoIds: idsDestino });

        // Remove do grupo origem
        if (grupoOrigem) {
            const idsOrigem = grupoOrigem.itens.map(i => i.talhao_id).filter(id => id !== talhaoId);
            sincronizarMutation.mutate({ grupoId: grupoOrigem.id, talhaoIds: idsOrigem });
        }
    }

    return (
        <div className="space-y-4">
            {/* Ações */}
            <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setIsAddGrupoOpen(true)}>
                    <Plus className="size-3.5 mr-1.5 transition-transform group-hover:scale-110" /> Novo Grupo
                </Button>
                <Button size="sm" variant="outline" onClick={() => setIsCopiarOpen(true)}>
                    <Copy className="size-3.5 mr-1.5 transition-transform group-hover:scale-110" /> Copiar safra anterior
                </Button>
            </div>

            <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
            >
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {/* Talhões sem grupo */}
                    <div className="border border-dashed rounded-xl p-3 space-y-2 bg-muted/20">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                            <Layers className="size-3.5" /> Sem grupo ({talhoesSemGrupo.length})
                        </p>
                        <SortableContext items={talhoesSemGrupo.map(t => t.id)} strategy={verticalListSortingStrategy}>
                            {talhoesSemGrupo.map(t => (
                                <TalhaoCard key={t.id} talhao={t} isDragging={activeId === t.id} />
                            ))}
                        </SortableContext>
                        {talhoesSemGrupo.length === 0 && (
                            <p className="text-xs text-muted-foreground text-center py-2">Todos agrupados</p>
                        )}
                    </div>

                    {/* Grupos */}
                    {grupos.map(grupo => {
                        const talhoesDoGrupo = fazendaTalhoes.filter(t =>
                            grupo.itens.some(i => i.talhao_id === t.id)
                        );
                        return (
                            <div
                                key={grupo.id}
                                id={grupo.id}
                                className="border rounded-xl p-3 space-y-2"
                                style={{ borderColor: grupo.cor ?? undefined }}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {grupo.cor && (
                                            <div className="size-3 rounded-full" style={{ backgroundColor: grupo.cor }} />
                                        )}
                                        <p className="text-xs font-semibold uppercase tracking-wide">{grupo.nome}</p>
                                        <Badge variant="outline" className="text-xs">{talhoesDoGrupo.length}</Badge>
                                    </div>
                                    <Button
                                        variant="ghost" size="icon-sm"
                                        onClick={() => excluirMutation.mutate(grupo.id)}
                                    >
                                        <Trash2 className="size-3.5 text-muted-foreground" />
                                    </Button>
                                </div>

                                <SortableContext items={talhoesDoGrupo.map(t => t.id)} strategy={verticalListSortingStrategy}>
                                    {talhoesDoGrupo.map(t => (
                                        <TalhaoCard key={t.id} talhao={t} isDragging={activeId === t.id} />
                                    ))}
                                </SortableContext>

                                {talhoesDoGrupo.length === 0 && (
                                    <div className="border-2 border-dashed rounded-lg p-3 text-center text-xs text-muted-foreground">
                                        Arraste talhões aqui
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                <DragOverlay>
                    {activeTalhao && (
                        <div className="flex items-center gap-2 px-3 py-2 bg-background border-2 border-primary rounded-lg shadow-lg text-sm font-medium">
                            <GripVertical className="size-4 text-muted-foreground" />
                            {activeTalhao.nome}
                        </div>
                    )}
                </DragOverlay>
            </DndContext>

            {/* Modal novo grupo */}
            <Dialog open={isAddGrupoOpen} onOpenChange={setIsAddGrupoOpen}>
                <DialogContent className="sm:max-w-[360px]">
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <Plus className="size-4 text-primary" />
                            </div>
                            <div className="space-y-0.5">
                                <DialogTitle>Novo Grupo</DialogTitle>
                                <DialogDescription className="text-xs">
                                    Crie um agrupamento para organizar os talhões da safra.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium text-muted-foreground">Nome do grupo</Label>
                            <Input
                                className="rounded-sm"
                                placeholder="Ex: Bloco Norte, Gleba 1..."
                                value={novoNome}
                                onChange={e => setNovoNome(e.target.value)}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium text-muted-foreground">Cor</Label>
                            <div className="flex gap-2 flex-wrap">
                                {CORES_PRESET.map(cor => (
                                    <button
                                        key={cor}
                                        type="button"
                                        className={cn(
                                            "size-7 rounded-full border-2 transition-transform hover:scale-110",
                                            novaCor === cor ? "border-foreground scale-110" : "border-transparent"
                                        )}
                                        style={{ backgroundColor: cor }}
                                        onClick={() => setNovaCor(cor)}
                                    />
                                ))}
                            </div>
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" type="button" onClick={() => setIsAddGrupoOpen(false)}>
                            <XCircle className="size-4" />
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            disabled={!novoNome.trim() || criarMutation.isPending}
                            onClick={() => criarMutation.mutate({ nome: novoNome.trim(), cor: novaCor, ordem: grupos.length })}
                        >
                            <CheckCircle2 className="size-4" />
                            Criar Grupo
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Modal copiar safra anterior */}
            <Dialog open={isCopiarOpen} onOpenChange={setIsCopiarOpen}>
                <DialogContent className="sm:max-w-[360px]">
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <Copy className="size-4 text-primary" />
                            </div>
                            <div className="space-y-0.5">
                                <DialogTitle>Copiar Grupos</DialogTitle>
                                <DialogDescription className="text-xs">
                                    Reaproveite a estrutura de grupos de uma safra anterior.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <p className="text-xs text-muted-foreground leading-relaxed">Informe o ID da safra de origem para copiar a estrutura de grupos e talhões.</p>
                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium text-muted-foreground">ID da safra de origem</Label>
                            <Input
                                className="rounded-sm"
                                placeholder="UUID da safra anterior"
                                value={safraOrigemId}
                                onChange={e => setSafraOrigemId(e.target.value)}
                            />
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" type="button" onClick={() => setIsCopiarOpen(false)}>
                            <XCircle className="size-4" />
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            disabled={!safraOrigemId.trim() || copiarMutation.isPending}
                            onClick={() => copiarMutation.mutate(safraOrigemId.trim())}
                        >
                            <CheckCircle2 className="size-4" />
                            Copiar Grupos
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
