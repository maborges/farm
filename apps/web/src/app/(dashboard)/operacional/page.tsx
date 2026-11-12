import Link from "next/link";
import {
  CalendarClock,
  Droplets,
  Fuel,
  Gauge,
  Lock,
  Tractor,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  ClipboardList
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
import { cn } from "@/lib/utils";

const CARDS = [
  {
    href: "/dashboard/operacional/frota",
    icon: Tractor,
    title: "Painel da Frota",
    description: "Visão consolidada de máquinas",
    color: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-500/10",
  },
  {
    href: "/dashboard/operacional/campo/tarefas",
    icon: ClipboardList,
    title: "Tarefas de Campo",
    description: "Ordens de serviço e operações",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    href: "/dashboard/operacional/frota/jornadas",
    icon: CalendarClock,
    title: "Jornadas",
    description: "Histórico e horas trabalhadas",
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    href: "/dashboard/operacional/frota/disponibilidade",
    icon: Lock,
    title: "Disponibilidade",
    description: "Bloqueios e checklist diário",
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-500/10",
  },
  {
    href: "/dashboard/operacional/frota/consumo",
    icon: Droplets,
    title: "Consumo",
    description: "Eficiência de combustível e alertas",
    color: "text-cyan-600 dark:text-cyan-400",
    bg: "bg-cyan-500/10",
  },
  {
    href: "/dashboard/operacional/frota/custos",
    icon: Gauge,
    title: "Custos",
    description: "Custo por máquina e hectare",
    color: "text-violet-600 dark:text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    href: "/dashboard/operacional/frota/manutencao-preventiva",
    icon: Wrench,
    title: "Manutenção",
    description: "Preventivas e ordens por criticidade",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    href: "/operacional/abastecimentos",
    icon: Fuel,
    title: "Abastecimentos",
    description: "Registro de combustível",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10",
  },
] as const;

export default function FrotaPage() {
  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Painel Operacional & Frota"
        description="Gestão de máquinas agrícolas, jornadas de operadores, manutenções e abastecimento."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Operacional" }]}
      />

      {/* ── Central de Ações & Comandos Operacionais no Topo ── */}
      <QuickActionGrid
        label="Ações & Comandos Operacionais da Frota"
        columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-8"
        actions={CARDS.map((card) => ({
          title: card.title,
          description: card.description,
          icon: card.icon,
          href: card.href,
        }))}
      />

      {/* ── Status Operacional Rápido ── */}
      <div className="rounded-sm border border-border/70 bg-card p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shrink-0">
            <CheckCircle2 className="size-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Disponibilidade Geral da Frota</p>
            <p className="text-xs text-muted-foreground">Equipamentos aptos para operação e planos preventivos em conformidade.</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className="h-8 text-xs rounded-sm">
            <Link href="/dashboard/operacional/frota/manutencao-preventiva">
              <Wrench className="size-3.5 mr-1 text-muted-foreground" />
              Ver Preventivas
            </Link>
          </Button>
          <Button asChild size="sm" variant="outline" className="h-8 text-xs rounded-sm border-primary/40 text-primary hover:bg-primary/10">
            <Link href="/dashboard/operacional/campo/tarefas">
              <ClipboardList className="size-3.5 mr-1" />
              Tarefas do Campo
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}


