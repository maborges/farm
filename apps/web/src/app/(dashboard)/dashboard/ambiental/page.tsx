"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Leaf,
  ShieldAlert,
  Droplets,
  TriangleAlert,
  MapPinned,
  FileSearch,
  ArrowRight,
  TreePine,
  AlertCircle,
} from "lucide-react";

interface DashboardAmbiental {
  total_cars: number;
  cars_ativos: number;
  cars_pendentes: number;
  total_alertas_abertos: number;
  alertas_criticos: number;
  total_outorgas: number;
  outorgas_vencendo: number;
  outorgas_vencidas: number;
}

export default function AmbientalPage() {
  const { data: dashboard, isLoading, isError, refetch } = useQuery<DashboardAmbiental>({
    queryKey: ["ambiental", "dashboard"],
    queryFn: () => apiFetch("/ambiental/dashboard"),
  });

  const summaryCards = [
    {
      label: "CARs",
      value: dashboard?.total_cars ?? 0,
      help: `${dashboard?.cars_pendentes ?? 0} em análise`,
      icon: <TreePine className="size-5 text-emerald-600" />,
    },
    {
      label: "Outorgas",
      value: dashboard?.total_outorgas ?? 0,
      help: `${dashboard?.outorgas_vencendo ?? 0} vencendo`,
      icon: <Droplets className="size-5 text-blue-600" />,
    },
    {
      label: "Alertas abertos",
      value: dashboard?.total_alertas_abertos ?? 0,
      help: `${dashboard?.alertas_criticos ?? 0} críticos`,
      icon: <ShieldAlert className="size-5 text-orange-600" />,
    },
    {
      label: "Outorgas vencidas",
      value: dashboard?.outorgas_vencidas ?? 0,
      help: "exigem ação imediata",
      icon: <TriangleAlert className="size-5 text-red-600" />,
    },
  ] as const;

  const quickActions = [
    {
      href: "/dashboard/ambiental/car/lista",
      title: "CARs",
      description: "Gerencie o Cadastro Ambiental Rural por propriedade.",
      icon: <MapPinned className="size-5" />,
    },
    {
      href: "/dashboard/ambiental/outorgas",
      title: "Outorgas hídricas",
      description: "Acompanhe captação, vencimentos e status das licenças.",
      icon: <Droplets className="size-5" />,
    },
    {
      href: "/dashboard/ambiental/monitoramento/alertas",
      title: "Alertas ambientais",
      description: "Registre eventos, resoluções e prioridades de campo.",
      icon: <ShieldAlert className="size-5" />,
    },
    {
      href: "/dashboard/ambiental/carbono",
      title: "Gestão de Carbono",
      description: "Acompanhe emissões, projetos e relatórios MRV.",
      icon: <Leaf className="size-5" />,
    },
    {
      href: "/dashboard/ambiental/car/importar",
      title: "Importar CAR",
      description: "Cadastre um CAR manualmente a partir dos dados oficiais.",
      icon: <FileSearch className="size-5" />,
    },
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
      <PageHeader
        title="Dashboard Ambiental"
        description="Resumo executivo do compliance ambiental, CARs, outorgas e alertas."
        icon={<Leaf className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Ambiental" },
        ]}
      />

      {isError && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-sm border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <span className="flex items-center gap-2"><AlertCircle className="size-4" />Não foi possível carregar os indicadores ambientais.</span>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Tentar novamente</Button>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-28 rounded-sm" />
            ))
          : summaryCards.map((card) => (
              <Card key={card.label} className="shadow-sm">
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex size-11 items-center justify-center rounded-sm bg-muted">
                    {card.icon}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                      {card.label}
                    </p>
                    <p className="text-2xl font-black tabular-nums">{card.value}</p>
                    <p className="text-xs text-muted-foreground">{card.help}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {quickActions.map((action) => (
          <Card key={action.href} className="group shadow-sm transition-shadow hover:shadow-md">
            <CardHeader className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 text-primary">
                  {action.icon}
                </div>
                <Badge variant="outline" className="text-[10px] font-semibold uppercase tracking-wide">
                  Acesso rápido
                </Badge>
              </div>
              <div className="space-y-1">
                <CardTitle className="text-base">{action.title}</CardTitle>
                <CardDescription className="text-sm">{action.description}</CardDescription>
              </div>
            </CardHeader>
            <CardFooter>
              <Button asChild variant="outline" size="sm" className="w-full">
                <Link href={action.href}>
                  Abrir
                  <ArrowRight data-icon="inline-end" className="size-4" />
                </Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Prioridades ambientais</CardTitle>
            <CardDescription>
              Itens que precisam de acompanhamento imediato.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-sm border bg-muted/20 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium">CARs em análise</p>
                <p className="text-xs text-muted-foreground">Registros pendentes de validação.</p>
              </div>
              <Badge variant="secondary">{dashboard?.cars_pendentes ?? 0}</Badge>
            </div>
            <div className="flex items-center justify-between rounded-sm border bg-muted/20 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium">Outorgas vencendo</p>
                <p className="text-xs text-muted-foreground">Renovações previstas para os próximos 90 dias.</p>
              </div>
              <Badge variant="warning">{dashboard?.outorgas_vencendo ?? 0}</Badge>
            </div>
            <div className="flex items-center justify-between rounded-sm border bg-muted/20 px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium">Alertas críticos</p>
                <p className="text-xs text-muted-foreground">Ocorrências de maior severidade.</p>
              </div>
              <Badge variant="destructive">{dashboard?.alertas_criticos ?? 0}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Atalhos do módulo</CardTitle>
            <CardDescription>
              Navegação direta para as telas operacionais.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button asChild variant="outline" className="w-full justify-between">
              <Link href="/dashboard/ambiental/car/lista">
                <span className="flex items-center gap-2">
                  <MapPinned data-icon="inline-start" className="size-4" />
                  Lista de CARs
                </span>
                <ArrowRight data-icon="inline-end" className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-between">
              <Link href="/dashboard/ambiental/outorgas">
                <span className="flex items-center gap-2">
                  <Droplets data-icon="inline-start" className="size-4" />
                  Outorgas hídricas
                </span>
                <ArrowRight data-icon="inline-end" className="size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="w-full justify-between">
              <Link href="/dashboard/ambiental/monitoramento/alertas">
                <span className="flex items-center gap-2">
                  <ShieldAlert data-icon="inline-start" className="size-4" />
                  Alertas ambientais
                </span>
                <ArrowRight data-icon="inline-end" className="size-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
