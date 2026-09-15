"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { Plus, Layers, PackageSearch, AlertTriangle, X, Save } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";
import { parseLocaleNumber } from "@/lib/utils";

interface Lote {
  id: string;
  produto_id: string;
  deposito_id: string;
  numero_lote: string;
  data_fabricacao: string | null;
  data_validade: string | null;
  quantidade_inicial: number;
  quantidade_atual: number;
  custo_unitario: number;
  nota_fiscal_ref: string | null;
  status: string;
  created_at: string;
  esgotado_por_estorno?: boolean;
}

interface Produto { id: string; nome: string; unidade_medida: string; }
interface Deposito { id: string; nome: string; unidade_produtiva_id: string; }

const STATUS_COLORS: Record<string, string> = {
  ATIVO: "bg-green-100 text-green-700 border-green-200",
  VENCIDO: "bg-red-100 text-red-700 border-red-200",
  ESGOTADO: "bg-gray-100 text-gray-600 border-gray-200",
  BLOQUEADO: "bg-yellow-100 text-yellow-700 border-yellow-200",
};

function NovoLoteDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { activeFazendaId: fazendaAtiva } = useAppStore();
  const [form, setForm] = useState({
    produto_id: "", deposito_id: "", numero_lote: "",
    data_fabricacao: "", data_validade: "",
    quantidade_inicial: "", custo_unitario: "0", nota_fiscal_ref: "",
  });

  const { data: produtos = [] } = useQuery<Produto[]>({
    queryKey: ["estoque-produtos"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
  });
  const { data: depositos = [] } = useQuery<Deposito[]>({
    queryKey: ["estoque-depositos", fazendaAtiva],
    queryFn: () => apiFetch(`/estoque/depositos${fazendaAtiva ? `?unidade_produtiva_id=${fazendaAtiva}` : ""}`),
  });

  const mutation = useMutation({
    mutationFn: (payload: object) => apiFetch("/estoque/lotes", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Lote cadastrado!"); qc.invalidateQueries({ queryKey: ["estoque-lotes"] }); onClose(); },
    onError: () => toast.error("Erro ao cadastrar lote."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_id || !form.numero_lote || !form.quantidade_inicial)
      return toast.error("Preencha os campos obrigatórios.");
    mutation.mutate({
      ...form,
      quantidade_inicial: parseLocaleNumber(form.quantidade_inicial),
      custo_unitario: parseLocaleNumber(form.custo_unitario, 0),
      data_fabricacao: form.data_fabricacao || null,
      data_validade: form.data_validade || null,
      nota_fiscal_ref: form.nota_fiscal_ref || null,
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <PackageSearch className="size-4 text-primary" />
              </div>
              <div className="space-y-0.5">
                <DialogTitle>Novo Lote</DialogTitle>
                <DialogDescription className="text-xs">
                  Cadastre um lote para manter a rastreabilidade de validade, saldo e origem.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <DialogBody className="grid gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label>Produto *</Label>
                <Select value={form.produto_id} onValueChange={v => setForm(f => ({ ...f, produto_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
                  <SelectContent>{produtos.map(p => <SelectItem key={p.id} value={p.id}>{p.nome}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="col-span-2 flex flex-col gap-1.5">
                <Label>Depósito *</Label>
                <Select value={form.deposito_id} onValueChange={v => setForm(f => ({ ...f, deposito_id: v }))}>
                  <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
                  <SelectContent>{depositos.map(d => <SelectItem key={d.id} value={d.id}>{d.nome}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Nº do Lote *</Label>
                <Input value={form.numero_lote} onChange={e => setForm(f => ({ ...f, numero_lote: e.target.value }))} placeholder="LOT-2024-001" />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>NF de Referência</Label>
                <Input value={form.nota_fiscal_ref} onChange={e => setForm(f => ({ ...f, nota_fiscal_ref: e.target.value }))} placeholder="000123" />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Data de Fabricação</Label>
                <Input type="date" value={form.data_fabricacao} onChange={e => setForm(f => ({ ...f, data_fabricacao: e.target.value }))} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Data de Validade</Label>
                <Input type="date" value={form.data_validade} onChange={e => setForm(f => ({ ...f, data_validade: e.target.value }))} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Quantidade Inicial *</Label>
                <Input type="number" min="0.001" step="0.001" value={form.quantidade_inicial} onChange={e => setForm(f => ({ ...f, quantidade_inicial: e.target.value }))} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Custo Unitário (R$)</Label>
                <Input type="number" min="0" step="0.01" value={form.custo_unitario} onChange={e => setForm(f => ({ ...f, custo_unitario: e.target.value }))} />
              </div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              <X data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button type="submit" variant="default" disabled={mutation.isPending}>
              <Save data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Salvando..." : "Cadastrar Lote"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function LoteCard({ lote, produtos, depositos }: { lote: Lote; produtos: Produto[]; depositos: Deposito[] }) {
  const produto = produtos.find(p => p.id === lote.produto_id);
  const deposito = depositos.find(d => d.id === lote.deposito_id);
  const pct = lote.quantidade_inicial > 0 ? (lote.quantidade_atual / lote.quantidade_inicial) * 100 : 0;
  const vencendo = lote.data_validade && new Date(lote.data_validade) <= new Date(Date.now() + 30 * 86400000);

  return (
    <Card className={`border-t-2 ${
      lote.status === "ATIVO" ? "border-t-green-500/70"
      : lote.status === "VENCIDO" ? "border-t-red-500/70"
      : lote.status === "ESGOTADO" && lote.esgotado_por_estorno ? "border-t-amber-400/70"
      : "border-t-gray-300"
    }`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-sm font-semibold">{produto?.nome ?? "—"}</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">{deposito?.nome ?? "—"}</p>
          </div>
          {lote.status === "ESGOTADO" && lote.esgotado_por_estorno ? (
            <Badge className="text-[10px] border bg-amber-100 text-amber-700 border-amber-200">ESTORNADO</Badge>
          ) : (
            <Badge className={`text-[10px] border ${STATUS_COLORS[lote.status] ?? ""}`}>{lote.status}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Lote</span>
          <span className="font-mono font-medium">{lote.numero_lote}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Saldo</span>
          <span>
            {lote.quantidade_atual.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })} / {lote.quantidade_inicial.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })} {produto?.unidade_medida}
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-1.5">
          <div className="bg-primary h-1.5 rounded-full transition-all" style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
        {lote.data_validade && (
          <div className={`flex justify-between ${vencendo ? "text-orange-600 font-medium" : ""}`}>
            <span className="text-muted-foreground flex items-center gap-1">
              {vencendo && <AlertTriangle className="size-3" />}Validade
            </span>
            <span>{new Date(lote.data_validade).toLocaleDateString("pt-BR")}</span>
          </div>
        )}
        {lote.nota_fiscal_ref && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">NF</span>
            <span>{lote.nota_fiscal_ref}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function LotesPage() {
  const { activeFazendaId: fazendaAtiva } = useAppStore();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const { data: lotes = [] } = useQuery<Lote[]>({
    queryKey: ["estoque-lotes", fazendaAtiva],
    queryFn: () => apiFetch("/estoque/lotes?apenas_ativos=false"),
  });
  const { data: alertas = [] } = useQuery<Lote[]>({
    queryKey: ["estoque-lotes-alertas"],
    queryFn: () => apiFetch("/estoque/lotes/alertas-validade?dias=30"),
  });
  const { data: produtos = [] } = useQuery<Produto[]>({
    queryKey: ["estoque-produtos"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
  });
  const { data: depositos = [] } = useQuery<Deposito[]>({
    queryKey: ["estoque-depositos", fazendaAtiva],
    queryFn: () => apiFetch(`/estoque/depositos${fazendaAtiva ? `?unidade_produtiva_id=${fazendaAtiva}` : ""}`),
  });

  const filtered = lotes.filter(l => {
    const nome = produtos.find(p => p.id === l.produto_id)?.nome ?? "";
    return nome.toLowerCase().includes(search.toLowerCase()) || l.numero_lote.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Lotes de Estoque"
        description="Rastreabilidade por lote — validade, quantidade e origem de cada item."
        icon={<Layers className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Lotes" },
        ]}
        actions={
          <Button size="sm" variant="default" onClick={() => setOpen(true)}>
            <Plus data-icon="inline-start" className="size-4" /> Novo Lote
          </Button>
        }
      />

      {alertas.length > 0 && (
        <div className="flex items-center gap-3 rounded-sm border border-orange-200 bg-orange-50 p-4 text-sm text-orange-700">
          <AlertTriangle className="size-4 shrink-0" />
          <span><strong>{alertas.length} lote(s)</strong> vencendo nos próximos 30 dias.</span>
        </div>
      )}

      <Tabs defaultValue="ativos">
        <div className="flex items-center justify-between gap-4">
          <TabsList>
            <TabsTrigger value="todos">Todos ({lotes.length})</TabsTrigger>
            <TabsTrigger value="ativos">Ativos ({lotes.filter(l => l.status === "ATIVO").length})</TabsTrigger>
            <TabsTrigger value="vencidos">Vencidos ({lotes.filter(l => l.status === "VENCIDO").length})</TabsTrigger>
          </TabsList>
          <Input
            placeholder="Buscar por produto ou nº lote..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="max-w-xs"
          />
        </div>

        {(["todos", "ativos", "vencidos"] as const).map(tab => (
          <TabsContent key={tab} value={tab} className="mt-4">
            {(() => {
              const items = tab === "ativos" ? filtered.filter(l => l.status === "ATIVO")
                : tab === "vencidos" ? filtered.filter(l => l.status === "VENCIDO")
                : filtered;
              if (!items.length)
                return (
                  <EmptyState
                    icon={<PackageSearch />}
                    title="Nenhum lote encontrado"
                    description="Cadastre um novo lote para rastrear validade, saldo e origem dos materiais."
                    action={{ label: "Novo Lote", onClick: () => setOpen(true) }}
                    className="rounded-sm border border-dashed bg-muted/20"
                  />
                );
              return (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {items.map(l => <LoteCard key={l.id} lote={l} produtos={produtos} depositos={depositos} />)}
                </div>
              );
            })()}
          </TabsContent>
        ))}
      </Tabs>

      {open && <NovoLoteDialog onClose={() => setOpen(false)} />}
    </div>
  );
}
