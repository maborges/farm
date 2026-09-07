import { useMemo, useState } from "react";
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
} from "lucide-react";
import { PageHeader, FornecedorCombobox } from "@/components/shared";
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
import { cn, parseLocaleNumber } from "@/lib/utils";

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
  created_at: string;
}

const TIPO_MOV_LABEL: Record<string, { label: string; color: string }> = {
  ENTRADA: { label: "Entrada", color: "bg-green-100 text-green-700 border-green-200" },
  SAIDA: { label: "Saída", color: "bg-red-100 text-red-700 border-red-200" },
  TRANSFERENCIA: { label: "Transferência", color: "bg-blue-100 text-blue-700 border-blue-200" },
  AJUSTE_POSITIVO: { label: "Ajuste ＋", color: "bg-teal-100 text-teal-700 border-teal-200" },
  AJUSTE_NEGATIVO: { label: "Ajuste −", color: "bg-orange-100 text-orange-700 border-orange-200" },
};

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

// ── Main Page ──────────────────────────────────────────────────────────────────


export function EntradaDialog({ produtos, depositos, onClose, onSuccess }: {
  produtos: Produto[];
  depositos: Deposito[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    produto_id: "", deposito_id: "",
    quantidade: "", custo_unitario: "0",
    nota_fiscal: "", fornecedor_id: "", data_entrada: "",
    motivo: "Compra",
  });

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/movimentacoes/entrada", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Entrada registrada!"); onSuccess(); onClose(); },
    onError: () => toast.error("Erro ao registrar entrada."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_id || !form.quantidade || !form.fornecedor_id)
      return toast.error("Preencha os campos obrigatórios, incluindo o fornecedor.");
    mutation.mutate({
      produto_id: form.produto_id,
      deposito_id: form.deposito_id,
      fornecedor_id: form.fornecedor_id,
      quantidade: parseLocaleNumber(form.quantidade),
      custo_unitario: parseLocaleNumber(form.custo_unitario, 0),
      motivo: [form.motivo, form.nota_fiscal && `NF ${form.nota_fiscal}`]
        .filter(Boolean).join(" | "),
    });
  };

  const selectedProduto = produtos.find(p => p.id === form.produto_id);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <ArrowDownToLine className="size-4 text-primary" />
              </div>
              <DialogTitle>Entrada de Material</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs font-medium">Produto *</Label>
              <Select value={form.produto_id} onValueChange={(v: string) => setForm(f => ({ ...f, produto_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o produto" /></SelectTrigger>
                <SelectContent className="rounded-sm">{produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome} ({p.unidade_medida})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs font-medium">Depósito de Destino *</Label>
              <Select value={form.deposito_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o depósito" /></SelectTrigger>
                <SelectContent className="rounded-sm">{depositos.filter(d => d.ativo).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Quantidade * {selectedProduto && <span className="text-muted-foreground">({selectedProduto.unidade_medida})</span>}</Label>
              <Input type="number" min="0.001" step="0.001" className="h-8 rounded-sm text-xs" value={form.quantidade}
                onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Custo Unitário (R$)</Label>
              <Input type="number" min="0" step="0.01" className="h-8 rounded-sm text-xs" value={form.custo_unitario}
                onChange={e => setForm(f => ({ ...f, custo_unitario: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nota Fiscal</Label>
              <Input placeholder="000123" className="h-8 rounded-sm text-xs" value={form.nota_fiscal}
                onChange={e => setForm(f => ({ ...f, nota_fiscal: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Fornecedor *</Label>
              <FornecedorCombobox value={form.fornecedor_id}
                onChange={id => setForm(f => ({ ...f, fornecedor_id: id }))} />
            </div>
            <div className="col-span-2 space-y-1.5">
              <Label className="text-xs font-medium">Motivo / Observação</Label>
              <Input className="h-8 rounded-sm text-xs" value={form.motivo} onChange={e => setForm(f => ({ ...f, motivo: e.target.value }))} />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <Save data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Registrando..." : "Confirmar Entrada"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: Saída de Material ──────────────────────────────────────────────────

export function SaidaDialog({ produtos, depositos, saldos, onClose, onSuccess }: {
  produtos: Produto[];
  depositos: Deposito[];
  saldos: Saldo[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    produto_id: "", deposito_id: "",
    quantidade: "", motivo: "", safra_id: "",
  });

  const saldoAtual = saldos.find(
    s => s.produto_id === form.produto_id && s.deposito_id === form.deposito_id
  );

  const { data: safras = [] } = useQuery<{ id: string; ano_safra: string }[]>({
    queryKey: ["safras-ativas"],
    queryFn: () => apiFetch("/safras?status=EM_ANDAMENTO&limit=50"),
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/movimentacoes/saida", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Saída registrada!"); onSuccess(); onClose(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao registrar saída."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_id || !form.quantidade || !form.motivo)
      return toast.error("Preencha todos os campos obrigatórios.");
    const qty = parseLocaleNumber(form.quantidade);
    if (qty > (saldoAtual?.quantidade_disponivel ?? 0)) {
      return toast.error(`Saldo insuficiente. Disponível: ${saldoAtual?.quantidade_disponivel ?? 0}`);
    }

    mutation.mutate({
      produto_id: form.produto_id,
      deposito_id: form.deposito_id,
      quantidade: qty,
      motivo: form.motivo,
      ...(form.safra_id ? { safra_id: form.safra_id } : {}),
    });
  };

  const selectedProduto = produtos.find(p => p.id === form.produto_id);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-red-100 flex items-center justify-center">
                <ArrowUpFromLine className="size-4 text-red-600" />
              </div>
              <DialogTitle>Saída de Material</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Produto *</Label>
              <Select value={form.produto_id} onValueChange={(v: string) => setForm(f => ({ ...f, produto_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o produto" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome} ({p.unidade_medida})</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Depósito de Origem *</Label>
                <Select value={form.deposito_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_id: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o depósito" /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {depositos.filter(d => d.ativo).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Quantidade * {selectedProduto && <span className="text-muted-foreground">({selectedProduto.unidade_medida})</span>}</Label>
                <Input type="number" min="0.001" step="0.001" className="h-8 rounded-sm text-xs" value={form.quantidade}
                  onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} />
              </div>
            </div>
            {saldoAtual && (
              <p className={cn(
                "text-xs p-2 rounded-sm border",
                (parseLocaleNumber(form.quantidade) > saldoAtual.quantidade_disponivel) 
                  ? "bg-red-50 border-red-100 text-red-700" 
                  : "bg-blue-50 border-blue-100 text-blue-700"
              )}>
                <strong>Saldo Disponível:</strong> {saldoAtual.quantidade_disponivel.toFixed(3)} {saldoAtual.unidade_medida}
                {saldoAtual.quantidade_reservada > 0 && (
                  <span className="block text-[10px] text-muted-foreground mt-0.5">
                    ({saldoAtual.quantidade_atual.toFixed(3)} total - {saldoAtual.quantidade_reservada.toFixed(3)} reservado)
                  </span>
                )}
              </p>
            )}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Motivo da Saída *</Label>
              <Select value={form.motivo} onValueChange={(v: string) => setForm(f => ({ ...f, motivo: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o motivo" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {MOTIVOS_SAIDA.map(m => <SelectItem key={m} value={m} className="text-xs">{m}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {safras.length > 0 && (
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">
                  Safra <span className="text-muted-foreground font-normal">(opcional — gera custo automático)</span>
                </Label>
                <Select value={form.safra_id} onValueChange={(v: string) => setForm(f => ({ ...f, safra_id: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Vincular a uma safra" /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    <SelectItem value="" className="text-xs">Nenhuma safra</SelectItem>
                    {safras.map(s => <SelectItem key={s.id} value={s.id} className="text-xs">{s.ano_safra}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <ArrowUpFromLine data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Registrando..." : "Confirmar Saída"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: Transferência ──────────────────────────────────────────────────────

export function TransferenciaDialog({ produtos, depositos, saldos, onClose, onSuccess }: {
  produtos: Produto[];
  depositos: Deposito[];
  saldos: Saldo[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    produto_id: "", deposito_origem_id: "", deposito_destino_id: "",
    quantidade: "", motivo: "Redistribuição de estoque",
  });

  const saldoAtual = saldos.find(
    s => s.produto_id === form.produto_id && s.deposito_id === form.deposito_origem_id
  );

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/movimentacoes/transferencia", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Transferência realizada!"); onSuccess(); onClose(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro na transferência."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_origem_id || !form.deposito_destino_id || !form.quantidade)
      return toast.error("Preencha todos os campos.");
    if (form.deposito_origem_id === form.deposito_destino_id)
      return toast.error("Origem e destino devem ser depósitos diferentes.");
    mutation.mutate({
      produto_id: form.produto_id,
      deposito_origem_id: form.deposito_origem_id,
      deposito_destino_id: form.deposito_destino_id,
      quantidade: parseLocaleNumber(form.quantidade),
      motivo: form.motivo,
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-blue-100 flex items-center justify-center">
                <ArrowRightLeft className="size-4 text-blue-600" />
              </div>
              <DialogTitle>Transferência entre Depósitos</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Produto *</Label>
              <Select value={form.produto_id} onValueChange={(v: string) => setForm(f => ({ ...f, produto_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o produto" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Depósito de Origem *</Label>
                <Select value={form.deposito_origem_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_origem_id: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Origem" /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {depositos.filter(d => d.ativo).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Depósito de Destino *</Label>
                <Select value={form.deposito_destino_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_destino_id: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Destino" /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {depositos.filter(d => d.ativo && d.id !== form.deposito_origem_id).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {saldoAtual && (
              <p className="text-xs text-muted-foreground bg-blue-50/50 border border-blue-100 rounded-sm px-3 py-2">
                Saldo disponível na origem: <strong className="text-blue-700">{saldoAtual.quantidade_atual.toFixed(3)} {saldoAtual.unidade_medida}</strong>
              </p>
            )}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Quantidade *</Label>
              <Input type="number" min="0.001" step="0.001" className="h-8 rounded-sm text-xs" value={form.quantidade}
                onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Motivo</Label>
              <Input className="h-8 rounded-sm text-xs" value={form.motivo} onChange={e => setForm(f => ({ ...f, motivo: e.target.value }))} />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <ArrowRightLeft data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Transferindo..." : "Confirmar Transferência"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: Ajuste de Estoque ──────────────────────────────────────────────────

const CATEGORIAS_AJUSTE: { value: string; label: string }[] = [
  { value: "CONTAGEM_INVENTARIO", label: "Contagem de inventário" },
  { value: "PERDA", label: "Perda física (quebra, deterioração)" },
  { value: "CORRECAO_LANCAMENTO", label: "Correção de lançamento" },
];

export function AjusteDialog({ produtos, depositos, saldos, onClose, onSuccess }: {
  produtos: Produto[];
  depositos: Deposito[];
  saldos: Saldo[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { activeFazendaId } = useAppStore();
  const [form, setForm] = useState({
    produto_id: "", deposito_id: "",
    quantidade_contada: "", motivo: "",
    categoria_ajuste: "CONTAGEM_INVENTARIO",
    safra_id: "", talhao_id: "",
  });

  const saldoAtual = saldos.find(
    s => s.produto_id === form.produto_id && s.deposito_id === form.deposito_id
  );

  const diff = form.quantidade_contada !== ""
    ? parseLocaleNumber(form.quantidade_contada) - (saldoAtual?.quantidade_atual ?? 0)
    : null;

  const ehPerda = form.categoria_ajuste === "PERDA";

  const { data: safras = [] } = useQuery<{ id: string; ano_safra: string }[]>({
    queryKey: ["safras-ativas"],
    queryFn: () => apiFetch("/safras?status=EM_ANDAMENTO&limit=50"),
    staleTime: 60_000,
    enabled: ehPerda,
  });

  const { data: talhoes = [] } = useQuery<{ id: string; nome: string }[]>({
    queryKey: ["talhoes-ajuste-perda", activeFazendaId],
    queryFn: () => apiFetch(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
    enabled: ehPerda && !!activeFazendaId,
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/movimentacoes/ajuste", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Ajuste registrado!"); onSuccess(); onClose(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro no ajuste."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_id || form.quantidade_contada === "" || !form.motivo)
      return toast.error("Preencha todos os campos.");
    if (diff === 0)
      return toast.error("Quantidade contada igual ao saldo atual. Nenhum ajuste necessário.");
    mutation.mutate({
      produto_id: form.produto_id,
      deposito_id: form.deposito_id,
      quantidade: parseLocaleNumber(form.quantidade_contada),
      motivo: form.motivo,
      categoria_ajuste: form.categoria_ajuste,
      ...(ehPerda && form.safra_id ? { safra_id: form.safra_id } : {}),
      ...(ehPerda && form.talhao_id ? { talhao_id: form.talhao_id } : {}),
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-orange-100 flex items-center justify-center">
                <SlidersHorizontal className="size-4 text-orange-600" />
              </div>
              <DialogTitle>Ajuste de Estoque</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Produto *</Label>
              <Select value={form.produto_id} onValueChange={(v: string) => setForm(f => ({ ...f, produto_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o produto" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Depósito *</Label>
              <Select value={form.deposito_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o depósito" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {depositos.filter(d => d.ativo).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {saldoAtual && (
              <p className="text-xs bg-muted/50 rounded-sm px-3 py-2 text-muted-foreground border border-muted-foreground/10">
                Saldo atual no sistema: <strong className="text-foreground">{saldoAtual.quantidade_atual.toFixed(3)} {saldoAtual.unidade_medida}</strong>
              </p>
            )}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Quantidade Contada (nova quantidade real) *</Label>
              <Input type="number" min="0" step="0.001" className="h-8 rounded-sm text-xs" value={form.quantidade_contada}
                onChange={e => setForm(f => ({ ...f, quantidade_contada: e.target.value }))} />
              {diff !== null && diff !== 0 && (
                <p className={cn(
                  "text-[10px] flex items-center gap-1 mt-1 font-medium px-1",
                  diff > 0 ? "text-green-600" : "text-red-600"
                )}>
                  {diff > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  Diferença: {diff > 0 ? "+" : ""}{diff.toFixed(3)} unidades
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Motivo do Ajuste *</Label>
              <Select value={form.motivo} onValueChange={(v: string) => setForm(f => ({ ...f, motivo: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o motivo" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {MOTIVOS_AJUSTE.map(m => <SelectItem key={m} value={m} className="text-xs">{m}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Categoria *</Label>
              <Select value={form.categoria_ajuste} onValueChange={(v: string) => setForm(f => ({ ...f, categoria_ajuste: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {CATEGORIAS_AJUSTE.map(c => <SelectItem key={c.value} value={c.value} className="text-xs">{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {ehPerda && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium">
                    Safra <span className="text-muted-foreground font-normal">(opcional — gera custo automático)</span>
                  </Label>
                  <Select value={form.safra_id} onValueChange={(v: string) => setForm(f => ({ ...f, safra_id: v }))}>
                    <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Vincular a uma safra" /></SelectTrigger>
                    <SelectContent className="rounded-sm">
                      <SelectItem value="" className="text-xs">Nenhuma safra</SelectItem>
                      {safras.map(s => <SelectItem key={s.id} value={s.id} className="text-xs">{s.ano_safra}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium">Talhão</Label>
                  <Select value={form.talhao_id} onValueChange={(v: string) => setForm(f => ({ ...f, talhao_id: v }))}>
                    <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Vincular a um talhão" /></SelectTrigger>
                    <SelectContent className="rounded-sm">
                      <SelectItem value="" className="text-xs">Nenhum talhão</SelectItem>
                      {talhoes.map(t => <SelectItem key={t.id} value={t.id} className="text-xs">{t.nome}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <SlidersHorizontal data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Ajustando..." : "Confirmar Ajuste"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: Novo Produto ───────────────────────────────────────────────────────

export function NovoProdutoDialog({ onClose, onSuccess }: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    nome: "", tipo: "DEFENSIVO", unidade_medida: "KG", estoque_minimo: "0",
  });

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/cadastros/produtos", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Produto cadastrado!"); onSuccess(); onClose(); },
    onError: () => toast.error("Erro ao cadastrar produto."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.nome) return toast.error("Informe o nome do produto.");
    mutation.mutate({ ...form, estoque_minimo: parseLocaleNumber(form.estoque_minimo, 0) });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Package className="size-4 text-primary" />
              </div>
              <DialogTitle>Novo Produto</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome *</Label>
              <Input placeholder="Ex: Herbicida Roundup" className="h-8 rounded-sm text-xs" value={form.nome}
                onChange={e => setForm(f => ({ ...f, nome: e.target.value }))} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Categoria</Label>
                <Select value={form.tipo} onValueChange={(v: string) => setForm(f => ({ ...f, tipo: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    <SelectItem value="DEFENSIVO" className="text-xs">Defensivo</SelectItem>
                    <SelectItem value="FERTILIZANTE" className="text-xs">Fertilizante</SelectItem>
                    <SelectItem value="SEMENTE" className="text-xs">Semente</SelectItem>
                    <SelectItem value="COMBUSTIVEL" className="text-xs">Combustível</SelectItem>
                    <SelectItem value="PECA" className="text-xs">Peça</SelectItem>
                    <SelectItem value="MATERIAL_GERAL" className="text-xs">Material Geral</SelectItem>
                    <SelectItem value="FERRAMENTA" className="text-xs">Ferramenta</SelectItem>
                    <SelectItem value="OUTRO" className="text-xs">Outro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Unidade</Label>
                <Select value={form.unidade_medida} onValueChange={(v: string) => setForm(f => ({ ...f, unidade_medida: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    <SelectItem value="KG" className="text-xs">KG</SelectItem>
                    <SelectItem value="L" className="text-xs">Litros (L)</SelectItem>
                    <SelectItem value="UN" className="text-xs">Unidade (UN)</SelectItem>
                    <SelectItem value="SACA" className="text-xs">Saca</SelectItem>
                    <SelectItem value="M3" className="text-xs">M³</SelectItem>
                    <SelectItem value="G" className="text-xs">Gramas (G)</SelectItem>
                    <SelectItem value="ML" className="text-xs">Mililitros (mL)</SelectItem>
                    <SelectItem value="CX" className="text-xs">Caixa (CX)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Estoque Mínimo (alerta de reposição)</Label>
              <Input type="number" min="0" step="0.001" className="h-8 rounded-sm text-xs" value={form.estoque_minimo}
                onChange={e => setForm(f => ({ ...f, estoque_minimo: e.target.value }))} />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <Save data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Salvando..." : "Cadastrar Produto"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Dialog: Novo Depósito ──────────────────────────────────────────────────────

export function NovoDepositoDialog({ fazendaId, deposito, onClose, onSuccess }: {
  fazendaId: string | null;
  deposito?: Deposito;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    nome: deposito?.nome ?? "",
    tipo: deposito?.tipo ?? "GERAL",
    localizacao_desc: deposito?.localizacao_desc ?? "",
    unidade_produtiva_id: deposito?.unidade_produtiva_id ?? fazendaId ?? "",
  });

  const isEditing = Boolean(deposito);

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch(
        isEditing ? `/estoque/depositos/${deposito?.id}` : "/estoque/depositos",
        { method: isEditing ? "PATCH" : "POST", body: JSON.stringify(payload) },
      ),
    onSuccess: () => {
      toast.success(isEditing ? "Depósito atualizado!" : "Depósito cadastrado!");
      onSuccess();
      onClose();
    },
    onError: () => toast.error(isEditing ? "Erro ao atualizar depósito." : "Erro ao cadastrar depósito."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.nome || !form.unidade_produtiva_id) return toast.error("Informe o nome e a fazenda.");
    const payload = isEditing
      ? {
          nome: form.nome,
          tipo: form.tipo,
          localizacao_desc: form.localizacao_desc || null,
        }
      : form;
    mutation.mutate(payload);
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Warehouse className="size-4 text-primary" />
              </div>
              <DialogTitle>{isEditing ? "Editar Depósito" : "Novo Depósito"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome *</Label>
              <Input placeholder="Ex: Almoxarifado Central" className="h-8 rounded-sm text-xs" value={form.nome}
                onChange={e => setForm(f => ({ ...f, nome: e.target.value }))} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Tipo</Label>
              <Select value={form.tipo} onValueChange={(v: string) => setForm(f => ({ ...f, tipo: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="GERAL" className="text-xs">Geral / Almoxarifado</SelectItem>
                  <SelectItem value="COMBUSTIVEL" className="text-xs">Combustível</SelectItem>
                  <SelectItem value="DEFENSIVOS" className="text-xs">Defensivos</SelectItem>
                  <SelectItem value="PECAS" className="text-xs">Peças</SelectItem>
                  <SelectItem value="GRAOS" className="text-xs">Grãos</SelectItem>
                  <SelectItem value="OUTROS" className="text-xs">Outros</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Localização</Label>
              <Input
                placeholder="Ex: Galpão 1, corredor B"
                className="h-8 rounded-sm text-xs"
                value={form.localizacao_desc}
                onChange={e => setForm(f => ({ ...f, localizacao_desc: e.target.value }))}
              />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <Save data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Salvando..." : isEditing ? "Salvar Alterações" : "Cadastrar Depósito"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Reserva: helpers inline ────────────────────────────────────────────────────

const RESERVA_STATUS: Record<string, { label: string; color: string }> = {
  ATIVA:     { label: "Ativa",     color: "bg-purple-100 text-purple-700 border-purple-200" },
  CONSUMIDA: { label: "Consumida", color: "bg-green-100 text-green-700 border-green-200" },
  CANCELADA: { label: "Cancelada", color: "bg-gray-100 text-gray-500 border-gray-200" },
};

export function ReservaStatusBadge({ status }: { status: string }) {
  const meta = RESERVA_STATUS[status] ?? { label: status, color: "" };
  return <Badge className={cn("text-[10px] border font-normal", meta.color)}>{meta.label}</Badge>;
}

export function ReservaConsumirButton({ reservaId, onSuccess }: { reservaId: string; onSuccess: () => void }) {
  const mutation = useMutation({
    mutationFn: () => apiFetch(`/estoque/reservas/${reservaId}/consumir`, { method: "PATCH", body: "{}" }),
    onSuccess: () => { toast.success("Reserva consumida — saída registrada!"); onSuccess(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao consumir reserva."),
  });
  return (
    <Button size="sm" variant="outline"
      disabled={mutation.isPending} onClick={() => mutation.mutate()}>
      <CheckCircle2 data-icon="inline-start" size={10} /> Consumir
    </Button>
  );
}

export function ReservaCancelarButton({ reservaId, onSuccess }: { reservaId: string; onSuccess: () => void }) {
  const mutation = useMutation({
    mutationFn: () => apiFetch(`/estoque/reservas/${reservaId}/cancelar`, { method: "PATCH", body: "{}" }),
    onSuccess: () => { toast.success("Reserva cancelada — saldo liberado."); onSuccess(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao cancelar reserva."),
  });
  return (
    <Button size="sm" variant="outline"
      disabled={mutation.isPending} onClick={() => mutation.mutate()}>
      <Ban data-icon="inline-start" size={10} /> Cancelar
    </Button>
  );
}

// ── Dialog: Nova Reserva ───────────────────────────────────────────────────────

const REFERENCIA_TIPOS = ["ORDEM_SERVICO", "PEDIDO_COMPRA", "SAFRA", "REQUISICAO", "MANUAL"];

export function ReservaDialog({ produtos, depositos, saldos, onClose, onSuccess }: {
  produtos: Produto[];
  depositos: Deposito[];
  saldos: Saldo[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    produto_id: "", deposito_id: "",
    quantidade: "", motivo: "",
    referencia_tipo: "MANUAL",
  });

  const saldoAtual = saldos.find(
    s => s.produto_id === form.produto_id && s.deposito_id === form.deposito_id
  );

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/reservas", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Reserva criada — saldo bloqueado!"); onSuccess(); onClose(); },
    onError: (e: any) => toast.error(e?.message ?? "Erro ao criar reserva."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.produto_id || !form.deposito_id || !form.quantidade || !form.motivo)
      return toast.error("Preencha todos os campos obrigatórios.");
    const qtd = parseLocaleNumber(form.quantidade);
    if (saldoAtual && qtd > saldoAtual.quantidade_disponivel)
      return toast.error(`Disponível: ${saldoAtual.quantidade_disponivel.toFixed(3)} — quantidade excede o saldo livre.`);
    mutation.mutate({
      produto_id: form.produto_id,
      deposito_id: form.deposito_id,
      quantidade: qtd,
      motivo: form.motivo,
      referencia_tipo: form.referencia_tipo,
    });
  };

  const selectedProduto = produtos.find(p => p.id === form.produto_id);

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg p-0">
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-purple-100 flex items-center justify-center">
                <Lock className="size-4 text-purple-600" />
              </div>
              <DialogTitle>Nova Reserva de Estoque</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="rounded-sm border border-purple-200 bg-purple-50 px-3 py-2 text-[11px] text-purple-700 leading-relaxed">
              O saldo reservado fica bloqueado e não pode ser consumido por saídas comuns.
              Use &quot;Consumir&quot; na aba Reservas para registrar a saída efetiva.
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Produto *</Label>
              <Select value={form.produto_id} onValueChange={(v: string) => setForm(f => ({ ...f, produto_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o produto" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome} ({p.unidade_medida})</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Depósito *</Label>
              <Select value={form.deposito_id} onValueChange={(v: string) => setForm(f => ({ ...f, deposito_id: v }))}>
                <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione o depósito" /></SelectTrigger>
                <SelectContent className="rounded-sm">
                  {depositos.filter(d => d.ativo).map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {saldoAtual && (
              <div className="grid grid-cols-2 gap-y-1 gap-x-4 text-[11px] bg-muted/50 rounded-sm px-3 py-2 border border-muted-foreground/10">
                <span className="text-muted-foreground">Total no depósito</span>
                <span className="font-medium text-right">{saldoAtual.quantidade_atual.toFixed(3)} {saldoAtual.unidade_medida}</span>
                <span className="text-muted-foreground">Já reservado</span>
                <span className="font-medium text-right text-purple-600">{saldoAtual.quantidade_reservada.toFixed(3)} {saldoAtual.unidade_medida}</span>
                <span className="text-muted-foreground font-semibold">Disponível para reservar</span>
                <span className="font-bold text-right text-green-700">{saldoAtual.quantidade_disponivel.toFixed(3)} {saldoAtual.unidade_medida}</span>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Quantidade * {selectedProduto && <span className="text-muted-foreground">({selectedProduto.unidade_medida})</span>}</Label>
                <Input type="number" min="0.001" step="0.001" className="h-8 rounded-sm text-xs" value={form.quantidade}
                  onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Tipo de Referência</Label>
                <Select value={form.referencia_tipo} onValueChange={(v: string) => setForm(f => ({ ...f, referencia_tipo: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {REFERENCIA_TIPOS.map(t => <SelectItem key={t} value={t} className="text-xs">{t.replace("_", " ")}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Motivo / Descrição *</Label>
              <Input placeholder="Ex: Reserva para safra de soja 2025" className="h-8 rounded-sm text-xs" value={form.motivo}
                onChange={e => setForm(f => ({ ...f, motivo: e.target.value }))} />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              disabled={mutation.isPending}
            >
              <Lock data-icon="inline-start" className="size-3.5" />
              {mutation.isPending ? "Reservando..." : "Confirmar Reserva"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
