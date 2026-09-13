"use client";

import { useState } from "react";
import { FolderTree, Map, Sprout, Trees, Droplets, Building2, Fence, ShieldCheck, Layers, LayoutGrid, Plus, Edit, Trash2, Warehouse, ChevronRight, ChevronDown, Wheat } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AREA_HIERARQUIA } from "@farm/zod-schemas";
import type { AreaRuralTree } from "@farm/zod-schemas";

// Ícones por tipo de área
const AREA_ICONS: Record<string, React.ReactNode> = {
  AREA_RURAL:       <FolderTree className="w-4 h-4" />,
  GLEBA:            <Map className="w-4 h-4" />,
  TALHAO:           <Sprout className="w-4 h-4" />,
  AREA_AMBIENTAL:   <ShieldCheck className="w-4 h-4" />,
  AREA_OPERACIONAL: <LayoutGrid className="w-4 h-4" />,
  PIQUETE:          <Fence className="w-4 h-4" />,
  ZONA_MANEJO:      <Layers className="w-4 h-4" />,
  SUBTALHAO:        <Sprout className="w-4 h-4" />,
  APP:              <Droplets className="w-4 h-4" />,
  RESERVA_LEGAL:    <Trees className="w-4 h-4" />,
  INFRAESTRUTURA:   <Building2 className="w-4 h-4" />,
  SEDE:             <Building2 className="w-4 h-4" />,
  ARMAZEM:          <Warehouse className="w-4 h-4" />,
  CURRAL:           <Fence className="w-4 h-4" />,
  OUTROS:           <FolderTree className="w-4 h-4" />,
};

// Cores por tipo de área (suaves no light, contrastantes no dark)
const AREA_COLORS: Record<string, string> = {
  AREA_RURAL:       "bg-green-100 text-green-600 dark:bg-green-500/20 dark:text-green-400",
  GLEBA:            "bg-purple-100 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400",
  TALHAO:           "bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400",
  AREA_AMBIENTAL:   "bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400",
  AREA_OPERACIONAL: "bg-teal-100 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400",
  PIQUETE:          "bg-cyan-100 text-cyan-600 dark:bg-cyan-500/20 dark:text-cyan-400",
  ZONA_MANEJO:      "bg-teal-100 text-teal-700 dark:bg-teal-500/20 dark:text-teal-400",
  SUBTALHAO:        "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
  APP:              "bg-sky-100 text-sky-600 dark:bg-sky-500/20 dark:text-sky-400",
  RESERVA_LEGAL:    "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400",
  INFRAESTRUTURA:   "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
  SEDE:             "bg-slate-200 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300",
  ARMAZEM:          "bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400",
  CURRAL:           "bg-orange-100 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400",
  OUTROS:           "bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400",
};

// Labels por tipo
const AREA_LABELS: Record<string, string> = {
  AREA_RURAL:       "Área Rural",
  GLEBA:            "Gleba",
  TALHAO:           "Talhão",
  AREA_AMBIENTAL:   "Área Ambiental",
  AREA_OPERACIONAL: "Área Operacional",
  PIQUETE:          "Piquete",
  ZONA_MANEJO:      "Zona de Manejo",
  SUBTALHAO:        "Subtalhão",
  APP:              "APP",
  RESERVA_LEGAL:    "Reserva Legal",
  INFRAESTRUTURA:   "Infraestrutura",
  SEDE:             "Sede",
  ARMAZEM:          "Armazém",
  CURRAL:           "Curral",
  OUTROS:           "Outros",
};

// Folhas não aceitam filhos
function isFolha(tipo: string): boolean {
  return (AREA_HIERARQUIA[tipo]?.length ?? 1) === 0;
}

interface AreaTreeItemProps {
  area: AreaRuralTree;
  level?: number;
  onSelect?: (area: AreaRuralTree) => void;
  onAdd?: (parentId: string, parentType: string) => void;
  onEdit?: (area: AreaRuralTree) => void;
  onDelete?: (area: AreaRuralTree) => void;
  selectedId?: string | null;
}

export function AreaTreeItem({
  area,
  level = 0,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  selectedId,
}: AreaTreeItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasChildren = area.filhos && area.filhos.length > 0;
  const isSelected = selectedId === area.id;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    }
  };

  const handleSelect = () => {
    onSelect?.(area);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleSelect();
      return;
    }

    if (!hasChildren) return;

    if (event.key === "ArrowRight" && !isExpanded) {
      event.preventDefault();
      setIsExpanded(true);
    } else if (event.key === "ArrowLeft" && isExpanded) {
      event.preventDefault();
      setIsExpanded(false);
    }
  };

  const handleAdd = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAdd?.(area.id, area.tipo);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(area);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(area);
  };

  return (
    <div className="select-none">
      {/* Item da árvore */}
      <div
        className={cn(
          "flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-all hover:bg-accent group",
          isSelected && "bg-primary/10 border border-primary/30"
        )}
        style={{ paddingLeft: `${level * 24 + 12}px` }}
        onClick={handleSelect}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-label={`${AREA_LABELS[area.tipo] || area.tipo}: ${area.nome}`}
        aria-expanded={hasChildren ? isExpanded : undefined}
      >
        {/* Toggle Chevron */}
        <button
          type="button"
          onClick={handleToggle}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.stopPropagation();
            }
          }}
          className="shrink-0 w-5 h-8 flex items-center justify-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={hasChildren ? (isExpanded ? `Recolher ${area.nome}` : `Expandir ${area.nome}`) : undefined}
          tabIndex={hasChildren ? 0 : -1}
          disabled={!hasChildren}
        >
          {hasChildren ? (
            isExpanded
              ? <ChevronDown className="w-4 h-4 text-muted-foreground" />
              : <ChevronRight className="w-4 h-4 text-muted-foreground" />
          ) : (
            <span className="w-4" />
          )}
        </button>

        {/* Ícone do tipo */}
        <div
          className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center",
            AREA_COLORS[area.tipo] || "bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400"
          )}
        >
          {AREA_ICONS[area.tipo] || <FolderTree className="w-4 h-4" />}
        </div>

        {/* Informações */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{area.nome}</span>
            {area.codigo && (
              <Badge variant="outline" className="text-xs">
                {area.codigo}
              </Badge>
            )}
            <Badge variant="secondary" className="text-xs">
              {AREA_LABELS[area.tipo] || area.tipo}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
            {area.area_hectares || area.area_hectares_manual ? (
              <span>
                {(area.area_hectares || area.area_hectares_manual)?.toFixed(2)} ha
              </span>
            ) : null}
            {(area as any).irrigado && (
              <Badge variant="outline" className="text-[10px] h-4 px-1 border-blue-200 bg-blue-50 text-blue-600 gap-0.5">
                <Droplets className="size-2.5" />
                {(area as any).tipo_irrigacao_nome || "Irrigado"}
              </Badge>
            )}
            {(area as any).tipo_solo_nome && (
              <span className="text-[10px] font-medium text-amber-700 bg-amber-50 px-1 rounded border border-amber-100">
                {(area as any).tipo_solo_nome}
              </span>
            )}
            {(area as any).cultivo_atual && (
              <Badge variant="outline" className="text-[10px] h-4 px-1 border-emerald-200 bg-emerald-50 text-emerald-700 gap-0.5">
                <Wheat className="size-2.5" />
                {(area as any).cultivo_atual.cultura} ({(area as any).cultivo_atual.safra_nome})
              </Badge>
            )}
            {area.descricao && (
              <span className="truncate max-w-[200px]">{area.descricao}</span>
            )}
          </div>
        </div>

        {/* Ações */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!isFolha(area.tipo) && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={handleAdd}
              title="Adicionar filho"
              aria-label="Adicionar filho"
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={handleEdit}
            title="Editar"
            aria-label="Editar"
          >
            <Edit className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
            onClick={handleDelete}
            title="Remover"
            aria-label="Remover"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Filhos (recursivo) */}
      {hasChildren && isExpanded && (
        <div className="transition-all">
          {area.filhos.map((filho: AreaRuralTree) => (
            <AreaTreeItem
              key={filho.id}
              area={filho}
              level={level + 1}
              onSelect={onSelect}
              onAdd={onAdd}
              onEdit={onEdit}
              onDelete={onDelete}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface AreaTreeProps {
  areas: AreaRuralTree[];
  onSelect?: (area: AreaRuralTree) => void;
  onAdd?: (parentId: string, parentType: string) => void;
  onEdit?: (area: AreaRuralTree) => void;
  onDelete?: (area: AreaRuralTree) => void;
  selectedId?: string | null;
  className?: string;
}

export function AreaTree({
  areas,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  selectedId,
  className,
}: AreaTreeProps) {
  if (!areas || areas.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FolderTree className="w-16 h-16 mx-auto mb-4 opacity-50" />
        <p className="text-sm">Nenhuma área rural cadastrada</p>
        <p className="text-xs mt-1">
          Clique em "Nova Área" para começar
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {areas.map((area) => (
        <AreaTreeItem
          key={area.id}
          area={area}
          onSelect={onSelect}
          onAdd={onAdd}
          onEdit={onEdit}
          onDelete={onDelete}
          selectedId={selectedId}
        />
      ))}
    </div>
  );
}

// Exportar helpers
export { AREA_ICONS, AREA_COLORS, AREA_LABELS };
