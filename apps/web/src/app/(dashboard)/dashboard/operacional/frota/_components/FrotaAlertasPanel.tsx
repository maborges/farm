import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { FrotaAlerta } from "./types";
import { formatDateOrDash } from "./utils";

interface FrotaAlertasPanelProps {
  alertas: FrotaAlerta[];
}

export function FrotaAlertasPanel({ alertas }: FrotaAlertasPanelProps) {
  return (
    <Card className="rounded-sm shadow-sm">
      <CardHeader>
        <CardTitle>Alertas operacionais</CardTitle>
        <CardDescription>Riscos simples calculados com base em abastecimento, OS, manutenção, documentos e custo.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {alertas.length === 0 ? (
          <div className="rounded-sm border border-emerald-200 bg-emerald-50/40 p-4 text-sm text-emerald-700">
            Nenhum alerta operacional crítico encontrado na frota.
          </div>
        ) : (
          alertas.map((alerta) => (
            <div
              key={`${alerta.tipo}-${alerta.equipamento_id}-${alerta.detalhe}`}
              className={cn(
                "rounded-sm border p-4",
                alerta.severidade === "danger"
                  ? "border-red-200 bg-red-50/40"
                  : "border-amber-200 bg-amber-50/40"
              )}
            >
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={alerta.severidade === "danger" ? "border-red-200 text-red-700" : "border-amber-200 text-amber-700"}>
                      {alerta.titulo}
                    </Badge>
                    <span className="text-sm font-medium">{alerta.equipamento_nome}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{alerta.detalhe}</p>
                </div>
                <div className="text-xs text-muted-foreground">
                  {alerta.data_referencia ? formatDateOrDash(alerta.data_referencia) : "Sem data de referência"}
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
export default FrotaAlertasPanel;
