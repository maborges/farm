"use client";

import React from "react";
import { useIAGrowthPersonasPerformance } from "@/hooks/ia/use-ia-growth-personas-performance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Users, 
  TrendingUp, 
  BrainCircuit, 
  Zap, 
  MousePointer2, 
  Sparkles,
  Search,
  Trophy,
  Clock,
  EyeOff
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DataTable, ColumnDef } from "@/components/ui/data-table";

export function IAGrowthPersonasDashboard() {
  const { data, isLoading } = useIAGrowthPersonasPerformance();

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

  if (!data) return null;

  const totalSkipped = data.timing_performance.reduce((acc, curr) => acc + curr.skipped, 0);

  const columns: ColumnDef<any>[] = [
    {
      id: "persona",
      header: "Persona",
      accessorKey: "persona",
      cell: (val) => (
        <div className="flex flex-col">
          <span className="font-black uppercase text-indigo-700 text-[11px]">{val}</span>
        </div>
      )
    },
    {
      id: "usuarios",
      header: "Usuários",
      accessorKey: "usuarios",
      sortable: true,
      cell: (val) => <span className="font-bold text-[11px]">{val}</span>
    },
    {
      id: "exibicoes",
      header: "Exibições",
      accessorKey: "exibicoes",
      sortable: true,
      cell: (val) => <span className="text-[11px]">{val}</span>
    },
    {
      id: "cliques",
      header: "Cliques",
      accessorKey: "cliques",
      sortable: true,
      cell: (val) => <span className="text-[11px]">{val}</span>
    },
    {
      id: "conversao",
      header: "Conversão",
      accessorKey: "conversao",
      sortable: true,
      cell: (val) => (
        <Badge variant="outline" className={cn(
          "text-[10px] font-black rounded-sm px-1.5 h-5",
          val > 5 ? "bg-emerald-500/10 text-emerald-600 border-emerald-200" : "bg-slate-100 text-slate-600 border-slate-200"
        )}>
          {val}%
        </Badge>
      )
    },
    {
      id: "melhor_abordagem",
      header: "Abordagem Ideal",
      accessorKey: "melhor_abordagem",
      cell: (val) => <span className="text-[10px] font-black uppercase text-amber-600">{val || "---"}</span>
    },
    {
      id: "melhor_contexto",
      header: "Contexto Top",
      accessorKey: "melhor_contexto",
      cell: (val) => <span className="text-[10px] font-black uppercase text-blue-600">{val || "---"}</span>
    },
    {
      id: "melhor_origem",
      header: "Origem Top",
      accessorKey: "melhor_origem",
      cell: (val) => (
        <div className="flex items-center gap-1">
          {val === "LLM" ? <Sparkles size={10} className="text-blue-500" /> : <Search size={10} className="text-slate-400" />}
          <span className="text-[10px] font-black uppercase">{val || "---"}</span>
        </div>
      )
    }
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-black uppercase tracking-tight flex items-center gap-2">
          <BrainCircuit className="h-5 w-5 text-indigo-600" />
          Observabilidade de Personas
        </h2>
        <p className="text-xs text-muted-foreground font-medium uppercase">
          Análise comportamental e performance de conversão por perfil de produtor.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-indigo-500 shadow-sm rounded-sm">
          <CardContent className="p-4">
            <p className="text-[9px] font-black text-muted-foreground uppercase mb-1">Usuários Classificados</p>
            <div className="flex items-center justify-between">
              <p className="text-2xl font-black text-indigo-600">{data.total_usuarios_classificados}</p>
              <Users className="h-4 w-4 text-indigo-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-emerald-500 shadow-sm rounded-sm">
          <CardContent className="p-4">
            <p className="text-[9px] font-black text-muted-foreground uppercase mb-1">Melhor Persona (Conv.)</p>
            <div className="flex items-center justify-between">
              <p className="text-lg font-black text-emerald-600 uppercase truncate">{data.melhor_persona_conversao || "---"}</p>
              <Trophy className="h-4 w-4 text-emerald-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500 shadow-sm rounded-sm">
          <CardContent className="p-4">
            <p className="text-[9px] font-black text-muted-foreground uppercase mb-1">Timing: Economia de Fricção</p>
            <div className="flex items-center justify-between">
              <p className="text-lg font-black text-amber-600 uppercase truncate">{totalSkipped} Bloqueios</p>
              <EyeOff className="h-4 w-4 text-amber-500 opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-blue-500 shadow-sm rounded-sm">
          <CardContent className="p-4">
            <p className="text-[9px] font-black text-muted-foreground uppercase mb-1">Origem Eficiente</p>
            <div className="flex items-center justify-between">
              <p className="text-lg font-black text-blue-600 uppercase truncate">{data.melhor_origem_geral || "---"}</p>
              <Sparkles className="h-4 w-4 text-blue-500 opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <Card className="shadow-sm rounded-sm border-t-2 border-t-indigo-500">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                <Users className="h-3 w-3" />
                Distribuição de Perfis
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 px-4 pb-4">
              {Object.entries(data.distribuicao_persona).map(([persona, count]) => {
                const percentage = (count / data.total_usuarios_classificados) * 100;
                return (
                  <div key={persona} className="space-y-1.5">
                    <div className="flex items-center justify-between text-[9px] font-black uppercase">
                      <span>{persona}</span>
                      <span className="text-indigo-600">{count} ({percentage.toFixed(1)}%)</span>
                    </div>
                    <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-indigo-500 transition-all duration-1000"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="shadow-sm rounded-sm border-t-2 border-t-slate-400">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                <Clock className="h-3 w-3" />
                Timing de Conversão
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 px-4 pb-4">
              {data.timing_performance.map((tp) => (
                <div key={tp.timing_decision} className="p-2.5 bg-muted/20 rounded-sm space-y-2 border border-border/30">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className={cn(
                      "text-[8px] font-black uppercase rounded-sm px-1.5 h-4",
                      tp.timing_decision === "FULL" ? "bg-indigo-500 text-white border-indigo-600" :
                      tp.timing_decision === "SOFT" ? "bg-blue-500/10 text-blue-600 border-blue-200" :
                      "bg-slate-500/10 text-slate-600 border-slate-200"
                    )}>
                      {tp.timing_decision}
                    </Badge>
                    <span className="text-[12px] font-black text-indigo-600">{tp.conversao}%</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 text-[8px] font-black uppercase text-muted-foreground text-center">
                    <div className="bg-background py-1 rounded-sm">
                      <p className="text-[10px] text-foreground">{tp.exibicoes}</p>
                      <p>Exib.</p>
                    </div>
                    <div className="bg-background py-1 rounded-sm">
                      <p className="text-[10px] text-foreground">{tp.cliques}</p>
                      <p>Cliques</p>
                    </div>
                    <div className="bg-background py-1 rounded-sm">
                      <p className="text-[10px] text-amber-600">{tp.skipped}</p>
                      <p>Skipped</p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-3 w-3" />
              Performance Detalhada por Persona
            </h3>
          </div>
          
          <DataTable 
            data={data.performance_por_persona} 
            columns={columns}
            searchable={true}
            searchPlaceholder="Filtrar personas..."
            exportable={true}
            exportFileName="performance_personas_growth"
            className="border-none p-0 shadow-none"
          />
        </div>
      </div>
    </div>
  );
}
