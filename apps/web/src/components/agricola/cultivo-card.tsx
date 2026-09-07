"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { MapPin, Pencil, Trash2, CalendarRange, Target, Rows3, FlaskConical } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";

interface CultivoArea {
    id: string;
    area_id: string;
    area_ha: number;
    area_nome?: string;
    area_hectares?: number;
    analise_solo_id?: string | null;
    analise_status?: string;
    regiao_analise?: string | null;
}

interface Cultivo {
    id: string;
    cultura: string;
    cultivar_nome: string | null;
    areas: CultivoArea[];
    sistema_plantio?: string | null;
    produtividade_meta_sc_ha?: number | null;
    consorciado?: boolean;
    data_inicio?: string | null;
    data_fim?: string | null;
    status?: string;
}

interface AreaRural {
    id: string;
    nome: string;
    area_hectares: number | null;
    area_hectares_manual?: number | null;
}

interface Props {
    cultivo: Cultivo;
    areas: AreaRural[];
    onEdit?: (cultivo: Cultivo) => void;
    onDelete?: (cultivoId: string) => void;
    onAnaliseSolo?: (area: CultivoArea) => void;
    readOnly?: boolean;
    /** Status da correção de solo por CultivoArea: PENDENTE (tarefa gerada, não concluída) ou CONCLUIDA. */
    cultivoAreaCorrecaoStatus?: Map<string, "PENDENTE" | "CONCLUIDA">;
}

function fmtDate(d: string | null | undefined) {
    if (!d) return null;
    try { return format(new Date(d), "dd/MM/yy", { locale: ptBR }); }
    catch { return null; }
}

const STATUS_COLORS: Record<string, string> = {
    PLANEJADO: "bg-slate-100 text-slate-600",
    PLANTADO: "bg-emerald-50 text-emerald-700",
    EM_DESENVOLVIMENTO: "bg-green-50 text-green-700",
    COLHIDO: "bg-yellow-50 text-yellow-700",
    CANCELADO: "bg-red-50 text-red-600",
};

const SISTEMA_LABEL: Record<string, string> = {
    CONVENCIONAL: "Convencional",
    PLANTIO_DIRETO: "Plantio Direto",
    ORGANICO: "Orgânico",
    INTEGRADO: "Integrado",
};

export function CultivoCard({ cultivo, areas, onEdit, onDelete, onAnaliseSolo, readOnly = false, cultivoAreaCorrecaoStatus }: Props) {
    const [editOpen, setEditOpen] = useState(false);
    const [editAreas, setEditAreas] = useState<Record<string, string>>({});

    const areaMap = Object.fromEntries(areas.map(a => [a.id, a]));
    const getAreaHaExibida = (areaId: string, fallback: number) => {
        const area = areaMap[areaId];
        return area?.area_hectares ?? area?.area_hectares_manual ?? fallback;
    };
    const totalArea = cultivo.areas.reduce((sum, ca) => sum + getAreaHaExibida(ca.area_id, ca.area_ha), 0);
    const dataInicio = fmtDate(cultivo.data_inicio);
    const dataFim = fmtDate(cultivo.data_fim);
    const statusColor = cultivo.status ? (STATUS_COLORS[cultivo.status] ?? "bg-slate-100 text-slate-600") : null;

    function handleOpenEdit() {
        const ha: Record<string, string> = {};
        for (const ca of cultivo.areas) {
            ha[ca.area_id] = String(ca.area_ha);
        }
        setEditAreas(ha);
        setEditOpen(true);
    }

    return (
        <>
            <Card className="overflow-hidden border-l-[3px] border-l-primary">
                {/* Header */}
                <div className="flex items-start justify-between px-4 pt-3 pb-2">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm">{cultivo.cultura}</span>
                            {cultivo.consorciado && (
                                <Badge variant="outline" className="text-xs py-0">Consorciado</Badge>
                            )}
                            {statusColor && cultivo.status && (
                                <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", statusColor)}>
                                    {cultivo.status.replace(/_/g, " ")}
                                </span>
                            )}
                        </div>
                        {cultivo.cultivar_nome && (
                            <p className="text-xs text-muted-foreground mt-0.5">{cultivo.cultivar_nome}</p>
                        )}
                    </div>
                    {!readOnly && (
                        <div className="flex gap-1 ml-2 flex-shrink-0">
                            <Button
                                size="icon-sm"
                                variant="outline"
                                onClick={handleOpenEdit}
                                aria-label="Editar cultivo"
                                title="Editar cultivo"
                            >
                                <Pencil />
                            </Button>
                            {onDelete && (
                                <Button
                                    size="icon-sm"
                                    variant="outline"
                                    onClick={() => onDelete(cultivo.id)}
                                    aria-label="Excluir cultivo"
                                    title="Excluir cultivo"
                                >
                                    <Trash2 />
                                </Button>
                            )}
                        </div>
                    )}
                </div>

                <CardContent className="px-4 pb-3 pt-0 space-y-2.5">
                    {/* Métricas em linha */}
                    <div className="flex items-center gap-3 flex-wrap text-xs text-muted-foreground">
                        {/* Área */}
                        <div className="flex items-center gap-1.5">
                            <MapPin className="size-3 flex-shrink-0" />
                            <span className="font-medium text-foreground">
                                {totalArea > 0
                                    ? `${totalArea.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha`
                                    : "—"}
                            </span>
                        </div>

                        {/* Período */}
                        {(dataInicio || dataFim) && (
                            <div className="flex items-center gap-1.5">
                                <CalendarRange className="size-3 flex-shrink-0" />
                                <span>{dataInicio ?? "?"} → {dataFim ?? "?"}</span>
                            </div>
                        )}

                        {/* Produtividade meta */}
                        {cultivo.produtividade_meta_sc_ha != null && (
                            <div className="flex items-center gap-1.5">
                                <Target className="size-3 flex-shrink-0" />
                                <span>{cultivo.produtividade_meta_sc_ha} sc/ha</span>
                            </div>
                        )}

                        {/* Sistema de plantio */}
                        {cultivo.sistema_plantio && (
                            <div className="flex items-center gap-1.5">
                                <Rows3 className="size-3 flex-shrink-0" />
                                <span>{SISTEMA_LABEL[cultivo.sistema_plantio] ?? cultivo.sistema_plantio}</span>
                            </div>
                        )}
                    </div>

                    {/* Talhões */}
                    {cultivo.areas.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                            {cultivo.areas.map(ca => {
                                const area = areaMap[ca.area_id];
                                const analiseStatus = ca.analise_status ?? "NAO_SELECIONADA";
                                return (
                                    <div key={ca.id} className="flex flex-col gap-1.5 text-xs p-2.5 bg-muted/30 border border-border/50 rounded-md">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="flex items-center gap-1.5 min-w-0">
                                                <MapPin className="size-3.5 text-muted-foreground flex-shrink-0" />
                                                <span className="font-semibold text-foreground truncate">{area?.nome || ca.area_id.slice(0, 8)}</span>
                                            </div>
                                            {onAnaliseSolo && (
                                                <Button
                                                    size="icon-sm"
                                                    variant="outline"
                                                    title={analiseStatus === "SELECIONADA" ? "Alterar análise de solo" : "Vincular análise de solo"}
                                                    onClick={(e) => { e.stopPropagation(); onAnaliseSolo(ca); }}
                                                    aria-label={analiseStatus === "SELECIONADA" ? "Alterar análise de solo" : "Vincular análise de solo"}
                                                >
                                                    <FlaskConical />
                                                </Button>
                                            )}
                                        </div>
                                        <div className="flex items-center justify-between mt-auto pt-1 border-t border-border/40">
                                            <span className="text-muted-foreground tabular-nums">
                                                {getAreaHaExibida(ca.area_id, ca.area_ha).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ha
                                            </span>
                                            {analiseStatus === "SELECIONADA" && (() => {
                                                const correcao = cultivoAreaCorrecaoStatus?.get(ca.id);
                                                if (correcao === "CONCLUIDA") {
                                                    return (
                                                        <span
                                                            className="text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded text-[10px] font-medium"
                                                            title="Correção de solo concluída no campo"
                                                        >
                                                            Correção concluída
                                                        </span>
                                                    );
                                                }
                                                if (correcao === "PENDENTE") {
                                                    return (
                                                        <span
                                                            className="text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded text-[10px] font-medium"
                                                            title="Tarefa de correção de solo gerada, aguardando execução no campo"
                                                        >
                                                            Correção pendente
                                                        </span>
                                                    );
                                                }
                                                return (
                                                    <span
                                                        className="text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded text-[10px] font-medium"
                                                        title="Análise de solo vinculada, mas nenhuma tarefa de correção foi gerada ainda"
                                                    >
                                                        Aguardando programação
                                                    </span>
                                                );
                                            })()}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={setEditOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Editar Talhões — {cultivo.cultura}</DialogTitle>
                        <p className="text-xs text-muted-foreground">
                            Ajuste os talhões vinculados ao cultivo e a área correspondente.
                        </p>
                    </DialogHeader>

                    <div className="space-y-3 py-4">
                        {areas.length === 0 ? (
                            <p className="text-sm text-muted-foreground">Nenhum talhão disponível</p>
                        ) : (
                            areas.map(area => {
                                const isSelected = cultivo.areas.some(ca => ca.area_id === area.id);
                                return (
                                    <div
                                        key={area.id}
                                        className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/40 transition-colors"
                                    >
                                        <Checkbox checked={isSelected} disabled className="h-4 w-4" />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium">{area.nome}</p>
                                            {area.area_hectares && (
                                                <p className="text-xs text-muted-foreground">{area.area_hectares} ha cadastrados</p>
                                            )}
                                        </div>
                                        {isSelected && (
                                            <Input
                                                type="number"
                                                step="0.01"
                                                placeholder="ha"
                                                className="w-20 h-8 text-xs"
                                                value={editAreas[area.id] ?? ""}
                                                onChange={e => setEditAreas(p => ({ ...p, [area.id]: e.target.value }))}
                                            />
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setEditOpen(false)}>Cancelar</Button>
                        <Button onClick={() => {
                            toast.info("Sincronização de áreas — em desenvolvimento");
                            setEditOpen(false);
                        }} size="sm">
                            Atualizar Áreas
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
