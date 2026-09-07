import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Droplet, AlertTriangle } from "lucide-react";

interface Pasture {
  name: string;
  lotacao: string;
  status: string;
  daysToCritical: number;
}

interface PastureRisk {
  overallRisk: string;
  deficitMm: number;
  criticalPastures: Pasture[];
}

interface PastureRotationCardProps {
  riskData: PastureRisk;
}

export function PastureRotationCard({ riskData }: PastureRotationCardProps) {
  const isHighRisk = riskData.overallRisk.toLowerCase() === "alto" || riskData.overallRisk.toLowerCase() === "crítico";

  return (
    <Card className={`h-full border-l-4 shadow-sm transition-all hover:shadow-md ${isHighRisk ? 'border-l-red-500' : 'border-l-amber-500'}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Droplet className={`size-5 ${isHighRisk ? 'text-red-500' : 'text-amber-500'}`} />
          <CardTitle className="text-lg">Rotação de Pasto</CardTitle>
        </div>
        <CardDescription>
          Capacidade de suporte vs Déficit Hídrico
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex items-center justify-between rounded-md bg-muted/50 p-3">
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground">Déficit Atual</span>
            <span className="font-semibold">{riskData.deficitMm} mm</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-xs text-muted-foreground">Risco Geral</span>
            <Badge variant={isHighRisk ? "destructive" : "secondary"}>
              {riskData.overallRisk}
            </Badge>
          </div>
        </div>

        <div className="space-y-3">
          <h4 className="text-sm font-medium">Pastos Críticos</h4>
          {riskData.criticalPastures.map((pasto, idx) => (
            <div key={idx} className="flex items-center justify-between rounded-md border p-2 text-sm">
              <div className="flex flex-col">
                <span className="font-medium">{pasto.name}</span>
                <span className="text-xs text-muted-foreground">Lotação: {pasto.lotacao}</span>
              </div>
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-amber-500" />
                <span className="text-xs font-semibold">{pasto.daysToCritical} dias rest.</span>
              </div>
            </div>
          ))}
          {riskData.criticalPastures.length === 0 && (
            <p className="text-sm text-muted-foreground">Nenhum pasto em estado crítico.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
