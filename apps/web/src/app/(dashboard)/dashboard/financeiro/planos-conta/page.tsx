"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Folder, FolderOpen, FolderTree, Loader2, Pencil, Plus, RotateCcw, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { useAppStore } from "@/lib/stores/app-store";

const CATEGORIAS_RFB = [
  "CUSTEIO",
  "INVESTIMENTO",
  "RECEITA_ATIVIDADE",
  "RECEITA_FORA_ATIVIDADE",
  "NAO_DEDUTIVEL",
] as const;

type CategoriaRFB = (typeof CATEGORIAS_RFB)[number];

type PlanoConta = {
  id: string;
  tenant_id: string;
  parent_id: string | null;
  codigo: string;
  nome: string;
  descricao: string | null;
  tipo: "RECEITA" | "DESPESA";
  natureza: "ANALITICA" | "SINTETICA";
  categoria_rfb: CategoriaRFB | null;
  ordem: number;
  is_sistema: boolean;
  ativo: boolean;
};

type PlanoContaTreeNode = PlanoConta & {
  nivel: number;
  children: PlanoContaTreeNode[];
};

type PlanoContaForm = {
  codigo: string;
  nome: string;
  descricao: string;
  tipo: "RECEITA" | "DESPESA";
  natureza: "ANALITICA" | "SINTETICA";
  categoria_rfb: CategoriaRFB;
  ordem: number;
  parent_id: string;
  ativo: boolean;
};

type PlanoContaLimitState = {
  message: string;
  max?: number;
  current?: number;
};

type BillingAccountResponse = {
  tenant?: {
    max_categorias_plano?: number | null;
  };
  assinatura?: {
    max_categorias_plano?: number | null;
  } | null;
};


function getCategoriaLabel(value: string | null) {
  switch (value) {
    case "CUSTEIO":
      return "Custeio";
    case "INVESTIMENTO":
      return "Investimento";
    case "RECEITA_ATIVIDADE":
      return "Receita da Atividade";
    case "RECEITA_FORA_ATIVIDADE":
      return "Receita Fora da Atividade";
    case "NAO_DEDUTIVEL":
      return "Não Dedutível";
    default:
      return value ?? "-";
  }
}

function getCategoriaDefault(tipo: PlanoContaForm["tipo"]): CategoriaRFB {
  return tipo === "RECEITA" ? "RECEITA_ATIVIDADE" : "CUSTEIO";
}

function parsePlanoContaLimitError(message: string): PlanoContaLimitState | null {
  const patterns = [
    /Você tem (\d+)\s+de\s+(\d+)\s+categorias/i,
    /Você tem (\d+)\s+categorias\s+e\s+o\s+plano\s+permite\s+até\s+(\d+)/i,
    /Limite de (\d+) categorias atingido\. Você tem (\d+) categoria\(s\)\./i,
  ];

  for (const pattern of patterns) {
    const matched = message.match(pattern);
    if (!matched) continue;

    const current = Number(matched[1]);
    const max = Number(matched[2]);

    return {
      message: `Seu plano atingiu o limite de categorias. Você tem ${current} categorias e o plano permite até ${max}.`,
      max,
      current,
    };
  }

  return null;
}

function getPlanoContaLimitFromAccount(account: BillingAccountResponse | undefined, current: number): PlanoContaLimitState | null {
  const rawLimit = account?.tenant?.max_categorias_plano ?? account?.assinatura?.max_categorias_plano ?? null;
  if (rawLimit === null || rawLimit === undefined || rawLimit < 0) return null;
  if (current < rawLimit) return null;

  return {
    max: rawLimit,
    current,
    message: `Seu plano atingiu o limite de categorias. Você tem ${current} categorias e o plano permite até ${rawLimit}.`,
  };
}


function PlanoTreeItem({
  node,
  onEdit,
  onDelete,
  isLast = false,
  expandAllSignal = 0,
  collapseAllSignal = 0,
}: {
  node: PlanoContaTreeNode;
  onEdit: (plano: PlanoConta) => void;
  onDelete: (planoId: string) => void;
  isLast?: boolean;
  expandAllSignal?: number;
  collapseAllSignal?: number;
}) {
  const hasChildren = node.children.length > 0;
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (expandAllSignal > 0) setOpen(true);
  }, [expandAllSignal]);

  useEffect(() => {
    if (collapseAllSignal > 0) setOpen(false);
  }, [collapseAllSignal]);

  return (
    <div className="relative">
      {node.nivel > 0 && (
        <>
          {/* Linha vertical */}
          <div className={cn(
            "absolute -left-[14px] top-0 w-px bg-border",
            isLast ? "h-5" : "h-full"
          )} />
          {/* Linha horizontal */}
          <div className="absolute -left-[14px] top-5 w-3 h-px bg-border" />
        </>
      )}

      <Collapsible open={open} onOpenChange={setOpen}>
        <summary
          className={cn(
            "group flex items-center gap-2 py-1.5 px-2 rounded-sm hover:bg-muted/40 transition-colors list-none [&::-webkit-details-marker]:hidden",
            hasChildren && "cursor-pointer"
          )}
          onClick={(e) => {
            e.preventDefault();
            if (hasChildren) setOpen((current) => !current);
          }}
        >
          {hasChildren ? (
            <div className="flex size-5 shrink-0 items-center justify-center rounded-sm text-muted-foreground transition-all">
              {open ? <FolderOpen className="size-4" /> : <Folder className="size-4" />}
            </div>
          ) : (
            <div className="size-5 shrink-0" />
          )}

          <div className="flex flex-1 items-center gap-2 min-w-0">
            <span className="inline-flex shrink-0 items-center rounded-sm bg-muted/50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-muted-foreground">
              {node.codigo}
            </span>
            <span className="truncate text-sm font-medium text-foreground">{node.nome}</span>
            {!node.ativo && <span className="shrink-0 rounded-sm bg-red-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-red-700">Inativo</span>}
            
            <div className="hidden items-center gap-2 text-[10px] text-muted-foreground md:flex ml-auto">
              <span className="bg-muted/50 px-1.5 py-0.5 rounded-sm">{getCategoriaLabel(node.categoria_rfb)}</span>
              <span className="bg-muted/50 px-1.5 py-0.5 rounded-sm">{node.tipo}</span>
              <span className="bg-muted/50 px-1.5 py-0.5 rounded-sm">{node.natureza}</span>
            </div>
          </div>

          <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button
              variant="ghost"
              size="icon"
              className="size-7 rounded-sm"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onEdit(node);
              }}
            >
              <Pencil className="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 rounded-sm text-red-600 hover:bg-red-50 hover:text-red-700"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(node.id);
              }}
              disabled={node.is_sistema}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </summary>

        {hasChildren && (
          <CollapsibleContent>
            <div className="relative ml-6 mt-1 flex flex-col gap-0.5">
              {node.children.map((child, index) => (
                <PlanoTreeItem
                  key={child.id}
                  node={child}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  isLast={index === node.children.length - 1}
                  expandAllSignal={expandAllSignal}
                  collapseAllSignal={collapseAllSignal}
                />
              ))}
            </div>
          </CollapsibleContent>
        )}
      </Collapsible>
    </div>
  );
}

function buildPlanoTree(planos: PlanoConta[]): PlanoContaTreeNode[] {
  const childrenByParent = new Map<string | null, PlanoConta[]>();

  for (const plano of planos) {
    const key = plano.parent_id ?? null;
    const current = childrenByParent.get(key) ?? [];
    current.push(plano);
    childrenByParent.set(key, current);
  }

  const sortPlanos = (items: PlanoConta[]) =>
    [...items].sort((a, b) => (a.ordem - b.ordem) || a.codigo.localeCompare(b.codigo));

  const walk = (parentId: string | null, nivel: number): PlanoContaTreeNode[] =>
    sortPlanos(childrenByParent.get(parentId) ?? []).map((plano) => ({
      ...plano,
      nivel,
      children: walk(plano.id, nivel + 1),
    }));

  return walk(null, 0);
}

function filterPlanoTree(nodes: PlanoContaTreeNode[], query: string): PlanoContaTreeNode[] {
  const q = query.trim().toLowerCase();
  if (!q) return nodes;

  return nodes
    .map((node) => {
      const children = filterPlanoTree(node.children, q);
      const selfMatch =
        node.codigo.toLowerCase().includes(q) ||
        node.nome.toLowerCase().includes(q) ||
        (node.categoria_rfb ?? "").toLowerCase().includes(q) ||
        node.tipo.toLowerCase().includes(q) ||
        node.natureza.toLowerCase().includes(q);

      if (!selfMatch && children.length === 0) return null;
      return { ...node, children };
    })
    .filter((node): node is PlanoContaTreeNode => node !== null);
}

function PlanoModal({
  initial,
  planos,
  onLimitReached,
  onClose,
}: {
  initial?: PlanoConta | null;
  planos: PlanoConta[];
  onLimitReached: (limit: PlanoContaLimitState) => void;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!initial;

  const [form, setForm] = useState<PlanoContaForm>({
    codigo: initial?.codigo ?? "",
    nome: initial?.nome ?? "",
    descricao: initial?.descricao ?? "",
    tipo: initial?.tipo ?? "DESPESA",
    natureza: initial?.natureza ?? "ANALITICA",
    categoria_rfb: initial?.categoria_rfb ?? getCategoriaDefault(initial?.tipo ?? "DESPESA"),
    ordem: initial?.ordem ?? 0,
    parent_id: initial?.parent_id ?? "",
    ativo: initial?.ativo ?? true,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit && initial) {
        return apiFetch(`/financeiro/planos-conta/${initial.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            nome: form.nome,
            descricao: form.descricao || null,
            categoria_rfb: form.categoria_rfb,
            ordem: form.ordem,
            ativo: form.ativo,
          }),
        });
      }

      return apiFetch("/financeiro/planos-conta/", {
        method: "POST",
        body: JSON.stringify({
          codigo: form.codigo,
          nome: form.nome,
          descricao: form.descricao || null,
          tipo: form.tipo,
          natureza: form.natureza,
          categoria_rfb: form.categoria_rfb,
          ordem: form.ordem,
          parent_id: form.parent_id || null,
        }),
      });
    },
    onSuccess: async () => {
      toast.success(isEdit ? "Plano atualizado." : "Plano criado.");
      await queryClient.invalidateQueries({ queryKey: ["planos-conta"] });
      onClose();
    },
    onError: (err: Error) => {
      const limit = parsePlanoContaLimitError(err.message);
      if (limit) {
        onLimitReached(limit);
        toast.error(limit.message);
        return;
      }

      toast.error(err.message || "Erro ao salvar.");
    },
  });

  const parentOptions = useMemo(() => {
    return planos
      .filter((plano) => plano.tipo === form.tipo)
      .sort((a, b) => a.codigo.localeCompare(b.codigo));
  }, [planos, form.tipo]);

  const inputClass =
    "w-full h-8 text-xs rounded-sm border border-border bg-background px-3 py-1 text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";

  return (
    <Dialog defaultOpen onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-full max-w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-sm">
        <DialogHeader className="border-b border-border px-6 py-5">
          <DialogTitle>{isEdit ? "Editar Plano de Conta" : "Novo Plano de Conta"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Atualize a categoria, a descrição e a ordem de exibição."
              : "Cadastre uma categoria do plano de contas com hierarquia e classificação RFB."}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
        >
          <DialogBody className="flex flex-col gap-4 p-5">
            {isEdit ? (
              <div className="rounded-sm border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Código, tipo, natureza e pai ficam preservados na edição. Para alterar a estrutura, crie um novo plano.
              </div>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-[140px_minmax(0,1fr)]">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Código <span className="text-destructive">*</span>
                </label>
                <Input
                  required
                  className={inputClass}
                  value={form.codigo}
                  placeholder="1.01"
                  onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))}
                  disabled={isEdit}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Nome <span className="text-destructive">*</span>
                </label>
                <Input
                  required
                  className={inputClass}
                  value={form.nome}
                  placeholder="Ex: Venda de Produtos Vegetais"
                  onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Tipo <span className="text-destructive">*</span>
                </label>
                <Select
                  value={form.tipo}
                  onValueChange={(value) => {
                    const tipo = value as PlanoContaForm["tipo"];
                    setForm((f) => ({
                      ...f,
                      tipo,
                      categoria_rfb: getCategoriaDefault(tipo),
                      parent_id: "",
                    }));
                  }}
                  disabled={isEdit}
                >
                  <SelectTrigger className="h-8 rounded-sm border-border bg-background px-3 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    <SelectItem value="DESPESA">Despesa</SelectItem>
                    <SelectItem value="RECEITA">Receita</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Natureza <span className="text-destructive">*</span>
                </label>
                <Select
                  value={form.natureza}
                  onValueChange={(value) => setForm((f) => ({ ...f, natureza: value as PlanoContaForm["natureza"] }))}
                  disabled={isEdit}
                >
                  <SelectTrigger className="h-8 rounded-sm border-border bg-background px-3 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    <SelectItem value="ANALITICA">Analítica</SelectItem>
                    <SelectItem value="SINTETICA">Sintética</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Ordem
                </label>
                <Input
                  type="number"
                  min="0"
                  step="1"
                  className={inputClass}
                  value={form.ordem}
                  onChange={(e) => setForm((f) => ({ ...f, ordem: Number(e.target.value) || 0 }))}
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Categoria RFB <span className="text-destructive">*</span>
                </label>
                <Select
                  value={form.categoria_rfb}
                  onValueChange={(value) => setForm((f) => ({ ...f, categoria_rfb: value as CategoriaRFB }))}
                >
                  <SelectTrigger className="h-8 rounded-sm border-border bg-background px-3 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {CATEGORIAS_RFB.map((categoria) => (
                      <SelectItem key={categoria} value={categoria}>
                        {getCategoriaLabel(categoria)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {!isEdit ? (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Conta Pai
                  </label>
                  <Select
                    value={form.parent_id || "__root__"}
                    onValueChange={(value) =>
                      setForm((f) => ({ ...f, parent_id: value === "__root__" ? "" : value }))
                    }
                  >
                    <SelectTrigger className="h-8 rounded-sm border-border bg-background px-3 text-sm">
                      <SelectValue placeholder="Sem pai" />
                    </SelectTrigger>
                    <SelectContent className="rounded-sm">
                      <SelectItem value="__root__">Sem pai</SelectItem>
                      {parentOptions.map((plano) => (
                        <SelectItem key={plano.id} value={plano.id}>
                          {plano.codigo} - {plano.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Situação
                  </label>
                  <div className="flex h-8 items-center justify-between rounded-sm border border-border bg-background px-3 text-sm text-muted-foreground">
                    <span>{form.ativo ? "Ativo" : "Inativo"}</span>
                    <Switch
                      checked={form.ativo}
                      onCheckedChange={(checked) => setForm((f) => ({ ...f, ativo: checked }))}
                      size="sm"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Descrição
              </label>
              <Input
                className={inputClass}
                value={form.descricao}
                placeholder="Opcional"
                onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
              />
            </div>
          </DialogBody>

          <DialogFooter className="border-t border-border px-6 py-4">
            <div className="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="outline" size="sm" onClick={onClose} className="rounded-sm">
                Cancelar
              </Button>
              <Button 
                type="submit" 
                variant="outline"
                size="sm"
                disabled={mutation.isPending}
                className="rounded-sm border-primary text-primary hover:bg-primary/5 shadow-sm"
              >
                {mutation.isPending ? <Loader2 size={14} className="animate-spin mr-2" /> : <Plus size={14} className="mr-2" />}
                {mutation.isPending ? "Salvando..." : "Salvar"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function PlanosContaPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const hasHydrated = useAppStore((s) => s._hasHydrated);
  const tenant = useAppStore((s) => s.tenant);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<PlanoConta | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; planoId?: string }>({ open: false });
  const [filtro, setFiltro] = useState("");
  const [limitState, setLimitState] = useState<PlanoContaLimitState | null>(null);
  const [expandAllSignal, setExpandAllSignal] = useState(0);
  const [collapseAllSignal, setCollapseAllSignal] = useState(0);
  const [isExpanded, setIsExpanded] = useState(true);

  const { data: planos = [], isLoading } = useQuery({
    queryKey: ["planos-conta"],
    queryFn: () => apiFetch<PlanoConta[]>("/financeiro/planos-conta/"),
    enabled: hasHydrated && !!tenant?.id,
  });
  const { data: account } = useQuery<BillingAccountResponse>({
    queryKey: ["billing", "account"],
    queryFn: () => apiFetch("/billing/my-account"),
    enabled: hasHydrated && !!tenant?.id,
  });

  const planosTree = useMemo(() => buildPlanoTree(planos), [planos]);
  const planosFiltrados = useMemo(() => filterPlanoTree(planosTree, filtro), [planosTree, filtro]);
  const planoContaLimitFromAccount = useMemo(
    () => getPlanoContaLimitFromAccount(account, planos.length),
    [account, planos.length]
  );
  const limitStateEffective = limitState ?? planoContaLimitFromAccount;
  const totalAnaliticas = useMemo(
    () => planos.filter((plano) => plano.natureza === "ANALITICA").length,
    [planos]
  );

  const seedMutation = useMutation({
    mutationFn: () => apiFetch("/financeiro/planos-conta/seed", { method: "POST" }),
    onSuccess: async () => {
      toast.success("Categorias padrão adicionadas ao plano de contas.");
      await queryClient.invalidateQueries({ queryKey: ["planos-conta"] });
    },
    onError: (err: Error) => {
      const limit = parsePlanoContaLimitError(err.message);
      if (limit) {
        setLimitState(limit);
        toast.error(limit.message);
        return;
      }

      toast.error(err.message || "Erro ao carregar categorias padrão.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/financeiro/planos-conta/${id}`, { method: "DELETE" }),
    onSuccess: async () => {
      toast.success("Plano removido.");
      await queryClient.invalidateQueries({ queryKey: ["planos-conta"] });
    },
    onError: (err: Error) => toast.error(err.message || "Erro ao remover."),
  });

  const closeModal = () => {
    setShowModal(false);
    setEditing(null);
  };

  const openCreateModal = () => {
    if (limitStateEffective && !editing) {
      toast.error(limitStateEffective.message);
      return;
    }

    setShowModal(true);
  };

  useEffect(() => {
    if (limitState?.max !== undefined && planos.length < limitState.max) {
      setLimitState(null);
    }
  }, [limitState, planos.length]);

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Planos de Conta"
        description="Cadastre e organize as categorias de receita e despesa usadas no financeiro."
        breadcrumbs={[
          { label: "Financeiro", href: "/dashboard/financeiro" },
          { label: "Planos de Conta" },
        ]}
        icon={<FolderTree className="text-primary" size={22} />}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending || Boolean(limitStateEffective)}
              className="rounded-sm"
            >
              {seedMutation.isPending ? (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              ) : (
                <RotateCcw className="mr-1.5 size-3.5" />
              )}
              Carregar padrão
            </Button>
            <Button 
              variant="outline"
              size="sm"
              onClick={openCreateModal} 
              disabled={Boolean(limitStateEffective)}
              className="rounded-sm"
            >
              <Plus className="mr-1.5 size-3.5" />
              Novo Plano
            </Button>
          </div>
        }
      />

      {limitStateEffective ? (
        <Card variant="warning">
          <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-card-title">Limite do plano atingido</p>
              <p className="text-sm text-card-description">{limitStateEffective.message}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="border-alert-warning-border bg-card/80"
              onClick={() => router.push("/dashboard/settings/billing")}
            >
              Fazer upgrade
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border-l-4 border-l-primary/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-black uppercase text-primary/80 tracking-[0.24em]">Total de Planos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-primary">{isLoading ? "..." : planos.length}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-black uppercase text-amber-700/80 tracking-[0.24em]">Contas Analíticas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-amber-700">{isLoading ? "..." : totalAnaliticas}</div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-blue-500/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-black uppercase text-blue-700/80 tracking-[0.24em]">Contas Sintéticas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-black text-blue-700">{isLoading ? "..." : planosTree.length}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 border-b border-border pb-4">
          <div className="space-y-1">
            <CardTitle className="text-sm font-semibold">Estrutura do Plano</CardTitle>
            <p className="text-sm text-muted-foreground">
              Visualização hierárquica com grupos sintéticos e contas analíticas.
            </p>
          </div>
          <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:w-64">
              <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Filtrar código, nome, tipo ou categoria..."
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
              />
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Expandir Tudo</span>
              <Switch
                checked={isExpanded}
                onCheckedChange={(checked) => {
                  setIsExpanded(checked);
                  if (checked) setExpandAllSignal((s) => s + 1);
                  else setCollapseAllSignal((s) => s + 1);
                }}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {isLoading ? (
            <div className="space-y-3">
              <div className="h-14 rounded-sm bg-muted/60" />
              <div className="h-14 rounded-sm bg-muted/60" />
              <div className="h-14 rounded-sm bg-muted/60" />
            </div>
          ) : planosFiltrados.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              Nenhum plano encontrado com o filtro atual.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {planosFiltrados.map((node) => (
                <PlanoTreeItem
                  key={node.id}
                  node={node}
                  onEdit={setEditing}
                  onDelete={(planoId) => setDeleteDialog({ open: true, planoId })}
                  expandAllSignal={expandAllSignal}
                  collapseAllSignal={collapseAllSignal}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ open })}>
        <DialogContent className="w-full max-w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-sm">
          <DialogHeader className="border-b border-border px-6 py-5">
            <DialogTitle>Remover Plano de Conta</DialogTitle>
            <DialogDescription>
              Esta ação não pode ser desfeita. Confirme apenas se o plano não estiver sendo usado.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="border-t border-border px-6 py-4">
            <div className="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDeleteDialog({ open: false })}>
                Cancelar
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="rounded-sm"
                onClick={() => {
                  if (deleteDialog.planoId) {
                    deleteMutation.mutate(deleteDialog.planoId);
                  }
                  setDeleteDialog({ open: false });
                }}
              >
                Remover
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {(showModal || editing) && (
        <PlanoModal
          initial={editing}
          planos={planos}
          onLimitReached={(limit) => {
            setLimitState(limit);
            closeModal();
          }}
          onClose={closeModal}
        />
      )}
    </div>
  );
}
