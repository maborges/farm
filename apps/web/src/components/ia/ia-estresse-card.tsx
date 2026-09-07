"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Zap, ArrowRight, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useSafrasAtivas } from "@/hooks/use-agricola";

interface IAEstresseData {
  nivel_risco: string;
  descricao: string;
  pior_cenario: {
    cenario: string;
    receita: number;
    custo: number;
    resultado: number;
    margem_resultante: number;
    variacao_resultado: number;
  } | null;
  todos_cenarios: any[];
  acao_recomendada: string;
  probabilidade: string;
}

const dashboardCardButtonClass = "h-8 rounded-sm px-3 text-xs font-semibold";

export function IAEstresseCard() {
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const activeGrupoId = useAppStore((state) => state.activeGrupoId);
  const grupos = useAppStore((state) => state.grupos);
  const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
  const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
  const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
  const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
  const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
  const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
  const router = useRouter();
  const [data, setData] = useState<IAEstresseData | null>(null);
  const [loading, setLoading] = useState(true);
  const { data: safras = [] } = useSafrasAtivas(unidadeContextoId);
  const safraAtivaId = safras[0]?.id ?? "";

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const response = await apiFetch<IAEstresseData>(
          `/ia/financeiro/simulacao-estresse?safra_id=${safraAtivaId}`
        );
        setData(response);
      } catch (error) {
        console.error("Erro ao carregar simulação de estresse:", error);
        setData(null);
      } finally {
        setLoading(false);
      }
    }

    if (!activeFazendaId || !safraAtivaId) {
      setData(null);
      setLoading(false);
      return;
    }

    loadData();
  }, [activeFazendaId, safraAtivaId]);

  if (loading) {
    return <Skeleton className="h-[280px] w-full rounded-sm" />;
  }

  if (!activeFazendaId) {
    return (
      <Card className="border-dashed bg-muted/30">
          <CardContent className="p-6 flex flex-col items-center text-center">
          <ShieldAlert className="size-8 text-muted-foreground/40 mb-3" />
          <h4 className="text-sm font-bold text-muted-foreground">Simulação de Estresse Indisponível</h4>
          <p className="text-xs text-muted-foreground mt-1 max-w-[220px]">
            Selecione uma fazenda para visualizar o pior cenário projetado pelo Copiloto.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.pior_cenario) {
    return null;
  }

  const isCritico = data.nivel_risco === "CRITICO";
  const isAlto = data.nivel_risco === "ALTO";

  const cardClass = isCritico
    ? "border-l-4 border-l-rose-500/80 bg-card shadow-sm animate-in fade-in slide-in-from-right-4 duration-500"
    : isAlto
      ? "border-l-4 border-l-amber-500/80 bg-card shadow-sm animate-in fade-in slide-in-from-right-4 duration-500"
      : "border-l-4 border-l-blue-500/80 bg-card shadow-sm animate-in fade-in slide-in-from-right-4 duration-500";

  const iconClass = isCritico
    ? "text-rose-600 bg-rose-100/80"
    : isAlto
      ? "text-amber-600 bg-amber-100/80"
      : "text-blue-600 bg-blue-100/80";

  const descriptionClass = isCritico
    ? "bg-rose-50/50 border-rose-100"
    : isAlto
      ? "bg-amber-50/50 border-amber-100"
      : "bg-blue-50/40 border-blue-100";

  return (
    <Card className={cardClass}>
      <CardHeader className="pb-2 border-b border-border/60 bg-background/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`size-8 rounded-sm flex items-center justify-center shrink-0 ${iconClass}`}>
              <ShieldAlert className="h-4 w-4" />
            </span>
            <CardTitle className="text-sm font-bold uppercase tracking-wider">Simulação de Estresse</CardTitle>
          </div>
          <Badge variant={isCritico ? "destructive" : isAlto ? "warning" : "default"} className="rounded-sm text-[10px]">
            {data.nivel_risco}
          </Badge>
        </div>
        <CardDescription className="text-xs font-medium mt-1">
          Pior cenário projetado pela IA (Step 206)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className={`p-3 rounded-sm border ${descriptionClass}`}>
          <p className="text-xs text-muted-foreground leading-relaxed italic">
            &quot;{data.descricao}&quot;
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Margem Crítica</span>
            <div className={`text-lg font-bold ${data.pior_cenario.margem_resultante < 0 ? 'text-red-600' : 'text-slate-900 dark:text-slate-100'}`}>
              {data.pior_cenario.margem_resultante}%
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold">Resultado Crítico</span>
            <div className={`text-lg font-bold ${data.pior_cenario.resultado < 0 ? 'text-red-600' : 'text-slate-900 dark:text-slate-100'}`}>
              R$ {data.pior_cenario.resultado.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        <div className="space-y-2 pt-1">
          <div className="flex items-center gap-2 text-[11px] font-bold text-foreground uppercase tracking-tighter">
            <Zap className="h-3 w-3 text-amber-500 fill-amber-500" />
            Ação Recomendada
          </div>
          <p className="text-xs text-muted-foreground">
            {data.acao_recomendada}
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className={`${dashboardCardButtonClass} w-full gap-2`}
          onClick={() => {
            if (!safraAtivaId) {
              return;
            }
            router.push(
              `/dashboard/financeiro/dre?safra_id=${safraAtivaId}&receita=-30&custos=20&auto_simular=true`
            );
          }}
          disabled={!safraAtivaId}
        >
          Simular Correção
          <ArrowRight className="h-3 w-3" />
        </Button>

        <div className="text-[9px] text-muted-foreground flex justify-between items-center pt-1 border-t border-border/60 mt-2">
          <span>Probabilidade: {data.probabilidade}</span>
          <span className="opacity-60">Copiloto IA — Simulação Extrema</span>
        </div>
      </CardContent>
    </Card>
  );
}
