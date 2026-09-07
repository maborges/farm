"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BrainCircuit } from "lucide-react";
import { useAppStore } from "@/lib/stores/app-store";
import { useSafrasAtivas } from "@/hooks/use-agricola";
import { PageHeader } from "@/components/shared/page-header";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
    { label: "IA", href: "/dashboard/ia/performance" },
    { label: "Resumo Safra" }
  ];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Resumo IA da Safra"
        description="Visão consolidada do status atual e principais métricas geradas pela IA."
        icon={<BrainCircuit className="text-primary animate-pulse" size={24} />}
        breadcrumbs={breadcrumbs}
      />

      <Card className="rounded-sm border-muted/40">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-black uppercase tracking-widest">Safra do resumo</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5 max-w-md">
            <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
              Safra
            </label>
            <Select
              value={effectiveSafraId}
              onValueChange={setSelectedSafraId}
              disabled={!hasHydrated || isLoadingSafras || safras.length === 0}
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
      
      <div className="max-w-4xl mx-auto w-full">
        <ResumoDiarioCard safraId={effectiveSafraId || undefined} />
      </div>
    </div>
  );
}
