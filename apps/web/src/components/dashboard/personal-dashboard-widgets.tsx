"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { closestCenter, DndContext, DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, LayoutDashboard, Package, Sprout, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";

type DashboardWidget = { id: string; label: string; description: string; href: string; icon: typeof Sprout };

const DEFAULT_WIDGETS: DashboardWidget[] = [
  { id: "safras", label: "Safras", description: "Planejamento agrícola", href: "/agricola/safras", icon: Sprout },
  { id: "tarefas", label: "Tarefas", description: "Operações de campo", href: "/dashboard/operacional/campo/tarefas", icon: LayoutDashboard },
  { id: "estoque", label: "Estoque", description: "Saldos e movimentações", href: "/suprimentos/estoque", icon: Package },
  { id: "financeiro", label: "Financeiro", description: "Fluxo e lançamentos", href: "/dashboard/financeiro", icon: Wallet },
];

const STORAGE_KEY = "agrosaas-dashboard-widgets";

function SortableWidget({ widget }: { widget: DashboardWidget }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: widget.id });
  const Icon = widget.icon;
  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className={isDragging ? "z-10 opacity-70" : ""}>
      <Button asChild variant="outline" className="h-auto min-h-16 w-full justify-start gap-3 px-3 py-2 text-left">
        <Link href={widget.href}>
          <span {...attributes} {...listeners} onClick={(event) => event.preventDefault()} className="cursor-grab touch-none rounded-sm p-1 text-muted-foreground hover:bg-muted" aria-label={`Reordenar ${widget.label}`}>
            <GripVertical className="size-4" aria-hidden="true" />
          </span>
          <span className="flex size-8 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary"><Icon className="size-4" aria-hidden="true" /></span>
          <span className="min-w-0"><span className="block truncate text-sm font-semibold">{widget.label}</span><span className="block truncate text-xs text-muted-foreground">{widget.description}</span></span>
        </Link>
      </Button>
    </div>
  );
}

export function PersonalDashboardWidgets() {
  const [widgets, setWidgets] = useState(DEFAULT_WIDGETS);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  useEffect(() => {
    try {
      const ids = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as string[];
      const ordered = ids.map((id) => DEFAULT_WIDGETS.find((widget) => widget.id === id)).filter((widget): widget is DashboardWidget => Boolean(widget));
      setWidgets([...ordered, ...DEFAULT_WIDGETS.filter((widget) => !ids.includes(widget.id))]);
    } catch {
      setWidgets(DEFAULT_WIDGETS);
    }
  }, []);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setWidgets((current) => {
      const oldIndex = current.findIndex((widget) => widget.id === active.id);
      const newIndex = current.findIndex((widget) => widget.id === over.id);
      const next = arrayMove(current, oldIndex, newIndex);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next.map((widget) => widget.id)));
      return next;
    });
  }

  return (
    <section className="rounded-sm border bg-card p-4 shadow-sm" aria-labelledby="personal-dashboard-title">
      <div className="mb-3 flex items-center justify-between gap-3"><div><h2 id="personal-dashboard-title" className="text-sm font-semibold">Meu painel</h2><p className="text-xs text-muted-foreground">Arraste para organizar seus acessos mais usados.</p></div><span className="text-[10px] text-muted-foreground">salvo neste dispositivo</span></div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}><SortableContext items={widgets.map((widget) => widget.id)} strategy={verticalListSortingStrategy}><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{widgets.map((widget) => <SortableWidget key={widget.id} widget={widget} />)}</div></SortableContext></DndContext>
    </section>
  );
}

