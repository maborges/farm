"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { 
  Bot, 
  Shield, 
  Zap, 
  AlertTriangle, 
  Settings2, 
  Info, 
  CheckCircle, 
  TrendingUp, 
  ArrowRight,
  BrainCircuit,
  TestTube2,
  LineChart,
  UserCheck
} from "lucide-react";
import { useIAExplanation, useIAProgresso } from "@/hooks";
import { Badge } from "@/components/ui/badge";
import { IAGrowthExperimentosDashboard } from "@/components/ia/ia-growth-experimentos-dashboard";
import { IAGrowthPersonasDashboard } from "@/components/ia/ia-growth-personas-dashboard";

interface IAConfig {
  ativo: boolean;
  nivel_autonomia: 'BAIXO' | 'MEDIO' | 'ALTO';
  tipos_permitidos: string[];
  limite_impacto_percentual: number;
}

interface TuningSuggestion {
  deve_ajustar: boolean;
  mensagem: string;
  novo_limite: number;
}

export function IASettingsClient() {
  const queryClient = useQueryClient();

  const { data: explanationData, isLoading: isLoadingExplanation } = useIAExplanation();
  const { data: progressoData, isLoading: isLoadingProgresso } = useIAProgresso();

  const { data, isLoading } = useQuery<IAConfig>({
    queryKey: ["ia-autopilot-config"],
    queryFn: () => apiFetch("/ia/autopilot/config"),
  });

  const mutation = useMutation({
    mutationFn: (vars: Partial<IAConfig>) => apiFetch("/ia/autopilot/config", {
        method: "PATCH",
        body: JSON.stringify(vars)
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-autopilot-config"] });
      toast.success("Configurações do Autopilot atualizadas com sucesso!");
    },
    onError: () => {
      toast.error("Erro ao atualizar configurações.");
    },
  });

  const { data: tuningSuggestion } = useQuery<TuningSuggestion>({
    queryKey: ["ia-autopilot-tuning-suggestion"],
    queryFn: () => apiFetch("/ia/autopilot/sugestao-tuning"),
    enabled: !!data?.ativo,
  });

  const applyTuningMutation = useMutation({
    mutationFn: (novoLimite: number) =>
      apiFetch("/ia/autopilot/aplicar-tuning", {
        method: "POST",
        body: JSON.stringify({ novo_limite: novoLimite }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-autopilot-config"] });
      queryClient.invalidateQueries({ queryKey: ["ia-autopilot-tuning-suggestion"] });
      toast.success("Autonomia ajustada conforme recomendação!");
    },
    onError: () => {
      toast.error("Erro ao aplicar recomendação.");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 w-full rounded-sm" />)}
        </div>
        <Skeleton className="h-[400px] w-full rounded-sm" />
      </div>
    );
  }

  const handleToggleActive = (checked: boolean) => {
    mutation.mutate({ ativo: checked });
  };

  const handleLevelChange = (level: string) => {
    mutation.mutate({ nivel_autonomia: level as any });
  };

  const handleImpactChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    mutation.mutate({ limite_impacto_percentual: parseFloat(e.target.value) });
  };

  const handleTypeToggle = (type: string, checked: boolean) => {
    const types = [...(data?.tipos_permitidos || [])];
    if (checked) {
      if (!types.includes(type)) types.push(type);
    } else {
      const index = types.indexOf(type);
      if (index > -1) types.splice(index, 1);
    }
    mutation.mutate({ tipos_permitidos: types });
  };

  return (
    <Tabs defaultValue="autopilot" className="w-full">
      <div className="flex items-center justify-between">
        <TabsList className="bg-muted/50 p-1 rounded-sm border border-border/50">
          <TabsTrigger value="autopilot" className="data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-sm text-[10px] font-black uppercase px-4 h-8">
            <Bot className="h-3 w-3 mr-2" />
            Autopilot
          </TabsTrigger>
          <TabsTrigger value="personas" className="data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-sm text-[10px] font-bold uppercase px-4 h-8">
            <BrainCircuit className="h-3.5 w-3.5 mr-2" />
            Personas
          </TabsTrigger>
          <TabsTrigger value="experimentos" className="data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-sm text-[10px] font-bold uppercase px-4 h-8">
            <TestTube2 className="h-3.5 w-3.5 mr-2" />
            A/B Tests
          </TabsTrigger>
          <TabsTrigger value="evolucao" className="data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-sm text-[10px] font-bold uppercase px-4 h-8">
            <LineChart className="h-3.5 w-3.5 mr-2" />
            Evolução
          </TabsTrigger>
        </TabsList>

        {data?.ativo && (
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 px-3 py-1 rounded-sm text-[10px] font-black uppercase animate-in fade-in zoom-in duration-500">
            <Zap className="h-3 w-3 mr-1.5 fill-emerald-500 animate-pulse" />
            Sistema Ativo
          </Badge>
        )}
      </div>

      <TabsContent value="autopilot" className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 outline-none">
        {tuningSuggestion?.deve_ajustar && (
          <Card variant="warning" className="relative shadow-sm">
              <div className="absolute top-0 left-0 w-1 h-full bg-alert-warning-icon" />
              <CardContent className="p-4 flex flex-col md:flex-row items-center justify-between gap-4">
                  <div className="flex items-start gap-3">
                      <div className="p-2 rounded-sm bg-alert-warning-border/40 text-alert-warning-icon shadow-sm shrink-0">
                          <Zap size={18} />
                      </div>
                      <div>
                          <h4 className="text-xs font-black uppercase tracking-widest text-card-title flex items-center gap-2">
                              Otimização de Autonomia
                              <span className="text-[9px] bg-alert-warning-border/50 px-1.5 py-0.5 rounded-full text-alert-warning-title animate-pulse">Recomendado</span>
                          </h4>
                          <p className="text-[11px] font-medium text-card-description mt-0.5 max-w-xl">
                              {tuningSuggestion.mensagem}
                          </p>
                      </div>
                  </div>
                  <Button 
                      variant="outline"
                      size="sm"
                      onClick={() => applyTuningMutation.mutate(tuningSuggestion.novo_limite)}
                      disabled={applyTuningMutation.isPending}
                      className="shrink-0 bg-card/80 hover:bg-card text-alert-warning-title border-alert-warning-border font-bold uppercase text-[10px] h-8 px-4 rounded-sm"
                  >
                      {applyTuningMutation.isPending ? "Aplicando..." : "Aplicar Recomendação"}
                      <Settings2 size={12} className="ml-2" />
                  </Button>
              </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 border-l-4 border-l-emerald-500 shadow-sm rounded-sm">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-sm font-black uppercase tracking-widest flex items-center gap-2">
                    Configurações do Autopilot
                  </CardTitle>
                  <CardDescription className="text-[10px] font-bold uppercase text-muted-foreground">
                    A IA executa ações de baixo risco sem confirmação manual.
                  </CardDescription>
                </div>
                <Switch 
                  checked={data?.ativo} 
                  onCheckedChange={handleToggleActive}
                  disabled={mutation.isPending}
                />
              </div>
            </CardHeader>
            <CardContent className={cn("space-y-8 transition-opacity duration-300", !data?.ativo && "opacity-40 pointer-events-none")}>
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-emerald-600" />
                  <Label className="text-[10px] font-black uppercase tracking-widest text-foreground">Nível de Autonomia</Label>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {[
                    { id: 'BAIXO', label: 'Conservador', desc: 'Apenas diagnósticos.', color: 'slate' },
                    { id: 'MEDIO', label: 'Equilibrado', desc: 'Ajustes de baixo impacto.', color: 'emerald' },
                    { id: 'ALTO', label: 'Avançado', desc: 'Execução em lote.', color: 'red' },
                  ].map((level) => (
                    <Button
                      key={level.id}
                      variant="outline"
                      size="sm"
                      className={cn(
                        "h-auto flex flex-col items-start p-3 text-left space-y-1 transition-all duration-300 rounded-sm border-2",
                        data?.nivel_autonomia === level.id 
                          ? "border-emerald-500 bg-emerald-50/5 shadow-sm" 
                          : "border-transparent bg-muted/30 hover:bg-muted/50"
                      )}
                      onClick={() => handleLevelChange(level.id)}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-bold text-[10px] uppercase">{level.label}</span>
                        {data?.nivel_autonomia === level.id && <CheckCircle className="h-3 w-3 text-emerald-500" />}
                      </div>
                      <span className="text-[9px] text-muted-foreground font-semibold leading-tight">{level.desc}</span>
                    </Button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Settings2 className="h-4 w-4 text-emerald-600" />
                    <Label className="text-[10px] font-black uppercase tracking-widest text-foreground">Ações Permitidas</Label>
                  </div>
                  <div className="space-y-2">
                    {[
                      { id: "SIMULACAO", label: "Simulações", desc: "Cenários no DRE" },
                      { id: "AJUSTE_CENARIO", label: "Ajustes", desc: "Metas de custos" },
                      { id: "ANALISE", label: "Análises", desc: "Diagnósticos profundos" },
                    ].map((type) => (
                      <div key={type.id} className="flex items-start space-x-3 p-2 rounded-sm hover:bg-muted/30 transition-colors border border-transparent hover:border-border/50">
                        <Checkbox 
                          id={type.id} 
                          checked={!!data?.tipos_permitidos?.includes(type.id)}
                          onChange={(e) => handleTypeToggle(type.id, e.currentTarget.checked)}
                          disabled={mutation.isPending}
                          className="mt-0.5"
                        />
                        <Label htmlFor={type.id} className="grid gap-0.5 leading-none cursor-pointer flex-1">
                          <span className="text-[10px] font-black uppercase">
                            {type.label}
                          </span>
                          <p className="text-[9px] text-muted-foreground font-bold">
                            {type.desc}
                          </p>
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-emerald-600" />
                    <Label className="text-[10px] font-black uppercase tracking-widest text-foreground">Limite de Segurança</Label>
                  </div>
                  <div className="p-4 bg-muted/30 border border-dashed rounded-sm space-y-3">
                    <div className="space-y-1.5">
                      <Label htmlFor="impacto" className="text-[9px] font-bold text-muted-foreground uppercase block">Impacto Máximo Permitido (%)</Label>
                      <div className="flex items-center gap-3">
                        <Input 
                          id="impacto" 
                          type="number" 
                          value={data?.limite_impacto_percentual} 
                          onChange={handleImpactChange}
                          className="h-8 w-24 text-xs font-bold rounded-sm border-emerald-500/20 bg-background"
                          min="0"
                          max="100"
                          step="0.1"
                          disabled={mutation.isPending}
                        />
                        <span className="text-[10px] font-bold text-emerald-600 bg-emerald-500/10 px-2 py-1 rounded-sm">
                          VALOR ATUAL
                        </span>
                      </div>
                    </div>
                    <p className="text-[9px] font-medium text-muted-foreground leading-relaxed italic">
                      A IA não executará ações que alterem a projeção financeira em mais de {data?.limite_impacto_percentual}%.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-1 shadow-sm rounded-sm border-t-4 border-t-blue-500">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-black uppercase tracking-widest flex items-center gap-2 text-blue-700">
                <UserCheck className="h-4 w-4" />
                Perfil da IA
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoadingExplanation ? (
                <div className="space-y-4">
                  <Skeleton className="h-20 w-full rounded-sm" />
                  <div className="grid grid-cols-2 gap-2">
                    <Skeleton className="h-12 w-full rounded-sm" />
                    <Skeleton className="h-12 w-full rounded-sm" />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30 rounded-sm">
                    <p className="text-[9px] font-black uppercase text-blue-700 dark:text-blue-400 mb-1">Status de Adaptação</p>
                    <p className="text-[11px] font-black text-blue-900 dark:text-blue-300 uppercase mb-2">
                      {explanationData?.perfil}
                    </p>
                    <p className="text-[10px] font-medium text-blue-800/70 dark:text-blue-400/70 leading-relaxed italic border-t border-blue-200/50 pt-2">
                      "{explanationData?.explicacao}"
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2.5 border rounded-sm bg-background/50">
                      <p className="text-[8px] font-black text-muted-foreground uppercase mb-0.5">Tempo Decisão</p>
                      <p className="text-sm font-black text-emerald-600">{explanationData?.metricas_usuario.tempo_medio}</p>
                    </div>
                    <div className="p-2.5 border rounded-sm bg-background/50">
                      <p className="text-[8px] font-black text-muted-foreground uppercase mb-0.5">Taxa Execução</p>
                      <p className="text-sm font-black text-emerald-600">{explanationData?.metricas_usuario.taxa_execucao}</p>
                    </div>
                  </div>

                  <Alert variant="warning">
                    <AlertTriangle />
                    <AlertDescription className="text-[9px] font-medium leading-tight">
                      O Autopilot atua exclusivamente em simulações e projeções, nunca em lançamentos bancários reais.
                    </AlertDescription>
                  </Alert>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      <TabsContent value="personas" className="animate-in fade-in slide-in-from-bottom-4 duration-500 outline-none">
        <IAGrowthPersonasDashboard />
      </TabsContent>

      <TabsContent value="experimentos" className="animate-in fade-in slide-in-from-bottom-4 duration-500 outline-none">
        <IAGrowthExperimentosDashboard />
      </TabsContent>

      <TabsContent value="evolucao" className="animate-in fade-in slide-in-from-bottom-4 duration-500 outline-none">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-1 shadow-sm rounded-sm border-l-4 border-l-emerald-500">
             <CardHeader>
               <CardTitle className="text-sm font-black uppercase tracking-widest">Seu Progresso</CardTitle>
             </CardHeader>
             <CardContent className="space-y-6">
                {isLoadingProgresso ? (
                   <Skeleton className="h-[300px] w-full rounded-sm" />
                ) : (
                  <div className="space-y-6">
                    <div className="p-4 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30 rounded-sm">
                      <p className="text-[9px] font-black text-emerald-800 dark:text-emerald-400 uppercase mb-1">Insight do Período</p>
                      <p className="text-[11px] font-bold text-emerald-700 dark:text-emerald-500 italic leading-relaxed">
                        "{progressoData?.mensagem_destaque}"
                      </p>
                    </div>

                    <div className="p-4 border border-dashed rounded-sm flex items-center justify-between">
                      <div>
                        <h4 className="text-[9px] font-black uppercase tracking-widest text-muted-foreground mb-1">Evolução de Perfil</h4>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-bold line-through opacity-40 uppercase">{progressoData?.progresso.perfil.anterior}</span>
                          <ArrowRight size={12} className="text-muted-foreground" />
                          <span className="text-xs font-black text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-sm uppercase">{progressoData?.progresso.perfil.atual}</span>
                        </div>
                      </div>
                      {progressoData?.progresso.perfil.evoluiu && (
                        <Badge className="bg-emerald-600 text-white animate-bounce text-[8px] font-black uppercase rounded-full">Level Up!</Badge>
                      )}
                    </div>

                    <div className="space-y-4">
                      {[
                        { label: 'Velocidade', value: progressoData?.progresso.tempo_decisao.atual, improvement: progressoData?.progresso.tempo_decisao.melhoria, icon: Zap, color: 'text-amber-500' },
                        { label: 'Execução', value: progressoData?.progresso.taxa_execucao.atual, improvement: progressoData?.progresso.taxa_execucao.melhoria, icon: CheckCircle, color: 'text-blue-500' },
                        { label: 'Impacto (ROI)', value: progressoData?.progresso.roi.total, improvement: progressoData?.progresso.roi.melhoria, icon: TrendingUp, color: 'text-emerald-500' },
                      ].map((stat, i) => (
                        <div key={i} className="flex items-center justify-between p-3 border rounded-sm hover:bg-muted/30 transition-colors">
                           <div className="flex items-center gap-3">
                             <div className={cn("p-2 rounded-sm bg-muted", stat.color.replace('text', 'bg').replace('500', '500/10'))}>
                               <stat.icon size={14} className={stat.color} />
                             </div>
                             <div>
                               <p className="text-[9px] font-black uppercase text-muted-foreground">{stat.label}</p>
                               <p className="text-sm font-black">{stat.value}</p>
                             </div>
                           </div>
                           <Badge variant="outline" className={cn(
                             "text-[9px] font-black rounded-sm h-5",
                             stat.improvement > 0 ? "bg-emerald-500/10 text-emerald-600 border-emerald-200" : "bg-amber-500/10 text-amber-600 border-amber-200"
                           )}>
                             {stat.improvement > 0 ? `+${stat.improvement}%` : `${stat.improvement}%`}
                           </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
             </CardContent>
          </Card>

          <Card className="lg:col-span-2 border-l-4 border-l-blue-500 shadow-sm rounded-sm">
             <CardHeader>
               <CardTitle className="text-sm font-black uppercase tracking-widest">Transparência dos Algoritmos</CardTitle>
               <CardDescription className="text-[10px] font-bold uppercase">Como os limites de decisão são calculados.</CardDescription>
             </CardHeader>
             <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="text-[10px] font-black uppercase text-foreground">Thresholds de Referência</h4>
                    <div className="grid grid-cols-1 gap-2">
                      {explanationData?.thresholds_referencia && Object.entries(explanationData.thresholds_referencia).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between p-2.5 bg-muted/30 rounded-sm">
                          <span className="text-[9px] font-bold text-muted-foreground uppercase">{key.replace(/_/g, ' ')}</span>
                          <span className="text-[10px] font-black">{typeof value === 'number' && value > 100 ? (value/1000).toFixed(1) + 's' : value.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-4">
                     <h4 className="text-[10px] font-black uppercase text-foreground">Metodologia</h4>
                     <p className="text-[11px] font-medium text-muted-foreground leading-relaxed">
                        Nossos modelos utilizam estatística bayesiana para inferir seu nível de conforto com as sugestões da IA. 
                        À medida que você executa ações sugeridas mais rapidamente, o sistema aumenta gradualmente os limites de autonomia permitidos.
                     </p>
                     <div className="p-4 border border-dashed rounded-sm bg-blue-50/30">
                        <p className="text-[10px] font-black uppercase text-blue-700 mb-2">Próxima Re-Calibração</p>
                        <div className="w-full bg-muted h-1.5 rounded-full overflow-hidden">
                           <div className="bg-blue-500 h-full w-2/3" />
                        </div>
                        <p className="text-[8px] font-bold text-muted-foreground mt-2 uppercase tracking-tighter">Faltam aprox. 48 h de uso intenso para novo ajuste.</p>
                     </div>
                  </div>
                </div>
             </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  );
}
