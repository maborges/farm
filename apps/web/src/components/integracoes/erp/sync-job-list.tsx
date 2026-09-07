import { Badge } from "@/components/ui/badge";
import type { ErpSyncJobViewModel } from "./sync-center-view-model";

interface ErpSyncJobListProps {
  jobs: ErpSyncJobViewModel[];
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Não disponível";
  }
  return new Date(value).toLocaleString("pt-BR");
}

function getStatusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    RUNNING: "secondary",
    SUCCESS: "default",
    FAILED: "destructive",
    PARTIAL: "secondary",
    PENDING: "secondary",
    CANCELLED: "destructive",
  };
  return variants[status] || "secondary";
}

function formatDuration(ms?: number | null) {
  if (ms == null) return "n/d";
  if (ms < 1000) return `${ms}ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const remainingS = s % 60;
  return `${m}m ${remainingS}s`;
}

export function ErpSyncJobList({ jobs }: ErpSyncJobListProps) {
  if (jobs.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhuma execução registrada.</p>;
  }

  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <div key={job.id} className="rounded-sm border bg-muted/20 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-medium">{job.capabilityName}</p>
              <p className="text-xs text-muted-foreground">
                Início: {formatDateTime(job.startedAt)} · Origem: {job.triggerLabel}
              </p>
            </div>
            <Badge variant={getStatusBadge(job.status)}>{job.status}</Badge>
          </div>
          <div className="mt-2 flex flex-col md:flex-row gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>Duração: {formatDuration(job.durationMs)}</span>
            <span>
              Processados: {job.processed ?? "n/d"} (Sucesso: {job.successes ?? "n/d"} · Erros: {job.failures ?? "n/d"})
            </span>
          </div>
          {job.message && <p className="mt-1 text-xs text-destructive">{job.message}</p>}
        </div>
      ))}
    </div>
  );
}
