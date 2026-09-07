"use client";

import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { CheckCircle2, Loader2, PackageCheck, User } from "lucide-react";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAppStore } from "@/lib/stores/app-store";

interface ItemPedido {
  id: string;
  produto_nome?: string | null;
  quantidade_solicitada: number;
  unidade: string;
  preco_estimado_unitario: number;
  quantidade_recebida: number;
  status_item: string;
}

interface PedidoParaReceber {
  id: string;
  numero?: string | null;
  fornecedor_nome: string;
  deposito_nome?: string | null;
  itens: ItemPedido[];
}

interface LinhaRecebimento {
  item_pedido_id: string;
  quantidade_recebida: string;
  preco_real_unitario: string;
  numero_lote_fornecedor: string;
}

export function ReceberPedidoDrawer({
  pedido,
  open,
  onOpenChange,
}: {
  pedido: PedidoParaReceber | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const user = useAppStore((s) => s.user);

  const [numeroNf, setNumeroNf] = useState("");
  const [chaveNfe, setChaveNfe] = useState("");
  const [linhas, setLinhas] = useState<LinhaRecebimento[]>([]);

  useEffect(() => {
    if (!pedido) return;
    setNumeroNf("");
    setChaveNfe("");
    setLinhas(
      pedido.itens
        .filter((item) => item.status_item !== "COMPLETO")
        .map((item) => ({
          item_pedido_id: item.id,
          quantidade_recebida: String(item.quantidade_solicitada - item.quantidade_recebida),
          preco_real_unitario: String(item.preco_estimado_unitario),
          numero_lote_fornecedor: "",
        }))
    );
  }, [pedido]);

  const receberMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      apiFetch(`/compras/pedidos/${id}/receber`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Recebimento confirmado!");
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(err.message || "Falha ao confirmar recebimento."),
  });

  if (!pedido) return null;

  const itensPendentes = pedido.itens.filter((item) => item.status_item !== "COMPLETO");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!numeroNf.trim()) {
      toast.error("Informe o número da nota fiscal.");
      return;
    }

    const itensPayload = linhas
      .filter((l) => parseFloat(l.quantidade_recebida) > 0)
      .map((l) => ({
        item_pedido_id: l.item_pedido_id,
        quantidade_recebida: parseFloat(l.quantidade_recebida),
        preco_real_unitario: parseFloat(l.preco_real_unitario) || 0,
        numero_lote_fornecedor: l.numero_lote_fornecedor.trim() || undefined,
      }));

    if (itensPayload.length === 0) {
      toast.error("Informe a quantidade recebida de ao menos um item.");
      return;
    }

    for (const linha of linhas) {
      const item = pedido.itens.find((i) => i.id === linha.item_pedido_id);
      if (!item) continue;
      const saldo = item.quantidade_solicitada - item.quantidade_recebida;
      const qtd = parseFloat(linha.quantidade_recebida) || 0;
      if (qtd > saldo) {
        toast.error(`Quantidade recebida de "${item.produto_nome}" não pode superar o saldo pendente (${saldo}).`);
        return;
      }
    }

    receberMutation.mutate({
      id: pedido.id,
      body: {
        numero_nf: numeroNf.trim(),
        chave_nfe: chaveNfe.trim() || undefined,
        itens: itensPayload,
      },
    });
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md flex flex-col">
        <form onSubmit={handleSubmit} className="flex flex-col h-full">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <PackageCheck className="size-4 text-emerald-600" /> Receber Pedido {pedido.numero || ""}
            </SheetTitle>
            <SheetDescription>
              {pedido.fornecedor_nome} — depósito {pedido.deposito_nome || "padrão"}
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-4 space-y-4">
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-medium">Nota Fiscal *</Label>
                <Input
                  className="h-8 rounded-sm text-xs"
                  placeholder="Nº da NF"
                  value={numeroNf}
                  onChange={(e) => setNumeroNf(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-medium">Chave NF-e</Label>
                <Input
                  className="h-8 rounded-sm text-xs"
                  placeholder="Opcional"
                  value={chaveNfe}
                  onChange={(e) => setChaveNfe(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium text-muted-foreground">Itens a receber</Label>
              <div className="divide-y rounded-sm border">
                {itensPendentes.map((item, idx) => {
                  const linha = linhas.find((l) => l.item_pedido_id === item.id);
                  const saldo = item.quantidade_solicitada - item.quantidade_recebida;
                  if (!linha) return null;
                  return (
                    <div key={item.id} className="p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold truncate">{item.produto_nome}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          saldo {saldo.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} {item.unidade}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Qtd. recebida</Label>
                          <Input
                            type="number" min="0" step="0.01"
                            className="h-8 rounded-sm text-xs"
                            value={linha.quantidade_recebida}
                            onChange={(e) => {
                              const v = e.target.value;
                              setLinhas((prev) => prev.map((l, i) => (i === idx ? { ...l, quantidade_recebida: v } : l)));
                            }}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Preço real (R$)</Label>
                          <Input
                            type="number" min="0" step="0.01"
                            className="h-8 rounded-sm text-xs"
                            value={linha.preco_real_unitario}
                            onChange={(e) => {
                              const v = e.target.value;
                              setLinhas((prev) => prev.map((l, i) => (i === idx ? { ...l, preco_real_unitario: v } : l)));
                            }}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Lote fornecedor</Label>
                          <Input
                            className="h-8 rounded-sm text-xs"
                            placeholder="Opcional"
                            value={linha.numero_lote_fornecedor}
                            onChange={(e) => {
                              const v = e.target.value;
                              setLinhas((prev) => prev.map((l, i) => (i === idx ? { ...l, numero_lote_fornecedor: v } : l)));
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <User className="size-3" /> Recebido por: <strong>{user?.name || "usuário atual"}</strong>
            </p>
          </div>

          <SheetFooter>
            <Button type="submit" size="sm" disabled={receberMutation.isPending}>
              {receberMutation.isPending ? (
                <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
              ) : (
                <CheckCircle2 data-icon="inline-start" className="size-3.5" />
              )}
              Confirmar Recebimento
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}
