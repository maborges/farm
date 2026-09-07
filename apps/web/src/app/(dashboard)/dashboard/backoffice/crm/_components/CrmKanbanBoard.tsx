"use client";

import { useSortable, SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem,
    DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    Target, Building2, Phone, Mail, MoreHorizontal, ArrowRight, CheckCircle2, XCircle, GripVertical, Plus
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Lead, Estagio, KanbanData, ORIGENS } from "./types";

interface DroppableColumnProps {
    id: string;
    children: React.ReactNode;
    items: string[];
}

export function DroppableColumn({ id, children, items }: DroppableColumnProps) {
    const { setNodeRef } = useDroppable({
        id: id,
        data: {
            type: "Column",
        },
    });

    return (
        <div ref={setNodeRef} className="flex-1 flex flex-col min-h-[150px]">
            <SortableContext
                id={id}
                items={items}
                strategy={verticalListSortingStrategy}
            >
                {children}
            </SortableContext>
        </div>
    );
}

interface SortableLeadCardProps {
    lead: Lead;
    onClick: () => void;
    onMove: (leadId: string, estagioId: string) => void;
    onConvert: (leadId: string) => void;
    onLose: (lead: Lead) => void;
    estagios: Estagio[];
}

export function SortableLeadCard({ lead, onClick, onMove, onConvert, onLose, estagios }: SortableLeadCardProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({
        id: lead.id,
        data: {
            type: "Lead",
            lead,
        },
    });

    const style = {
        transform: CSS.Translate.toString(transform),
        transition,
        opacity: isDragging ? 0.3 : 1,
    };

    return (
        <Card
            ref={setNodeRef}
            style={style}
            className={cn(
                "cursor-default hover:shadow-md transition-shadow group relative",
                isDragging && "ring-2 ring-primary border-primary"
            )}
            onClick={onClick}
        >
            <CardContent className="p-3 space-y-2">
                <div className="flex items-start justify-between">
                    <p className="font-semibold text-sm leading-tight flex-1 pr-6">{lead.nome}</p>
                    <div className="flex items-center gap-1 absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        {/* Drag Handle */}
                        <div
                            {...attributes}
                            {...listeners}
                            className="p-1 cursor-grab active:cursor-grabbing hover:bg-accent rounded-sm"
                        >
                            <GripVertical className="size-3 text-muted-foreground" />
                        </div>
                        <DropdownMenu>
                            <DropdownMenuTrigger
                                className={cn(
                                    buttonVariants({ variant: "ghost", size: "icon-sm" }),
                                    "h-6 w-6 p-0"
                                )}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <MoreHorizontal className="size-3" />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                {estagios
                                    .filter((e) => e.id !== lead.estagio_id)
                                    .map((e) => (
                                        <DropdownMenuItem
                                            key={e.id}
                                            onClick={(ev) => {
                                                ev.stopPropagation();
                                                onMove(lead.id, e.id);
                                            }}
                                        >
                                            <ArrowRight className="size-3 mr-2" />
                                            Mover para {e.nome}
                                        </DropdownMenuItem>
                                    ))}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                    onClick={(ev) => { ev.stopPropagation(); onConvert(lead.id); }}
                                    className="text-green-600"
                                >
                                    <CheckCircle2 className="size-3 mr-2" /> Converter
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={(ev) => { ev.stopPropagation(); onLose(lead); }}
                                    className="text-red-600"
                                >
                                    <XCircle className="size-3 mr-2" /> Marcar como perdido
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>

                {lead.empresa && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Building2 className="size-3" />
                        <span className="truncate">{lead.empresa}</span>
                    </div>
                )}

                <div className="flex items-center justify-between">
                    <Badge className={cn("text-[9px] border font-normal", ORIGENS[lead.origem]?.color ?? ORIGENS.manual.color)}>
                        {ORIGENS[lead.origem]?.label ?? lead.origem}
                    </Badge>
                    {lead.valor_estimado != null && lead.valor_estimado > 0 && (
                        <span className="text-xs font-semibold text-emerald-600">
                            {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(lead.valor_estimado)}
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    {lead.telefone && (
                        <span className="flex items-center gap-0.5">
                            <Phone className="size-2.5" /> {lead.telefone}
                        </span>
                    )}
                    {lead.email && (
                        <span className="flex items-center gap-0.5 truncate">
                            <Mail className="size-2.5" /> {lead.email}
                        </span>
                    )}
                </div>

                <p className="text-[10px] text-muted-foreground">
                    {formatDistanceToNow(new Date(lead.updated_at), { addSuffix: true, locale: ptBR })}
                </p>
            </CardContent>
        </Card>
    );
}

interface CrmKanbanBoardProps {
    kanban: KanbanData | null | undefined;
    kanbanLeads: Record<string, Lead[]>;
    onLeadClick: (lead: Lead) => void;
    onMove: (leadId: string, estagioId: string) => void;
    onConvert: (leadId: string) => void;
    onLose: (lead: Lead) => void;
    setShowNewEstagio: (v: boolean) => void;
}

export function CrmKanbanBoard({
    kanban,
    kanbanLeads,
    onLeadClick,
    onMove,
    onConvert,
    onLose,
    setShowNewEstagio,
}: CrmKanbanBoardProps) {
    return (
        <div className="flex gap-3 pb-4 min-h-[500px] w-full">
            {kanban?.estagios.map((estagio) => (
                <div
                    key={estagio.id}
                    className="flex-1 min-w-[200px] flex flex-col bg-muted/30 rounded-lg group/column h-full border border-transparent hover:border-muted-foreground/10 transition-colors"
                >
                    {/* Column Header */}
                    <div className="p-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: estagio.cor }}
                            />
                            <span className="font-semibold text-sm">{estagio.nome}</span>
                            <Badge variant="secondary" className="text-[10px] px-1.5">
                                {kanbanLeads[estagio.id]?.length ?? 0}
                            </Badge>
                        </div>
                    </div>

                    <Separator />

                    {/* Column Cards */}
                    <ScrollArea className="flex-1 max-h-[calc(100vh-420px)] overflow-hidden">
                        <DroppableColumn
                            id={estagio.id}
                            items={kanbanLeads[estagio.id]?.map((l) => l.id) ?? []}
                        >
                            <div className="p-2 space-y-2 pb-10 min-h-[300px]">
                                {(kanbanLeads[estagio.id] ?? []).length === 0 && (
                                    <div className="text-center text-muted-foreground text-[10px] py-12 bg-muted/20 border border-dashed rounded-lg border-muted-foreground/20">
                                        Arraste aqui
                                    </div>
                                )}
                                {(kanbanLeads[estagio.id] ?? []).map((lead) => (
                                    <SortableLeadCard
                                        key={lead.id}
                                        lead={lead}
                                        onClick={() => onLeadClick(lead)}
                                        onMove={onMove}
                                        onConvert={onConvert}
                                        onLose={onLose}
                                        estagios={kanban.estagios}
                                    />
                                ))}
                            </div>
                        </DroppableColumn>
                    </ScrollArea>
                </div>
            ))}

            {/* Empty state */}
            {kanban?.estagios.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center py-20 text-muted-foreground">
                    <Target className="size-12 mb-4 opacity-30" />
                    <p className="font-medium">Nenhum estágio criado</p>
                    <p className="text-sm">Crie estágios para montar seu pipeline comercial.</p>
                    <Button className="mt-4" size="sm" onClick={() => setShowNewEstagio(true)}>
                        <Plus className="size-4 mr-1" /> Criar Estágio
                    </Button>
                </div>
            )}
        </div>
    );
}
