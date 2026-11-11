"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BrainCircuit, Sprout, TrendingUp, Sparkles, AlertTriangle } from "lucide-react";
import { useAppStore } from "@/lib/stores/app-store";
import { useSafrasAtivas } from "@/hooks/use-agricola";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ResumoDiarioCard } from "@/components/dashboard/resumo-diario-card";
import { getSafraLabel } from "@/lib/safra-label";

type IAResumoViewProps = {
  initialSafraId?: string;
};

export function IAResumoView({ initialSafraId }: IAResumoViewProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const activeGrupoId = useAppStore((state) => state.activeGrupoId);
  const grupos = useAppStore((state) => state.grupos);
  const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
  const hasHydrated = useAppStore((state) => state._hasHydrated);
  const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
  const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
  const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
  const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
  const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
  const { data: safras = [], isLoading: isLoadingSafras } = useSafrasAtivas(unidadeContextoId);
  const [selectedSafraId, setSelectedSafraId] = useState<string>(initialSafraId ?? "");

  const effectiveSafraId =
    safras.find((safra) => safra.id === selectedSafraId)?.id ??
    (initialSafraId && safras.some((safra) => safra.id === initialSafraId)
      ? initialSafraId
      : safras[0]?.id ?? selectedSafraId);

  useEffect(() => {
    if (initialSafraId && safras.some((s) => s.id === initialSafraId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedSafraId(initialSafraId);
    }
  }, [initialSafraId, safras]);

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
    { label: "Copiloto IA", href: "/dashboard/ia/resumo" },
    { label: "Resumo da Safra" },
  ];

  const safraSelecionada = safras.find((s) => s.id === effectiveSafraId);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Resumo IA da Safra"
        description="Diagnóstico consolidado de saúde financeira, riscos e recomendações analíticas geradas pelo Copiloto."
        icon={<BrainCircuit className="text-primary" size={22} />}
        breadcrumbs={breadcrumbs}
      />

      {/* BARRA DE CONTEXTO E SELEÇÃO DE SAFRA */}
      <Card className="rounded-sm border border-border/70 bg-card shadow-xs">
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-sm bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Sprout className="size-4.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">
                  {safraSelecionada ? (safraSelecionada.nome ?? getSafraLabel(safraSelecionada)) : "Safra em Análise"}
                </span>
                {safraSelecionada?.cultura && (
                  <Badge variant="secondary" className="text-[10px] rounded-sm py-0 h-4">
                    {safraSelecionada.cultura}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Alterne a safra abaixo para recalcular os insights e simulações do Copiloto.
              </p>
            </div>
          </div>

          <div className="w-full sm:w-72 shrink-0">
            <Select
              value={effectiveSafraId}
              onValueChange={setSelectedSafraId}
              disabled={!hasHydrated || isLoadingSafras || safras.length === 0}
            >
              <SelectTrigger className="h-8 text-xs rounded-sm">
                <SelectValue placeholder={isLoadingSafras ? "Carregando safras..." : "Selecionar safra"} />
              </SelectTrigger>
              <SelectContent>
                {safras.map((safra) => (
                  <SelectItem key={safra.id} value={safra.id} className="text-xs">
                    {safra.nome ?? getSafraLabel(safra)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* ÁREA CENTRAL DO RESUMO ANALÍTICO */}
      <div className="w-full">
        <ResumoDiarioCard safraId={effectiveSafraId || undefined} />
      </div>
    </div>
  );
}

