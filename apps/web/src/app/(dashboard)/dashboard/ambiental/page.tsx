"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
import {
  LayoutDashboard,
  Leaf,
  ShieldAlert,
  Droplets,
  TriangleAlert,
  MapPinned,
  FileSearch,
  ArrowRight,
  TreePine,
  AlertCircle,
  Map,
  Layers,
  History,
  CheckCircle2,
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
      accent: "border-l-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/10",
    },
    {
      label: "Outorgas",
      value: dashboard?.total_outorgas ?? 0,
      help: `${dashboard?.outorgas_vencendo ?? 0} vencendo`,
      icon: <Droplets className="size-5 text-blue-600" />,
      accent: "border-l-blue-500 bg-blue-50/40 dark:bg-blue-950/10",
    },
    {
      label: "Alertas abertos",
      value: dashboard?.total_alertas_abertos ?? 0,
      help: `${dashboard?.alertas_criticos ?? 0} críticos`,
      icon: <ShieldAlert className="size-5 text-orange-600" />,
      accent: "border-l-orange-500 bg-orange-50/40 dark:bg-orange-950/10",
    },
    {
      label: "Outorgas vencidas",
      value: dashboard?.outorgas_vencidas ?? 0,
      help: "exigem ação imediata",
      icon: <TriangleAlert className="size-5 text-red-600" />,
      accent: "border-l-red-500 bg-red-50/40 dark:bg-red-950/10",
    },
  ] as const;

  const quickActions = [
    {
      href: "/dashboard/ambiental/car/lista",
      title: "CARs da Fazenda",
      description: "Cadastro Ambiental Rural e situação cadastral",
      icon: MapPinned,
      badge: dashboard?.total_cars ? `${dashboard.total_cars}` : undefined,
    },
    {
      href: "/dashboard/ambiental/car/importar",
      title: "Importar CAR",
      description: "Upload e integração com bases oficiais",
      icon: FileSearch,
    },
    {
      href: "/dashboard/ambiental/car/areas",
      title: "Áreas & Preservação",
      description: "APP, reserva legal e vegetação nativa",
      icon: Layers,
    },
    {
      href: "/dashboard/ambiental/outorgas",
      title: "Outorgas Hídricas",
      description: "Captação de água, poços e vencimentos",
      icon: Droplets,
      badge: dashboard?.outorgas_vencendo ? `${dashboard.outorgas_vencendo} vencer` : undefined,
    },
    {
      href: "/dashboard/ambiental/monitoramento/alertas",
      title: "Alertas & Embargos",
      description: "Monitoramento por satélite e autuações",
      icon: ShieldAlert,
      badge: dashboard?.alertas_criticos ? `${dashboard.alertas_criticos} críticos` : undefined,
    },
    {
      href: "/dashboard/ambiental/monitoramento/mapa",
      title: "Mapa Ambiental",
      description: "Visão geoespacial de polígonos e zonas",
      icon: Map,
    },
    {
      href: "/dashboard/ambiental/monitoramento/historico",
      title: "Histórico & Laudos",
      description: "Linha do tempo de monitoramento e auditoria",
      icon: History,
    },
    {
      href: "/dashboard/ambiental/carbono",
      title: "Gestão de Carbono",
      description: "Estoque de carbono, créditos e MRV",
      icon: Leaf,
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Painel Ambiental"
        description="Acompanhe conformidade, recursos hídricos e ocorrências ambientais."
        icon={<LayoutDashboard className="size-5 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Ambiental" },
        ]}
      />

      {/* Quick Actions Grid */}
      <QuickActionGrid actions={quickActions} />

      {isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription className="flex items-center justify-between gap-3">
            <span>Não foi possível carregar os indicadores ambientais.</span>
            <Button variant="outline" size="sm" onClick={() => refetch()}>Tentar novamente</Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-28 rounded-sm" />
            ))
          : summaryCards.map((card) => (
              <Card key={card.label} className={`rounded-sm border-l-4 shadow-sm ${card.accent}`}>
                <CardContent className="flex items-center gap-4 p-4">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-sm bg-background/80">
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

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="rounded-sm shadow-sm">
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
              <Badge variant="secondary" className="bg-amber-100 text-amber-800">{dashboard?.outorgas_vencendo ?? 0}</Badge>
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

        <Card className="rounded-sm shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Conformidade e Monitoramento</CardTitle>
            <CardDescription>
              Status de conformidade e integridade geoespacial.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-sm border bg-muted/20">
              <div className="p-2 rounded-sm bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700">
                <CheckCircle2 className="size-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">Base de dados sincronizada</p>
                <p className="text-xs text-muted-foreground">Polígonos de CAR e licenças hídricas validados.</p>
              </div>
              <Badge variant="outline" className="text-xs rounded-sm border-emerald-300 text-emerald-700">Regular</Badge>
            </div>
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-muted-foreground">Última checagem satelital</span>
              <span className="text-xs font-medium">Hoje às 06:00</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
