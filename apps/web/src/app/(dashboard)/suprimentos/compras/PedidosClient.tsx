"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  ShoppingBag, Search, Filter, MoreHorizontal,
  CheckCircle2, XCircle, Clock, Truck, Ban, ShieldCheck,
  Package, Warehouse, Calendar,
  DollarSign, Download, Pencil, CreditCard,
  ArrowLeft, RotateCcw, Save, Loader2, Scale,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuSeparator 
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { format } from "date-fns";
import { useState } from "react";
import { cn } from "@/lib/utils";
import Link from "next/link";
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
import { ReceberPedidoDrawer } from "@/components/compras/ReceberPedidoDrawer";

interface ItemPedido {
  id: string;
  produto_nome?: string | null;
  deposito_id?: string | null;
  deposito_nome?: string | null;
  quantidade_solicitada: number;
  unidade: string;
  preco_estimado_unitario: number;
  quantidade_recebida: number;
  status_item: string;
}

interface Pedido {
  id: string;
  numero?: string | null;
  fornecedor_nome: string;
  condicoes_pagamento?: string | null;
  valor_adiantamento?: number | null;
  item_nome?: string | null;
  deposito_nome?: string | null;
  endereco_entrega?: string | null;
  prazo_entrega_dias?: number | null;
  quantidade?: number | null;
  unidade?: string | null;
  valor_total: number;
  valor_unitario: number | null;
  status: "ABERTO" | "ENVIADO" | "CONFIRMADO" | "RECUSADO_FORNECEDOR" | "RECEBIDO" | "CANCELADO";
  created_at: string;
  itens: ItemPedido[];
  peso_liquido_kg?: number | null;
}

function hasDisplayValue(value?: string | null) {
  return Boolean(value && value.trim() && value !== "N/A");
}

function uniqueDisplayValues(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter(hasDisplayValue) as string[]));
}

function getItemLabel(pedido: Pedido) {
  if (hasDisplayValue(pedido.item_nome)) return pedido.item_nome as string;
  const nomes = uniqueDisplayValues(pedido.itens.map((item) => item.produto_nome));
  if (nomes.length === 1) return nomes[0];
  if (pedido.itens.length > 1) return "Múltiplos itens";
  return "Item não informado";
}

function getQuantidadeLabel(pedido: Pedido) {
  if (pedido.quantidade != null && pedido.unidade) {
    return `${pedido.quantidade.toLocaleString("pt-BR")} ${pedido.unidade}`;
  }
  return pedido.itens.length > 0 ? `${pedido.itens.length} itens` : "Sem itens";
}

function getEntregaLabel(pedido: Pedido) {
  if (hasDisplayValue(pedido.deposito_nome)) return pedido.deposito_nome as string;
  const depositos = uniqueDisplayValues(pedido.itens.map((item) => item.deposito_nome));
  if (depositos.length === 1) return depositos[0];
  if (depositos.length > 1) return "Múltiplos depósitos";
  const depositoIds = uniqueDisplayValues(pedido.itens.map((item) => item.deposito_id));
  if (depositoIds.length === 1) return "Depósito vinculado ao item";
  if (depositoIds.length > 1) return "Depósitos vinculados aos itens";
  return "Depósito vinculado ao pedido";
}

const statusConfig = {
  ABERTO: { label: "Aberto", color: "bg-blue-100 text-blue-700 border-blue-200", icon: Clock },
  ENVIADO: { label: "Aguardando Confirmação", color: "bg-purple-100 text-purple-700 border-purple-200", icon: Truck },
  CONFIRMADO: { label: "Confirmado pelo Fornecedor", color: "bg-teal-100 text-teal-700 border-teal-200", icon: ShieldCheck },
  RECUSADO_FORNECEDOR: { label: "Recusado pelo Fornecedor", color: "bg-orange-100 text-orange-700 border-orange-200", icon: Ban },
  RECEBIDO: { label: "Recebido", color: "bg-emerald-100 text-emerald-700 border-emerald-200", icon: CheckCircle2 },
  CANCELADO: { label: "Cancelado", color: "bg-red-100 text-red-700 border-red-200", icon: XCircle },
};

export function PedidosClient({ initialData }: { initialData: Pedido[] }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    pedidoId: string | null;
    status: string | null;
    title: string;
    description: string;
  }>({
    open: false,
    pedidoId: null,
    status: null,
    title: "",
    description: "",
  });
  const [condicoesDialog, setCondicoesDialog] = useState<{
    open: boolean;
    pedidoId: string | null;
    valor: string;
  }>({ open: false, pedidoId: null, valor: "" });
  const [adiantamentoDialog, setAdiantamentoDialog] = useState<{
    open: boolean;
    pedidoId: string | null;
    valor: string;
  }>({ open: false, pedidoId: null, valor: "" });
  const [receberDrawer, setReceberDrawer] = useState<{ open: boolean; pedidoId: string | null }>({
    open: false,
    pedidoId: null,
  });
  const [estornoDialog, setEstornoDialog] = useState<{ open: boolean; pedidoId: string | null; motivo: string }>({
    open: false,
    pedidoId: null,
    motivo: "",
  });
  const queryClient = useQueryClient();
  const menuItemClass = "gap-2 text-xs";
  const menuIconClass = "size-4 shrink-0";

  const { data: pedidos = initialData } = useQuery<Pedido[]>({
    queryKey: ["compras-pedidos"],
    queryFn: () => apiFetch(`/compras/pedidos`),
    initialData,
    staleTime: 30_000,
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string, status: string }) => 
      apiFetch(`/compras/pedidos/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Status do pedido atualizado!");
    },
    onError: () => toast.error("Falha ao atualizar status."),
  });

  const enviarFornecedorMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/compras/pedidos/${id}/enviar`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Pedido enviado ao fornecedor por e-mail — aguardando confirmação.");
    },
    onError: (e: any) => toast.error(e?.message || "Falha ao enviar pedido ao fornecedor."),
  });

  const solicitarPesagemMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/compras/pedidos/${id}/solicitar-pesagem-balanca`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Pesagem solicitada à balança!");
    },
    onError: (e: any) => toast.error(e?.message || "Falha ao solicitar pesagem."),
  });

  const estornarRecebimentoMutation = useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
      apiFetch(`/compras/pedidos/${id}/estornar-recebimento`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Recebimento estornado — pedido voltou ao status anterior.");
      setEstornoDialog({ open: false, pedidoId: null, motivo: "" });
    },
    onError: (e: any) => toast.error(e?.message || "Falha ao estornar recebimento."),
  });

  const updateCondicoesMutation = useMutation({
    mutationFn: ({ id, condicoes_pagamento }: { id: string, condicoes_pagamento: string }) =>
      apiFetch(`/compras/pedidos/${id}/condicoes-pagamento`, {
        method: "PATCH",
        body: JSON.stringify({ condicoes_pagamento }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Condições de pagamento atualizadas!");
      setCondicoesDialog({ open: false, pedidoId: null, valor: "" });
    },
    onError: () => toast.error("Falha ao atualizar condições de pagamento."),
  });

  const updateAdiantamentoMutation = useMutation({
    mutationFn: ({ id, valor_adiantamento }: { id: string, valor_adiantamento: number }) =>
      apiFetch(`/compras/pedidos/${id}/adiantamento`, {
        method: "PATCH",
        body: JSON.stringify({ valor_adiantamento }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Adiantamento atualizado!");
      setAdiantamentoDialog({ open: false, pedidoId: null, valor: "" });
    },
    onError: (e: any) => toast.error(e?.message || "Falha ao atualizar adiantamento."),
  });

  const handleDownloadPdf = async (pedido: Pedido) => {
    const loadingToast = toast.loading("Gerando PDF...");
    try {
      const blob = await apiFetch<Blob>(`/compras/pedidos/${pedido.id}/pdf`, {
        method: "GET",
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${pedido.numero || pedido.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.dismiss(loadingToast);
      toast.success("PDF baixado com sucesso!");
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error("Erro ao gerar PDF.");
    }
  };

  const filteredPedidos = pedidos.filter(p =>
    (p.fornecedor_nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
     getItemLabel(p).toLowerCase().includes(searchTerm.toLowerCase()) ||
     getEntregaLabel(p).toLowerCase().includes(searchTerm.toLowerCase())) &&
    (!filterStatus || p.status === filterStatus)
  );

  const statusCounts = filteredPedidos.reduce((acc, pedido) => {
    acc[pedido.status] = (acc[pedido.status] ?? 0) + 1;
    return acc;
  }, {
    ABERTO: 0,
    ENVIADO: 0,
    CONFIRMADO: 0,
    RECUSADO_FORNECEDOR: 0,
    RECEBIDO: 0,
    CANCELADO: 0,
  } as Record<Pedido["status"], number>);

  const totalValor = filteredPedidos.reduce((sum, pedido) => sum + pedido.valor_total, 0);
  const hasFilters = Boolean(searchTerm || filterStatus);

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Pedidos de Compra"
        description="Acompanhe a oficialização, o recebimento e o histórico financeiro dos pedidos."
        icon={<ShoppingBag className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Compras", href: "/suprimentos/compras" },
          { label: "Pedidos" }
        ]}
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/suprimentos/compras/solicitacoes">
              <ArrowLeft data-icon="inline-start" className="size-3.5" />
              Solicitações
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card className="rounded-sm shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex size-10 items-center justify-center rounded-sm bg-blue-500/10 text-blue-600">
              <Clock className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase text-muted-foreground">Abertos</p>
              <p className="text-2xl font-black tabular-nums">{statusCounts.ABERTO}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-sm shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex size-10 items-center justify-center rounded-sm bg-purple-500/10 text-purple-600">
              <Truck className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase text-muted-foreground">Enviados</p>
              <p className="text-2xl font-black tabular-nums">{statusCounts.ENVIADO}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-sm shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex size-10 items-center justify-center rounded-sm bg-emerald-500/10 text-emerald-600">
              <CheckCircle2 className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase text-muted-foreground">Recebidos</p>
              <p className="text-2xl font-black tabular-nums">{statusCounts.RECEBIDO}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-sm shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex size-10 items-center justify-center rounded-sm bg-red-500/10 text-red-600">
              <XCircle className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase text-muted-foreground">Cancelados</p>
              <p className="text-2xl font-black tabular-nums">{statusCounts.CANCELADO}</p>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-sm shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex size-10 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <DollarSign className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase text-muted-foreground">Valor total</p>
              <p className="text-base font-black tabular-nums">
                {totalValor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-sm shadow-sm">
        <CardContent className="p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-md">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por fornecedor ou item..."
                className="h-8 pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter data-icon="inline-start" className="size-3.5 text-primary" />
                    {filterStatus ? statusConfig[filterStatus as keyof typeof statusConfig].label : "Todos os status"}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48 rounded-sm">
                  <DropdownMenuItem className={menuItemClass} onClick={() => setFilterStatus(null)}>Todos</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {Object.entries(statusConfig).map(([key, config]) => (
                    <DropdownMenuItem key={key} className={menuItemClass} onClick={() => setFilterStatus(key)}>
                      <config.icon data-icon="inline-start" className="size-3.5 shrink-0 text-primary" />
                      {config.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              {(searchTerm || filterStatus) && (
                <Button variant="ghost" size="sm" onClick={() => { setSearchTerm(""); setFilterStatus(null); }}>
                  <RotateCcw data-icon="inline-start" className="size-3.5" />
                  Limpar filtros
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4">
        {filteredPedidos.map((pedido) => {
          const Config = statusConfig[pedido.status];
          const itemLabel = getItemLabel(pedido);
          const quantidadeLabel = getQuantidadeLabel(pedido);
          const entregaLabel = getEntregaLabel(pedido);
          return (
            <Card key={pedido.id} className="rounded-sm shadow-sm hover:shadow-md transition-shadow overflow-hidden">
              <CardHeader className="border-b">
                <div className="flex items-start gap-3">
                  <div className="size-10 shrink-0 rounded-sm bg-primary/10 flex items-center justify-center">
                    <ShoppingBag className="size-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {pedido.numero && (
                        <span className="font-mono text-[11px] font-bold text-muted-foreground">
                          {pedido.numero}
                        </span>
                      )}
                      <CardTitle className="truncate text-sm font-black uppercase tracking-tight">
                        {pedido.fornecedor_nome}
                      </CardTitle>
                      <Badge variant="outline" className={cn("rounded-sm border text-[9px] font-bold uppercase", Config.color)}>
                        {Config.label}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs">
                      {itemLabel} • {quantidadeLabel} • {entregaLabel}
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-8 rounded-sm"
                        title="Ações"
                      >
                        <MoreHorizontal className="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56 rounded-sm">
                      <DropdownMenuLabel className="p-2 text-[10px] font-bold uppercase text-muted-foreground">Gerenciar Pedido</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className={menuItemClass}
                        onClick={() => enviarFornecedorMutation.mutate(pedido.id)}
                        disabled={!["ABERTO", "ENVIADO"].includes(pedido.status) || enviarFornecedorMutation.isPending}
                      >
                        <Truck data-icon="inline-start" className={cn(menuIconClass, "text-amber-600")} />
                        {pedido.status === "ABERTO" && "Enviar ao Fornecedor"}
                        {pedido.status === "ENVIADO" && "Reenviar ao Fornecedor"}
                        {!["ABERTO", "ENVIADO"].includes(pedido.status) &&
                          `Enviar ao Fornecedor (pedido já está ${statusConfig[pedido.status].label.toLowerCase()})`}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className={cn(menuItemClass, "text-emerald-600")}
                        onClick={() => setReceberDrawer({ open: true, pedidoId: pedido.id })}
                        disabled={["RECEBIDO", "CANCELADO", "RECUSADO_FORNECEDOR"].includes(pedido.status)}
                      >
                        <CheckCircle2 data-icon="inline-start" className={cn(menuIconClass, "text-emerald-600")} /> Confirmar Recebimento
                      </DropdownMenuItem>
                      {pedido.status === "RECEBIDO" && (
                        <DropdownMenuItem
                          className={cn(menuItemClass, "text-amber-600")}
                          onClick={() => setEstornoDialog({ open: true, pedidoId: pedido.id, motivo: "" })}
                        >
                          <RotateCcw data-icon="inline-start" className={cn(menuIconClass, "text-amber-600")} /> Estornar Recebimento
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem
                        className={cn(menuItemClass, "text-blue-600")}
                        onClick={() => solicitarPesagemMutation.mutate(pedido.id)}
                        disabled={
                          ["CANCELADO", "RECUSADO_FORNECEDOR"].includes(pedido.status) ||
                          pedido.peso_liquido_kg != null ||
                          solicitarPesagemMutation.isPending
                        }
                      >
                        <Scale data-icon="inline-start" className={cn(menuIconClass, "text-blue-600")} />
                        {pedido.peso_liquido_kg != null ? "Pesagem já registrada" : "Solicitar Pesagem"}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className={menuItemClass} onClick={() => handleDownloadPdf(pedido)}>
                        <Download data-icon="inline-start" className={menuIconClass} /> Baixar PDF
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className={cn(menuItemClass, "text-red-600")}
                        onClick={() => setConfirmDialog({
                          open: true,
                          pedidoId: pedido.id,
                          status: "CANCELADO",
                          title: "Cancelar pedido?",
                          description: "Esta ação não pode ser desfeita e o pedido será invalidado."
                        })}
                        disabled={["RECEBIDO", "CANCELADO"].includes(pedido.status)}
                      >
                        <XCircle data-icon="inline-start" className={cn(menuIconClass, "text-red-600")} /> Cancelar Pedido
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>

              <CardContent className="grid gap-4 py-4 md:grid-cols-[minmax(0,1fr)_auto]">
                <div className="grid gap-3 sm:grid-cols-6">
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">Produto</p>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <Package className="size-3.5 text-muted-foreground" />
                      {itemLabel}
                    </p>
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">Depósito / Endereço de Entrega</p>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <Warehouse className="size-3.5 text-muted-foreground" />
                      {entregaLabel}
                    </p>
                    {pedido.endereco_entrega && (
                      <p className="mt-0.5 text-[10px] text-muted-foreground">{pedido.endereco_entrega}</p>
                    )}
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">Criado em</p>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <Calendar className="size-3.5 text-muted-foreground" />
                      {format(new Date(pedido.created_at), "dd/MM/yyyy")}
                    </p>
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">Condições de Pagamento</p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-xs"
                        aria-label="Editar condições de pagamento"
                        className="rounded-sm text-muted-foreground hover:text-primary"
                        disabled={pedido.status === "RECEBIDO" || pedido.status === "CANCELADO"}
                        onClick={() => setCondicoesDialog({
                          open: true,
                          pedidoId: pedido.id,
                          valor: pedido.condicoes_pagamento ?? "",
                        })}
                      >
                        <Pencil className="size-3" />
                      </Button>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <CreditCard className="size-3.5 text-muted-foreground" />
                      {pedido.condicoes_pagamento || "Não definidas"}
                    </p>
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">Adiantamento</p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-xs"
                        aria-label="Editar adiantamento"
                        className="rounded-sm text-muted-foreground hover:text-primary"
                        disabled={pedido.status !== "ABERTO" && pedido.status !== "ENVIADO"}
                        onClick={() => setAdiantamentoDialog({
                          open: true,
                          pedidoId: pedido.id,
                          valor: pedido.valor_adiantamento ? String(pedido.valor_adiantamento) : "",
                        })}
                      >
                        <Pencil className="size-3" />
                      </Button>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <DollarSign className="size-3.5 text-muted-foreground" />
                      {pedido.valor_adiantamento
                        ? pedido.valor_adiantamento.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
                        : "Sem adiantamento"}
                    </p>
                  </div>
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <p className="text-[10px] font-bold uppercase text-muted-foreground">Prazo de Entrega</p>
                    <p className="mt-1 flex items-center gap-1 text-sm font-semibold">
                      <Truck className="size-3.5 text-muted-foreground" />
                      {pedido.prazo_entrega_dias ? `${pedido.prazo_entrega_dias} dias` : "A combinar"}
                    </p>
                  </div>
                </div>

                <div className="flex min-w-[220px] flex-col justify-center rounded-sm border bg-primary/5 p-4 text-right">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground">Valor total</span>
                  <p className="text-2xl font-black tabular-nums text-primary">
                    {pedido.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </p>
                  <span className="text-[9px] font-bold uppercase text-muted-foreground">
                    {pedido.valor_unitario !== null
                      ? `${pedido.valor_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} / ${pedido.unidade}`
                      : "Múltiplos itens"}
                  </span>
                </div>
              </CardContent>

              <CardFooter className="justify-between">
                <p className="text-[10px] font-bold uppercase text-muted-foreground">
                  Pedido monitorado pelo fluxo de compras
                </p>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/suprimentos/compras/solicitacoes">
                    <ArrowLeft data-icon="inline-start" className="size-3.5" />
                    Solicitações
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          );
        })}

        {filteredPedidos.length === 0 && (
          <Card className="rounded-sm shadow-sm">
            <CardContent className="p-0">
              <EmptyState
                icon={<ShoppingBag />}
                title="Nenhum pedido encontrado"
                description="Acompanhe suas solicitações para gerar novos pedidos."
                action={
                  hasFilters
                    ? { label: "Limpar filtros", onClick: () => { setSearchTerm(""); setFilterStatus(null); } }
                    : { label: "Ver solicitações", href: "/suprimentos/compras/solicitacoes" }
                }
                secondaryAction={
                  hasFilters
                    ? { label: "Ver solicitações", href: "/suprimentos/compras/solicitacoes" }
                    : undefined
                }
              />
            </CardContent>
          </Card>
        )}
      </div>

      <AlertDialog 
        open={confirmDialog.open} 
        onOpenChange={(open) => setConfirmDialog(prev => ({ ...prev, open }))}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmDialog.title}
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm text-muted-foreground">
              {confirmDialog.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              variant={confirmDialog.status === "CANCELADO" ? "destructive" : "default"}
              size="sm"
              onClick={() => {
                const { pedidoId, status } = confirmDialog;
                if (pedidoId && status) {
                  setConfirmDialog({
                    open: false,
                    pedidoId: null,
                    status: null,
                    title: "",
                    description: "",
                  });
                  updateStatusMutation.mutate({ id: pedidoId, status });
                }
              }}
            >
              {confirmDialog.status === "CANCELADO" ? (
                <XCircle data-icon="inline-start" className="size-3.5" />
              ) : (
                <CheckCircle2 data-icon="inline-start" className="size-3.5" />
              )}
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={estornoDialog.open} onOpenChange={(open) => !open && setEstornoDialog({ open: false, pedidoId: null, motivo: "" })}>
        <DialogContent className="max-w-sm p-0">
          <form onSubmit={(e) => {
            e.preventDefault();
            if (estornoDialog.pedidoId && estornoDialog.motivo.trim().length >= 3) {
              estornarRecebimentoMutation.mutate({ id: estornoDialog.pedidoId, motivo: estornoDialog.motivo.trim() });
            }
          }}>
            <DialogHeader>
              <DialogTitle>Estornar recebimento?</DialogTitle>
            </DialogHeader>
            <DialogBody className="space-y-3">
              <p className="text-xs text-muted-foreground leading-relaxed">
                O estoque recebido será revertido, a despesa gerada será desativada e o pedido volta ao status
                anterior. Só é possível se nada desse estoque já tiver sido consumido — caso contrário, use
                Devolução ao Fornecedor.
              </p>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Justificativa do estorno *</Label>
                <Textarea
                  className="text-xs rounded-sm min-h-20"
                  placeholder="Ex: recebimento confirmado por engano, era outro pedido."
                  value={estornoDialog.motivo}
                  onChange={(e) => setEstornoDialog((d) => ({ ...d, motivo: e.target.value }))}
                  required
                  minLength={3}
                />
              </div>
            </DialogBody>
            <DialogFooter>
              <Button type="button" variant="outline" size="sm" onClick={() => setEstornoDialog({ open: false, pedidoId: null, motivo: "" })}>
                Cancelar
              </Button>
              <Button type="submit" size="sm" disabled={estornarRecebimentoMutation.isPending || estornoDialog.motivo.trim().length < 3}>
                {estornarRecebimentoMutation.isPending ? (
                  <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
                ) : (
                  <RotateCcw data-icon="inline-start" className="size-3.5" />
                )}
                Estornar
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={condicoesDialog.open} onOpenChange={(open) => !open && setCondicoesDialog({ open: false, pedidoId: null, valor: "" })}>
        <DialogContent className="max-w-sm p-0">
          <form onSubmit={(e) => {
            e.preventDefault();
            if (condicoesDialog.pedidoId) {
              updateCondicoesMutation.mutate({ id: condicoesDialog.pedidoId, condicoes_pagamento: condicoesDialog.valor });
            }
          }}>
            <DialogHeader>
              <DialogTitle>Condições de Pagamento</DialogTitle>
            </DialogHeader>
            <DialogBody className="space-y-1.5">
              <Label className="text-xs font-medium">Condições *</Label>
              <Input
                placeholder="Ex: 30% adiantado + 30 dias"
                className="h-8 rounded-sm text-xs"
                value={condicoesDialog.valor}
                onChange={(e) => setCondicoesDialog(d => ({ ...d, valor: e.target.value }))}
              />
            </DialogBody>
            <DialogFooter>
              <Button type="button" variant="outline" size="sm" onClick={() => setCondicoesDialog({ open: false, pedidoId: null, valor: "" })}>
                Cancelar
              </Button>
              <Button type="submit" size="sm" disabled={updateCondicoesMutation.isPending || !condicoesDialog.valor.trim()}>
                {updateCondicoesMutation.isPending ? (
                  <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
                ) : (
                  <Save data-icon="inline-start" className="size-3.5" />
                )}
                Salvar
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={adiantamentoDialog.open} onOpenChange={(open) => !open && setAdiantamentoDialog({ open: false, pedidoId: null, valor: "" })}>
        <DialogContent className="max-w-sm p-0">
          <form onSubmit={(e) => {
            e.preventDefault();
            if (adiantamentoDialog.pedidoId) {
              updateAdiantamentoMutation.mutate({ id: adiantamentoDialog.pedidoId, valor_adiantamento: parseFloat(adiantamentoDialog.valor) || 0 });
            }
          }}>
            <DialogHeader>
              <DialogTitle>Adiantamento</DialogTitle>
            </DialogHeader>
            <DialogBody className="space-y-1.5">
              <Label className="text-xs font-medium">Valor do Adiantamento (R$)</Label>
              <Input
                type="number" min="0" step="0.01"
                placeholder="0,00"
                className="h-8 rounded-sm text-xs"
                value={adiantamentoDialog.valor}
                onChange={(e) => setAdiantamentoDialog(d => ({ ...d, valor: e.target.value }))}
              />
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Gerado como despesa própria (contas a pagar) somente após o fornecedor confirmar o aceite do pedido.
              </p>
            </DialogBody>
            <DialogFooter>
              <Button type="button" variant="outline" size="sm" onClick={() => setAdiantamentoDialog({ open: false, pedidoId: null, valor: "" })}>
                Cancelar
              </Button>
              <Button type="submit" size="sm" disabled={updateAdiantamentoMutation.isPending}>
                {updateAdiantamentoMutation.isPending ? (
                  <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
                ) : (
                  <Save data-icon="inline-start" className="size-3.5" />
                )}
                Salvar
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ReceberPedidoDrawer
        pedido={pedidos.find((p) => p.id === receberDrawer.pedidoId) ?? null}
        open={receberDrawer.open}
        onOpenChange={(open) => setReceberDrawer((d) => ({ ...d, open }))}
      />
    </div>
  );
}
