"use client";

import React, { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, CheckSquare, ShieldAlert, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
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

import type { CollectorBulkReviewResponse, CollectorStagingItem } from "./types";

interface CollectorStagingTabProps {
  items: CollectorStagingItem[];
  isLoading: boolean;
  canUpdate: boolean;
}

export function CollectorStagingTab({ items, isLoading, canUpdate }: CollectorStagingTabProps) {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [reviewModal, setReviewModal] = useState<{
    acao: "APROVAR" | "REJEITAR";
    ids: string[];
    title: string;
  } | null>(null);
  const [justificativa, setJustificativa] = useState(
    "Evidência literal conferida integralmente no documento oficial de origem."
  );

  const pendentes = useMemo(
    () => items.filter((item) => item.status_revisao === "PENDENTE_REVISAO"),
    [items]
  );

  const invalidateCollectorQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-sources"] });
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-staging"] });
    queryClient.invalidateQueries({ queryKey: ["backoffice-collector-runs"] });
  };

  const singleReviewMutation = useMutation({
    mutationFn: ({ id, acao, just }: { id: string; acao: "APROVAR" | "REJEITAR"; just: string }) => {
      const endpoint = acao === "APROVAR" ? "approve" : "reject";
      return apiFetch<CollectorStagingItem>(
        `/api/v1/backoffice/agro/mercado/collector/staging/${id}/${endpoint}`,
        {
          method: "POST",
          body: { justificativa: just },
        }
      );
    },
    onSuccess: (res) => {
      toast.success(`Observação de ${res.commodity_id} (${res.uf}) marcada como ${res.status_revisao}.`);
      setReviewModal(null);
      setSelectedIds([]);
      invalidateCollectorQueries();
    },
    onError: (err: Error) => {
      toast.error(`Erro ao revisar observação: ${err.message}`);
    },
  });

  const bulkReviewMutation = useMutation({
    mutationFn: ({ ids, acao, just }: { ids: string[]; acao: "APROVAR" | "REJEITAR"; just: string }) =>
      apiFetch<CollectorBulkReviewResponse>(
        "/api/v1/backoffice/agro/mercado/collector/staging/bulk-review",
        {
          method: "POST",
          body: { staging_ids: ids, acao, justificativa: just },
        }
      ),
    onSuccess: (res) => {
      toast.success(`Lote processado: ${res.aprovados} aprovados, ${res.rejeitados} rejeitados.`);
      setReviewModal(null);
      setSelectedIds([]);
      invalidateCollectorQueries();
    },
    onError: (err: Error) => {
      toast.error(`Erro na revisão em lote: ${err.message}`);
    },
  });

  const toggleSelect = (id: string, checked: boolean) => {
    setSelectedIds((prev) => (checked ? Array.from(new Set([...prev, id])) : prev.filter((x) => x !== id)));
  };

  const columns: ColumnDef<CollectorStagingItem>[] = [
    {
      id: "select",
      header: "",
      exportable: false,
      cell: (_val, row) =>
        row.status_revisao === "PENDENTE_REVISAO" ? (
          <Checkbox
            checked={selectedIds.includes(row.id)}
            onCheckedChange={(checked) => toggleSelect(row.id, Boolean(checked))}
            aria-label={`Selecionar ${row.commodity_id}`}
          />
        ) : null,
    },
    {
      id: "commodity",
      header: "Produto / UF & Praça",
      accessorFn: (r) => `${r.commodity_id} ${r.uf} ${r.praca} ${r.source_sigla}`,
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-0.5 text-xs">
          <div className="font-semibold">
            {row.commodity_id} · {row.uf}
          </div>
          <div className="text-[11px] text-muted-foreground">{row.praca}</div>
          <div className="text-[10px] font-mono text-muted-foreground">
            {row.source_sigla} · Ref.: {row.data_referencia}
          </div>
        </div>
      ),
    },
    {
      id: "valor",
      header: "Valor Extraído & Comparativo",
      accessorKey: "valor_normalizado",
      sortable: true,
      cell: (_val, row) => (
        <div className="space-y-0.5 text-xs">
          <div className="font-mono font-semibold text-emerald-700 dark:text-emerald-400">
            R$ {Number(row.valor_normalizado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })} /{" "}
            {row.unidade_normalizada}
          </div>
          {row.ultimo_valor_ativo !== null && row.ultimo_valor_ativo !== undefined && (
            <div className="text-[10px] text-muted-foreground font-mono">
              Ativo: R$ {Number(row.ultimo_valor_ativo).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              {row.variacao_contra_ativo_pct !== null && row.variacao_contra_ativo_pct !== undefined
                ? ` (${Number(row.variacao_contra_ativo_pct) > 0 ? "+" : ""}${row.variacao_contra_ativo_pct}%)`
                : ""}
            </div>
          )}
          {row.flags_anomalia.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-0.5">
              {row.flags_anomalia.map((flag) => (
                <Badge key={flag} variant="outline" className="rounded-sm text-[9px] border-amber-500/40 text-amber-700 dark:text-amber-400">
                  {flag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      ),
    },
    {
      id: "evidencia",
      header: "Trecho Literal de Evidência",
      accessorKey: "trecho_evidencia",
      cell: (_val, row) => (
        <div className="max-w-xs font-mono text-[10px] bg-muted/50 p-1.5 rounded-sm border break-words">
          {row.trecho_evidencia}
        </div>
      ),
    },
    {
      id: "actions",
      header: "",
      isActionColumn: true,
      exportable: false,
      cell: (_val, row) =>
        canUpdate && row.status_revisao === "PENDENTE_REVISAO" ? (
          <div className="flex items-center justify-end gap-0">
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-7 border-0 text-emerald-700 hover:text-emerald-800 dark:text-emerald-400"
              title="Aprovar e Publicar"
              aria-label={`Aprovar ${row.commodity_id}`}
              onClick={() => {
                setJustificativa("Evidência literal conferida integralmente no documento oficial.");
                setReviewModal({
                  acao: "APROVAR",
                  ids: [row.id],
                  title: `Aprovar ${row.commodity_id} (${row.uf}) — ${row.source_sigla}`,
                });
              }}
            >
              <Check className="h-3.5 w-3.5" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="size-7 border-0 text-red-600 hover:text-red-700 dark:text-red-400"
              title="Rejeitar Observação"
              aria-label={`Rejeitar ${row.commodity_id}`}
              onClick={() => {
                setJustificativa("Divergência ou anomalia identificada na revisão humana.");
                setReviewModal({
                  acao: "REJEITAR",
                  ids: [row.id],
                  title: `Rejeitar ${row.commodity_id} (${row.uf}) — ${row.source_sigla}`,
                });
              }}
            >
              <XCircle className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : null,
    },
  ];

  return (
    <div className="space-y-4">
      <Card className="rounded-sm">
        <CardHeader className="pb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-amber-600" />
              Fila de Revisão Humana (Quarentena Imutável)
            </CardTitle>
            <CardDescription className="text-xs">
              Cotações extraídas via IA Nível 2 ou marcadas com anomalia estatística aguardam aprovação 1-clique com conferência do trecho literal de origem. Valores não podem ser editados manualmente.
            </CardDescription>
          </div>
          {canUpdate && pendentes.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="rounded-sm"
                onClick={() =>
                  setSelectedIds(
                    selectedIds.length === pendentes.length ? [] : pendentes.map((p) => p.id)
                  )
                }
              >
                <CheckSquare className="h-3.5 w-3.5 mr-1.5" />
                {selectedIds.length === pendentes.length ? "Desmarcar" : `Selecionar (${pendentes.length})`}
              </Button>
              {selectedIds.length > 0 && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-sm border-emerald-600 text-emerald-700 dark:text-emerald-400"
                    onClick={() => {
                      setJustificativa("Lote validado contra boletim oficial.");
                      setReviewModal({
                        acao: "APROVAR",
                        ids: selectedIds,
                        title: `Aprovar em lote (${selectedIds.length} itens)`,
                      });
                    }}
                  >
                    <Check className="h-3.5 w-3.5 mr-1.5" />
                    Aprovar Selecionados ({selectedIds.length})
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-sm border-red-600 text-red-700 dark:text-red-400"
                    onClick={() => {
                      setJustificativa("Lote rejeitado em revisão administrativa.");
                      setReviewModal({
                        acao: "REJEITAR",
                        ids: selectedIds,
                        title: `Rejeitar em lote (${selectedIds.length} itens)`,
                      });
                    }}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1.5" />
                    Rejeitar Selecionados ({selectedIds.length})
                  </Button>
                </>
              )}
            </div>
          )}
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-9 w-full rounded-sm" />
              <Skeleton className="h-12 w-full rounded-sm" />
            </div>
          ) : (
            <DataTable
              data={items}
              columns={columns}
              searchable
              searchPlaceholder="Buscar commodity, UF, fonte ou evidência..."
              exportable
              exportFileName="quarentena-coletor-agro"
              emptyMessage="Nenhuma observação aguardando revisão humana na quarentena."
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(reviewModal)} onOpenChange={() => setReviewModal(null)}>
        <DialogContent className="rounded-sm max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">{reviewModal?.title}</DialogTitle>
            <DialogDescription className="text-xs">
              Esta decisão será gravada permanentemente no AdminAuditLog sem alteração dos números extraídos.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-1 text-xs">
            <Label className="text-xs">Justificativa Obrigatória</Label>
            <Textarea
              rows={3}
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
              className="rounded-sm text-xs"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              className="rounded-sm"
              onClick={() => setReviewModal(null)}
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className={`rounded-sm ${
                reviewModal?.acao === "APROVAR"
                  ? "border-emerald-600 text-emerald-700 dark:text-emerald-400"
                  : "border-red-600 text-red-700 dark:text-red-400"
              }`}
              disabled={
                singleReviewMutation.isPending ||
                bulkReviewMutation.isPending ||
                justificativa.trim().length < 5
              }
              onClick={() => {
                if (!reviewModal) return;
                if (reviewModal.ids.length === 1) {
                  singleReviewMutation.mutate({
                    id: reviewModal.ids[0],
                    acao: reviewModal.acao,
                    just: justificativa,
                  });
                } else {
                  bulkReviewMutation.mutate({
                    ids: reviewModal.ids,
                    acao: reviewModal.acao,
                    just: justificativa,
                  });
                }
              }}
            >
              Confirmar {reviewModal?.acao === "APROVAR" ? "Aprovação" : "Rejeição"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
