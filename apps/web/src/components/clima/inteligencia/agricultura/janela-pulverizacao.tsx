import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JanelaPulverizacao } from "@/lib/agricola/clima-api";
import { Droplets, Wind, ThermometerSun, AlertCircle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  data?: JanelaPulverizacao[];
}

export function JanelaPulverizacaoCard({ data }: Props) {
  const windows = data ?? [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "verde": return "bg-emerald-500 text-emerald-950 border-emerald-600";
      case "amarelo": return "bg-amber-400 text-amber-950 border-amber-500";
      case "vermelho": return "bg-red-500 text-red-50 border-red-600";
      default: return "bg-slate-200 text-slate-800 border-slate-300";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "verde": return <CheckCircle2 size={14} className="text-emerald-900" />;
      case "amarelo": return <AlertCircle size={14} className="text-amber-900" />;
      case "vermelho": return <AlertCircle size={14} className="text-red-100" />;
      default: return null;
    }
  };

  return (
    <Card className="rounded-sm flex flex-col h-full border-border/60">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Droplets className="h-5 w-5 text-sky-500" />
            Janela Ideal de Pulverização
          </CardTitle>
          <span className="text-xs bg-muted px-2 py-1 rounded-sm text-muted-foreground font-medium border border-border">
            Predição 24h
          </span>
        </div>
        <CardDescription>
          Viabilidade de aplicação de defensivos baseada em temperatura, vento e umidade (risco de deriva/evaporação).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 overflow-x-auto pb-6">
        <div className="min-w-[600px]">
          {/* Cabeçalho da tabela de janela */}
          {windows.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">Não há previsão horária disponível para calcular uma janela segura.</p> : null}
          <div className="grid grid-cols-7 gap-2 mb-2 text-xs font-semibold text-muted-foreground uppercase text-center">
            {windows.map((w, i) => (
              <div key={i}>{w.hora}</div>
            ))}
          </div>
          
          {/* Status coloridos */}
          <div className="grid grid-cols-7 gap-2 mb-4">
            {windows.map((w, i) => (
              <div 
                key={i} 
                className={cn("flex flex-col items-center justify-center p-3 rounded-sm border shadow-sm", getStatusColor(w.status))}
              >
                {getStatusIcon(w.status)}
                <span className="font-bold text-sm mt-1 uppercase tracking-wider">{w.status}</span>
                {w.motivo && (
                  <span className="text-[9px] mt-1 text-center font-medium leading-tight opacity-90 line-clamp-2">
                    {w.motivo}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Dados detalhados */}
          <div className="grid grid-cols-7 gap-2 text-xs text-center border-t border-border pt-3">
            {windows.map((w, i) => (
              <div key={i} className="flex flex-col gap-2 opacity-80">
                <div className="flex items-center justify-center gap-1" title="Vento (Risco de Deriva)">
                  <Wind size={12} /> {w.vento_kmh} <span className="text-[10px]">km/h</span>
                </div>
                <div className="flex items-center justify-center gap-1" title="Temperatura">
                  <ThermometerSun size={12} /> {w.temp_c}°C
                </div>
                <div className="flex items-center justify-center gap-1 text-sky-600" title="Umidade Relativa">
                  <Droplets size={12} /> {w.umidade_pct}%
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
