import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ThermometerSun } from "lucide-react";

interface GduCardProps {
  gduAcumulado: number;
}

export function GduCard({ gduAcumulado }: GduCardProps) {
  return (
    <Card className="rounded-sm flex flex-col justify-between">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <ThermometerSun className="h-4 w-4 text-orange-500" />
          Graus-Dias Úteis (GDU)
        </CardTitle>
        <CardDescription className="text-xs">
          Acúmulo térmico da cultura atual
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-4xl font-bold tracking-tighter">
            {gduAcumulado.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}
          </span>
          <span className="text-sm text-muted-foreground font-medium">°C</span>
        </div>
        <div className="mt-4 pt-4 border-t flex justify-between items-center">
          <span className="text-xs text-muted-foreground">Base: 10°C</span>
          <Badge variant="outline" className="bg-orange-500/10 text-orange-600 hover:bg-orange-500/20 border-0 rounded-sm">
            Favorável
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
