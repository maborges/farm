"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { ClipboardCheck, Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogBody,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface DepositoOption {
  id: string;
  nome: string;
}

interface ContagemItem {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  quantidade_sistema: number;
  quantidade_contada: number | null;
  divergencia: number | null;
  movimento_ajuste_id: string | null;
}

interface Contagem {
  id: string;
  deposito_id: string;
  status: "ABERTA" | "CONCLUIDA" | "CANCELADA";
  aberta_em: string;
  concluida_em: string | null;
  observacoes: string | null;
  itens: ContagemItem[];
}

const STATUS_CONFIG: Record<Contagem["status"], { label: string; color: string }> = {
  ABERTA: { label: "Aberta", color: "bg-blue-100 text-blue-700 border-blue-200" },
  CONCLUIDA: { label: "Concluída", color: "bg-green-100 text-green-700 border-green-200" },
  CANCELADA: { label: "Cancelada", color: "bg-gray-100 text-gray-600 border-gray-200" },
};

export function ContagemEstoqueTab({ depositos }: { depositos: DepositoOption[] }) {
  const queryClient = useQueryClient();
  const [novaOpen, setNovaOpen] = useState(false);
  const [depositoSelecionado, setDepositoSelecionado] = useState("");
  const [contagemAberta, setContagemAberta] = useState<string | null>(null);

  const { data: contagens = [], isLoading } = useQuery<Contagem[]>({
    queryKey: ["contagens-estoque"],
    queryFn: () => apiFetch<Contagem[]>("/estoque/contagens/"),
  });

  const { data: detalhe } = useQuery<Contagem>({
    queryKey: ["contagem-estoque", contagemAberta],
    queryFn: () => apiFetch<Contagem>(`/estoque/contagens/${contagemAberta}`),
    enabled: !!contagemAberta,
  });

  const abrirMutation = useMutation({
    mutationFn: () =>
      apiFetch<Contagem>("/estoque/contagens/", {
        method: "POST",
        body: JSON.stringify({ deposito_id: depositoSelecionado }),
      }),
    onSuccess: (contagem) => {
      queryClient.invalidateQueries({ queryKey: ["contagens-estoque"] });
      toast.success("Contagem de inventário aberta");
      setNovaOpen(false);
      setDepositoSelecionado("");
      setContagemAberta(contagem.id);
    },
    onError: () => toast.error("Erro ao abrir contagem"),
  });

  const registrarItemMutation = useMutation({
    mutationFn: ({ produtoId, quantidade }: { produtoId: string; quantidade: number }) =>
      apiFetch(`/estoque/contagens/${contagemAberta}/itens/${produtoId}`, {
        method: "PATCH",
        body: JSON.stringify({ quantidade_contada: quantidade }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contagem-estoque", contagemAberta] });
    },
    onError: () => toast.error("Erro ao registrar quantidade contada"),
  });

  const concluirMutation = useMutation({
    mutationFn: () => apiFetch(`/estoque/contagens/${contagemAberta}/concluir`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contagens-estoque"] });
      queryClient.invalidateQueries({ queryKey: ["contagem-estoque", contagemAberta] });
      queryClient.invalidateQueries({ queryKey: ["saldos"] });
      toast.success("Contagem concluída — ajustes de divergência aplicados");
    },
    onError: () => toast.error("Erro ao concluir contagem"),
  });

  const cancelarMutation = useMutation({
    mutationFn: () => apiFetch(`/estoque/contagens/${contagemAberta}/cancelar`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contagens-estoque"] });
      toast.success("Contagem cancelada");
      setContagemAberta(null);
    },
    onError: () => toast.error("Erro ao cancelar contagem"),
  });

  if (contagemAberta && detalhe) {
    const deposito = depositos.find(d => d.id === detalhe.deposito_id);
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Contagem — {deposito?.nome ?? "Depósito"}</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Aberta em {new Date(detalhe.aberta_em).toLocaleString("pt-BR")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={STATUS_CONFIG[detalhe.status].color + " border text-xs font-normal"}>
                {STATUS_CONFIG[detalhe.status].label}
              </Badge>
              <Button variant="ghost" size="icon" className="size-7" onClick={() => setContagemAberta(null)} aria-label="Fechar">
                <X size={14} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="text-xs">
                <TableHead>Produto</TableHead>
                <TableHead className="text-right">Saldo no sistema</TableHead>
                <TableHead className="text-right w-40">Quantidade contada</TableHead>
                <TableHead className="text-right">Divergência</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {detalhe.itens.map((item) => (
                <ContagemItemRow
                  key={item.id}
                  item={item}
                  disabled={detalhe.status !== "ABERTA"}
                  onSalvar={(quantidade) =>
                    registrarItemMutation.mutate({ produtoId: item.produto_id, quantidade })
                  }
                />
              ))}
            </TableBody>
          </Table>
        </CardContent>
        {detalhe.status === "ABERTA" && (
          <div className="flex items-center justify-end gap-2 p-4 border-t">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline" size="sm">Cancelar contagem</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancelar contagem?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Nenhum ajuste de saldo será aplicado. Esta ação não pode ser desfeita.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Voltar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => cancelarMutation.mutate()}>Cancelar contagem</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm">Concluir contagem</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Concluir contagem?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Itens com divergência entre a quantidade contada e o saldo do sistema geram um
                    ajuste de estoque automático. Itens não contados são mantidos como estão.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Voltar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => concluirMutation.mutate()}>Concluir contagem</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Contagem de Inventário</CardTitle>
          <Button size="sm" className="gap-1.5 h-8" onClick={() => setNovaOpen(true)}>
            <Plus size={14} /> Nova contagem
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="text-xs">
              <TableHead>Depósito</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Aberta em</TableHead>
              <TableHead>Concluída em</TableHead>
              <TableHead className="text-right">Itens</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? null : contagens.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-16 text-muted-foreground text-sm">
                  <ClipboardCheck className="mx-auto mb-2 size-8 text-muted-foreground/50" />
                  Nenhuma contagem de inventário registrada ainda.
                </TableCell>
              </TableRow>
            ) : (
              contagens.map((c) => (
                <TableRow key={c.id} className="cursor-pointer" onClick={() => setContagemAberta(c.id)}>
                  <TableCell className="font-medium text-sm py-2.5">
                    {depositos.find(d => d.id === c.deposito_id)?.nome ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge className={STATUS_CONFIG[c.status].color + " border text-[10px] font-normal"}>
                      {STATUS_CONFIG[c.status].label}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {new Date(c.aberta_em).toLocaleString("pt-BR")}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {c.concluida_em ? new Date(c.concluida_em).toLocaleString("pt-BR") : "—"}
                  </TableCell>
                  <TableCell className="text-right text-xs tabular-nums">{c.itens.length}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>

      <Dialog open={novaOpen} onOpenChange={setNovaOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader className="border-b">
            <DialogTitle>Nova contagem de inventário</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-2">
            <Select value={depositoSelecionado} onValueChange={setDepositoSelecionado}>
              <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o depósito" /></SelectTrigger>
              <SelectContent>
                {depositos.map((d) => (
                  <SelectItem key={d.id} value={d.id}>{d.nome}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Todos os produtos com saldo neste depósito serão pré-carregados para contagem.
            </p>
          </DialogBody>
          <DialogFooter className="border-t px-6 pb-6 pt-4">
            <Button variant="outline" onClick={() => setNovaOpen(false)}>Cancelar</Button>
            <Button disabled={!depositoSelecionado || abrirMutation.isPending} onClick={() => abrirMutation.mutate()}>
              Abrir contagem
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function ContagemItemRow({
  item, disabled, onSalvar,
}: {
  item: ContagemItem;
  disabled: boolean;
  onSalvar: (quantidade: number) => void;
}) {
  const [valor, setValor] = useState(item.quantidade_contada?.toString() ?? "");

  return (
    <TableRow>
      <TableCell className="font-medium text-sm py-2.5">{item.produto_nome ?? "—"}</TableCell>
      <TableCell className="text-right text-xs text-muted-foreground tabular-nums">
        {item.quantidade_sistema.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
      </TableCell>
      <TableCell className="text-right">
        <Input
          type="number"
          step="0.001"
          className="h-7 text-xs text-right"
          value={valor}
          disabled={disabled}
          onChange={(e) => setValor(e.target.value)}
          onBlur={() => {
            const num = parseFloat(valor);
            if (!Number.isNaN(num) && num !== item.quantidade_contada) onSalvar(num);
          }}
        />
      </TableCell>
      <TableCell className="text-right text-xs tabular-nums">
        {item.divergencia === null ? (
          <span className="text-muted-foreground">—</span>
        ) : item.divergencia === 0 ? (
          <span className="text-green-600">OK</span>
        ) : (
          <span className={item.divergencia > 0 ? "text-blue-600" : "text-red-600"}>
            {item.divergencia > 0 ? "+" : ""}{item.divergencia.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
          </span>
        )}
      </TableCell>
    </TableRow>
  );
}
