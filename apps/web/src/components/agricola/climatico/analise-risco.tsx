import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Droplets, Snowflake, ShieldCheck } from "lucide-react";
import type { RiscoClimatico } from "@/lib/agricola/clima-api";

interface AnaliseRiscoProps {
  riscos: RiscoClimatico[];
}

export function AnaliseRisco({ riscos }: AnaliseRiscoProps) {
  const getIcon = (tipo: string) => {
    if (tipo.toLowerCase().includes("geada")) return <Snowflake className="h-5 w-5" />;
    if (tipo.toLowerCase().includes("hídrico") || tipo.toLowerCase().includes("seca")) return <Droplets className="h-5 w-5" />;
    if (tipo.toLowerCase().includes("normal")) return <ShieldCheck className="h-5 w-5" />;
    return <AlertTriangle className="h-5 w-5" />;
  };

  const getColor = (nivel: string) => {
    switch (nivel.toUpperCase()) {
      case "CRITICO": return "bg-red-500/10 text-red-600 border-red-500/20";
      case "ALTO": return "bg-orange-500/10 text-orange-600 border-orange-500/20";
      case "MEDIO": return "bg-yellow-500/10 text-yellow-600 border-yellow-500/20";
      case "BAIXO": return "bg-green-500/10 text-green-600 border-green-500/20";
      default: return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    }
  };

  return (
    <Card className="rounded-sm flex flex-col justify-between">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          Análise de Risco Climático
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-2">
        {riscos.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum risco detectado.</p>
        ) : (
          riscos.map((risco, idx) => (
            <div key={idx} className={`rounded-sm border p-3 flex items-start gap-3 ${getColor(risco.nivel)}`}>
              <div className="mt-0.5">{getIcon(risco.tipo)}</div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">{risco.tipo}</span>
                  <Badge variant="outline" className={`rounded-sm border-0 bg-transparent ${getColor(risco.nivel)}`}>
                    {risco.nivel}
                  </Badge>
                </div>
                <p className="text-xs opacity-90 leading-relaxed">{risco.mensagem}</p>
                {risco.data_alerta && (
                  <p className="text-[10px] font-medium opacity-70">
                    Registrado em: {new Date(risco.data_alerta).toLocaleDateString("pt-BR")}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
