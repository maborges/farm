"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { toast } from "sonner";
import { ClipboardList, Plus, CheckCircle2, XCircle, Package, Clock, ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/empty-state";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ItemReq {
  id: string; produto_id: string; deposito_id: string | null;
  quantidade_solicitada: number; quantidade_aprovada: number | null;
  quantidade_entregue: number | null; quantidade_devolvida: number | null; observacoes: string | null;
}
interface Requisicao {
  id: string; numero?: string | null;
  unidade_produtiva_id: string; solicitante_id: string; solicitante_nome?: string | null;
  aprovador_id: string | null; aprovador_nome?: string | null;
  data_solicitacao: string; data_necessidade: string | null;
  status: string; origem_tipo: string; observacoes: string | null;
  itens: ItemReq[];
}
interface Produto { id: string; nome: string; unidade_medida: string; }
interface Deposito { id: string; nome: string; }
interface UnidadeProdutiva { id: string; nome: string; }
interface SafraResumo { id: string; status: string; ano_safra: string; cultura: string | null; }
interface TarefaResumo { id: string; tipo: string; descricao: string; status: string; }

const STATUS_REQ: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  PENDENTE:   { label: "Pendente",   color: "bg-yellow-100 text-yellow-700", icon: <Clock className="size-3" /> },
  APROVADA:   { label: "Aprovada",   color: "bg-blue-100 text-blue-700",    icon: <CheckCircle2 className="size-3" /> },
  SEPARANDO:  { label: "Separando",  color: "bg-orange-100 text-orange-700", icon: <Package className="size-3" /> },
  ENTREGUE:   { label: "Entregue",   color: "bg-green-100 text-green-700",  icon: <CheckCircle2 className="size-3" /> },
  RECUSADA:   { label: "Recusada",   color: "bg-red-100 text-red-700",      icon: <XCircle className="size-3" /> },
  CANCELADA:  { label: "Cancelada",  color: "bg-gray-100 text-gray-500",    icon: <XCircle className="size-3" /> },
};

const ORIGENS = ["ORDEM_SERVICO", "MANUTENCAO", "PRODUCAO", "OUTRO"];

// ── Nova Requisição ───────────────────────────────────────────────────────────

function NovaRequisicaoDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { activeFazendaId } = useAppStore();
  const tenantId = useAppStore((s) => s.tenant?.id);
  const [form, setForm] = useState({
    unidade_produtiva_id: activeFazendaId ?? "",
    origem_tipo: "OUTRO",
    origem_id: "",
    data_necessidade: "",
    observacoes: "",
  });
  const [itens, setItens] = useState([{ produto_id: "", quantidade_solicitada: "", observacoes: "" }]);

  const { data: produtos = [] } = useQuery<Produto[]>({
    queryKey: ["estoque-produtos"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
  });
  const { data: fazendas = [] } = useQuery<UnidadeProdutiva[]>({
    queryKey: ["unidades-produtivas"],
    queryFn: () => apiFetch("/unidades-produtivas"),
    enabled: !!tenantId,
  });
  const { data: safras = [] } = useQuery<SafraResumo[]>({
    queryKey: ["safras-requisicao", tenantId],
    queryFn: () => apiFetch("/safras/"),
    enabled: !!tenantId,
  });
  const safraAtiva = safras.find((s) => !["ENCERRADA", "CANCELADA"].includes(s.status)) ?? null;
  const { data: tarefas = [] } = useQuery<TarefaResumo[]>({
    queryKey: ["tarefas-requisicao", safraAtiva?.id],
    queryFn: () => apiFetch(`/safras/${safraAtiva?.id}/tarefas`),
    enabled: !!safraAtiva?.id && form.origem_tipo === "ORDEM_SERVICO",
  });

  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch("/estoque/requisicoes", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Requisição criada!"); qc.invalidateQueries({ queryKey: ["requisicoes"] }); onClose(); },
    onError: () => toast.error("Erro ao criar requisição."),
  });

  const addItem = () => setItens(i => [...i, { produto_id: "", quantidade_solicitada: "", observacoes: "" }]);
  const rmItem = (idx: number) => setItens(i => i.filter((_, n) => n !== idx));
  const updItem = (idx: number, field: string, val: string) =>
    setItens(i => i.map((item, n) => n === idx ? { ...item, [field]: val } : item));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.unidade_produtiva_id) return toast.error("Selecione a fazenda.");
    mutation.mutate({
      ...form,
      origem_id: form.origem_id || null,
      data_necessidade: form.data_necessidade || null,
      observacoes: form.observacoes || null,
      itens: itens.map(i => ({
        produto_id: i.produto_id,
        quantidade_solicitada: parseFloat(i.quantidade_solicitada),
        observacoes: i.observacoes || null,
      })),
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto p-0"
        style={{ width: "min(calc(100vw - 2rem), 42rem)" }}
      >
        <form onSubmit={submit}>
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <ClipboardList className="size-4 text-primary" />
              </div>
              <div className="space-y-0.5">
                <DialogTitle>Nova Requisição de Material</DialogTitle>
                <DialogDescription className="text-xs">
                  Registre materiais para aprovação e separação pelo almoxarifado.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Fazenda *</Label>
                <Select value={form.unidade_produtiva_id} onValueChange={(v: string) => setForm(f => ({ ...f, unidade_produtiva_id: v }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione..." /></SelectTrigger>
                  <SelectContent className="rounded-sm">{fazendas.map(f => <SelectItem key={f.id} value={f.id} className="text-xs">{f.nome}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Origem</Label>
                <Select value={form.origem_tipo} onValueChange={(v: string) => setForm(f => ({ ...f, origem_tipo: v, origem_id: "" }))}>
                  <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent className="rounded-sm">{ORIGENS.map(o => <SelectItem key={o} value={o} className="text-xs">{o.replace("_", " ")}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              {form.origem_tipo === "ORDEM_SERVICO" && (
                <div className="col-span-2 flex flex-col gap-1.5">
                  <Label className="text-xs font-medium">OS / Tarefa vinculada</Label>
                  <Select
                    value={form.origem_id}
                    onValueChange={(v: string) => setForm(f => ({ ...f, origem_id: v }))}
                    disabled={!safraAtiva}
                  >
                    <SelectTrigger className="h-8 rounded-sm text-xs">
                      <SelectValue placeholder={safraAtiva ? "Selecione a tarefa..." : "Selecione uma safra ativa"} />
                    </SelectTrigger>
                    <SelectContent className="rounded-sm">
                      {tarefas.map((t) => (
                        <SelectItem key={t.id} value={t.id} className="text-xs">
                          {t.tipo} · {t.descricao} ({t.status})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Data de Necessidade</Label>
                <Input type="date" className="h-8 rounded-sm text-xs" value={form.data_necessidade} onChange={e => setForm(f => ({ ...f, data_necessidade: e.target.value }))} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Observações</Label>
                <Input className="h-8 rounded-sm text-xs" value={form.observacoes} onChange={e => setForm(f => ({ ...f, observacoes: e.target.value }))} />
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between border-b pb-2">
                <p className="text-sm font-semibold">Materiais Solicitados</p>
                <Button type="button" size="sm" variant="outline" onClick={addItem}>
                  <Plus data-icon="inline-start" className="size-3" /> Material
                </Button>
              </div>
              <div className="flex flex-col gap-2">
                {itens.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-3 items-end p-3 border rounded-sm bg-muted/5">
                    <div className="col-span-7 flex flex-col gap-1.5">
                      <Label className="text-[10px] font-semibold uppercase text-muted-foreground">Produto *</Label>
                      <Select value={item.produto_id} onValueChange={(v: string) => updItem(idx, "produto_id", v)}>
                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Produto..." /></SelectTrigger>
                        <SelectContent className="rounded-sm">{produtos.map(p => <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-4 flex flex-col gap-1.5">
                      <Label className="text-[10px] font-semibold uppercase text-muted-foreground">Quantidade *</Label>
                      <Input type="number" step="0.001" min="0" className="h-8 rounded-sm text-xs" value={item.quantidade_solicitada}
                        onChange={e => updItem(idx, "quantidade_solicitada", e.target.value)} />
                    </div>
                    <div className="col-span-1 pb-0.5">
                      {itens.length > 1 && (
                        <Button type="button" size="icon-sm" variant="ghost" onClick={() => rmItem(idx)}>
                          <XCircle data-icon="inline-start" className="size-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
              variant="default"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Enviando..." : (
                <>
                  <CheckCircle2 data-icon="inline-start" className="size-3.5" />
                  Criar Requisição
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Aprovar Dialog ────────────────────────────────────────────────────────────

function AprovarDialog({ req, onClose }: { req: Requisicao; onClose: () => void }) {
  const qc = useQueryClient();
  const { activeFazendaId } = useAppStore();
  const [aprovacoes, setAprovacoes] = useState<Record<string, { qtd: string; deposito_id: string }>>({});

  const { data: produtos = [] } = useQuery<Produto[]>({ queryKey: ["estoque-produtos"], queryFn: () => apiFetch("/cadastros/produtos?ativo=true") });
  const { data: depositos = [] } = useQuery<Deposito[]>({
    queryKey: ["estoque-depositos", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/depositos${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
  });

  const getAp = (id: string) => aprovacoes[id] ?? { qtd: "", deposito_id: "" };
  const mutation = useMutation({
    mutationFn: (payload: object) =>
      apiFetch(`/estoque/requisicoes/${req.id}/aprovar`, { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: () => { toast.success("Requisição aprovada!"); qc.invalidateQueries({ queryKey: ["requisicoes"] }); onClose(); },
    onError: () => toast.error("Erro ao aprovar."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      itens: req.itens.map(i => ({
        item_id: i.id,
        quantidade_aprovada: parseFloat(getAp(i.id).qtd) || i.quantidade_solicitada,
        deposito_id: getAp(i.id).deposito_id || null,
      })),
    });
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent
        className="max-h-[90vh] p-0"
        style={{ width: "min(calc(100vw - 2rem), 36rem)" }}
      >
        <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col">
          <DialogHeader className="border-b px-4 py-4 sm:px-5">
            <div className="flex min-w-0 items-start gap-2.5 pr-6">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <CheckCircle2 className="size-4 text-primary" />
              </div>
              <div className="min-w-0 space-y-0.5">
                <DialogTitle className="truncate">
                  Aprovar Requisição{req.numero && <span className="ml-1.5 font-mono text-xs text-muted-foreground">{req.numero}</span>}
                </DialogTitle>
                <DialogDescription className="text-xs leading-relaxed">
                  {req.solicitante_nome && `Solicitado por ${req.solicitante_nome} · `}
                  Revise as quantidades e indique o depósito de saída.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-2.5 px-4 py-3 sm:px-5">
            {req.itens.map(item => {
              const prod = produtos.find(p => p.id === item.produto_id);
              return (
                <div key={item.id} className="flex flex-col gap-3 rounded-sm border bg-muted/5 p-3">
                  <div className="flex min-w-0 items-center gap-2 border-b pb-2">
                    <Package className="size-3.5 text-muted-foreground" />
                    <p className="truncate text-sm font-semibold">{prod?.nome ?? "—"}</p>
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-[10px] font-semibold uppercase text-muted-foreground">Qtd. aprovada · solicitada: {item.quantidade_solicitada}</Label>
                      <Input type="number" step="0.001" min="0" className="h-8 rounded-sm text-xs"
                        placeholder={String(item.quantidade_solicitada)}
                        value={getAp(item.id).qtd}
                        onChange={e => setAprovacoes(a => ({ ...a, [item.id]: { ...getAp(item.id), qtd: e.target.value } }))}
                      />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <Label className="text-[10px] font-semibold uppercase text-muted-foreground">Depósito de Saída</Label>
                      <Select value={getAp(item.id).deposito_id}
                        onValueChange={(v: string) => setAprovacoes(a => ({ ...a, [item.id]: { ...getAp(item.id), deposito_id: v } }))}>
                        <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue placeholder="Selecione..." /></SelectTrigger>
                        <SelectContent className="rounded-sm">{depositos.map(d => <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              );
            })}
          </DialogBody>
          <DialogFooter className="px-4 py-3 sm:px-5">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button 
              type="submit" 
              size="sm"
              variant="default"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Aprovando..." : (
                <>
                  <CheckCircle2 data-icon="inline-start" className="size-3.5" />
                  Confirmar Aprovação
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Confirmação de Retirada / Devolução (reautenticação) ───────────────────────

function ConfirmacaoCredencialDialog({
  req,
  tipo,
  onClose,
}: {
  req: Requisicao;
  tipo: "RETIRADA" | "DEVOLUCAO";
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const userEmail = useAppStore((s) => s.user?.email);
  const [email, setEmail] = useState(userEmail ?? "");
  const [senha, setSenha] = useState("");
  const [quantidades, setQuantidades] = useState<Record<string, string>>({});

  const { data: produtos = [] } = useQuery<Produto[]>({ queryKey: ["estoque-produtos"], queryFn: () => apiFetch("/cadastros/produtos?ativo=true") });

  const itensRelevantes = tipo === "RETIRADA"
    ? req.itens
    : req.itens.filter((i) => (i.quantidade_entregue ?? 0) > 0);

  const isRetirada = tipo === "RETIRADA";
  const endpoint = isRetirada ? "confirmar-retirada" : "confirmar-devolucao";

  const mutation = useMutation({
    mutationFn: () =>
      apiFetch(`/estoque/requisicoes/${req.id}/${endpoint}`, {
        method: "POST",
        body: JSON.stringify({
          email,
          senha,
          itens: itensRelevantes.map((i) => ({
            item_id: i.id,
            [isRetirada ? "quantidade_conferida" : "quantidade_devolvida"]: parseFloat(quantidades[i.id] ?? "0") || 0,
          })),
        }),
      }),
    onSuccess: () => {
      toast.success(isRetirada ? "Retirada confirmada!" : "Devolução registrada!");
      qc.invalidateQueries({ queryKey: ["requisicoes"] });
      onClose();
    },
    onError: (err: Error) => toast.error(err.message || "Erro ao confirmar."),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !senha) return toast.error("Informe e-mail e senha para confirmar.");
    mutation.mutate();
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
              <div className="space-y-0.5">
                <DialogTitle>{isRetirada ? "Confirmar Retirada" : "Registrar Devolução"}</DialogTitle>
                <DialogDescription className="text-xs">
                  {isRetirada
                    ? "Confira a quantidade realmente retirada de cada item e confirme sua identidade."
                    : "Informe a quantidade de sobra devolvida de cada item e confirme sua identidade."}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              {itensRelevantes.map((item) => {
                const prod = produtos.find((p) => p.id === item.produto_id);
                const referencia = isRetirada
                  ? item.quantidade_aprovada ?? item.quantidade_solicitada
                  : item.quantidade_entregue ?? 0;
                return (
                  <div key={item.id} className="flex items-center justify-between gap-3 p-3 border rounded-sm bg-muted/5">
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{prod?.nome ?? "—"}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {isRetirada ? "Aprovado" : "Retirado"}: {referencia} {prod?.unidade_medida}
                      </p>
                    </div>
                    <Input
                      type="number"
                      step="0.001"
                      min="0"
                      className="h-8 w-28 rounded-sm text-xs"
                      placeholder={isRetirada ? String(referencia) : "0"}
                      value={quantidades[item.id] ?? (isRetirada ? String(referencia) : "")}
                      onChange={(e) => setQuantidades((q) => ({ ...q, [item.id]: e.target.value }))}
                    />
                  </div>
                );
              })}
            </div>
            <div className="border-t pt-4 flex flex-col gap-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Confirme sua identidade
              </p>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">E-mail de quem está {isRetirada ? "retirando" : "devolvendo"} *</Label>
                <Input
                  type="email"
                  className="h-8 rounded-sm text-xs"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Senha *</Label>
                <Input
                  type="password"
                  className="h-8 rounded-sm text-xs"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              <XCircle data-icon="inline-start" className="size-3.5" />
              Cancelar
            </Button>
            <Button type="submit" size="sm" disabled={mutation.isPending}>
              {mutation.isPending ? "Confirmando..." : (
                <>
                  <CheckCircle2 data-icon="inline-start" className="size-3.5" />
                  {isRetirada ? "Confirmar Retirada" : "Confirmar Devolução"}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function RequisicoesPage() {
  const { activeFazendaId } = useAppStore();
  const qc = useQueryClient();
  const [novaReq, setNovaReq] = useState(false);
  const [aprovando, setAprovando] = useState<Requisicao | null>(null);
  const [confirmando, setConfirmando] = useState<{ req: Requisicao; tipo: "RETIRADA" | "DEVOLUCAO" } | null>(null);
  const [tab, setTab] = useState("pendentes");

  const { data: requisicoes = [] } = useQuery<Requisicao[]>({
    queryKey: ["requisicoes", activeFazendaId],
    queryFn: () => apiFetch(`/estoque/requisicoes${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
  });
  const { data: produtos = [] } = useQuery<Produto[]>({ queryKey: ["estoque-produtos"], queryFn: () => apiFetch("/cadastros/produtos?ativo=true") });

  const avancarStatus = useMutation({
    mutationFn: ({ id, acao }: { id: string; acao: string }) =>
      apiFetch(`/estoque/requisicoes/${id}/${acao}`, { method: "PATCH", body: JSON.stringify({ itens: [] }) }),
    onSuccess: () => { toast.success("Status atualizado!"); qc.invalidateQueries({ queryKey: ["requisicoes"] }); },
    onError: () => toast.error("Erro ao atualizar."),
  });

  const recusar = useMutation({
    mutationFn: (id: string) => apiFetch(`/estoque/requisicoes/${id}/recusar`, { method: "PATCH" }),
    onSuccess: () => { toast.success("Requisição recusada."); qc.invalidateQueries({ queryKey: ["requisicoes"] }); },
  });

  const filtradas = {
    pendentes: requisicoes.filter(r => r.status === "PENDENTE"),
    aprovadas: requisicoes.filter(r => ["APROVADA", "SEPARANDO"].includes(r.status)),
    concluidas: requisicoes.filter(r => ["ENTREGUE", "RECUSADA", "CANCELADA"].includes(r.status)),
  };

  const ReqCard = ({ req }: { req: Requisicao }) => {
    const meta = STATUS_REQ[req.status] ?? { label: req.status, color: "bg-gray-100 text-gray-700", icon: null };
    return (
      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {req.numero && (
                  <span className="font-mono text-[11px] font-bold text-muted-foreground">{req.numero}</span>
                )}
                <Badge className={`text-xs flex items-center gap-1 ${meta.color}`}>{meta.icon}{meta.label}</Badge>
                <Badge variant="outline" className="text-xs">{req.origem_tipo.replace("_", " ")}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                {req.solicitante_nome && `${req.solicitante_nome} · `}
                {new Date(req.data_solicitacao).toLocaleDateString("pt-BR")}
                {req.data_necessidade && ` · Necessário em ${new Date(req.data_necessidade).toLocaleDateString("pt-BR")}`}
              </p>
            </div>
            <div className="flex gap-2">
              {req.status === "PENDENTE" && (
                <>
                  <Button size="sm" variant="outline" onClick={() => recusar.mutate(req.id)}>Recusar</Button>
                  <Button size="sm" onClick={() => setAprovando(req)}>
                    <CheckCircle2 data-icon="inline-start" className="size-4" /> Aprovar
                  </Button>
                </>
              )}
              {req.status === "APROVADA" && (
                <Button size="sm" variant="outline"
                  onClick={() => avancarStatus.mutate({ id: req.id, acao: "separar" })}>
                  <ArrowRight data-icon="inline-start" className="size-4" /> Iniciar Separação
                </Button>
              )}
              {req.status === "SEPARANDO" && (
                <Button size="sm"
                  onClick={() => setConfirmando({ req, tipo: "RETIRADA" })}>
                  <Package data-icon="inline-start" className="size-4" /> Confirmar Retirada
                </Button>
              )}
              {req.status === "ENTREGUE" && req.itens.some((i) => (i.quantidade_entregue ?? 0) > (i.quantidade_devolvida ?? 0)) && (
                <Button size="sm" variant="outline"
                  onClick={() => setConfirmando({ req, tipo: "DEVOLUCAO" })}>
                  <ArrowRight data-icon="inline-start" className="size-4 rotate-180" /> Registrar devolução
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-1">
            {req.itens.map(item => {
              const prod = produtos.find(p => p.id === item.produto_id);
              return (
                <div key={item.id} className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>{prod?.nome ?? "—"}</span>
                  <span className="font-mono">
                    {item.quantidade_entregue != null
                      ? `${item.quantidade_entregue} / ${item.quantidade_solicitada} ${prod?.unidade_medida}`
                      : item.quantidade_aprovada != null
                      ? `apr: ${item.quantidade_aprovada} ${prod?.unidade_medida}`
                      : `${item.quantidade_solicitada} ${prod?.unidade_medida}`}
                    {item.quantidade_devolvida ? ` · devolvido: ${item.quantidade_devolvida}` : ""}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="p-6 space-y-6 w-full">
      <PageHeader
        title="Requisições de Material"
        description="Solicitações internas ao almoxarifado — fluxo de aprovação e entrega."
        icon={<ClipboardList className="size-4 text-primary" />}
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Requisições" },
        ]}
        actions={
          <Button size="sm" variant="default" onClick={() => setNovaReq(true)}>
            <Plus data-icon="inline-start" className="size-4" /> Nova Requisição
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase tracking-wide">Pendentes</CardDescription>
            <CardTitle className="text-2xl">{filtradas.pendentes.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase tracking-wide">Em andamento</CardDescription>
            <CardTitle className="text-2xl">{filtradas.aprovadas.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase tracking-wide">Concluídas</CardDescription>
            <CardTitle className="text-2xl">{filtradas.concluidas.length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="pendentes">Pendentes ({filtradas.pendentes.length})</TabsTrigger>
          <TabsTrigger value="aprovadas">Em Andamento ({filtradas.aprovadas.length})</TabsTrigger>
          <TabsTrigger value="concluidas">Concluídas ({filtradas.concluidas.length})</TabsTrigger>
        </TabsList>

        {(["pendentes", "aprovadas", "concluidas"] as const).map(t => (
          <TabsContent key={t} value={t} className="mt-4 space-y-3">
            {filtradas[t].length === 0 ? (
              <EmptyState
                icon={<ClipboardList />}
                title="Nenhuma requisição aqui"
                description="Crie uma requisição para iniciar o fluxo de aprovação e entrega de materiais."
                action={{ label: "Nova Requisição", onClick: () => setNovaReq(true) }}
                className="rounded-sm border border-dashed bg-muted/20"
              />
            ) : filtradas[t].map(req => <ReqCard key={req.id} req={req} />)}
          </TabsContent>
        ))}
      </Tabs>

      {novaReq && <NovaRequisicaoDialog onClose={() => setNovaReq(false)} />}
      {aprovando && <AprovarDialog req={aprovando} onClose={() => setAprovando(null)} />}
      {confirmando && (
        <ConfirmacaoCredencialDialog
          req={confirmando.req}
          tipo={confirmando.tipo}
          onClose={() => setConfirmando(null)}
        />
      )}
    </div>
  );
}
