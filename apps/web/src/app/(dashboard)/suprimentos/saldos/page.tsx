"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { 
  Warehouse, Package, AlertTriangle, TrendingUp,
  PieChart, Bell, Settings2, CheckCircle2
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, 
  DialogTrigger, DialogFooter, DialogDescription 
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useState } from "react";

interface Saldo {
  id: string;
  deposito_id: string;
  produto_id: string;
  produto_nome: string;
  deposito_nome: string;
  quantidade_atual: number;
  quantidade_reservada: number;
  quantidade_disponivel: number;
  unidade_medida: string;
  preco_medio: number;
  estoque_minimo: number | null;
  abaixo_minimo: boolean;
  ultima_atualizacao: string;
}

function MinimoDialog({ saldo }: { saldo: Saldo }) {
  const [minimo, setMinimo] = useState(saldo.estoque_minimo?.toString() || "");
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (newMinimo: number) => 
      apiFetch(`/estoque/saldos/${saldo.id}/minimo`, {
        method: "PATCH",
        body: JSON.stringify({ deposito_id: saldo.deposito_id, estoque_minimo: newMinimo }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estoque-saldos"] });
      toast.success("Estoque mínimo atualizado!");
      setOpen(false);
    },
    onError: () => toast.error("Falha ao atualizar estoque mínimo."),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
          <Settings2 className="size-3 text-muted-foreground" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="text-sm font-bold uppercase tracking-tight">Estoque Mínimo</DialogTitle>
          <DialogDescription className="text-xs">
            Defina o limite de segurança para {saldo.produto_nome} no {saldo.deposito_nome}.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase text-muted-foreground">Quantidade Mínima ({saldo.unidade_medida})</label>
            <Input
              type="number"
              value={minimo}
              onChange={(e) => setMinimo(e.target.value)}
              className="h-9 rounded-sm"
              placeholder="Ex: 50.00"
            />
          </div>
        </div>
        <DialogFooter>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => mutation.mutate(parseFloat(minimo))}
            disabled={mutation.isPending}
            className="rounded-sm font-bold uppercase text-[10px]"
          >
            {mutation.isPending ? "Salvando..." : "Salvar Configuração"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface AlertaEstoqueItem {
  id: string;
  produto_id: string;
  deposito_id: string;
  produto_nome: string;
  deposito_nome: string;
  quantidade_atual: number;
  estoque_minimo: number;
  unidade_medida: string;
  quantidade_sugerida: number;
}

function SolicitarCompraButton({ alerta }: { alerta: AlertaEstoqueItem }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => 
      apiFetch(`/compras/solicitacoes`, {
        method: "POST",
        body: JSON.stringify({
          item_id: alerta.produto_id,
          deposito_id: alerta.deposito_id,
          quantidade_solicitada: alerta.quantidade_sugerida,
          unidade: alerta.unidade_medida,
          origem: "REPOSICAO_ESTOQUE",
          origem_id: alerta.id
        }),
      }),
    onSuccess: () => {
      toast.success(`Solicitação de compra para ${alerta.produto_nome} criada!`);
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
    },
    onError: () => toast.error("Falha ao criar solicitação de compra."),
  });

  return (
    <Button 
      variant="outline" 
      size="sm" 
      className="h-7 text-[9px] font-bold uppercase rounded-sm border-orange-300 text-orange-700 hover:bg-orange-100 shrink-0 ml-2"
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      <CheckCircle2 className="size-3 mr-1" />
      {mutation.isPending ? "Processando..." : "Solicitar Compra"}
    </Button>
  );
}

export default function SaldosPage() {
  const { activeFazendaId } = useAppStore();
  const fazendaParam = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

  const { data: saldos = [], isLoading } = useQuery<Saldo[]>({
    queryKey: ["estoque-saldos", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/saldos${fazendaParam}`),
  });

  const { data: alertas = [] } = useQuery<AlertaEstoqueItem[]>({
    queryKey: ["estoque-alertas", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/alertas-reposicao`),
  });

  const totalValor = saldos.reduce((acc, s) => acc + s.quantidade_atual * (s.preco_medio || 0), 0);
  const totalItens = saldos.length;
  const itensCriticos = saldos.filter(s => s.abaixo_minimo).length;
  
  // Agrupar por produto
  const saldosPorProduto = saldos.reduce((acc, s) => {
    if (!acc[s.produto_id]) {
      acc[s.produto_id] = {
        nome: s.produto_nome,
        total: 0,
        unidade: s.unidade_medida,
        depositos: []
      };
    }
    acc[s.produto_id].total += s.quantidade_atual;
    acc[s.produto_id].depositos.push(s);
    return acc;
  }, {} as Record<string, { nome: string, total: number, unidade: string, depositos: Saldo[] }>);

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Saldos de Estoque"
        description="Visão detalhada do inventário disponível em todos os depósitos."
        icon={<Warehouse className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Saldos de Estoque" }
        ]}
      />

      {/* Alertas de Reposição */}
      {itensCriticos > 0 && (
        <Card className="rounded-sm border-l-4 border-l-orange-500 shadow-md bg-orange-50/20 overflow-hidden animate-in fade-in slide-in-from-top-4">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 p-2 bg-orange-100 rounded-full">
                <Bell className="size-4 text-orange-600 animate-bounce" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-black text-orange-800 uppercase tracking-tight">Alertas de Reposição Necessária</h4>
                <p className="text-xs text-orange-700/80 mb-3">Há {itensCriticos} itens operando abaixo do estoque mínimo de segurança.</p>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {alertas.slice(0, 3).map(s => (
                    <div key={s.id} className="flex items-center justify-between p-2 bg-white/50 rounded-sm border border-orange-200">
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-black uppercase truncate">{s.produto_nome}</p>
                        <p className="text-[9px] text-muted-foreground uppercase">{s.deposito_nome}</p>
                        <p className="text-[8px] text-orange-600 font-bold uppercase tracking-tighter">Sugestão: +{s.quantidade_sugerida} {s.unidade_medida}</p>
                      </div>
                      <div className="text-right flex items-center gap-2">
                        <p className="text-xs font-black text-red-600">{s.quantidade_atual.toFixed(1)} {s.unidade_medida}</p>
                        <SolicitarCompraButton alerta={s} />
                      </div>
                    </div>
                  ))}
                  {itensCriticos > 3 && (
                    <div className="flex items-center justify-center p-2 border border-dashed border-orange-300 rounded-sm">
                      <span className="text-[9px] font-bold text-orange-600 uppercase">+{itensCriticos - 3} outros alertas</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Section */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-sm border-l-4 border-l-emerald-500 shadow-sm bg-emerald-50/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Valor Total</p>
                <p className="text-2xl font-black text-emerald-700">R$ {totalValor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</p>
              </div>
              <TrendingUp className="size-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="rounded-sm border-l-4 border-l-blue-500 shadow-sm bg-blue-50/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Posições Ativas</p>
                <p className="text-2xl font-black text-blue-700">{totalItens}</p>
              </div>
              <Package className="size-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card className={cn(
          "rounded-sm border-l-4 shadow-sm",
          itensCriticos > 0 ? "border-l-red-500 bg-red-50/10" : "border-l-green-500 bg-green-50/10"
        )}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Itens Críticos</p>
                <p className={cn("text-2xl font-black", itensCriticos > 0 ? "text-red-600" : "text-green-600")}>
                  {itensCriticos}
                </p>
              </div>
              <AlertTriangle className={cn("size-8", itensCriticos > 0 ? "text-red-200" : "text-green-200")} />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-sm border-l-4 border-l-primary shadow-sm bg-primary/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Capacidade Total</p>
                <p className="text-2xl font-black text-primary">82%</p>
              </div>
              <Warehouse className="size-8 text-primary/20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content: Grouped by Product */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Object.values(saldosPorProduto).map((item) => (
          <Card key={item.nome} className="rounded-sm shadow-sm overflow-hidden border-t-2 border-t-primary/20">
            <CardHeader className="p-4 pb-2 bg-muted/20">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-sm font-bold uppercase tracking-tight truncate" title={item.nome}>{item.nome}</CardTitle>
                  <CardDescription className="text-[10px] uppercase font-medium">{item.depositos.length} depósitos</CardDescription>
                </div>
                <Badge variant="outline" className="text-[10px] rounded-sm font-bold bg-white shrink-0 ml-2">{item.unidade}</Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-4 space-y-4">
              <div className="flex items-end justify-between">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-muted-foreground uppercase">Saldo Consolidado</span>
                  <p className="text-3xl font-black tabular-nums">{item.total.toFixed(2)}</p>
                </div>
                {item.depositos.some(s => s.abaixo_minimo) && (
                  <Badge className="bg-red-500 text-white border-0 text-[9px] font-bold uppercase py-0.5 animate-pulse">REPOR</Badge>
                )}
              </div>

              <div className="space-y-2">
                {item.depositos.map((dep) => (
                    <div key={dep.deposito_id} className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <div className="flex items-center gap-1 min-w-0">
                          <span className="text-muted-foreground font-medium truncate max-w-[120px]">{dep.deposito_nome}</span>
                          <MinimoDialog saldo={dep} />
                        </div>
                        <span className="font-bold tabular-nums">
                          {dep.quantidade_disponivel.toFixed(2)} 
                          {dep.quantidade_reservada > 0 && <span className="text-[9px] text-purple-600 ml-1">(-{dep.quantidade_reservada.toFixed(2)} R)</span>}
                        </span>
                      </div>
                      <Progress 
                        value={dep.estoque_minimo ? Math.min(100, (dep.quantidade_disponivel / (dep.estoque_minimo * 2)) * 100) : 100} 
                        className={cn("h-1", dep.abaixo_minimo ? "bg-red-100 [&>div]:bg-red-500" : "bg-emerald-100 [&>div]:bg-emerald-500")}
                      />
                      {dep.estoque_minimo && (
                        <div className="flex justify-end">
                          <span className="text-[8px] text-muted-foreground font-bold uppercase tracking-tighter">Mínimo: {dep.estoque_minimo} {dep.unidade_medida}</span>
                        </div>
                      )}
                    </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
        
        {Object.values(saldosPorProduto).length === 0 && (
          <div className="col-span-full py-20 text-center border-2 border-dashed rounded-sm bg-muted/20">
            <Package className="size-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm text-muted-foreground">Nenhum saldo encontrado para esta unidade.</p>
          </div>
        )}
      </div>
      
      {/* Visual Analytics Placeholder */}
      <Card className="rounded-sm shadow-sm border-dashed border-2">
        <CardContent className="p-12 flex flex-col items-center justify-center text-center space-y-4">
          <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center">
            <PieChart className="size-8 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-bold uppercase tracking-tight">Análise Estratégica de Estoque</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Em breve: Visualize a distribuição de insumos em tempo real no mapa da sua propriedade e receba sugestões automáticas de compra.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
