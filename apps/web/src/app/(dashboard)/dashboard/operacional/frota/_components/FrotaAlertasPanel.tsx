import { CheckCircle2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
          <Alert variant="success">
            <CheckCircle2 />
            <AlertDescription>
              Nenhum alerta operacional crítico encontrado na frota.
            </AlertDescription>
          </Alert>
        ) : (
          alertas.map((alerta) => (
            <div
              key={`${alerta.tipo}-${alerta.equipamento_id}-${alerta.detalhe}`}
              className={cn(
                "rounded-sm border p-4",
                alerta.severidade === "danger"
                  ? "border-alert-destructive-border bg-alert-destructive-bg text-alert-destructive-title"
                  : "border-alert-warning-border bg-alert-warning-bg text-alert-warning-title"
              )}
            >
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={alerta.severidade === "danger" ? "danger" : "warning"}>
                      {alerta.titulo}
                    </Badge>
                    <span className="text-sm font-medium">{alerta.equipamento_nome}</span>
                  </div>
                  <p
                    className={cn(
                      "text-sm",
                      alerta.severidade === "danger"
                        ? "text-alert-destructive-description"
                        : "text-alert-warning-description"
                    )}
                  >
                    {alerta.detalhe}
                  </p>
                </div>
                <div
                  className={cn(
                    "text-xs",
                    alerta.severidade === "danger"
                      ? "text-alert-destructive-description"
                      : "text-alert-warning-description"
                  )}
                >
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
