import { Clock3, CheckCircle, AlertTriangle, PlayCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ErpSyncCenterViewModel } from "./sync-center-view-model";

interface ErpSyncSummaryProps {
  summary: ErpSyncCenterViewModel["summary"];
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Não disponível";
  }
  return new Date(value).toLocaleString("pt-BR");
}

export function ErpSyncSummary({ summary }: ErpSyncSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock3 className="h-4 w-4" />
          Resumo operacional
        </CardTitle>
        <CardDescription>Visão geral do funcionamento do Sync Center.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-sm border bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Políticas ativas</p>
          <div className="mt-2 flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-primary" />
            <span className="text-xl font-bold">{summary.activePolicies}</span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Sincronizações automáticas habilitadas</p>
        </div>
        <div className="rounded-sm border bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Em andamento</p>
          <div className="mt-2 flex items-center gap-2">
            <PlayCircle className={`h-4 w-4 ${summary.runningJobs > 0 ? "text-primary animate-pulse" : "text-muted-foreground"}`} />
            <span className="text-xl font-bold">{summary.runningJobs}</span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Jobs executando neste momento</p>
        </div>
        <div className="rounded-sm border bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Falhas recentes</p>
          <div className="mt-2 flex items-center gap-2">
            <AlertTriangle className={`h-4 w-4 ${summary.recentFailures > 0 ? "text-destructive" : "text-muted-foreground"}`} />
            <span className="text-xl font-bold">{summary.recentFailures}</span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Falhas nas execuções exibidas</p>
        </div>
        <div className="rounded-sm border bg-muted/20 p-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Horários</p>
          <p className="mt-2 text-xs text-muted-foreground font-medium">
            Último sucesso: <span className="text-foreground">{formatDateTime(summary.lastSuccessAt)}</span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground font-medium">
            Próxima atualização prevista: <span className="text-foreground">{formatDateTime(summary.nextRunAt)}</span>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
