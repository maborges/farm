import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bug, ShieldAlert } from "lucide-react";

interface ParasiteAlert {
  id: string;
  type: string;
  riskLevel: string;
  eclosionDate: string;
  recommendation: string;
}

interface ParasiteAlertCardProps {
  alerts: ParasiteAlert[];
}

export function ParasiteAlertCard({ alerts }: ParasiteAlertCardProps) {
  return (
    <Card className="h-full border-l-4 border-l-orange-500 shadow-sm transition-all hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Bug className="size-5 text-orange-500" />
          <CardTitle className="text-lg">Alerta de Parasitas</CardTitle>
        </div>
        <CardDescription>
          Previsão de eclosão baseada em GDU e Umidade
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {alerts.map((alert) => (
            <div key={alert.id} className="flex flex-col gap-2 rounded-md border p-3">
              <div className="flex items-start justify-between">
                <div className="flex flex-col">
                  <span className="text-sm font-bold">{alert.type}</span>
                  <span className="text-xs text-muted-foreground mt-1">Eclosão Prevista: {alert.eclosionDate}</span>
                </div>
                <Badge variant={alert.riskLevel.toLowerCase() === 'crítico' ? 'destructive' : 'secondary'} className="text-[10px]">
                  {alert.riskLevel}
                </Badge>
              </div>
              <div className="mt-2 flex items-start gap-2 rounded bg-orange-500/10 p-2 text-xs text-orange-800 dark:text-orange-200">
                <ShieldAlert className="mt-0.5 size-3 shrink-0" />
                <p>{alert.recommendation}</p>
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <p className="text-sm text-muted-foreground">Nenhum alerta de parasita ativo.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
