import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CalendarDays, Info } from "lucide-react";

interface IatfWindow {
  id: string;
  startDate: string;
  endDate: string;
  score: number;
  recommendation: string;
  lotes: string[];
}

interface IatfWindowCardProps {
  windows: IatfWindow[];
}

export function IatfWindowCard({ windows }: IatfWindowCardProps) {
  return (
    <Card className="h-full border-l-4 border-l-emerald-500 shadow-sm transition-all hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <CalendarDays className="size-5 text-emerald-600" />
          <CardTitle className="text-lg">Janela de IATF</CardTitle>
        </div>
        <CardDescription>
          Previsão de estresse térmico x melhores janelas reprodutivas
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {windows.map((win) => (
            <div key={win.id} className="flex flex-col gap-2 rounded-md border p-3">
              <div className="flex items-center justify-between">
                <div className="flex flex-col">
                  <span className="text-sm font-semibold">
                    {win.startDate} até {win.endDate}
                  </span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {win.lotes.map((lote) => (
                      <Badge key={lote} variant="secondary" className="text-[10px]">
                        {lote}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-xs text-muted-foreground">Score Climático</span>
                  <span className={`text-lg font-bold ${win.score >= 90 ? 'text-emerald-500' : 'text-amber-500'}`}>
                    {win.score}%
                  </span>
                </div>
              </div>
              <div className="flex items-start gap-2 rounded bg-muted/50 p-2 text-xs text-muted-foreground">
                <Info className="mt-0.5 size-3 shrink-0" />
                <p>{win.recommendation}</p>
              </div>
            </div>
          ))}
          {windows.length === 0 && (
            <p className="text-sm text-muted-foreground">Nenhuma janela ideal nos próximos dias.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
