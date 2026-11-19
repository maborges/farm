"use client";

import { useMemo, useState } from "react";
import { EntradaDialog, SaidaDialog, TransferenciaDialog, AjusteDialog, NovoProdutoDialog, NovoDepositoDialog, ReservaDialog, ReservaStatusBadge, ReservaConsumirButton, ReservaCancelarButton } from "./_components/EstoqueDialogs";
import { ContagemEstoqueTab } from "./_components/ContagemEstoqueTab";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { usePermission } from "@/hooks/use-permission";
import {
  Pickaxe, Package, History, Plus, Search, Warehouse,
  AlertTriangle, ArrowDownToLine, ArrowUpFromLine, RefreshCw,
  ArrowRightLeft, SlidersHorizontal, ClipboardList, Filter,
  ChevronDown, X, TrendingDown, TrendingUp, DollarSign,
  Lock, Unlock, CheckCircle2, Ban, XCircle, Save, FileSpreadsheet,
  MoreHorizontal, Pencil, Trash2, ClipboardCheck,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogBody,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Saldo {
  id: string;
  produto_id: string;
  deposito_id: string;
  produto_nome: string;
  deposito_nome: string;
  quantidade_atual: number;
  quantidade_reservada: number;
  quantidade_disponivel: number;
  unidade_medida: string;
  preco_medio: number;
  abaixo_minimo: boolean;
  ultima_atualizacao: string;
}

interface Reserva {
  id: string;
  produto_id: string;
  deposito_id: string;
  criado_por_id: string | null;
  quantidade: number;
  motivo: string;
  referencia_tipo: string | null;
  referencia_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface Alerta {
  produto_id: string;
  produto_nome: string;
  deposito_nome: string;
  quantidade_atual: number;
  estoque_minimo: number;
  unidade_medida: string;
  deficit: number;
}

interface Produto {
  id: string;
  nome: string;
  tipo: string;
  unidade_medida: string;
  estoque_minimo: number;
  preco_medio: number;
  ativo: boolean;
}

interface Deposito {
  id: string;
  unidade_produtiva_id: string;
  nome: string;
  tipo: string;
  localizacao_desc?: string | null;
  ativo: boolean;
}

interface Movimentacao {
  id: string;
  tipo: string;
  origem_tipo?: string | null;
  origem_id?: string | null;
  produto_nome: string;
  deposito_nome?: string;
  deposito_origem_nome?: string;
  deposito_destino_nome?: string;
  quantidade: number;
  custo_unitario: number;
  motivo: string;
  usuario_nome?: string;
  data_movimentacao?: string | null;
  created_at?: string | null;
}

const TIPO_MOV_LABEL: Record<string, { label: string; color: string }> = {
  ENTRADA: { label: "Entrada", color: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/20" },
  SAIDA: { label: "Saída", color: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/20" },
  TRANSFERENCIA: { label: "Transferência", color: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/20" },
  AJUSTE: { label: "Ajuste", color: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/20" },
  SALDO_INICIAL: { label: "Saldo inicial", color: "bg-teal-500/15 text-teal-700 dark:text-teal-300 border-teal-500/20" },
  DEVOLUCAO: { label: "Devolução", color: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/20" },
};

const FILTROS_TIPO_MOV = [
  { value: "TODOS", label: "Todos os tipos" },
  { value: "ENTRADA", label: "Entradas" },
  { value: "SAIDA", label: "Saídas" },
  { value: "TRANSFERENCIA", label: "Transferências" },
  { value: "AJUSTE", label: "Ajustes" },
  { value: "SALDO_INICIAL", label: "Saldo inicial" },
  { value: "DEVOLUCAO", label: "Devoluções" },
];

function normalizarFiltroTipoMov(value: string | null) {
  return FILTROS_TIPO_MOV.some(tipo => tipo.value === value) ? value : "TODOS";
}

const MOTIVOS_SAIDA = [
  "Consumo na lavoura",
  "Abastecimento de máquina",
  "Ordem de serviço",
  "Requisição interna",
  "Descarte / vencido",
  "Transferência para terceiros",
  "Outro",
];

const MOTIVOS_AJUSTE = [
  "Inventário físico",
  "Erro de lançamento",
  "Perda / quebra",
  "Sobra de inventário",
  "Recebimento não registrado",
  "Outro",
];

function formatDateTimePtBr(value?: string | null) {
  if (!value) {
    return { date: "—", time: "" };
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { date: "—", time: "" };
  }

  return {
    date: date.toLocaleDateString("pt-BR"),
    time: date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
  };
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export function EstoqueClient({ initialData }: { initialData: any }) {
  const searchParams = useSearchParams();
  const { activeFazendaId } = useAppStore();
  const canViewImplantacao = usePermission("estoque:implantacao_assistida:view");
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [histSearch, setHistSearch] = useState("");
  const [histTipo, setHistTipo] = useState(() => normalizarFiltroTipoMov(searchParams.get("tipo")));
  const initialTab = searchParams.get("aba") || "posicao";
  const origemTipoFiltro = searchParams.get("origem_tipo");
  const origemIdFiltro = searchParams.get("origem_id");
  const [dialog, setDialog] = useState<
    "entrada" | "saida" | "transferencia" | "ajuste" | "produto" | "deposito" | "reserva" | null
  >(null);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [depositoEmEdicao, setDepositoEmEdicao] = useState<Deposito | null>(null);
  const [depositoParaInativar, setDepositoParaInativar] = useState<Deposito | null>(null);

  const fazendaParam = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";

  const { data: saldos = [], isLoading: loadingSaldos } = useQuery<Saldo[]>({
    queryKey: ["estoque-saldos", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/saldos${fazendaParam}`),
    initialData: initialData.saldos,
  });

  const { data: alertas = [] } = useQuery<Alerta[]>({
    queryKey: ["estoque-alertas", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/alertas${fazendaParam}`),
    initialData: initialData.alertas,
  });

  const { data: produtos = [] } = useQuery<Produto[]>({
    queryKey: ["estoque-produtos"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
    initialData: initialData.produtos,
  });

  const { data: depositos = [] } = useQuery<Deposito[]>({
    queryKey: ["estoque-depositos", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/depositos${fazendaParam}`),
    initialData: initialData.depositos,
  });

  const { data: reservas = [], isLoading: loadingReservas } = useQuery<Reserva[]>({
    queryKey: ["estoque-reservas", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/reservas?status=`),
    initialData: initialData.reservas,
  });

  const { data: movimentacoes = [], isLoading: loadingMov } = useQuery<Movimentacao[]>({
    queryKey: ["estoque-movimentacoes", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/movimentacoes${fazendaParam}&limit=200`),
    initialData: initialData.movimentacoes,
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["estoque-saldos"] });
    queryClient.invalidateQueries({ queryKey: ["estoque-alertas"] });
    queryClient.invalidateQueries({ queryKey: ["estoque-movimentacoes"] });
    queryClient.invalidateQueries({ queryKey: ["estoque-reservas"] });
    queryClient.invalidateQueries({ queryKey: ["estoque-depositos"] });
  };

  const inativarDepositoMutation = useMutation({
    mutationFn: (depositoId: string) =>
      apiFetch(`/estoque/depositos/${depositoId}`, {
        method: "PATCH",
        body: JSON.stringify({ ativo: false }),
      }),
    onSuccess: () => {
      toast.success("Depósito inativado.");
      invalidateAll();
      setDepositoParaInativar(null);
    },
    onError: () => toast.error("Erro ao inativar depósito."),
  });

  const reservasAtivas = reservas.filter(r => r.status === "ATIVA");

  const saldosFiltrados = saldos.filter(s =>
    s.produto_nome.toLowerCase().includes(search.toLowerCase()) ||
    s.deposito_nome.toLowerCase().includes(search.toLowerCase())
  );

  const movFiltradas = movimentacoes.filter(m => {
    const matchTipo = histTipo === "TODOS" || m.tipo === histTipo;
    const matchSearch = m.produto_nome.toLowerCase().includes(histSearch.toLowerCase());
    const matchOrigemTipo = !origemTipoFiltro || m.origem_tipo === origemTipoFiltro;
    const matchOrigemId = !origemIdFiltro || m.origem_id === origemIdFiltro;
    return matchTipo && matchSearch && matchOrigemTipo && matchOrigemId;
  });

  const filtroImplantacaoAtivo = useMemo(
    () => origemTipoFiltro === "IMPLANTACAO" && Boolean(origemIdFiltro),
    [origemIdFiltro, origemTipoFiltro],
  );

  const totalValorEstoque = saldos.reduce(
    (acc, s) => acc + s.quantidade_atual * (s.preco_medio ?? 0),
    0
  );

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Almoxarifado & Estoque"
        description="Entradas, saídas, transferências, ajustes e inventário físico."
        icon={<Warehouse className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Estoque" },
        ]}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" size="sm" onClick={() => setDialog("produto")}>
              <Plus data-icon="inline-start" size={14} /> Produto
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDialog("deposito")}>
              <Plus data-icon="inline-start" size={14} /> Depósito
            </Button>
            <Button variant="outline" size="sm" asChild disabled={!canViewImplantacao}>
              <Link href="/suprimentos/estoque/implantacao-assistida">
                <FileSpreadsheet data-icon="inline-start" size={14} /> Implantação Assistida
              </Link>
            </Button>
            <Separator orientation="vertical" className="h-6 hidden sm:block" />
            <Button variant="outline" size="sm" onClick={() => setDialog("reserva")}>
              <Lock data-icon="inline-start" size={14} /> Reservar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDialog("transferencia")}>
              <ArrowRightLeft data-icon="inline-start" size={14} /> Transferir
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDialog("ajuste")}>
              <SlidersHorizontal data-icon="inline-start" size={14} /> Ajustar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDialog("saida")}>
              <ArrowUpFromLine data-icon="inline-start" size={14} /> Saída
            </Button>
            <Button size="sm" onClick={() => setDialog("entrada")}>
              <ArrowDownToLine data-icon="inline-start" size={14} /> Entrada
            </Button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="rounded-sm border border-border/70 shadow-xs">
          <CardContent className="p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Itens em Estoque</p>
            <p className="text-2xl font-bold mt-1 tabular-nums">{saldos.length}</p>
            <p className="text-xs text-muted-foreground mt-1">posições ativas</p>
          </CardContent>
        </Card>
        <Card className="rounded-sm border border-border/70 shadow-xs">
          <CardContent className="p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Valor Total</p>
            <p className="text-2xl font-bold mt-1 tabular-nums text-foreground">
              {totalValorEstoque > 0
                ? `R$ ${(totalValorEstoque / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}k`
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">custo médio ponderado</p>
          </CardContent>
        </Card>
        <Card
          variant={alertas.length > 0 ? "destructive" : "default"}
          className="shadow-xs transition-colors"
        >
          <CardContent className="p-4">
            <p className={cn(
              "text-[10px] font-semibold uppercase tracking-wider",
              alertas.length > 0 ? "text-card-description" : "text-muted-foreground"
            )}>Abaixo do Mínimo</p>
            <p className={cn(
              "text-2xl font-bold mt-1 tabular-nums",
              alertas.length > 0 ? "text-card-title" : "text-foreground"
            )}>
              {alertas.length}
            </p>
            <p className={cn(
              "text-xs mt-1",
              alertas.length > 0 ? "text-card-description" : "text-muted-foreground"
            )}>
              {alertas.length === 0 ? "estoque saudável" : "itens para repor"}
            </p>
          </CardContent>
        </Card>
        <Card className="rounded-sm border border-border/70 shadow-xs">
          <CardContent className="p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Depósitos Ativos</p>
            <p className="text-2xl font-bold mt-1 tabular-nums">{depositos.filter(d => d.ativo).length}</p>
            <p className="text-xs text-muted-foreground mt-1">locais de armazenagem</p>
          </CardContent>
        </Card>
      </div>

      {/* Alerta de reposição */}
      {alertas.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertDescription className="text-xs leading-relaxed">
            <strong className="font-semibold text-alert-title">{alertas.length} produto(s)</strong> abaixo do estoque mínimo:{" "}
            {alertas.slice(0, 3).map(a => a.produto_nome).join(", ")}
            {alertas.length > 3 && ` e mais ${alertas.length - 3}...`}
          </AlertDescription>
        </Alert>
      )}

      {/* Tabs principais */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="posicao" className="gap-1.5">
            <Package size={14} /> Posição
            {alertas.length > 0 && (
              <Badge variant="secondary" className="bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/20 text-[9px] h-4 px-1.5 ml-1 rounded-sm">
                {alertas.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="reservas" className="gap-1.5">
            <Lock size={14} /> Reservas
            {reservasAtivas.length > 0 && (
              <Badge variant="secondary" className="bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/20 text-[9px] h-4 px-1.5 ml-1 rounded-sm">
                {reservasAtivas.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="historico" className="gap-1.5">
            <History size={14} /> Histórico
          </TabsTrigger>
          <TabsTrigger value="produtos" className="gap-1.5">
            <ClipboardList size={14} /> Produtos
          </TabsTrigger>
          <TabsTrigger value="depositos" className="gap-1.5">
            <Warehouse size={14} /> Depósitos
          </TabsTrigger>
          <TabsTrigger value="contagem" className="gap-1.5">
            <ClipboardCheck size={14} /> Contagem
          </TabsTrigger>
        </TabsList>

        {/* ── POSIÇÃO ─────────────────────────────────────────────────────────── */}
        <TabsContent value="posicao" className="mt-4">
          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base">Posição de Estoque</CardTitle>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar produto ou depósito..."
                    className="pl-9 w-64 h-8 text-sm"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs">
                    <TableHead>Produto</TableHead>
                    <TableHead>Depósito</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Reservado</TableHead>
                    <TableHead className="text-right">Disponível</TableHead>
                    <TableHead>U.M.</TableHead>
                    <TableHead className="text-right">Preço Médio</TableHead>
                    <TableHead className="text-right">Valor Total</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loadingSaldos ? (
                    Array(5).fill(0).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={7}><Skeleton className="h-7 w-full" /></TableCell>
                      </TableRow>
                    ))
                  ) : saldosFiltrados.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-16 text-muted-foreground text-sm">
                        Nenhum item com saldo. Registre uma entrada de material para começar.
                      </TableCell>
                    </TableRow>
                  ) : (
                    saldosFiltrados.map(s => (
                      <TableRow key={s.id} className={s.abaixo_minimo ? "bg-rose-500/[0.04] hover:bg-rose-500/[0.08]" : ""}>
                        <TableCell className="font-medium text-sm py-2.5">{s.produto_nome}</TableCell>
                        <TableCell className="text-muted-foreground text-xs">{s.deposito_nome}</TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground tabular-nums">
                          {s.quantidade_atual.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-xs">
                          {s.quantidade_reservada > 0 ? (
                            <span className="text-purple-600 dark:text-purple-400 font-medium flex items-center justify-end gap-1">
                              <Lock size={10} />{s.quantidade_reservada.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className={cn(
                          "text-right font-bold tabular-nums text-sm",
                          s.abaixo_minimo ? "text-rose-600 dark:text-rose-400" : "text-foreground"
                        )}>
                          {s.quantidade_disponivel.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{s.unidade_medida}</TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground tabular-nums">
                          {s.preco_medio > 0 ? `R$ ${s.preco_medio.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                        </TableCell>
                        <TableCell className="text-right text-xs font-medium tabular-nums">
                          {s.preco_medio > 0
                            ? `R$ ${(s.quantidade_atual * s.preco_medio).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                            : "—"}
                        </TableCell>
                        <TableCell>
                          {s.abaixo_minimo ? (
                            <Badge variant="outline" className="bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20 text-[10px] gap-1 font-medium rounded-sm">
                              <AlertTriangle size={9} /> Repor
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 text-[10px] font-medium rounded-sm">
                              OK
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── RESERVAS ───────────────────────────────────────────────────────── */}
        <TabsContent value="reservas" className="mt-4">
          <Card className="shadow-sm">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Reservas de Estoque</CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Saldo bloqueado para uso futuro garantido. Não pode ser consumido por outras saídas.
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => setDialog("reserva")}>
                <Lock data-icon="inline-start" size={12} /> Nova Reserva
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs">
                    <TableHead>Produto</TableHead>
                    <TableHead>Depósito</TableHead>
                    <TableHead className="text-right">Quantidade</TableHead>
                    <TableHead>Referência</TableHead>
                    <TableHead>Motivo</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Data</TableHead>
                    <TableHead className="text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loadingReservas ? (
                    Array(3).fill(0).map((_, i) => (
                      <TableRow key={i}><TableCell colSpan={8}><Skeleton className="h-7 w-full" /></TableCell></TableRow>
                    ))
                  ) : reservas.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-16 text-muted-foreground text-sm">
                        Nenhuma reserva cadastrada.
                      </TableCell>
                    </TableRow>
                  ) : (
                    reservas.map(r => {
                      const produto = saldos.find(s => s.produto_id === r.produto_id);
                      const deposito = depositos.find(d => d.id === r.deposito_id);
                      return (
                        <TableRow key={r.id} className={r.status !== "ATIVA" ? "opacity-60" : ""}>
                          <TableCell className="font-medium text-sm">{produto?.produto_nome ?? r.produto_id.slice(0, 8)}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{deposito?.nome ?? "—"}</TableCell>
                          <TableCell className="text-right font-bold tabular-nums text-sm text-purple-600 dark:text-purple-400">
                            {r.quantidade.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {r.referencia_tipo ?? "—"}
                          </TableCell>
                          <TableCell className="text-xs max-w-40 truncate" title={r.motivo}>{r.motivo}</TableCell>
                          <TableCell>
                            <ReservaStatusBadge status={r.status} />
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(r.created_at).toLocaleDateString("pt-BR")}
                          </TableCell>
                          <TableCell className="text-right">
                            {r.status === "ATIVA" && (
                              <div className="flex justify-end gap-1">
                                <ReservaConsumirButton reservaId={r.id} onSuccess={invalidateAll} />
                                <ReservaCancelarButton reservaId={r.id} onSuccess={invalidateAll} />
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── HISTÓRICO ──────────────────────────────────────────────────────── */}
        <TabsContent value="historico" className="mt-4">
          {filtroImplantacaoAtivo ? (
            <Alert variant="info" className="mb-4">
              <History />
              <AlertDescription>
                Mostrando apenas movimentações da implantação assistida desta sessão.
              </AlertDescription>
            </Alert>
          ) : null}
          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <CardTitle className="text-base">Histórico de Movimentações</CardTitle>
                <div className="flex items-center gap-2">
                  <Select value={histTipo} onValueChange={setHistTipo}>
                    <SelectTrigger className="h-8 text-xs w-[180px]">
                      <div className="flex items-center gap-2 truncate">
                        <Filter size={12} className="shrink-0 text-muted-foreground" />
                        <span className="truncate"><SelectValue /></span>
                      </div>
                    </SelectTrigger>
                    <SelectContent>
                      {FILTROS_TIPO_MOV.map(tipo => (
                        <SelectItem key={tipo.value} value={tipo.value}>
                          {tipo.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Buscar produto..."
                      className="pl-8 h-8 w-48 text-xs"
                      value={histSearch}
                      onChange={e => setHistSearch(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs">
                    <TableHead>Data</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead>Produto</TableHead>
                    <TableHead>Origem / Destino</TableHead>
                    <TableHead className="text-right">Qtd</TableHead>
                    <TableHead className="text-right">Custo Unit.</TableHead>
                    <TableHead>Motivo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loadingMov ? (
                    Array(6).fill(0).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={7}><Skeleton className="h-7 w-full" /></TableCell>
                      </TableRow>
                    ))
                  ) : movFiltradas.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-16 text-muted-foreground text-sm">
                        Nenhuma movimentação encontrada.
                      </TableCell>
                    </TableRow>
                  ) : (
                    movFiltradas.map(m => {
                      const meta = TIPO_MOV_LABEL[m.tipo] ?? { label: m.tipo, color: "" };
                      const local = m.deposito_nome
                        ? m.deposito_nome
                        : `${m.deposito_origem_nome ?? "?"} → ${m.deposito_destino_nome ?? "?"}`;
                      const movimentacaoDate = formatDateTimePtBr(m.data_movimentacao ?? m.created_at);
                      return (
                        <TableRow key={m.id}>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {movimentacaoDate.date}{" "}
                            {movimentacaoDate.time ? (
                              <span className="text-[10px]">{movimentacaoDate.time}</span>
                            ) : null}
                          </TableCell>
                          <TableCell>
                            <Badge className={cn("text-[10px] border font-normal", meta.color)}>{meta.label}</Badge>
                          </TableCell>
                          <TableCell className="text-sm font-medium">{m.produto_nome}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{local}</TableCell>
                          <TableCell className="text-right text-sm font-bold tabular-nums">
                            {m.quantidade < 0
                              ? <span className="text-rose-600 dark:text-rose-400">−{Math.abs(m.quantidade).toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}</span>
                              : <span className="text-emerald-600 dark:text-emerald-400">+{m.quantidade.toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}</span>}
                          </TableCell>
                          <TableCell className="text-right text-xs text-muted-foreground tabular-nums">
                            {m.custo_unitario > 0 ? `R$ ${m.custo_unitario.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground max-w-40 truncate" title={m.motivo}>
                            {m.motivo ?? "—"}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── PRODUTOS ───────────────────────────────────────────────────────── */}
        <TabsContent value="produtos" className="mt-4">
          <Card className="shadow-sm">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-base">Catálogo de Produtos</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setDialog("produto")}>
                <Plus data-icon="inline-start" size={12} /> Novo Produto
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="text-xs">
                    <TableHead>Produto</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead>U.M.</TableHead>
                    <TableHead className="text-right">Estoque Mín.</TableHead>
                    <TableHead className="text-right">Preço Médio</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {produtos.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-16 text-muted-foreground text-sm">
                        Nenhum produto cadastrado.
                      </TableCell>
                    </TableRow>
                  ) : (
                    produtos.map(p => (
                      <TableRow key={p.id}>
                        <TableCell className="font-medium text-sm">{p.nome}</TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="text-[10px] font-normal">{p.tipo}</Badge>
                        </TableCell>
                        <TableCell className="text-xs">{p.unidade_medida}</TableCell>
                        <TableCell className="text-right text-xs text-muted-foreground">
                          {p.estoque_minimo > 0 ? p.estoque_minimo : "—"}
                        </TableCell>
                        <TableCell className="text-right text-sm font-medium">
                          {p.preco_medio > 0 ? `R$ ${p.preco_medio.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn(
                            "text-[10px] font-medium rounded-sm border",
                            p.ativo
                              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                              : "bg-muted text-muted-foreground border-border"
                          )}>
                            {p.ativo ? "Ativo" : "Inativo"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="size-7 text-primary hover:text-primary"
                            aria-label="Ver histórico"
                            onClick={() => {
                              setHistSearch(p.nome);
                              setActiveTab("historico");
                            }}
                          >
                            <History className="size-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── DEPÓSITOS ──────────────────────────────────────────────────────── */}
        <TabsContent value="depositos" className="mt-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-muted-foreground">{depositos.length} depósito(s) cadastrado(s)</p>
            <Button size="sm" variant="outline" onClick={() => setDialog("deposito")}>
              <Plus data-icon="inline-start" size={12} /> Novo Depósito
            </Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {depositos.length === 0 ? (
              <p className="col-span-3 text-center py-16 text-muted-foreground text-sm">
                Nenhum depósito cadastrado.
              </p>
            ) : (
              depositos.map(dep => {
                const itens = saldos.filter(s => s.deposito_id === dep.id);
                const valorDep = itens.reduce((a, s) => a + s.quantidade_atual * (s.preco_medio ?? 0), 0);
                return (
                  <Card key={dep.id} className="shadow-sm">
                    <CardHeader className="p-4 flex flex-row items-center gap-3 space-y-0">
                      <div className="p-2 bg-primary/10 rounded-sm shrink-0">
                        <Warehouse className="size-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <CardTitle className="text-sm font-semibold truncate">{dep.nome}</CardTitle>
                        <CardDescription className="text-xs uppercase">{dep.tipo}</CardDescription>
                      </div>
                      <Badge variant="outline" className={cn(
                        "ml-auto text-[10px] shrink-0 font-medium rounded-sm border",
                        dep.ativo
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                          : "bg-muted text-muted-foreground border-border"
                      )}>
                        {dep.ativo ? "Ativo" : "Inativo"}
                      </Badge>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="size-7 p-0 shrink-0">
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44 rounded-sm">
                          <DropdownMenuItem
                            className="text-xs gap-2"
                            onClick={() => setDepositoEmEdicao(dep)}
                          >
                            <Pencil className="size-3.5" />
                            Editar
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-xs gap-2 text-red-600 focus:text-red-600"
                            disabled={!dep.ativo}
                            onClick={() => setDepositoParaInativar(dep)}
                          >
                            <Trash2 className="size-3.5" />
                            Excluir
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </CardHeader>
                    <CardContent className="px-4 pb-4 space-y-1">
                      {dep.localizacao_desc && (
                        <div className="flex justify-between gap-3 text-xs">
                          <span className="text-muted-foreground">Localização</span>
                          <span className="font-medium text-right truncate">{dep.localizacao_desc}</span>
                        </div>
                      )}
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Itens com saldo</span>
                        <span className="font-medium">{itens.length}</span>
                      </div>
                      {valorDep > 0 && (
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Valor estimado</span>
                          <span className="font-medium">
                            R$ {valorDep.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </TabsContent>
        {/* ── CONTAGEM DE INVENTÁRIO ──────────────────────────────────────────── */}
        <TabsContent value="contagem" className="mt-4">
          <ContagemEstoqueTab depositos={depositos} />
        </TabsContent>
      </Tabs>

      {/* ── Dialogs ─────────────────────────────────────────────────────────── */}
      {dialog === "entrada" && (
        <EntradaDialog
          produtos={produtos}
          depositos={depositos}
          onClose={() => setDialog(null)}
          onSuccess={invalidateAll}
        />
      )}
      {dialog === "saida" && (
        <SaidaDialog
          produtos={produtos}
          depositos={depositos}
          saldos={saldos}
          onClose={() => setDialog(null)}
          onSuccess={invalidateAll}
        />
      )}
      {dialog === "transferencia" && (
        <TransferenciaDialog
          produtos={produtos}
          depositos={depositos}
          saldos={saldos}
          onClose={() => setDialog(null)}
          onSuccess={invalidateAll}
        />
      )}
      {dialog === "ajuste" && (
        <AjusteDialog
          produtos={produtos}
          depositos={depositos}
          saldos={saldos}
          onClose={() => setDialog(null)}
          onSuccess={invalidateAll}
        />
      )}
      {dialog === "reserva" && (
        <ReservaDialog
          produtos={produtos}
          depositos={depositos}
          saldos={saldos}
          onClose={() => setDialog(null)}
          onSuccess={invalidateAll}
        />
      )}
      {dialog === "produto" && (
        <NovoProdutoDialog
          onClose={() => setDialog(null)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ["estoque-produtos"] })}
        />
      )}
      {dialog === "deposito" && (
        <NovoDepositoDialog
          fazendaId={activeFazendaId}
          onClose={() => setDialog(null)}
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ["estoque-depositos"] })}
        />
      )}
      {depositoEmEdicao && (
        <NovoDepositoDialog
          fazendaId={activeFazendaId}
          deposito={depositoEmEdicao}
          onClose={() => setDepositoEmEdicao(null)}
          onSuccess={invalidateAll}
        />
      )}
      <AlertDialog
        open={Boolean(depositoParaInativar)}
        onOpenChange={(open) => !open && setDepositoParaInativar(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir depósito?</AlertDialogTitle>
            <AlertDialogDescription>
              O depósito será inativado para novos lançamentos, preservando saldos,
              lotes, compras, reservas e histórico vinculados a ele.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              disabled={inativarDepositoMutation.isPending}
              onClick={() => {
                if (depositoParaInativar) {
                  inativarDepositoMutation.mutate(depositoParaInativar.id);
                }
              }}
            >
              {inativarDepositoMutation.isPending ? "Excluindo..." : "Excluir"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ── Dialog: Entrada de Material ────────────────────────────────────────────────
