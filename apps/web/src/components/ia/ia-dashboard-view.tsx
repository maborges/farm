"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BrainCircuit, Target, TrendingUp, Zap, Sparkles, Activity, AlertTriangle, Compass, SlidersHorizontal } from "lucide-react";
import { useAppStore } from "@/lib/stores/app-store";
import { useSafrasAtivas } from "@/hooks/use-agricola";
import { PageHeader } from "@/components/shared/page-header";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { QuickActionGrid } from "@/components/ui/quick-action-grid";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { IAPlanoAcaoCard } from "@/components/ia/ia-plano-acao-card";
import { IAPredicoesCard } from "@/components/ia/ia-predicoes-card";
import { IAEstresseCard } from "@/components/ia/ia-estresse-card";
import { getSafraLabel } from "@/lib/safra-label";

type IADashboardViewProps = {
  initialSafraId?: string;
};

export function IADashboardView({ initialSafraId }: IADashboardViewProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const activeGrupoId = useAppStore((state) => state.activeGrupoId);
  const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
  const grupos = useAppStore((state) => state.grupos);
  const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
  const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
  const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
  const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
  const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
  const { data: safras = [], isLoading: isLoadingSafras } = useSafrasAtivas(unidadeContextoId);
  const [selectedSafraId, setSelectedSafraId] = useState<string>(initialSafraId ?? "");

  const effectiveSafraId =
    safras.find((safra) => safra.id === selectedSafraId)?.id ??
    (initialSafraId && safras.some((safra) => safra.id === initialSafraId) ? initialSafraId : safras[0]?.id ?? "");

  useEffect(() => {
    if (!effectiveSafraId) {
      return;
    }

    const currentSafraParam = searchParams.get("safra_id");
    if (currentSafraParam === effectiveSafraId) {
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set("safra_id", effectiveSafraId);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [effectiveSafraId, pathname, router, searchParams]);

  const breadcrumbs = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Inteligência Artificial" },
  ];

  const handleSafraChange = (value: string) => {
    setSelectedSafraId(value);
  };

  const safraParam = effectiveSafraId ? `?safra_id=${effectiveSafraId}` : "";
  const quickActions = [
    {
      href: `/dashboard/ia/resumo${safraParam}`,
      title: "Resumo da Safra",
      desc: "Síntese executiva diária e status consolidado",
      icon: Sparkles,
      badge: "Diário",
    },
    {
      href: `/dashboard/ia/plano-acao${safraParam}`,
      title: "Plano de Ação",
      desc: "Tarefas priorizadas e mitigação de gargalos",
      icon: Target,
    },
    {
      href: `/dashboard/ia/performance${safraParam}`,
      title: "Performance de Modelos",
      desc: "Acurácia de predições e aprendizado contínuo",
      icon: Activity,
    },
    {
      href: `/dashboard/inteligencia-operacional/recomendacoes`,
      title: "Recomendações IA",
      desc: "Sugestões de manejo e otimização em campo",
      icon: Compass,
    },
    {
      href: `/dashboard/agricola/prioridades`,
      title: "Matriz de Prioridades",
      desc: "Classificação por impacto operacional e custo",
      icon: AlertTriangle,
    },
    {
      href: `/dashboard/ia#predicoes`,
      title: "Predição de Riscos",
      desc: "Modelos preditivos de produtividade e pragas",
      icon: TrendingUp,
    },
    {
      href: `/dashboard/ia#estresse`,
      title: "Simulação de Estresse",
      desc: "Análise de estresse hídrico e térmico",
      icon: Zap,
    },
    {
      href: `/dashboard/configuracoes/globais`,
      title: "Ajustes de Modelo",
      desc: "Parâmetros e sensibilidade dos alertas IA",
      icon: SlidersHorizontal,
    },
  ];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Copiloto IA"
        description="Seu copiloto prioriza o que exige atenção agora. Menos ruído, mais decisão."
        icon={<BrainCircuit className="text-primary animate-pulse" size={24} />}
        breadcrumbs={breadcrumbs}
      />

      {/* Quick Actions Grid */}
      <QuickActionGrid
        actions={quickActions.map(a => ({
          title: a.title,
          description: a.desc,
          icon: a.icon,
          href: a.href,
          badge: a.badge,
        }))}
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          {
            icon: Target,
            titulo: "Decisão essencial",
            texto: "A IA escolhe o que mais importa agora e prepara a ação para você.",
            cls: "text-primary",
            bg: "bg-primary/5 border-primary/15",
          },
          {
            icon: Zap,
            titulo: "Ação em um clique",
            texto: "Não precisa analisar tudo. O Copiloto já fez isso e te entrega a decisão pronta.",
            cls: "text-amber-600",
            bg: "bg-amber-500/5 border-amber-500/15",
          },
          {
            icon: TrendingUp,
            titulo: "Aprende com você",
            texto: "Com o tempo, a IA adapta o tom e a prioridade ao seu perfil de decisão.",
            cls: "text-emerald-600",
            bg: "bg-emerald-500/5 border-emerald-500/15",
          },
        ].map(({ icon: Icon, titulo, texto, cls, bg }) => (
          <div key={titulo} className={`rounded-sm border px-4 py-3 flex items-start gap-3 ${bg}`}>
            <Icon className={`size-4 shrink-0 mt-0.5 ${cls}`} />
            <div className="space-y-0.5">
              <p className={`text-[11px] font-black uppercase tracking-wide ${cls}`}>{titulo}</p>
              <p className="text-xs text-muted-foreground leading-snug">{texto}</p>
            </div>
          </div>
        ))}
      </div>

      <Card className="rounded-sm border-muted/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-black uppercase tracking-widest">Contexto da IA</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5 max-w-md">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Safra
            </label>
            <Select
              value={effectiveSafraId}
              onValueChange={handleSafraChange}
              disabled={isLoadingSafras || safras.length === 0}
            >
              <SelectTrigger className="rounded-sm">
                <SelectValue placeholder={isLoadingSafras ? "Carregando safras..." : "Selecionar safra"} />
              </SelectTrigger>
              <SelectContent>
                {safras.map((safra) => (
                  <SelectItem key={safra.id} value={safra.id}>
                    {safra.nome ?? getSafraLabel(safra)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              A safra ativa é selecionada automaticamente quando existe uma no contexto da fazenda.
            </p>
          </div>
        </CardContent>
      </Card>

      <Separator className="rounded-sm" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <IAPlanoAcaoCard safraId={effectiveSafraId || undefined} />
        </div>
        <div className="space-y-6">
          <IAPredicoesCard safraId={effectiveSafraId || undefined} />
          <IAEstresseCard />
        </div>
      </div>
    </div>
  );
}
