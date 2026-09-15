"use client";

import React from "react";
import { 
  useIAGrowthExperimentos, 
  useIAGrowthExperimentoResultado, 
  useIAGrowthFinalizarExperimento,
  useIAGrowthCriarExperimento
} from "@/hooks";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { 
  FlaskConical, 
  Play, 
  StopCircle, 
  TrendingUp, 
  Users, 
  MousePointer2, 
  CheckCircle2,
  Trophy,
  AlertCircle,
  Plus
} from "lucide-react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogFooter
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/status-badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

const CONTEXTOS = [
  { value: "progresso", label: "Progresso (ROI)" },
  { value: "acao", label: "Ação de Impacto" },
  { value: "resumo", label: "Resumo Diário" },
] as const;

export function IAGrowthExperimentosDashboard() {
  const { data: experimentos, isLoading } = useIAGrowthExperimentos();
  const finalizeMutation = useIAGrowthFinalizarExperimento();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[200px] w-full" />
        <Skeleton className="h-[200px] w-full" />
      </div>
    );
  }

  const ativos = experimentos?.filter(e => e.status === "ATIVO") || [];
  const finalizados = experimentos?.filter(e => e.status === "FINALIZADO") || [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-xl font-black uppercase tracking-tight flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-emerald-600" />
            Comparação de ações comerciais
          </h2>
          <p className="text-xs text-muted-foreground font-medium uppercase">
            Gerencie e acompanhe o desempenho das variações de CTAs e mensagens.
          </p>
        </div>
        <CreateExperimentoDialog />
      </div>

      <div className="space-y-6">
        <h3 className="text-xs font-black uppercase tracking-widest text-emerald-600 flex items-center gap-2">
          <Play className="h-3 w-3 fill-emerald-600" />
          Experimentos Ativos
        </h3>
        
        {ativos.length === 0 ? (
          <div className="p-8 border border-dashed rounded-sm text-center">
            <p className="text-xs font-bold text-muted-foreground uppercase">Nenhum experimento ativo no momento.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {ativos.map(exp => (
              <ExperimentoCard key={exp.id} experimento={exp} />
            ))}
          </div>
        )}
      </div>

      {finalizados.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-3 w-3" />
            Histórico de Experimentos
          </h3>
          <div className="grid grid-cols-1 gap-4 opacity-70 hover:opacity-100 transition-opacity">
            {finalizados.map(exp => (
              <ExperimentoCard key={exp.id} experimento={exp} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ExperimentoCard({ experimento }: { experimento: any }) {
  const { data: resultado, isLoading } = useIAGrowthExperimentoResultado(experimento.id);
  const finalizeMutation = useIAGrowthFinalizarExperimento();
  const [confirmFinalize, setConfirmFinalize] = React.useState(false);

  const handleFinalize = () => {
    setConfirmFinalize(true);
  };

  return (
    <>
    <Card className={cn(
      "border-l-4 shadow-sm overflow-hidden",
      experimento.status === "ATIVO" ? "border-l-emerald-500" : "border-l-muted"
    )}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm font-black uppercase tracking-wider">{experimento.nome}</CardTitle>
              <Badge variant="outline" className="text-[9px] uppercase px-1.5 py-0 h-4">
                {experimento.contexto}
              </Badge>
              {experimento.status === "ATIVO" && (
                <StatusBadge status="ativo" />
              )}
            </div>
            <CardDescription className="text-[10px] font-bold uppercase">
              Iniciado em {new Date(experimento.created_at).toLocaleDateString()}
            </CardDescription>
          </div>
          {experimento.status === "ATIVO" && (
            <Button 
              variant="outline" 
              size="sm" 
              className="h-8 rounded-sm px-3 text-xs font-semibold border-red-200 text-red-600 hover:bg-red-50"
              onClick={handleFinalize}
              disabled={finalizeMutation.isPending}
            >
              <StopCircle data-icon="inline-start" />
              Finalizar
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : resultado ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 border rounded-sm bg-muted/20">
                <p className="text-[9px] font-black text-muted-foreground uppercase mb-1 flex items-center gap-1">
                  <Users size={10} /> Total Impressões
                </p>
                <p className="text-lg font-black">{resultado.total_exibicoes}</p>
              </div>
              <div className="p-3 border rounded-sm bg-muted/20">
                <p className="text-[9px] font-black text-muted-foreground uppercase mb-1 flex items-center gap-1">
                  <MousePointer2 size={10} /> Total Cliques
                </p>
                <p className="text-lg font-black">{resultado.total_cliques}</p>
              </div>
              <div className="p-3 border rounded-sm bg-muted/20">
                <p className="text-[9px] font-black text-muted-foreground uppercase mb-1 flex items-center gap-1">
                  <TrendingUp size={10} /> Taxa Média
                </p>
                <p className="text-lg font-black text-emerald-600">
                  {resultado.total_exibicoes > 0 
                    ? ((resultado.total_cliques / resultado.total_exibicoes) * 100).toFixed(1) 
                    : "0"}%
                </p>
              </div>
              <div className="p-3 border rounded-sm bg-emerald-500/5 border-emerald-500/20">
                <p className="text-[9px] font-black text-emerald-600 uppercase mb-1 flex items-center gap-1">
                  <Trophy size={10} /> Vencedora
                </p>
                <p className="text-lg font-black text-emerald-700">
                  {resultado.vencedora || "---"}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Desempenho por Variante</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {resultado.variantes.map((v: any) => (
                  <div key={v.variante_id} className={cn(
                    "p-3 border rounded-sm relative overflow-hidden",
                    v.nome === resultado.vencedora ? "border-emerald-500 bg-emerald-50/20 shadow-sm" : "bg-muted/5"
                  )}>
                    {v.nome === resultado.vencedora && (
                      <div className="absolute top-0 right-0 p-1">
                        <Trophy size={14} className="text-emerald-500" />
                      </div>
                    )}
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-black uppercase">Variante {v.nome}</span>
                      <Badge variant="secondary" className="text-[10px] font-black">{v.conversao}%</Badge>
                    </div>
                    <div className="flex items-center gap-4 text-[10px] font-bold text-muted-foreground uppercase">
                      <span>{v.exibicoes} views</span>
                      <span>{v.cliques} clicks</span>
                    </div>
                    {/* Progress bar */}
                    <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
                      <div 
                        className={cn("h-full transition-all duration-1000", v.nome === resultado.vencedora ? "bg-emerald-500" : "bg-muted-foreground/30")}
                        style={{ width: `${v.conversao}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {!resultado.significancia_atingida && experimento.status === "ATIVO" && (
              <div className="flex items-center gap-2 p-2 bg-amber-50 rounded-sm border border-amber-100">
                <AlertCircle size={12} className="text-amber-600" />
                <p className="text-[9px] font-medium text-amber-700 uppercase">
                  Aguardando mais dados para atingir significância estatística (min. 20 views/variante).
                </p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground font-bold uppercase italic">Sem dados de telemetria disponíveis.</p>
        )}
      </CardContent>
    </Card>

    <ConfirmDialog
      open={confirmFinalize}
      title="Finalizar experimento?"
      description={`O experimento "${experimento.nome}" será encerrado e não receberá mais dados.`}
      confirmText="Finalizar"
      onCancel={() => setConfirmFinalize(false)}
      onConfirm={() => {
        finalizeMutation.mutate(experimento.id, {
          onSuccess: () => toast.success("Experimento finalizado!"),
          onError: () => toast.error("Erro ao finalizar experimento."),
          onSettled: () => setConfirmFinalize(false),
        });
      }}
    />
    </>
  );
}

function CreateExperimentoDialog() {
  const [open, setOpen] = React.useState(false);
  const [nome, setNome] = React.useState("");
  const [contexto, setContexto] = React.useState("progresso");
  const createMutation = useIAGrowthCriarExperimento();

  const handleCreate = () => {
    if (!nome) return toast.error("Nome é obrigatório");
    
    // Variantes padrão para teste rápido
    const variantes = [
      { nome: "A", peso: 50, config_override: { cta_label: "Falar com Especialista" } },
      { nome: "B", peso: 50, config_override: { cta_label: "Começar Agora" } }
    ];

    createMutation.mutate({ nome, contexto, variantes }, {
      onSuccess: () => {
        toast.success("Experimento criado com sucesso!");
        setOpen(false);
        setNome("");
      },
      onError: () => toast.error("Erro ao criar experimento.")
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button 
          variant="outline"
          size="sm" 
          className="h-8 rounded-sm px-3 text-xs font-semibold"
        >
          <Plus data-icon="inline-start" />
          Novo experimento
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-sm font-black uppercase tracking-wider">Criar Novo Experimento A/B</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="nome" className="text-[10px] font-black uppercase text-muted-foreground">Nome do Experimento</Label>
            <Input 
              id="nome" 
              value={nome} 
              onChange={(e) => setNome(e.target.value)} 
              placeholder="Ex: Teste de CTA de Upgrade" 
              className="h-8 text-xs font-bold rounded-sm"
            />
          </div>
          <div className="grid gap-2">
            <Label className="text-[10px] font-black uppercase text-muted-foreground">Contexto</Label>
            <Select value={contexto} onValueChange={setContexto}>
              <SelectTrigger className="h-8 text-xs font-bold rounded-sm">
                <span className="truncate">
                  {CONTEXTOS.find((item) => item.value === contexto)?.label ?? "Selecione o contexto"}
                </span>
              </SelectTrigger>
              <SelectContent>
                {CONTEXTOS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button 
            variant="outline"
            className="h-8 w-full rounded-sm px-3 text-xs font-semibold"
            onClick={handleCreate}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? "Criando..." : "Criar experimento"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
