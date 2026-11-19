"use client";

import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { useSafrasAtivas } from "@/hooks/use-agricola";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ClipboardList, Zap, ShieldCheck, ArrowRight, TrendingUp, TrendingDown, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useIAFeedback, useIATimer } from "@/hooks";

interface IAActionItem {
  id: string;
  tipo: string;
  descricao: string;
  impacto_estimado: string;
  impacto_valor: number;
  prioridade: number;
  acao_sugerida: string;
  parametros_json: any;
}

interface IAAutopilotActionExecutada {
  descricao: string;
  tipo: string;
  impacto: string;
}

interface IAPlanoAcaoData {
  nivel_risco: string;
  resumo: string;
  acoes: IAActionItem[];
  data_geracao: string;
  acoes_executadas_automaticamente?: IAAutopilotActionExecutada[];
}

const fmt = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);

export function IAPlanoAcaoCard({ safraId }: { safraId?: string }) {
  const activeFazendaId = useAppStore((state) => state.activeFazendaId);
  const activeGrupoId = useAppStore((state) => state.activeGrupoId);
  const grupos = useAppStore((state) => state.grupos);
  const firstUnidadeProdutivaId = useAppStore((state) => state.unidadesProdutivasAutorizadas[0]?.id ?? null);
  const grupoAtivo = grupos.find((grupo) => grupo.id === activeGrupoId) ?? grupos[0] ?? null;
  const fazendasDoGrupoAtivo = grupoAtivo?.fazendas ?? [];
  const activeFazendaValida = !!activeFazendaId && fazendasDoGrupoAtivo.some((fazenda) => fazenda.id === activeFazendaId);
  const fallbackFazendaId = fazendasDoGrupoAtivo[0]?.id ?? firstUnidadeProdutivaId ?? undefined;
  const unidadeContextoId = activeFazendaValida ? activeFazendaId : fallbackFazendaId;
  const { data: safras = [], isLoading: safrasLoading } = useSafrasAtivas(unidadeContextoId);
  const effectiveSafraId = safraId ?? safras[0]?.id;
  const router = useRouter();
  const { showFeedback } = useIAFeedback();
  const { getElapsedTime } = useIATimer();

  const { data, isLoading } = useQuery<IAPlanoAcaoData>({
    queryKey: ["ia-plano-acao", effectiveSafraId, activeFazendaId],
    queryFn: () => apiFetch(`/ia/financeiro/plano-acao?safra_id=${effectiveSafraId}`),
    enabled: !!effectiveSafraId,
  });

  const mutation = useMutation({
    mutationFn: (acao: IAActionItem) => 
      apiFetch("/ia/acoes-assistidas/registrar", {
        method: "POST",
        body: {
          origem: "PLANO_ACAO",
          origem_id: acao.id,
          tipo_acao: acao.acao_sugerida,
          parametros_json: acao.parametros_json
        }
      }),
    onSuccess: (res: any, variables: IAActionItem) => {
      const tempo_decisao = getElapsedTime();
      
      showFeedback({
        impacto_valor: variables.impacto_valor,
        tempo_decisao_ms: tempo_decisao,
        tipo_ia: variables.tipo,
        origem: "PLANO_ACAO_INDIVIDUAL"
      });
      
      const params = new URLSearchParams();
      params.set("action_id", res.id); // ID da ação assistida registrada
      params.set("auto_simular", "true");
      
      if (variables.parametros_json) {
        Object.entries(variables.parametros_json).forEach(([key, value]) => {
          params.set(key, String(value));
        });
      }

      router.push(`/dashboard/financeiro/dre?${params.toString()}`);
    },
    onError: () => {
      toast.error("Erro ao preparar execução assistida.");
    }
  });

  const batchMutation = useMutation({
    mutationFn: (acoes: IAActionItem[]) => 
      apiFetch("/ia/acoes-assistidas/registrar", {
        method: "POST",
        body: {
          origem: "PLANO_ACAO",
          tipo_acao: "BATCH",
          parametros_json: {
            acoes_ids: acoes.map(a => a.id),
            agregado: acoes.reduce((acc, a) => ({ ...acc, ...a.parametros_json }), {})
          }
        }
      }),
    onSuccess: (res: any, acoes: IAActionItem[]) => {
      const tempo_decisao = getElapsedTime();
      const impactoTotal = acoes.reduce((acc, a) => acc + (a.impacto_valor || 0), 0);

      showFeedback({
        impacto_valor: impactoTotal,
        tempo_decisao_ms: tempo_decisao,
        tipo_ia: "BATCH_PLANO_ACAO",
        origem: "PLANO_ACAO_BATCH"
      });
      
      const params = new URLSearchParams();
      params.set("action_id", res.id);
      params.set("auto_simular", "true");
      params.set("is_batch", "true");
      
      // Agregar todos os parâmetros
      const agregado = acoes.reduce((acc, a) => ({ ...acc, ...a.parametros_json }), {});
      Object.entries(agregado).forEach(([key, value]) => {
        params.set(key, String(value));
      });

      router.push(`/dashboard/financeiro/dre?${params.toString()}`);
    }
  });

  if (isLoading || safrasLoading) {
    return <Skeleton className="h-[400px] w-full rounded-sm" />;
  }

  if (!effectiveSafraId) {
    return (
      <Card className="border-dashed bg-muted/30">
        <CardContent className="p-12 flex flex-col items-center text-center">
          <Sparkles className="size-12 text-muted-foreground/20 mb-4" />
          <h3 className="text-lg font-bold text-muted-foreground">Plano de Ação Indisponível</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-sm">
            Selecione uma fazenda com safra ativa para gerar o plano estratégico do Copiloto.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.acoes) {
    return (
      <Card className="border-dashed bg-muted/30">
          <CardContent className="p-12 flex flex-col items-center text-center">
          <Sparkles className="size-12 text-muted-foreground/20 mb-4" />
          <h3 className="text-lg font-bold text-muted-foreground">Plano de Ação Indisponível</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-sm">
            Nao foi possível gerar um plano estratégico. Certifique-se de que existem lançamentos financeiros e uma safra ativa selecionada.
          </p>
        </CardContent>
      </Card>
    );
  }

  const isCritico = data.nivel_risco === "CRITICO";
  const isAlto = data.nivel_risco === "ALTO";
  const impactoTotal = data.acoes.reduce((acc, a) => acc + (a.impacto_valor || 0), 0);

  return (
    <Card className="border-l-4 border-l-alert-success-icon shadow-md animate-in fade-in slide-in-from-bottom-4 duration-700">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-alert-success-bg text-alert-success-icon border border-alert-success-border rounded-sm">
              <ClipboardList className="h-4 w-4" />
            </div>
            <CardTitle className="text-sm font-black uppercase tracking-widest">Plano de Recuperação IA</CardTitle>
          </div>
          <Badge variant={isCritico ? "destructive" : isAlto ? "warning" : "secondary"} className="rounded-sm text-[9px] font-black h-5 uppercase">
            {data.nivel_risco}
          </Badge>
        </div>
        <CardDescription className="text-[11px] font-bold text-muted-foreground mt-1 uppercase tracking-tighter">
          Estratégia personalizada (Step 209)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="p-3 bg-alert-success-bg/60 rounded-sm border border-alert-success-border">
          <p className="text-xs text-alert-success-description font-medium leading-relaxed italic">
            &quot;{data.resumo}&quot;
          </p>
          <div className="mt-2 pt-2 border-t border-alert-success-border flex justify-between items-center">
            <span className="text-[10px] font-black text-alert-success-title uppercase tracking-widest">Impacto Total</span>
            <span className="text-sm font-black text-alert-success-title">{fmt(impactoTotal)}</span>
          </div>
        </div>

        {data.acoes.length > 1 && (
          <Button 
            onClick={() => batchMutation.mutate(data.acoes)}
            disabled={batchMutation.isPending || mutation.isPending}
            variant="outline"
            size="sm"
            className="w-full border-emerald-600/30 text-emerald-700 dark:text-emerald-400 font-black uppercase text-[10px] gap-2 h-9 rounded-sm"
          >
            {batchMutation.isPending ? "Processando Plano..." : "Executar Plano Completo"}
            <Zap className="h-3 w-3 text-emerald-600 animate-pulse" />
          </Button>
        )}

        <div className="space-y-3">
          <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest px-1">Ações Detalhadas</h4>
          
          {data.acoes.map((acao, index) => (
            <div 
              key={acao.id} 
              className={`p-3 rounded-sm border transition-all duration-300 ${
                acao.prioridade === 1 
                  ? 'border-emerald-200 bg-white dark:bg-slate-900 shadow-sm ring-1 ring-emerald-500/10' 
                  : 'border-border/40 bg-muted/20'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-black ${
                    acao.prioridade === 1 ? 'bg-emerald-600 text-white' : 'bg-muted text-muted-foreground'
                  }`}>
                    {index + 1}
                  </span>
                  <Badge variant="outline" className="text-[9px] h-4 px-1.5 uppercase font-black border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                    {acao.tipo.replace('_', ' ')}
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                   {acao.tipo.includes('RECEITA') ? <TrendingUp className="h-3 w-3 text-emerald-500" /> : <TrendingDown className="h-3 w-3 text-red-500" />}
                   <span className="text-[11px] font-black text-slate-900 dark:text-slate-100">
                     {acao.impacto_estimado}
                   </span>
                </div>
              </div>
              
              <p className="text-xs text-muted-foreground font-medium mb-3 leading-snug">
                {acao.descricao}
              </p>

              <Button 
                onClick={() => mutation.mutate(acao)}
                disabled={mutation.isPending || batchMutation.isPending}
                variant="outline" 
                size="sm" 
                className={`w-full h-8 text-[10px] font-black uppercase gap-2 transition-all active:scale-95 border-emerald-600/20 text-emerald-600`}
              >
                {mutation.isPending ? "Processando..." : "Executar Ação Individual"}
                <ArrowRight className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>

        {data.acoes_executadas_automaticamente && data.acoes_executadas_automaticamente.length > 0 && (
          <div className="space-y-2 mt-2 p-2 bg-blue-50/30 dark:bg-blue-950/10 border border-blue-100/50 dark:border-blue-900/20 rounded-sm">
            <h4 className="text-[9px] font-black text-blue-700 dark:text-blue-400 uppercase tracking-widest flex items-center gap-2">
              <Zap className="h-3 w-3 fill-blue-500 animate-pulse" />
              Autopilot: Otimização em Segundo Plano
            </h4>
            <div className="space-y-1.5">
              {data.acoes_executadas_automaticamente.map((auto, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <p className="text-[10px] text-slate-600 dark:text-slate-400 font-medium leading-tight">{auto.descricao}</p>
                  <span className="text-[9px] font-black text-blue-600 shrink-0">{auto.impacto}</span>
                </div>
              ))}
            </div>
            <p className="text-[8px] text-blue-500/60 font-bold italic pt-1 border-t border-blue-500/10">
              Essas ações foram simuladas automaticamente com base no seu nível de autonomia.
            </p>
          </div>
        )}

        <div className="text-[9px] text-muted-foreground flex justify-between items-center pt-2 border-t border-border mt-2">
          <div className="flex items-center gap-1 font-bold">
            <ShieldCheck className="h-3 w-3 text-emerald-500" />
            <span>Copiloto IA Ativo</span>
          </div>
          <span className="opacity-60">Gerado em {new Date(data.data_geracao).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}
