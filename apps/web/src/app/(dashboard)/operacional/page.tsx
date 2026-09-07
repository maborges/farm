import Link from "next/link";
import {
    ArrowUpRight,
    CalendarClock,
    Droplets,
    Fuel,
    Gauge,
    Lock,
    Tractor,
    Wrench,
} from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { ModuleCard } from "@/components/shared/module-card";
import { Button } from "@/components/ui/button";

const QUICK_LINKS = [
    {
        href: "/dashboard/operacional/frota",
        icon: <Tractor />,
        title: "Painel Executivo da Frota",
        description: "Visão consolidada de custos, manutenção, abastecimento e risco operacional.",
        action: "Abrir painel",
    },
    {
        href: "/dashboard/operacional/frota/jornadas",
        icon: <CalendarClock />,
        title: "Jornadas",
        description: "Abertura, encerramento e histórico operacional dos equipamentos.",
        action: "Ver jornadas",
    },
    {
        href: "/dashboard/operacional/frota/disponibilidade",
        icon: <Lock />,
        title: "Disponibilidade",
        description: "Bloqueios, checklist, conformidade e status operacional.",
        action: "Ver disponibilidade",
    },
    {
        href: "/dashboard/operacional/frota/consumo",
        icon: <Droplets />,
        title: "Consumo",
        description: "Eficiência de combustível, alertas e anomalias de consumo.",
        action: "Ver consumo",
    },
    {
        href: "/dashboard/operacional/frota/custos",
        icon: <Gauge />,
        title: "Custos",
        description: "Custo real por equipamento, por safra e por operação.",
        action: "Ver custos",
    },
    {
        href: "/dashboard/operacional/frota/manutencao-preventiva",
        icon: <Wrench />,
        title: "Manutenção Preventiva",
        description: "Planos, vencimentos e ordens geradas por criticidade.",
        action: "Abrir manutenção",
    },
    {
        href: "/operacional/abastecimentos",
        icon: <Fuel />,
        title: "Abastecimentos",
        description: "Controle de combustível e histórico de abastecimento.",
        action: "Ver abastecimentos",
    },
    {
        href: "/cadastros/equipamentos",
        icon: <ArrowUpRight />,
        title: "Cadastros de Equipamentos",
        description: "Cadastro mestre de ativos, sem mistura com a visão operacional.",
        action: "Abrir cadastro",
    },
] as const;

export default function FrotaPage() {
    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Painel da Frota"
                description="Acesso rápido aos fluxos operacionais da frota e equipamentos."
                icon={<Tractor className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Painel da Frota" }]}
                actions={
                    <Button asChild size="sm" className="h-8">
                        <Link href="/dashboard/operacional/frota">
                            <ArrowUpRight className="size-3.5 mr-1.5" />
                            Abrir painel executivo
                        </Link>
                    </Button>
                }
            />

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {QUICK_LINKS.map((item) => (
                    <ModuleCard
                        key={item.href}
                        module="operacional"
                        icon={item.icon}
                        title={item.title}
                        description={item.description}
                        className="min-h-[172px]"
                    >
                        <Button asChild variant="outline" size="sm" className="h-8 mt-3 w-full justify-start">
                            <Link href={item.href}>
                                {item.action}
                            </Link>
                        </Button>
                    </ModuleCard>
                ))}
            </div>
        </div>
    );
}
