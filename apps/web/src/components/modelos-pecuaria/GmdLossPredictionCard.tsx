import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingDown, ThermometerSun } from "lucide-react";

interface GmdImpact {
  forecastedThi: number;
  heatwaveDays: number;
  impact: {
    dryMatterIntakeDropPercent: number;
    lostWeightGramsPerDay: number;
    totalFinancialLossEst: number;
    affectedLotes: string[];
  }
}

interface GmdLossPredictionCardProps {
  data: GmdImpact;
}

export function GmdLossPredictionCard({ data }: GmdLossPredictionCardProps) {
  const isHighStress = data.forecastedThi > 78;

  return (
    <Card className="h-full border-l-4 border-l-red-500 shadow-sm transition-all hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <TrendingDown className="size-5 text-red-500" />
          <CardTitle className="text-lg">Predição de GMD</CardTitle>
        </div>
        <CardDescription>
          Impacto do ITH no Ganho Médio Diário e Consumo
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex gap-4">
          <div className="flex-1 rounded-md border p-3 flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <ThermometerSun className="size-3" />
                ITH Máx Previsto
              </span>
              <span className={`text-xl font-bold ${isHighStress ? 'text-red-500' : 'text-amber-500'}`}>
                {data.forecastedThi}
              </span>
            </div>
            <Badge variant="outline" className={isHighStress ? 'border-red-500 text-red-500' : ''}>
              {data.heatwaveDays} dias
            </Badge>
          </div>
        </div>

        <div className="space-y-3 rounded-md bg-muted/50 p-3 text-sm">
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">Quebra Consumo (MS)</span>
            <span className="font-semibold text-amber-500">-{data.impact.dryMatterIntakeDropPercent}%</span>
          </div>
          <div className="flex justify-between border-b pb-2">
            <span className="text-muted-foreground">Perda de Peso (dia)</span>
            <span className="font-semibold text-red-500">-{data.impact.lostWeightGramsPerDay}g / cab</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground font-medium">Prejuízo Estimado</span>
            <span className="font-bold text-red-500">
              R$ {data.impact.totalFinancialLossEst.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground">Lotes Afetados</span>
          <div className="flex flex-wrap gap-1">
            {data.impact.affectedLotes.map(lote => (
              <Badge key={lote} variant="secondary" className="text-[10px]">
                {lote}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
