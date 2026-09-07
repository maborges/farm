import { RefreshCw, PlayCircle, Clock3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErpSyncSummary } from "./sync-summary";
import { ErpSyncJobList } from "./sync-job-list";
import type { ErpSyncCenterViewModel } from "./sync-center-view-model";

interface ErpSyncCenterProps {
  viewModel: ErpSyncCenterViewModel | null;
  syncing: Record<string, boolean>;
}

export function ErpSyncCenter({ viewModel, syncing }: ErpSyncCenterProps) {
  if (!viewModel) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Atualizações e execuções</h2>
          <p className="text-muted-foreground">
            Acompanhe as sincronizações do ERP, atualizações automáticas, execuções e ações manuais.
          </p>
        </div>
      </div>

      <ErpSyncSummary summary={viewModel.summary} />

      {viewModel.manualActions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4" />
              Ações manuais
            </CardTitle>
            <CardDescription>Operações que podem ser disparadas manualmente nesta integração.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {viewModel.manualActions.map((action) => {
              const isSyncing = action.capabilityCode ? syncing[action.capabilityCode] : syncing["full"];
              return (
                <div key={action.id} className="flex flex-col gap-1">
                  <Button
                    variant="secondary"
                    disabled={!action.enabled || isSyncing}
                    onClick={() => void action.execute()}
                  >
                    <RefreshCw className={`mr-2 h-4 w-4 ${isSyncing ? "animate-spin" : ""}`} />
                    {action.label}
                  </Button>
                  {action.description && (
                    <span className="text-xs text-muted-foreground">{action.description}</span>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      <div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock3 className="h-4 w-4" />
              Execuções recentes
            </CardTitle>
            <CardDescription>Acompanhamento de processos agendados e eventos de sincronização.</CardDescription>
          </CardHeader>
          <CardContent>
            <ErpSyncJobList jobs={viewModel.jobs} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
