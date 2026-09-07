"use client";

import { useState, type ElementType, type FormEvent } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import {
  ArrowRightLeft,
  BadgeCheck,
  CheckCircle2,
  Loader2,
  Package,
  Plus,
  Scale,
  Truck,
  XCircle,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

type Comercializacao = {
  id: string;
  numero_contrato: string | null;
  commodity_id: string;
  comprador_id: string;
  quantidade: number;
  unidade: string;
  preco_unitario: number;
  moeda: string;
  valor_total: number;
  forma_pagamento: string | null;
  data_entrega_prevista: string | null;
  data_entrega_real: string | null;
  local_entrega: string | null;
  frete_por_conta: string | null;
  produto_colhido_id: string | null;
  nf_numero: string | null;
  nf_serie: string | null;
  nf_chave: string | null;
  status: string;
  observacoes: string | null;
  receita_id: string | null;
  created_at: string;
  updated_at: string;
  peso_liquido_kg?: number | null;
};

type Commodity = {
  id: string;
  nome: string;
  unidade_padrao: string;
};

type Pessoa = {
  id: string;
  nome_exibicao: string;
  tipo: string;
  ativo: boolean;
};

type ProdutoColhido = {
  id: string;
  safra_id: string;
  commodity_id: string;
  quantidade: number;
  unidade: string;
  peso_liquido_kg: number;
  peso_liquido_comercial_kg: number | null;
  status: string;
  data_entrada: string;
};

type ComercializacaoCreate = {
  commodity_id: string;
  comprador_id: string;
  numero_contrato?: string;
  quantidade: number;
  unidade: string;
  preco_unitario: number;
  moeda: string;
  forma_pagamento?: string;
  data_entrega_prevista?: string;
  local_entrega?: string;
  frete_por_conta?: string;
  produto_colhido_id: string;
  observacoes?: string;
};

const statusAcoes: Record<string, Array<{ label: string; status: string; icon: ElementType }>> = {
  RASCUNHO: [
    { label: "Confirmar", status: "CONFIRMADO", icon: BadgeCheck },
    { label: "Cancelar", status: "CANCELADO", icon: XCircle },
  ],
  CONFIRMADO: [
    { label: "Em trânsito", status: "EM_TRANSITO", icon: Truck },
    { label: "Cancelar", status: "CANCELADO", icon: XCircle },
  ],
  EM_TRANSITO: [
    { label: "Entregue", status: "ENTREGUE", icon: Package },
    { label: "Cancelar", status: "CANCELADO", icon: XCircle },
  ],
  ENTREGUE: [
    { label: "Finalizar", status: "FINALIZADO", icon: CheckCircle2 },
  ],
};

function fmtMoney(v: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v ?? 0);
}

function fmtNumber(v: number | null | undefined, digits = 3) {
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v ?? 0);
}

function StatusActions({
  item,
  onTransition,
  loading,
  onSolicitarPesagem,
  solicitandoPesagem,
}: {
  item: Comercializacao;
  onTransition: (id: string, status: string) => void;
  loading: boolean;
  onSolicitarPesagem: (id: string) => void;
  solicitandoPesagem: boolean;
}) {
  const actions = statusAcoes[item.status] ?? [];
  const podeSolicitarPesagem =
    !["CANCELADO"].includes(item.status) && item.peso_liquido_kg == null;

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <Button
            key={action.status}
            size="xs"
            variant={action.status === "CANCELADO" ? "destructive" : "outline"}
            disabled={loading}
            onClick={() => onTransition(item.id, action.status)}
            className="rounded-sm"
          >
            {loading ? <Loader2 className="size-3.5 animate-spin" /> : <Icon className="size-3.5" />}
            {action.label}
          </Button>
        );
      })}
      {podeSolicitarPesagem && (
        <Button
          key="solicitar-pesagem"
          size="xs"
          variant="outline"
          disabled={solicitandoPesagem}
          onClick={() => onSolicitarPesagem(item.id)}
          className="rounded-sm text-blue-600"
        >
          {solicitandoPesagem ? <Loader2 className="size-3.5 animate-spin" /> : <Scale className="size-3.5" />}
          Solicitar Pesagem
        </Button>
      )}
      {actions.length === 0 && !podeSolicitarPesagem && (
        <span className="text-xs text-muted-foreground">Sem ação</span>
      )}
    </div>
  );
}

function NovaComercializacaoDialog({
  open,
  onOpenChange,
  commodities,
  pessoas,
  produtosColhidos,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commodities: Commodity[];
  pessoas: Pessoa[];
  produtosColhidos: ProdutoColhido[];
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ComercializacaoCreate>({
    commodity_id: "",
    comprador_id: "",
    quantidade: 0,
    unidade: "SACA_60KG",
    preco_unitario: 0,
    moeda: "BRL",
    forma_pagamento: "",
    data_entrega_prevista: new Date().toISOString().split("T")[0],
    local_entrega: "",
    frete_por_conta: "",
    produto_colhido_id: "",
    observacoes: "",
  });

  const mutation = useMutation({
    mutationFn: (payload: ComercializacaoCreate) =>
      apiFetch("/financeiro/comercializacoes/", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => {
      toast.success("Comercialização criada.");
      queryClient.invalidateQueries({ queryKey: ["comercializacoes"] });
      onOpenChange(false);
      setForm({
        commodity_id: "",
        comprador_id: "",
        quantidade: 0,
        unidade: "SACA_60KG",
        preco_unitario: 0,
        moeda: "BRL",
        forma_pagamento: "",
        data_entrega_prevista: new Date().toISOString().split("T")[0],
        local_entrega: "",
        frete_por_conta: "",
        produto_colhido_id: "",
        observacoes: "",
      });
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao criar comercialização."),
  });

  const commoditySelecionada = commodities.find((c) => c.id === form.commodity_id);
  const commodityUnidade = commoditySelecionada?.unidade_padrao ?? form.unidade;

  const handleProduto = (produtoId: string) => {
    const produto = produtosColhidos.find((item) => item.id === produtoId);
    setForm((current) => ({
      ...current,
      produto_colhido_id: produtoId,
      commodity_id: produto?.commodity_id ?? current.commodity_id,
      quantidade: produto?.peso_liquido_comercial_kg ?? produto?.quantidade ?? current.quantidade,
      unidade: produto?.unidade ?? current.unidade,
    }));
  };

  const handleCommodityChange = (commodityId: string) => {
    const commodity = commodities.find((item) => item.id === commodityId);
    setForm((current) => ({
      ...current,
      commodity_id: commodityId,
      unidade: commodity?.unidade_padrao ?? current.unidade,
    }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.produto_colhido_id) return toast.error("Selecione o lote (produto colhido) de origem.");
    if (!form.commodity_id) return toast.error("Selecione a commodity.");
    if (!form.comprador_id) return toast.error("Selecione o comprador.");
    if (form.quantidade <= 0) return toast.error("Informe uma quantidade válida.");
    if (form.preco_unitario <= 0) return toast.error("Informe um preço unitário válido.");
    mutation.mutate({
      ...form,
      produto_colhido_id: form.produto_colhido_id,
      numero_contrato: form.numero_contrato?.trim() || undefined,
      forma_pagamento: form.forma_pagamento?.trim() || undefined,
      local_entrega: form.local_entrega?.trim() || undefined,
      frete_por_conta: form.frete_por_conta?.trim() || undefined,
      observacoes: form.observacoes?.trim() || undefined,
      data_entrega_prevista: form.data_entrega_prevista || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl gap-0 p-0">
        <DialogHeader className="border-b border-border px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <ArrowRightLeft className="size-4" />
            </div>
            <div>
              <DialogTitle>Nova Comercialização</DialogTitle>
              <DialogDescription>Vincule produto colhido, comprador e condições comerciais.</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <DialogBody className="grid gap-4 px-6 py-5">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Produto colhido *</Label>
                <Select value={form.produto_colhido_id} onValueChange={handleProduto}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Selecione o lote..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {produtosColhidos.length === 0 ? (
                      <SelectItem value="empty" disabled>
                        Nenhum lote armazenado
                      </SelectItem>
                    ) : (
                      produtosColhidos.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.id.slice(0, 8)} · {fmtNumber(item.peso_liquido_comercial_kg ?? item.quantidade, 3)} {item.unidade}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Commodity</Label>
                <Select value={form.commodity_id} onValueChange={handleCommodityChange}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {commodities.map((commodity) => (
                      <SelectItem key={commodity.id} value={commodity.id}>
                        {commodity.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Comprador</Label>
                <Select value={form.comprador_id} onValueChange={(value) => setForm((current) => ({ ...current, comprador_id: value }))}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {pessoas.map((pessoa) => (
                      <SelectItem key={pessoa.id} value={pessoa.id}>
                        {pessoa.nome_exibicao}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Número do contrato</Label>
                <Input
                  className="rounded-sm"
                  value={form.numero_contrato ?? ""}
                  onChange={(event) => setForm((current) => ({ ...current, numero_contrato: event.target.value }))}
                  placeholder="CTR-2026-001"
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quantidade</Label>
                <Input
                  type="number"
                  step="0.001"
                  min="0.001"
                  className="rounded-sm"
                  value={form.quantidade}
                  onChange={(event) => setForm((current) => ({ ...current, quantidade: Number(event.target.value) }))}
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Unidade</Label>
                <Input
                  className="rounded-sm"
                  value={commodityUnidade}
                  onChange={(event) => setForm((current) => ({ ...current, unidade: event.target.value }))}
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Preço unitário</Label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0.0001"
                  className="rounded-sm"
                  value={form.preco_unitario}
                  onChange={(event) => setForm((current) => ({ ...current, preco_unitario: Number(event.target.value) }))}
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Moeda</Label>
                <Input
                  className="rounded-sm"
                  value={form.moeda}
                  onChange={(event) => setForm((current) => ({ ...current, moeda: event.target.value.toUpperCase() }))}
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Forma de pagamento</Label>
                <Select value={form.forma_pagamento ?? ""} onValueChange={(value) => setForm((current) => ({ ...current, forma_pagamento: value }))}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Opcional" />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {["A_VISTA", "PRAZO", "BOLETO", "PIX", "TRANSFERENCIA"].map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Entrega prevista</Label>
                <Input
                  type="date"
                  className="rounded-sm"
                  value={form.data_entrega_prevista ?? ""}
                  onChange={(event) => setForm((current) => ({ ...current, data_entrega_prevista: event.target.value }))}
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Frete por conta</Label>
                <Select value={form.frete_por_conta ?? ""} onValueChange={(value) => setForm((current) => ({ ...current, frete_por_conta: value }))}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Opcional" />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {["COMPRADOR", "VENDEDOR", "CIF", "FOB"].map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Local de entrega</Label>
              <Input
                className="rounded-sm"
                value={form.local_entrega ?? ""}
                onChange={(event) => setForm((current) => ({ ...current, local_entrega: event.target.value }))}
                placeholder="Armazém central, cooperativa, indústria..."
              />
            </div>

            <div className="grid gap-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Observações</Label>
              <Input
                className="rounded-sm"
                value={form.observacoes ?? ""}
                onChange={(event) => setForm((current) => ({ ...current, observacoes: event.target.value }))}
                placeholder="Condições comerciais, NF, observações operacionais"
              />
            </div>
          </DialogBody>

          <DialogFooter className="border-t border-border px-6 py-4">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)} className="rounded-sm">
              Cancelar
            </Button>
            <Button type="submit" disabled={mutation.isPending} className="rounded-sm">
              {mutation.isPending ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Plus className="mr-2 size-4" />}
              Criar comercialização
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function ComercializacoesPage() {
  const queryClient = useQueryClient();
  const { token, _hasHydrated } = useAppStore();
  const [open, setOpen] = useState(false);
  const canLoad = _hasHydrated && !!token;

  const { data: comercializacoes = [], isLoading: loadingComercializacoes } = useQuery<Comercializacao[]>({
    queryKey: ["comercializacoes"],
    queryFn: () => apiFetch("/financeiro/comercializacoes/"),
    enabled: canLoad,
  });

  const { data: commodities = [], isLoading: loadingCommodities } = useQuery<Commodity[]>({
    queryKey: ["comercializacoes-commodities"],
    queryFn: () => apiFetch("/cadastros/commodities"),
    enabled: canLoad,
  });

  const { data: pessoas = [], isLoading: loadingPessoas } = useQuery<Pessoa[]>({
    queryKey: ["comercializacoes-pessoas"],
    queryFn: () => apiFetch("/cadastros/pessoas", { params: { ativo: true } }),
    enabled: canLoad,
  });

  const { data: produtosColhidos = [], isLoading: loadingProdutos } = useQuery<ProdutoColhido[]>({
    queryKey: ["comercializacoes-produtos-colhidos"],
    queryFn: () => apiFetch("/agricola/produtos-colhidos/", { params: { status: "ARMAZENADO" } }),
    enabled: canLoad,
  });

  const transitionMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiFetch(`/financeiro/comercializacoes/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => {
      toast.success("Status atualizado.");
      queryClient.invalidateQueries({ queryKey: ["comercializacoes"] });
    },
    onError: (error: Error) => toast.error(error.message || "Erro ao atualizar status."),
  });

  const solicitarPesagemMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/financeiro/comercializacoes/${id}/solicitar-pesagem-balanca`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Pesagem solicitada à balança!");
      queryClient.invalidateQueries({ queryKey: ["comercializacoes"] });
    },
    onError: (error: Error) => toast.error(error.message || "Falha ao solicitar pesagem."),
  });

  const commodityById = Object.fromEntries(commodities.map((commodity) => [commodity.id, commodity.nome]));
  const compradorById = Object.fromEntries(pessoas.map((pessoa) => [pessoa.id, pessoa.nome_exibicao]));
  const produtoById = Object.fromEntries(
    produtosColhidos.map((produto) => [
      produto.id,
      `${fmtNumber(produto.peso_liquido_comercial_kg ?? produto.quantidade, 3)} ${produto.unidade}`,
    ])
  );

  const totalVenda = comercializacoes.reduce((acc, item) => acc + Number(item.valor_total || 0), 0);
  const totalAtivas = comercializacoes.filter((item) => !["FINALIZADO", "CANCELADO"].includes(item.status)).length;
  const totalReceitas = comercializacoes.filter((item) => item.receita_id).length;
  const totalConfirmadas = comercializacoes.filter((item) => item.status === "CONFIRMADO").length;

  const columns: ColumnDef<Comercializacao>[] = [
    {
      id: "numero_contrato",
      header: "Contrato",
      accessorKey: "numero_contrato",
      cell: (value: string | null, row) => (
        <div className="flex flex-col">
          <span className="font-medium text-foreground">{value || row.id.slice(0, 8)}</span>
          <span className="text-xs text-muted-foreground">{row.id.slice(0, 8)}</span>
        </div>
      ),
    },
    {
      id: "commodity_id",
      header: "Commodity",
      accessorFn: (row) => commodityById[row.commodity_id] ?? row.commodity_id,
    },
    {
      id: "comprador_id",
      header: "Comprador",
      accessorFn: (row) => compradorById[row.comprador_id] ?? row.comprador_id,
    },
    {
      id: "produto_colhido_id",
      header: "Produto",
      accessorFn: (row) => produtoById[row.produto_colhido_id ?? ""] ?? row.produto_colhido_id ?? "—",
    },
    {
      id: "quantidade",
      header: "Qtd.",
      accessorKey: "quantidade",
      cell: (value: number, row) => `${fmtNumber(value, 3)} ${row.unidade}`,
    },
    {
      id: "valor_total",
      header: "Valor total",
      accessorKey: "valor_total",
      cell: (value: number) => fmtMoney(value),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: (value: string) => <WorkflowStatusBadge status={value} />,
    },
    {
      id: "actions",
      header: "Ações",
      isActionColumn: true,
      exportable: false,
      cell: (_: unknown, row) => (
        <StatusActions
          item={row}
          onTransition={(id, status) => transitionMutation.mutate({ id, status })}
          loading={transitionMutation.isPending}
          onSolicitarPesagem={(id) => solicitarPesagemMutation.mutate(id)}
          solicitandoPesagem={solicitarPesagemMutation.isPending}
        />
      ),
    },
  ];

  const loading = loadingComercializacoes || loadingCommodities || loadingPessoas || loadingProdutos;

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Comercializações"
        description="Fechamento operacional de venda, entrega e liquidação."
        breadcrumbs={[
          { label: "Financeiro", href: "/dashboard/financeiro" },
          { label: "Comercializações" },
        ]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm" className="rounded-sm">
              <Link href="/dashboard/financeiro">Painel financeiro</Link>
            </Button>
            <Button size="sm" className="rounded-sm" onClick={() => setOpen(true)}>
              <Plus className="mr-2 size-4" />
              Nova comercialização
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-blue-500/80">
          <CardContent className="p-5">
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-blue-700/70">Em aberto</p>
            <p className="mt-2 text-2xl font-black">{totalAtivas}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-emerald-500/80">
          <CardContent className="p-5">
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-emerald-700/70">Receitas vinculadas</p>
            <p className="mt-2 text-2xl font-black">{totalReceitas}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500/80">
          <CardContent className="p-5">
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-amber-700/70">Confirmadas</p>
            <p className="mt-2 text-2xl font-black">{totalConfirmadas}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-slate-500/80">
          <CardContent className="p-5">
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-700/70">Valor total</p>
            <p className="mt-2 text-xl font-black">{fmtMoney(totalVenda)}</p>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <Skeleton className="h-80 w-full rounded-sm" />
      ) : (
        <DataTable
          data={comercializacoes}
          columns={columns}
          searchable
          exportable
          exportFileName="comercializacoes"
          emptyMessage="Nenhuma comercialização registrada."
        />
      )}

      <NovaComercializacaoDialog
        open={open}
        onOpenChange={setOpen}
        commodities={commodities}
        pessoas={pessoas}
        produtosColhidos={produtosColhidos}
      />
    </div>
  );
}
