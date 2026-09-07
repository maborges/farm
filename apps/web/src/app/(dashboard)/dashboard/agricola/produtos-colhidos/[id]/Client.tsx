"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RefreshCw, PencilLine, Wheat } from "lucide-react";
import { toast } from "sonner";
import type {
  ProdutoColhido,
  ProdutoColhidoCustoResumo,
  ProdutoColhidoCustoAlocacao,
} from "@farm/zod-schemas";

function toBRL(v: number | null | undefined) {
  return v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function ProdutoColhidoDetalheClient({ produtoId }: { produtoId: string }) {
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const podeAjustar = user?.tenant_role === "agronomo" || user?.tenant_role === "admin" || user?.tenant_role === "owner";

  const [overrideAberto, setOverrideAberto] = useState<ProdutoColhidoCustoAlocacao | null>(null);
  const [valorAjuste, setValorAjuste] = useState("");
  const [justificativa, setJustificativa] = useState("");

  const { data: lote, isLoading: carregandoLote } = useQuery<ProdutoColhido>({
    queryKey: ["agricola", "produtos-colhidos", produtoId],
    queryFn: () => apiFetch(`/agricola/produtos-colhidos/${produtoId}`),
  });

  const { data: custos, isLoading: carregandoCustos } = useQuery<ProdutoColhidoCustoResumo>({
    queryKey: ["agricola", "produtos-colhidos", produtoId, "custos"],
    queryFn: () => apiFetch(`/agricola/produtos-colhidos/${produtoId}/custos`),
  });

  const reconciliarMut = useMutation({
    mutationFn: () => apiFetch(`/agricola/produtos-colhidos/${produtoId}/reconciliar-custos`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agricola", "produtos-colhidos", produtoId, "custos"] });
      toast.success("Custos reconciliados com sucesso.");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const overrideMut = useMutation({
    mutationFn: () =>
      apiFetch(`/agricola/produtos-colhidos/${produtoId}/custos/override`, {
        method: "POST",
        body: {
          cost_allocation_id: overrideAberto!.cost_allocation_id,
          valor_atribuido: Number(valorAjuste),
          justificativa,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agricola", "produtos-colhidos", produtoId, "custos"] });
      toast.success("Ajuste manual aplicado.");
      setOverrideAberto(null);
      setValorAjuste("");
      setJustificativa("");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const abrirOverride = (item: ProdutoColhidoCustoAlocacao) => {
    setOverrideAberto(item);
    setValorAjuste(String(item.valor_atribuido));
    setJustificativa("");
  };

  if (carregandoLote) return <div className="p-6"><Skeleton className="h-60 w-full" /></div>;
  if (!lote) return <div className="p-6 text-sm text-muted-foreground">Lote não encontrado.</div>;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title={`Lote — ${new Date(lote.data_entrada).toLocaleDateString("pt-BR", { timeZone: "UTC" })}`}
        description={`${lote.quantidade.toLocaleString("pt-BR")} ${lote.unidade}`}
        icon={<Wheat className="size-5" />}
        breadcrumbs={[
          { label: "Produtos Colhidos", href: "/dashboard/agricola/produtos-colhidos" },
          { label: "Detalhe" },
        ]}
        actions={<WorkflowStatusBadge status={lote.status} />}
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Quantidade", value: `${lote.quantidade.toLocaleString("pt-BR")} ${lote.unidade}` },
          { label: "Peso Líquido", value: `${lote.peso_liquido_kg.toLocaleString("pt-BR")} kg` },
          { label: "Custo Unit. (colheita)", value: toBRL(lote.custo_unitario_producao) },
          { label: "Custo Total Alocado (oficial)", value: toBRL(custos?.total) },
        ].map((k) => (
          <Card key={k.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-xs text-muted-foreground">{k.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">{k.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Custo Alocado por Lançamento (fonte oficial)</CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={() => reconciliarMut.mutate()}
            disabled={reconciliarMut.isPending}
          >
            <RefreshCw className={`size-3.5 mr-1 ${reconciliarMut.isPending ? "animate-spin" : ""}`} />
            Reconciliar
          </Button>
        </CardHeader>
        <CardContent>
          {carregandoCustos ? (
            <Skeleton className="h-32 w-full" />
          ) : !custos || custos.itens.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nenhum custo alocado ainda. Clique em "Reconciliar" para calcular a partir dos lançamentos de custo do talhão/safra.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Origem</TableHead>
                  <TableHead>Percentual</TableHead>
                  <TableHead>Valor Atribuído</TableHead>
                  <TableHead>Justificativa</TableHead>
                  {podeAjustar && <TableHead className="text-right">Ações</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {custos.itens.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <WorkflowStatusBadge
                        status={item.origem_calculo}
                        label={item.origem_calculo === "MANUAL" ? "Ajuste manual" : "Automático"}
                      />
                    </TableCell>
                    <TableCell>{item.percentual_atribuido.toFixed(2)}%</TableCell>
                    <TableCell>{toBRL(item.valor_atribuido)}</TableCell>
                    <TableCell className="text-muted-foreground text-xs">{item.justificativa || "—"}</TableCell>
                    {podeAjustar && (
                      <TableCell className="text-right">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="size-7 text-primary hover:text-primary"
                          aria-label="Ajustar manualmente"
                          onClick={() => abrirOverride(item)}
                        >
                          <PencilLine className="size-3.5" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!overrideAberto} onOpenChange={(open) => !open && setOverrideAberto(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ajustar custo manualmente</AlertDialogTitle>
            <AlertDialogDescription>
              Esse ajuste substitui o valor calculado automaticamente para este lançamento e não será sobrescrito
              por uma reconciliação futura. Justificativa é obrigatória para auditoria.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <Label className="text-xs">Valor atribuído (R$)</Label>
              <Input
                type="number"
                step="0.01"
                value={valorAjuste}
                onChange={(e) => setValorAjuste(e.target.value)}
              />
            </div>
            <div>
              <Label className="text-xs">Justificativa *</Label>
              <Textarea
                value={justificativa}
                onChange={(e) => setJustificativa(e.target.value)}
                placeholder="Ex: ajuste manual por custo de secagem lançado após a colheita."
              />
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => overrideMut.mutate()}
              disabled={!justificativa.trim() || !valorAjuste || overrideMut.isPending}
            >
              Confirmar ajuste
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
