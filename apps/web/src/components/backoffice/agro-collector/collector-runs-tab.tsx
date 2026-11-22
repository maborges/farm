"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Activity,
  AlertTriangle,
  Download,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";

import type { CollectorRunItem, CollectorSourceItem } from "./types";

interface CollectorRunsTabProps {
  runs: CollectorRunItem[];
  isLoading: boolean;
  canUpdate: boolean;
}

export function CollectorRunsTab({ runs, isLoading, canUpdate }: CollectorRunsTabProps) {
  const queryClient = useQueryClient();
  const [sentinelRun, setSentinelRun] = useState<CollectorRunItem | null>(null);
  const [justificativa, setJustificativa] = useState("Aplicação auditada de nova URL sugerida pelo Sentinela.");

  const pendingSentinelRuns = useMemo(
    () => runs.filter((r) => r.sugestao_sentinela?.url_sugerida && !r.sugestao_sentinela.aplicada_em),
    [runs]
  );

  const applySentinelMutation = useMutation({
    mutationFn: ({ runId, just }: { runId: string; just: string }) =>
      apiFetch<CollectorSourceItem>(
        `/api/v1/backoffice/agro/mercado/collector/runs/${runId}/apply-sentinel`,
        {
          method: "POST",
          body: { justificativa: just },
        }
      ),
    onSuccess: (src) => {
      toast.success(`URL da fonte '${src.sigla}' atualizada via Sentinela.`);
      setSentinelRun(null);
      queryClient.invalidateQueries({ queryKey: ["backoffice-collector-sources"] });
      queryClient.invalidateQueries({ queryKey: ["backoffice-collector-runs"] });
    },
    onError: (err: Error) => {
      toast.error(`Erro ao aplicar sugestão do Sentinela: ${err.message}`);
    },
  });

  const handleDownloadArtifact = async (run: CollectorRunItem) => {
    try {
      const blob = await apiFetch<Blob>(
        `/api/v1/backoffice/agro/mercado/collector/runs/${run.id}/artifact`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${run.source_slug}_${run.id.slice(0, 8)}.bin`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(`Falha ao baixar artefato: ${err instanceof Error ? err.message : "Erro"}`);
    }
  };

  const columns: ColumnDef<CollectorRunItem>[] = [
    {
      id: "source",
      header: "Fonte & Disparo",
      accessorFn: (r) => `${r.source_sigla} ${r.trigger_tipo} ${r.executado_por ?? ""}`,
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-0.5 text-xs">
          <div className="font-medium">{row.source_sigla}</div>
          <div className="text-[10px] text-muted-foreground">
            {row.trigger_tipo} · {row.executado_por ?? "worker"}
          </div>
          <div className="text-[10px] text-muted-foreground">
            {format(new Date(row.iniciado_em), "dd/MM/yyyy HH:mm", { locale: ptBR })}
          </div>
        </div>
      ),
    },
    {
      id: "status",
      header: "Status & Contadores",
      accessorKey: "status",
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-1">
          <Badge
            variant="outline"
            className={`rounded-sm text-[10px] ${
              row.status === "SUCESSO"
                ? "border-emerald-600/30 text-emerald-700 bg-emerald-50 dark:text-emerald-400"
                : row.status === "FALHA"
                ? "border-red-600/30 text-red-700 bg-red-50 dark:text-red-400"
                : "border-amber-600/30 text-amber-700 bg-amber-50 dark:text-amber-400"
            }`}
          >
            {row.status}
          </Badge>
          <div className="text-[10px] font-mono text-muted-foreground">
            Ext:{row.total_extraidos} · Pub:{row.total_publicados} · Quar:{row.total_quarentena} · Rej:{row.total_rejeitados}
          </div>
        </div>
      ),
    },
    {
      id: "integridade",
      header: "SHA-256 & IA",
      accessorFn: (r) => `${r.sha256_bruto ?? ""} ${r.modelo_ia ?? ""}`,
      cell: (_val, row) => (
        <div className="space-y-0.5 text-[11px]">
          <div className="font-mono text-muted-foreground">
            {row.sha256_bruto ? `${row.sha256_bruto.slice(0, 14)}...` : "—"}
          </div>
          {row.modelo_ia ? (
            <div className="text-[10px] text-sky-700 dark:text-sky-400 font-mono">
              {row.modelo_ia} · {row.tokens_entrada + row.tokens_saida} tok · US$ {row.custo_estimado_usd}
            </div>
          ) : (
            <div className="text-[10px] text-muted-foreground">Determinístico Nível 1</div>
          )}
        </div>
      ),
    },
    {
      id: "actions",
      header: "",
      isActionColumn: true,
      exportable: false,
      cell: (_val, row) => (
        <div className="flex items-center justify-end gap-0">
          {row.has_artifact && !row.artifact_expurgado && (
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-7 border-0 text-emerald-700 dark:text-emerald-400"
              title="Download forense do artefato bruto"
              aria-label={`Baixar artefato da execução ${row.id}`}
              onClick={() => handleDownloadArtifact(row)}
            >
              <Download className="h-3.5 w-3.5" />
            </Button>
          )}
          {canUpdate && row.sugestao_sentinela?.url_sugerida && !row.sugestao_sentinela.aplicada_em && (
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-7 border-0 text-amber-600 dark:text-amber-400"
              title="Revisar e aplicar URL sugerida pelo Sentinela"
              aria-label={`Aplicar Sentinela da execução ${row.id}`}
              onClick={() => setSentinelRun(row)}
            >
              <Wand2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {pendingSentinelRuns.length > 0 && (
        <Alert className="rounded-sm border-amber-500/40 bg-amber-50/40 dark:bg-amber-950/20">
          <Sparkles className="h-4 w-4 text-amber-600" />
          <AlertTitle className="text-xs font-semibold">
            Sugestões Pendentes do Agente Sentinela ({pendingSentinelRuns.length})
          </AlertTitle>
          <AlertDescription className="space-y-2 mt-2 text-xs">
            {pendingSentinelRuns.map((run) => (
              <div
                key={run.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 rounded-sm border bg-background"
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="font-semibold">
                    {run.source_sigla} — Nova URL detectada na página índice
                  </div>
                  <div className="font-mono text-[11px] break-all text-emerald-700 dark:text-emerald-400">
                    {run.sugestao_sentinela?.url_sugerida}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Evidência: {run.sugestao_sentinela?.evidencia}
                  </div>
                </div>
                {canUpdate && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-sm shrink-0 border-amber-600 text-amber-700 dark:text-amber-400"
                    onClick={() => setSentinelRun(run)}
                  >
                    <Wand2 className="h-3.5 w-3.5 mr-1.5" />
                    Aplicar Sugestão
                  </Button>
                )}
              </div>
            ))}
          </AlertDescription>
        </Alert>
      )}

      <Card className="rounded-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Execuções, Artefatos Forenses &amp; Telemetria IA
          </CardTitle>
          <CardDescription className="text-xs">
            Histórico de coletas agendadas e manuais, consumo de tokens Nível 2 e download de artefatos gzip dentro dos 12 meses de retenção.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full rounded-sm" />
              <Skeleton className="h-12 w-full rounded-sm" />
            </div>
          ) : (
            <DataTable
              data={runs}
              columns={columns}
              searchable
              searchPlaceholder="Buscar por fonte, status ou SHA-256..."
              exportable
              exportFileName="execucoes-coletor-agro"
              emptyMessage="Nenhuma execução registrada até o momento."
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(sentinelRun)} onOpenChange={() => setSentinelRun(null)}>
        <DialogContent className="rounded-sm max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              Aplicar Nova URL do Agente Sentinela
            </DialogTitle>
            <DialogDescription className="text-xs">
              A URL sugerida já foi verificada contra a whitelist da fonte e será registrada no AdminAuditLog.
            </DialogDescription>
          </DialogHeader>

          {sentinelRun && (
            <div className="space-y-3 text-xs py-1">
              <div className="p-2.5 border rounded-sm bg-muted/40 font-mono text-[11px] break-all">
                {sentinelRun.sugestao_sentinela?.url_sugerida}
              </div>
              <div>
                <Label className="text-xs">Justificativa Administrativa (Obrigatória)</Label>
                <Textarea
                  rows={3}
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  className="rounded-sm mt-1 text-xs"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setSentinelRun(null)}
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm border-amber-600 text-amber-700 dark:text-amber-400"
              disabled={applySentinelMutation.isPending || justificativa.trim().length < 5 || !sentinelRun}
              onClick={() => {
                if (sentinelRun) {
                  applySentinelMutation.mutate({ runId: sentinelRun.id, just: justificativa });
                }
              }}
            >
              Confirmar Atualização de URL
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
