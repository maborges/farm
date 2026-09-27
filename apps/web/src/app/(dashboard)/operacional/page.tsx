import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  Droplets,
  Fuel,
  Gauge,
  Lock,
  Tractor,
  Wrench,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const CARDS = [
  {
    href: "/dashboard/operacional/frota",
    icon: Tractor,
    title: "Painel Executivo da Frota",
    description: "Visão consolidada de custos, manutenção, abastecimento e risco operacional.",
    color: "text-orange-600",
    bg: "bg-orange-50",
  },
  {
    href: "/dashboard/operacional/frota/jornadas",
    icon: CalendarClock,
    title: "Jornadas",
    description: "Abertura, encerramento e histórico operacional dos equipamentos.",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    href: "/dashboard/operacional/frota/disponibilidade",
    icon: Lock,
    title: "Disponibilidade",
    description: "Bloqueios, checklist, conformidade e status operacional.",
    color: "text-red-600",
    bg: "bg-red-50",
  },
  {
    href: "/dashboard/operacional/frota/consumo",
    icon: Droplets,
    title: "Consumo",
    description: "Eficiência de combustível, alertas e anomalias de consumo.",
    color: "text-cyan-600",
    bg: "bg-cyan-50",
  },
  {
    href: "/dashboard/operacional/frota/custos",
    icon: Gauge,
    title: "Custos",
    description: "Custo real por equipamento, por safra e por operação.",
    color: "text-violet-600",
    bg: "bg-violet-50",
  },
  {
    href: "/dashboard/operacional/frota/manutencao-preventiva",
    icon: Wrench,
    title: "Manutenção Preventiva",
    description: "Planos, vencimentos e ordens geradas por criticidade.",
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  {
    href: "/operacional/abastecimentos",
    icon: Fuel,
    title: "Abastecimentos",
    description: "Controle de combustível e histórico de abastecimento.",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
] as const;

export default function FrotaPage() {
  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Painel da Frota"
        description="Acesso rápido aos fluxos operacionais da frota e equipamentos."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Painel da Frota" }]}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((card) => (
          <Link key={card.href} href={card.href}>
            <Card className="h-full shadow-sm hover:shadow-md transition-shadow cursor-pointer group">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className={cn("p-2.5 rounded-sm", card.bg)}>
                    <card.icon className={cn("size-5", card.color)} />
                  </div>
                  <ArrowRight
                    size={16}
                    className="text-muted-foreground group-hover:translate-x-0.5 transition-transform mt-1"
                  />
                </div>
                <CardTitle className="text-base mt-3">{card.title}</CardTitle>
                <CardDescription className="text-xs">{card.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

