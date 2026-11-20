"use client";

import Link from "next/link";
import {
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Droplets,
  Fuel,
  Gauge,
  Lock,
  Tractor,
  Wrench,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { QuickActionGrid, type QuickActionItem } from "@/components/ui/quick-action-grid";

const CARDS: QuickActionItem[] = [
  { href: "/dashboard/operacional/frota", icon: Tractor, title: "Painel da Frota", description: "Visão consolidada de máquinas" },
  { href: "/dashboard/operacional/campo/tarefas", icon: ClipboardList, title: "Tarefas de Campo", description: "Ordens de serviço e operações" },
  { href: "/dashboard/operacional/frota/jornadas", icon: CalendarClock, title: "Jornadas", description: "Histórico e horas trabalhadas" },
  { href: "/dashboard/operacional/frota/disponibilidade", icon: Lock, title: "Disponibilidade", description: "Bloqueios e checklist diário" },
  { href: "/dashboard/operacional/frota/consumo", icon: Droplets, title: "Consumo", description: "Eficiência de combustível e alertas" },
  { href: "/dashboard/operacional/frota/custos", icon: Gauge, title: "Custos", description: "Custo por máquina e hectare" },
  { href: "/dashboard/operacional/frota/manutencao-preventiva", icon: Wrench, title: "Manutenção", description: "Preventivas e ordens por criticidade" },
  { href: "/operacional/abastecimentos", icon: Fuel, title: "Abastecimentos", description: "Registro de combustível" },
];

export function OperacionalDashboardClient() {
  return (
    <div className="w-full space-y-6 p-6">
      <PageHeader
        title="Painel Operacional & Frota"
        description="Gestão de máquinas agrícolas, jornadas de operadores, manutenções e abastecimento."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Operacional" }]}
      />

      <QuickActionGrid
        label="Ações & Comandos Operacionais da Frota"
        columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-8"
        actions={CARDS}
      />

      <div className="flex flex-col gap-4 rounded-sm border border-border/70 bg-card p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="shrink-0 rounded-sm bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="size-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Disponibilidade Geral da Frota</p>
            <p className="text-xs text-muted-foreground">Equipamentos aptos para operação e planos preventivos em conformidade.</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className="h-8 rounded-sm text-xs">
            <Link href="/dashboard/operacional/frota/manutencao-preventiva">
              <Wrench className="mr-1 size-3.5 text-muted-foreground" />
              Ver Preventivas
            </Link>
          </Button>
          <Button asChild size="sm" variant="outline" className="h-8 rounded-sm border-primary/40 text-xs text-primary hover:bg-primary/10">
            <Link href="/dashboard/operacional/campo/tarefas">
              <ClipboardList className="mr-1 size-3.5" />
              Tarefas do Campo
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
