"use client";

import { useState, useRef, useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  ClipboardList, Search, Filter, MoreHorizontal,
  CheckCircle2, XCircle, Clock, AlertCircle,
  Package, Warehouse, Calendar, DollarSign, Plus, FileText, Save,
  Trash2, Lock, Edit
} from "lucide-react";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, 
  DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuSeparator 
} from "@/components/ui/dropdown-menu";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter 
} from "@/components/ui/sheet";
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger, DialogBody 
} from "@/components/ui/dialog";
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "@/components/ui/select";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Label } from "@/components/ui/label";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { CotacaoSolicitacaoDialog } from "@/components/compras/CotacaoSolicitacaoDialog";
import { CotacaoMultiItemDialog } from "@/components/compras/CotacaoMultiItemDialog";
import { CotacaoSolicitacaoList } from "@/components/compras/CotacaoSolicitacaoList";

interface SolicitacaoItem {
  id: string;
  produto_id: string;
  produto_nome?: string | null;
  deposito_id: string;
  deposito_nome?: string | null;
  quantidade_solicitada: number;
  unidade: string;
  quantidade_alocada: number;
  status_atendimento: "PENDENTE" | "PARCIAL" | "ATENDIDO";
  valor_ultima_compra?: number | null;
  data_ultima_compra?: string | null;
}

interface Solicitacao {
  id: string;
  numero?: string | null;
  solicitante_id?: string | null;
  solicitante_nome?: string | null;
  itens: SolicitacaoItem[];
  // Atalho legado — espelha o primeiro item.
  item_id: string;
  produto_nome: string;
  deposito_id: string;
  deposito_nome: string;
  quantidade_solicitada: number;
  unidade: string;
  origem: string;
  status: "ABERTA" | "EM_ANALISE" | "APROVADA" | "ENCERRADA" | "CANCELADA";
  created_at: string;
}

const atendimentoConfig = {
  PENDENTE: { label: "Pendente", color: "bg-slate-100 text-slate-600 border-slate-200" },
  PARCIAL: { label: "Parcial", color: "bg-amber-100 text-amber-700 border-amber-200" },
  ATENDIDO: { label: "Atendido", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
};

interface ProdutoItem {
  id: string;
  nome: string;
  unidade_medida?: string;
}

interface DepositoItem {
  id: string;
  nome: string;
}

interface NovaSolicitacaoItemInput {
  produto_id: string;
  deposito_id: string;
  quantidade_solicitada: string;
  unidade: string;
}

interface NovaSolicitacaoInput {
  itens: NovaSolicitacaoItemInput[];
}

interface NovaSolicitacaoPayload {
  itens: {
    produto_id: string;
    deposito_id: string;
    quantidade_solicitada: number;
    unidade: string;
  }[];
  origem: "MANUAL";
}

const statusConfig = {
  ABERTA: { label: "Aberta", color: "bg-blue-100 text-blue-700 border-blue-200", icon: Clock },
  EM_ANALISE: { label: "Em Análise", color: "bg-amber-100 text-amber-700 border-amber-200", icon: Search },
  APROVADA: { label: "Aprovada", color: "bg-emerald-100 text-emerald-700 border-emerald-200", icon: CheckCircle2 },
  ENCERRADA: { label: "Encerrada", color: "bg-slate-200 text-slate-700 border-slate-300", icon: Lock },
  CANCELADA: { label: "Cancelada", color: "bg-red-100 text-red-700 border-red-200", icon: XCircle },
};

const formatQuantidadePtBR = (value: number) =>
  value.toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });

function ProdutoCombobox({ value, onChange, produtos, disabled }: {
  value: string;
  onChange: (val: string) => void;
  produtos: ProdutoItem[];
  disabled?: boolean;
}) {
  const [aberto, setAberto] = useState(false);
  const [termo, setTermo] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickFora(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAberto(false);
      }
    }
    document.addEventListener("mousedown", handleClickFora);
    return () => document.removeEventListener("mousedown", handleClickFora);
  }, []);

  const selecionado = produtos.find(p => p.id === value);
  const filtrados = produtos.filter(p => p.nome.toLowerCase().includes(termo.toLowerCase()));

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
        <Input
          disabled={disabled}
          placeholder="Buscar produto..."
          className="h-8 rounded-sm text-xs pl-7"
          value={aberto ? termo : (selecionado?.nome ?? "")}
          onFocus={() => { setAberto(true); setTermo(""); }}
          onChange={e => setTermo(e.target.value)}
        />
      </div>
      {aberto && (
        <div className="absolute z-50 mt-1 w-full rounded-sm border bg-popover shadow-md">
          <ScrollArea className="max-h-48">
            {filtrados.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">Nenhum produto encontrado.</p>
            ) : (
              filtrados.map(p => (
                <button
                  key={p.id}
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent"
                  onClick={() => { onChange(p.id); setAberto(false); }}
                >
                  <Package className="size-3.5 text-muted-foreground shrink-0" />
                  <span className="truncate">{p.nome}</span>
                  {p.unidade_medida && (
                    <span className="ml-auto text-muted-foreground shrink-0 text-[10px]">{p.unidade_medida}</span>
                  )}
                </button>
              ))
            )}
          </ScrollArea>
        </div>
      )}
    </div>
  );
}

export function SolicitacoesClient({ initialData }: { initialData: Solicitacao[] }) {
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [cotacaoDialogOpen, setCotacaoDialogOpen] = useState(false);
  const [selectedSolicitacao, setSelectedSolicitacao] = useState<Solicitacao | null>(null);
  
  // Sheet State
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedSolicitacaoForSheet, setSelectedSolicitacaoForSheet] = useState<Solicitacao | null>(null);

  // Dialog State
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Encerrar solicitação (ação exclusiva do solicitante)
  const [encerrarAlvo, setEncerrarAlvo] = useState<Solicitacao | null>(null);

  // Adicionar item a uma solicitação já existente
  const [addItemDialogOpen, setAddItemDialogOpen] = useState(false);

  // Editar item
  const [editItem, setEditItem] = useState<{ id: string, produto_nome: string, quantidade: number, unidade: string } | null>(null);
  const [editQuantidade, setEditQuantidade] = useState<string>("");

  const queryClient = useQueryClient();

  // Queries
  const { data: solicitacoes = initialData, isLoading } = useQuery<Solicitacao[]>({
    queryKey: ["compras-solicitacoes", filterStatus],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.append("status", filterStatus);
      return apiFetch(`/compras/solicitacoes?${params.toString()}`);
    },
    initialData: filterStatus === null ? initialData : undefined,
  });

  const { data: produtos = [] } = useQuery<ProdutoItem[]>({
    queryKey: ["cadastros-produtos", "compras"],
    queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
    enabled: createDialogOpen || addItemDialogOpen,
  });

  const { data: depositos = [] } = useQuery<DepositoItem[]>({
    queryKey: ["estoque-depositos"],
    queryFn: () => apiFetch("/estoque/depositos"),
    enabled: createDialogOpen || addItemDialogOpen,
  });

  // Mutations
  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => 
      apiFetch(`/compras/solicitacoes/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Status atualizado com sucesso!");
      
      // Update local state for active sheet if open
      if (selectedSolicitacaoForSheet && selectedSolicitacaoForSheet.id === variables.id) {
        setSelectedSolicitacaoForSheet(prev => prev ? { ...prev, status: variables.status as Solicitacao["status"] } : null);
      }
    },
    onError: () => toast.error("Falha ao atualizar status."),
  });

  const createSolicitacaoMutation = useMutation({
    mutationFn: (data: NovaSolicitacaoPayload) =>
      apiFetch("/compras/solicitacoes", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Solicitação de compra criada com sucesso!");
      setCreateDialogOpen(false);
      form.reset();
    },
    onError: () => toast.error("Falha ao criar solicitação."),
  });

  const addItemMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: NovaSolicitacaoPayload["itens"][number] }) =>
      apiFetch(`/compras/solicitacoes/${id}/itens`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: (updated: Solicitacao) => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Item adicionado à solicitação!");
      setAddItemDialogOpen(false);
      addItemForm.reset({ produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" });
      setSelectedSolicitacaoForSheet(updated);
    },
    onError: () => toast.error("Falha ao adicionar item."),
  });

  const deleteItemMutation = useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) =>
      apiFetch(`/compras/solicitacoes/${id}/itens/${itemId}`, {
        method: "DELETE",
      }),
    onSuccess: (updated: Solicitacao) => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Item removido com sucesso!");
      setSelectedSolicitacaoForSheet(updated);
    },
    onError: () => toast.error("Falha ao remover item."),
  });

  const editItemMutation = useMutation({
    mutationFn: ({ id, itemId, quantidade_solicitada }: { id: string; itemId: string; quantidade_solicitada: number }) =>
      apiFetch(`/compras/solicitacoes/${id}/itens/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ quantidade_solicitada }),
      }),
    onSuccess: (updated: Solicitacao) => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Quantidade atualizada com sucesso!");
      setSelectedSolicitacaoForSheet(updated);
      setEditItem(null);
    },
    onError: () => toast.error("Falha ao atualizar quantidade."),
  });

  const addItemForm = useForm<NovaSolicitacaoItemInput>({
    defaultValues: { produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" },
  });

  const onAddItemProdutoChange = (prodId: string) => {
    addItemForm.setValue("produto_id", prodId);
    const selectedProd = produtos.find(p => p.id === prodId);
    if (selectedProd?.unidade_medida) {
      addItemForm.setValue("unidade", selectedProd.unidade_medida);
    }
  };

  const onAddItemSubmit = (data: NovaSolicitacaoItemInput) => {
    if (!selectedSolicitacaoForSheet) return;
    addItemMutation.mutate({
      id: selectedSolicitacaoForSheet.id,
      data: {
        produto_id: data.produto_id,
        deposito_id: data.deposito_id,
        quantidade_solicitada: parseFloat(data.quantidade_solicitada),
        unidade: data.unidade,
      },
    });
  };

  const encerrarMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/compras/solicitacoes/${id}/encerrar`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      toast.success("Solicitação encerrada.");
      setEncerrarAlvo(null);
      setSheetOpen(false);
    },
    onError: (err: any) => toast.error(err?.message || "Apenas quem criou a solicitação pode encerrá-la."),
  });

  // Form setup — lista dinâmica de itens (produto + depósito + quantidade)
  const form = useForm<NovaSolicitacaoInput>({
    defaultValues: {
      itens: [{ produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" }],
    }
  });
  const { fields: itemFields, append: appendItem, remove: removeItem } = useFieldArray({
    control: form.control,
    name: "itens",
  });

  const onProdutoChange = (index: number, prodId: string) => {
    form.setValue(`itens.${index}.produto_id`, prodId);
    const selectedProd = produtos.find(p => p.id === prodId);
    if (selectedProd?.unidade_medida) {
      form.setValue(`itens.${index}.unidade`, selectedProd.unidade_medida);
    }
  };

  const handleAddCotacaoForSolicitacao = (solicitacao: Solicitacao) => {
    if (solicitacao.status === "CANCELADA") {
      toast.warning("Não é possível adicionar cotação em uma solicitação cancelada.");
      return;
    }
    if (solicitacao.status === "ENCERRADA") {
      toast.warning("Não é possível adicionar cotação em uma solicitação encerrada.");
      return;
    }
    if (solicitacao.status !== "APROVADA") {
      toast.warning("Aprove a solicitação antes de registrar uma cotação.");
      return;
    }

    setSelectedSolicitacao(solicitacao);
    setSheetOpen(false);
    setCotacaoDialogOpen(true);
  };

  const handleIniciarAnalise = (solicitacao: Solicitacao) => {
    if (solicitacao.status === "EM_ANALISE") {
      toast.info("Esta solicitação já está em análise.");
      return;
    }

    if (solicitacao.status === "APROVADA") {
      toast.warning("Solicitações aprovadas não podem voltar para análise.");
      return;
    }

    if (solicitacao.status === "CANCELADA") {
      toast.warning("Solicitações canceladas não podem entrar em análise.");
      return;
    }

    updateStatusMutation.mutate({ id: solicitacao.id, status: "EM_ANALISE" });
  };

  const onSubmit = (data: NovaSolicitacaoInput) => {
    createSolicitacaoMutation.mutate({
      itens: data.itens.map((item) => ({
        produto_id: item.produto_id,
        deposito_id: item.deposito_id,
        quantidade_solicitada: parseFloat(item.quantidade_solicitada),
        unidade: item.unidade,
      })),
      origem: "MANUAL",
    });
  };

  // DataTable column definitions
  const columns: ColumnDef<Solicitacao>[] = [
    {
      id: "produto_nome",
      header: "Solicitação / Itens",
      accessorKey: "produto_nome",
      sortable: true,
      cell: (_value, row) => (
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-sm bg-muted flex items-center justify-center shrink-0">
            <Package className="size-4 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              {row.numero && (
                <span className="font-mono text-[10px] font-bold text-muted-foreground">{row.numero}</span>
              )}
            </div>
            {row.itens.length > 1 ? (
              <div className="space-y-0.5 mt-0.5">
                {row.itens.map((i) => (
                  <div key={i.id} className="font-mono text-[10px] text-muted-foreground truncate">
                    {i.produto_nome}
                  </div>
                ))}
              </div>
            ) : (
              <span className="font-semibold block text-xs truncate">
                {row.itens[0]?.produto_nome || row.produto_nome}
              </span>
            )}
            <span className="text-[9px] text-muted-foreground uppercase font-bold flex items-center gap-1 mt-0.5">
              <Warehouse className="size-2.5" />
              {row.itens.length > 1 ? `${row.itens.length} itens` : row.deposito_nome}
            </span>
          </div>
        </div>
      )
    },
    {
      id: "quantidade_solicitada",
      header: "Quantidade",
      accessorKey: "quantidade_solicitada",
      sortable: true,
      cell: (value, row) =>
        row.itens.length > 1 ? (
          <div className="space-y-0.5">
            {row.itens.map((i) => (
              <div key={i.id} className="font-mono text-[10px] text-muted-foreground">
                {i.quantidade_solicitada.toFixed(1)} {i.unidade}
              </div>
            ))}
          </div>
        ) : (
          <div className="font-mono font-semibold text-xs">
            {Number(value).toFixed(1)} <span className="text-muted-foreground text-[10px]">{row.unidade}</span>
          </div>
        )
    },
    {
      id: "solicitante_nome",
      header: "Solicitante",
      accessorKey: "solicitante_nome",
      sortable: true,
      cell: (value) => (
        <span className="text-xs font-medium">{value || "—"}</span>
      )
    },
    {
      id: "origem",
      header: "Origem",
      accessorKey: "origem",
      sortable: true,
      cell: (value) => (
        <Badge variant="secondary" className="rounded-sm text-[9px] font-bold uppercase py-0 px-1.5 h-5 flex items-center w-fit border border-muted-foreground/10">
          {value}
        </Badge>
      )
    },
    {
      id: "created_at",
      header: "Data",
      accessorKey: "created_at",
      sortable: true,
      cell: (value) => (
        <span className="text-[11px] text-muted-foreground font-mono">
          {format(new Date(value), "dd/MM/yyyy HH:mm")}
        </span>
      )
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      sortable: true,
      cell: (value) => {
        const config = statusConfig[value as keyof typeof statusConfig] || { label: value, color: "", icon: Clock };
        const Icon = config.icon;
        return (
          <Badge variant="outline" className={cn("text-[9px] font-bold uppercase rounded-sm border py-0 px-1.5 h-5 flex items-center w-fit gap-1", config.color)}>
            <Icon className="size-2.5" />
            {config.label}
          </Badge>
        );
      }
    },
    {
      id: "acoes",
      header: "",
      sortable: false,
      filterable: false,
      exportable: false,
      isActionColumn: true,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:bg-primary/10 hover:text-primary rounded-sm"
            title="Ver Detalhes"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedSolicitacaoForSheet(row);
              setSheetOpen(true);
            }}
          >
            <Edit className="size-3.5" />
          </Button>

          {row.status === "ABERTA" && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-amber-600 hover:text-amber-700 hover:bg-amber-100 rounded-sm"
              title="Iniciar Análise"
              onClick={(e) => {
                e.stopPropagation();
                handleIniciarAnalise(row);
              }}
            >
              <Search className="size-3.5" />
            </Button>
          )}

          {(row.status === "ABERTA" || row.status === "EM_ANALISE") && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-100 rounded-sm"
              title="Aprovar"
              onClick={(e) => {
                e.stopPropagation();
                updateStatusMutation.mutate({ id: row.id, status: "APROVADA" });
              }}
            >
              <CheckCircle2 className="size-3.5" />
            </Button>
          )}

          {row.status === "APROVADA" && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-primary hover:text-primary hover:bg-primary/10 rounded-sm"
              title="Adicionar Cotação"
              onClick={(e) => {
                e.stopPropagation();
                handleAddCotacaoForSolicitacao(row);
              }}
            >
              <DollarSign className="size-3.5" />
            </Button>
          )}

          {(row.status !== "CANCELADA" && row.status !== "ENCERRADA" && row.status !== "APROVADA") && (
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive hover:bg-destructive/10 rounded-sm"
              title="Cancelar"
              onClick={(e) => {
                e.stopPropagation();
                updateStatusMutation.mutate({ id: row.id, status: "CANCELADA" });
              }}
            >
              <XCircle className="size-3.5" />
            </Button>
          )}
        </div>
      )
    }
  ];

  return (
    <div className="flex-1 p-6 space-y-6 max-w-6xl w-full">
      <PageHeader
        title="Solicitações de Compra"
        description="Gerencie as solicitações internas e reposições automáticas de estoque."
        icon={<ClipboardList className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Suprimentos", href: "/suprimentos" },
          { label: "Compras", href: "/suprimentos/compras" },
          { label: "Solicitações" }
        ]}
        actions={
          <div className="flex items-center gap-2.5">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Filter data-icon="inline-start" className="size-3.5 text-primary" />
                  {filterStatus ? statusConfig[filterStatus as keyof typeof statusConfig].label : "Todos os Status"}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 rounded-sm">
                <DropdownMenuItem className="text-xs" onClick={() => setFilterStatus(null)}>Todos os Status</DropdownMenuItem>
                <DropdownMenuSeparator />
                {Object.entries(statusConfig).map(([key, config]) => (
                  <DropdownMenuItem key={key} className="text-xs" onClick={() => setFilterStatus(key)}>
                    <config.icon data-icon="inline-start" className="size-3.5 text-primary" />
                    {config.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <Dialog open={createDialogOpen} onOpenChange={(open) => {
              setCreateDialogOpen(open);
              if (!open) {
                form.reset({ itens: [{ produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" }] });
              }
            }}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus data-icon="inline-start" className="size-4" />
                  Nova Solicitação
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[680px] rounded-sm p-0">
                <DialogHeader className="border-b px-4 py-2.5">
                  <div className="flex items-center gap-3">
                    <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                      <ClipboardList className="size-4" />
                    </div>
                    <div className="min-w-0">
                      <DialogTitle>Criar Solicitação de Compra</DialogTitle>
                      <DialogDescription className="truncate text-xs leading-tight">
                        Informe um ou mais itens (produto, depósito e quantidade) para abrir a solicitação.
                      </DialogDescription>
                    </div>
                  </div>
                </DialogHeader>

                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
                    <DialogBody className="grid min-h-0 flex-1 gap-3 overflow-y-auto px-4 py-2.5">
                      {itemFields.map((field, index) => (
                        <div key={field.id} className="grid gap-3 rounded-sm border border-dashed p-3">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-black uppercase text-muted-foreground">Item {index + 1}</span>
                            {itemFields.length > 1 && (
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="size-6 text-destructive hover:text-destructive"
                                aria-label="Remover item"
                                onClick={() => removeItem(index)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            )}
                          </div>

                          <FormField
                            control={form.control}
                            name={`itens.${index}.produto_id`}
                            rules={{ required: "Selecione um produto" }}
                            render={({ field }) => (
                              <FormItem className="space-y-1.5">
                                <FormLabel className="text-xs font-medium">Produto / Item *</FormLabel>
                                <FormControl>
                                  <ProdutoCombobox 
                                    value={field.value || ""} 
                                    onChange={(val) => { field.onChange(val); onProdutoChange(index, val); }} 
                                    produtos={produtos} 
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={form.control}
                            name={`itens.${index}.deposito_id`}
                            rules={{ required: "Selecione um depósito" }}
                            render={({ field }) => (
                              <FormItem className="space-y-1.5">
                                <FormLabel className="text-xs font-medium">Depósito de Destino *</FormLabel>
                                <Select value={field.value || "none"} onValueChange={(val) => field.onChange(val === "none" ? "" : val)}>
                                  <FormControl>
                                    <SelectTrigger className="h-8 rounded-sm text-xs">
                                      <SelectValue placeholder="Selecione o depósito..." />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent className="rounded-sm">
                                    <SelectItem value="none" className="text-xs">Selecione o depósito...</SelectItem>
                                    {depositos.map(d => (
                                      <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <div className="grid grid-cols-2 gap-3">
                            <FormField
                              control={form.control}
                              name={`itens.${index}.quantidade_solicitada`}
                              rules={{ required: "Informe a quantidade", min: { value: 0.1, message: "Mínimo de 0.1" } }}
                              render={({ field }) => (
                                <FormItem className="space-y-1.5">
                                  <FormLabel className="text-xs font-medium">Quantidade *</FormLabel>
                                  <FormControl>
                                    <Input
                                      type="number"
                                      step="0.1"
                                      placeholder="0.0"
                                      className="h-8 text-xs rounded-sm"
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />

                            <FormField
                              control={form.control}
                              name={`itens.${index}.unidade`}
                              rules={{ required: "Informe a unidade" }}
                              render={({ field }) => (
                                <FormItem className="space-y-1.5">
                                  <FormLabel className="text-xs font-medium">Unidade *</FormLabel>
                                  <FormControl>
                                    <Input
                                      type="text"
                                      placeholder="Ex: KG"
                                      className="h-8 text-xs rounded-sm uppercase font-mono disabled:opacity-75 disabled:bg-muted"
                                      disabled={true}
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                        </div>
                      ))}

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="w-full border-dashed"
                        onClick={() => appendItem({ produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" })}
                      >
                        <Plus data-icon="inline-start" className="size-3.5" />
                        Adicionar item
                      </Button>
                    </DialogBody>

                    <DialogFooter className="border-t px-4 py-2.5">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setCreateDialogOpen(false)}
                      >
                        <XCircle data-icon="inline-start" className="size-3.5" />
                        Cancelar
                      </Button>
                      <Button
                        type="submit"
                        variant="default"
                        size="sm"
                        disabled={createSolicitacaoMutation.isPending}
                      >
                        <Save data-icon="inline-start" className="size-3.5" />
                        {createSolicitacaoMutation.isPending ? "Criando..." : "Criar Solicitação"}
                      </Button>
                    </DialogFooter>
                  </form>
                </Form>
              </DialogContent>
            </Dialog>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={solicitacoes}
        isLoading={isLoading}
        searchPlaceholder="Buscar por produto ou depósito..."
        exportFileName="solicitacoes-compra"
        onRowClick={(row) => {
          setSelectedSolicitacaoForSheet(row);
          setSheetOpen(true);
        }}
      />

      {/* Details Slide panel */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="!w-[calc(100vw-24px)] !max-w-none sm:!max-w-none lg:!w-[65vw] 2xl:!w-[960px] flex flex-col gap-0 p-0 rounded-sm border-l">
          {selectedSolicitacaoForSheet && (
            <>
              <SheetHeader className="border-b px-4 pt-4 pb-3">
                <div className="flex items-start gap-3">
                  <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                    <ClipboardList className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <SheetTitle className="text-base">
                        {selectedSolicitacaoForSheet.numero || selectedSolicitacaoForSheet.produto_nome}
                      </SheetTitle>
                      <Badge
                        variant="outline"
                        className={cn(
                          "h-4 rounded-sm border text-[9px] font-bold uppercase",
                          statusConfig[selectedSolicitacaoForSheet.status]?.color
                        )}
                      >
                        {statusConfig[selectedSolicitacaoForSheet.status]?.label}
                      </Badge>
                    </div>
                    <SheetDescription className="text-xs leading-tight">
                      {selectedSolicitacaoForSheet.solicitante_nome
                        ? `Solicitado por ${selectedSolicitacaoForSheet.solicitante_nome}`
                        : "Detalhes da solicitação de compra."}
                    </SheetDescription>
                  </div>
                </div>
              </SheetHeader>

              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
                <div className="space-y-4">
                  <div className="rounded-sm border">
                    <div className="flex items-center justify-between border-b bg-muted/20 px-3 py-2">
                      <span className="text-[10px] font-black uppercase text-muted-foreground">Itens da Solicitação</span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={selectedSolicitacaoForSheet.status === "ENCERRADA" || selectedSolicitacaoForSheet.status === "CANCELADA"}
                        onClick={() => setAddItemDialogOpen(true)}
                      >
                        <Plus data-icon="inline-start" className="size-3.5" />
                        Adicionar item
                      </Button>
                    </div>
                    <div className="divide-y">
                      {selectedSolicitacaoForSheet.itens.map((item) => (
                        <div key={item.id} className="flex items-center gap-3 px-3 py-2">
                          <div className="flex size-8 items-center justify-center rounded-sm bg-muted shrink-0">
                            <Package className="size-4 text-muted-foreground" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <span className="block truncate text-xs font-semibold">{item.produto_nome}</span>
                            <span className="flex items-center gap-1 text-[9px] font-bold uppercase text-muted-foreground">
                              <Warehouse className="size-2.5" /> {item.deposito_nome}
                            </span>
                          </div>
                          <div className="text-right font-mono text-xs font-semibold shrink-0">
                            {formatQuantidadePtBR(item.quantidade_alocada)} / {formatQuantidadePtBR(item.quantidade_solicitada)}
                            <span className="ml-1 text-[10px] text-muted-foreground">{item.unidade}</span>
                          </div>
                          <Badge variant="outline" className={cn("h-4 rounded-sm border text-[9px] font-bold uppercase shrink-0", atendimentoConfig[item.status_atendimento]?.color)}>
                            {atendimentoConfig[item.status_atendimento]?.label}
                          </Badge>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-6 text-primary hover:bg-primary/10 shrink-0"
                            disabled={selectedSolicitacaoForSheet.status === "ENCERRADA" || selectedSolicitacaoForSheet.status === "CANCELADA"}
                            onClick={() => {
                              setEditItem({
                                id: item.id,
                                produto_nome: item.produto_nome || "",
                                quantidade: item.quantidade_solicitada,
                                unidade: item.unidade,
                              });
                              setEditQuantidade(item.quantidade_solicitada.toString());
                            }}
                            title="Editar Quantidade"
                          >
                            <Edit className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-6 text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0"
                            disabled={selectedSolicitacaoForSheet.status === "ENCERRADA" || selectedSolicitacaoForSheet.status === "CANCELADA"}
                            onClick={() => deleteItemMutation.mutate({ id: selectedSolicitacaoForSheet.id, itemId: item.id })}
                            title="Remover Item"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 rounded-sm border border-dashed bg-muted/20 p-4 text-xs">
                    <div>
                      <span className="mb-0.5 block text-[10px] font-bold uppercase text-muted-foreground">Origem da Solicitação</span>
                      <span className="flex items-center gap-1 font-bold uppercase">
                        <AlertCircle className="size-3.5 text-primary" /> {selectedSolicitacaoForSheet.origem}
                      </span>
                    </div>
                    <div>
                      <span className="mb-0.5 block text-[10px] font-bold uppercase text-muted-foreground">Criado Em</span>
                      <span className="flex items-center gap-1 font-mono font-bold uppercase">
                        <Calendar className="size-3.5 text-muted-foreground" /> {format(new Date(selectedSolicitacaoForSheet.created_at), "dd/MM/yyyy HH:mm")}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-sm border border-dashed bg-muted/10 p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="block text-[10px] font-bold uppercase text-muted-foreground">Controle de Status</span>
                    </div>
                    <div className="flex flex-col gap-2 sm:grid sm:grid-cols-2 lg:flex lg:flex-row lg:flex-wrap lg:items-center">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-center lg:w-40"
                        onClick={() => handleIniciarAnalise(selectedSolicitacaoForSheet)}
                        disabled={updateStatusMutation.isPending}
                      >
                        <Search data-icon="inline-start" className="size-3" />
                        Iniciar Análise
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-center lg:w-44"
                        onClick={() => {
                          if (selectedSolicitacaoForSheet.status === "CANCELADA") {
                            toast.warning("Não é possível aprovar uma solicitação cancelada.");
                            return;
                          }
                          if (selectedSolicitacaoForSheet.status === "ENCERRADA") {
                            toast.warning("Esta solicitação já está encerrada.");
                            return;
                          }
                          updateStatusMutation.mutate({ id: selectedSolicitacaoForSheet.id, status: "APROVADA" })
                        }}
                        disabled={selectedSolicitacaoForSheet.status === "APROVADA"}
                      >
                        <CheckCircle2 data-icon="inline-start" className="size-3" />
                        Aprovar Solicitação
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-center lg:w-40"
                        onClick={() => {
                          if (selectedSolicitacaoForSheet.status === "CANCELADA") {
                            toast.warning("Esta solicitação já está cancelada.");
                            return;
                          }
                          if (selectedSolicitacaoForSheet.status === "ENCERRADA") {
                            toast.warning("Não é possível cancelar uma solicitação encerrada.");
                            return;
                          }
                          updateStatusMutation.mutate({ id: selectedSolicitacaoForSheet.id, status: "CANCELADA" })
                        }}
                      >
                        <XCircle data-icon="inline-start" className="size-3" />
                        Cancelar Pedido
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-center lg:w-40"
                        onClick={() => {
                          if (selectedSolicitacaoForSheet.status === "CANCELADA") {
                            toast.warning("Não é possível encerrar uma solicitação cancelada.");
                            return;
                          }
                          if (selectedSolicitacaoForSheet.status === "ENCERRADA") {
                            toast.warning("Esta solicitação já está encerrada.");
                            return;
                          }
                          setEncerrarAlvo(selectedSolicitacaoForSheet);
                        }}
                      >
                        <Lock data-icon="inline-start" className="size-3" />
                        Encerrar
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full justify-center lg:ml-auto lg:w-44"
                        onClick={() => handleAddCotacaoForSolicitacao(selectedSolicitacaoForSheet)}
                      >
                        <DollarSign data-icon="inline-start" className="size-3" />
                        Adicionar Cotação
                      </Button>
                    </div>
                  </div>

                  {selectedSolicitacaoForSheet.status === "APROVADA" && (
                    <div className="space-y-3 border-t border-dashed pt-4">
                      <h4 className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-muted-foreground">
                        <FileText className="size-4 text-emerald-600" />
                        Cotações e Alocação por Fornecedor
                      </h4>
                      <div className="overflow-hidden rounded-sm border">
                        <CotacaoSolicitacaoList
                          solicitacaoId={selectedSolicitacaoForSheet.id}
                          itens={selectedSolicitacaoForSheet.itens}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <SheetFooter className="border-t px-4 py-3">
                <Button variant="outline" size="sm" onClick={() => setSheetOpen(false)}>
                  Fechar
                </Button>
              </SheetFooter>
            </>
          )}
        </SheetContent>
      </Sheet>

      <AlertDialog open={!!encerrarAlvo} onOpenChange={(open) => !open && setEncerrarAlvo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Encerrar solicitação?</AlertDialogTitle>
            <AlertDialogDescription>
              Itens ainda pendentes ou parcialmente atendidos deixarão de ser buscados pelo setor de compras.
              Só quem criou a solicitação pode encerrá-la — use apenas se o atendimento parcial já resolve a sua necessidade.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={encerrarMutation.isPending}
              onClick={() => encerrarAlvo && encerrarMutation.mutate(encerrarAlvo.id)}
            >
              Encerrar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={addItemDialogOpen} onOpenChange={(open) => {
        setAddItemDialogOpen(open);
        if (!open) addItemForm.reset({ produto_id: "", deposito_id: "", quantidade_solicitada: "", unidade: "UN" });
      }}>
        <DialogContent className="sm:max-w-[480px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Plus className="size-4" />
              </div>
              <div className="min-w-0">
                <DialogTitle>Adicionar Item</DialogTitle>
                <DialogDescription className="truncate text-xs leading-tight">
                  Inclui um novo produto nesta solicitação{selectedSolicitacaoForSheet?.numero ? ` (${selectedSolicitacaoForSheet.numero})` : ""}.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <Form {...addItemForm}>
            <form onSubmit={addItemForm.handleSubmit(onAddItemSubmit)} className="flex min-h-0 flex-1 flex-col">
              <DialogBody className="grid min-h-0 flex-1 gap-3 overflow-y-auto px-4 py-2.5">
                <FormField
                  control={addItemForm.control}
                  name="produto_id"
                  rules={{ required: "Selecione um produto" }}
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel className="text-xs font-medium">Produto / Item *</FormLabel>
                      <FormControl>
                        <ProdutoCombobox 
                          value={field.value || ""} 
                          onChange={(val) => { field.onChange(val); onAddItemProdutoChange(val); }} 
                          produtos={produtos} 
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={addItemForm.control}
                  name="deposito_id"
                  rules={{ required: "Selecione um depósito" }}
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel className="text-xs font-medium">Depósito de Destino *</FormLabel>
                      <Select value={field.value || "none"} onValueChange={(val) => field.onChange(val === "none" ? "" : val)}>
                        <FormControl>
                          <SelectTrigger className="h-8 rounded-sm text-xs">
                            <SelectValue placeholder="Selecione o depósito..." />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="rounded-sm">
                          <SelectItem value="none" className="text-xs">Selecione o depósito...</SelectItem>
                          {depositos.map(d => (
                            <SelectItem key={d.id} value={d.id} className="text-xs">{d.nome}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-3">
                  <FormField
                    control={addItemForm.control}
                    name="quantidade_solicitada"
                    rules={{ required: "Informe a quantidade", min: { value: 0.1, message: "Mínimo de 0.1" } }}
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Quantidade *</FormLabel>
                        <FormControl>
                          <Input type="number" step="0.1" placeholder="0.0" className="h-8 text-xs rounded-sm" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={addItemForm.control}
                    name="unidade"
                    rules={{ required: "Informe a unidade" }}
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Unidade *</FormLabel>
                        <FormControl>
                          <Input type="text" placeholder="Ex: KG" className="h-8 text-xs rounded-sm uppercase font-mono disabled:opacity-75 disabled:bg-muted" disabled={true} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </DialogBody>

              <DialogFooter className="border-t px-4 py-2.5">
                <Button type="button" variant="outline" size="sm" onClick={() => setAddItemDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" size="sm" disabled={addItemMutation.isPending}>
                  {addItemMutation.isPending ? "Adicionando..." : "Adicionar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editItem} onOpenChange={(open) => !open && setEditItem(null)}>
        <DialogContent className="sm:max-w-[400px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Edit className="size-4" />
              </div>
              <div className="min-w-0">
                <DialogTitle>Editar Quantidade</DialogTitle>
                <DialogDescription className="truncate text-xs leading-tight">
                  {editItem?.produto_nome}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <div className="p-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nova Quantidade ({editItem?.unidade})</Label>
              <Input
                type="number"
                step="0.1"
                value={editQuantidade}
                onChange={(e) => setEditQuantidade(e.target.value)}
                className="h-8 text-xs rounded-sm"
              />
            </div>
          </div>
          <DialogFooter className="border-t px-4 py-2.5">
            <Button type="button" variant="outline" size="sm" onClick={() => setEditItem(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={editItemMutation.isPending || !editQuantidade || parseFloat(editQuantidade) <= 0}
              onClick={() => {
                if (selectedSolicitacaoForSheet && editItem) {
                  editItemMutation.mutate({
                    id: selectedSolicitacaoForSheet.id,
                    itemId: editItem.id,
                    quantidade_solicitada: parseFloat(editQuantidade),
                  });
                }
              }}
            >
              {editItemMutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {selectedSolicitacao && (
        selectedSolicitacao.itens.length > 1 ? (
          <CotacaoMultiItemDialog
            isOpen={cotacaoDialogOpen}
            onClose={() => setCotacaoDialogOpen(false)}
            solicitacaoId={selectedSolicitacao.id}
            itens={selectedSolicitacao.itens}
          />
        ) : (
          <CotacaoSolicitacaoDialog
            isOpen={cotacaoDialogOpen}
            onClose={() => setCotacaoDialogOpen(false)}
            solicitacaoId={selectedSolicitacao.id}
            produtoNome={selectedSolicitacao.produto_nome}
            produtoId={selectedSolicitacao.item_id}
          />
        )
      )}
    </div>
  );
}
