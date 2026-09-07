"use client";

import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Package, Plus, Pencil, XCircle, Save, Copy, Trash2 } from "lucide-react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";

// ---------------------------------------------------------------------------
// Enums — espelham backend UnidadeMedida
// ---------------------------------------------------------------------------

const UNIDADES = [
  { value: "UN", label: "UN — Unidade" },
  { value: "KG", label: "KG — Quilograma" },
  { value: "G", label: "G — Grama" },
  { value: "T", label: "T — Tonelada" },
  { value: "L", label: "L — Litro" },
  { value: "ML", label: "ML — Mililitro" },
  { value: "M3", label: "M³ — Metro cúbico" },
  { value: "SACA", label: "SACA — Saca 60 kg" },
  { value: "SC40", label: "SC40 — Saca 40 kg" },
  { value: "FARDO", label: "FARDO" },
  { value: "CX", label: "CX — Caixa" },
  { value: "M", label: "M — Metro linear" },
  { value: "M2", label: "M² — Metro quadrado" },
  { value: "H", label: "H — Hora" },
];

const STORAGE_KEY_INCLUIR_PRODUTOS_SISTEMA = "cadastros-produtos:incluir-sistema:v2";

const hasTenantOwnership = (tenantId: string | null | undefined) =>
  tenantId !== null &&
  tenantId !== undefined &&
  tenantId !== "" &&
  tenantId !== "null";

// Categorias-sistema agrícolas semeadas na migration 20260723f — mesmos IDs
// usados em core/cadastros/produtos/service.py:CATEGORIA_SISTEMA_PARA_TIPO.
const CATEGORIAS_SISTEMA_AGRICOLAS = new Set([
  "11111111-ca70-0000-0000-000000000001", // Sementes
  "11111111-ca70-0000-0000-000000000002", // Defensivos Agrícolas
  "11111111-ca70-0000-0000-000000000003", // Fertilizantes e Corretivos
  "11111111-ca70-0000-0000-000000000004", // Inoculantes
]);

// Achata a árvore de categorias em ordem pai → filhos (DFS), com `depth` para
// indentação visual no Select — sem isso, pai e filhas ficam misturados numa
// lista plana e o usuário não consegue distinguir hierarquia (nem saber que
// uma categoria-pai também pode ser escolhida diretamente, herdando o plano
// de contas vinculado a ela — ver ComprasService._resolver_plano_conta_por_categoria).
const buildCategoriaHierarquia = (categorias: CategoriaProduto[]): { id: string; nome: string; depth: number }[] => {
  const porPai = new Map<string | null, CategoriaProduto[]>();
  for (const c of categorias) {
    const chave = c.parent_id ?? null;
    if (!porPai.has(chave)) porPai.set(chave, []);
    porPai.get(chave)!.push(c);
  }
  for (const lista of porPai.values()) {
    lista.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  }

  const resultado: { id: string; nome: string; depth: number }[] = [];
  const visitar = (parentId: string | null, depth: number, visitados: Set<string>) => {
    for (const c of porPai.get(parentId) ?? []) {
      if (visitados.has(c.id)) continue; // guardrail contra ciclo acidental
      visitados.add(c.id);
      resultado.push({ id: c.id, nome: c.nome, depth });
      visitar(c.id, depth + 1, visitados);
    }
  };
  visitar(null, 0, new Set());
  return resultado;
};

// Sobe a árvore de categorias (via parent_id) até achar uma categoria-sistema
// conhecida — decide se mostra o campo "Princípio Ativo" (produto agrícola).
const isCategoriaAgricola = (categoriaId: string | undefined, categorias: CategoriaProduto[]): boolean => {
  let atualId = categoriaId;
  const visitados = new Set<string>();
  while (atualId && !visitados.has(atualId)) {
    if (CATEGORIAS_SISTEMA_AGRICOLAS.has(atualId)) return true;
    visitados.add(atualId);
    atualId = categorias.find((c) => c.id === atualId)?.parent_id ?? undefined;
  }
  return false;
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Marca { id: string; nome: string; }
export interface ModeloProduto { id: string; nome: string; marca_id: string; }
export interface CategoriaProduto { id: string; nome: string; cor?: string; parent_id?: string | null; }

export interface Produto {
  id: string;
  tenant_id?: string | null;
  nome: string;
  tipo: string;
  unidade_medida: string;
  codigo_interno?: string;
  sku?: string;
  codigo_barras?: string;
  descricao?: string;
  marca_id?: string;
  modelo_id?: string;
  marca?: string;
  fabricante?: string;
  referencia_fabricante?: string;
  categoria_id?: string;
  produto_referencia_id?: string | null;
  qtd_conteudo?: number;
  unidade_conteudo?: string;
  estoque_minimo: number;
  preco_medio: number;
  preco_ultima_compra?: number;
  ativo: boolean;
  principio_ativo?: string;
  detalhe_agricola?: {
    principio_ativo?: string;
  };
  // desnormalizados
  marca_nome?: string;
  modelo_nome?: string;
  categoria_nome?: string;
}

type FormState = Omit<Partial<Produto>, "id" | "marca_nome" | "modelo_nome" | "categoria_nome">;

const emptyForm = (): FormState => ({
  nome: "", unidade_medida: "UN", ativo: true,
  codigo_interno: "", sku: "", descricao: "",
  marca_id: undefined, modelo_id: undefined,
  marca: "", fabricante: "", referencia_fabricante: "",
  categoria_id: undefined, principio_ativo: "",
  qtd_conteudo: undefined, unidade_conteudo: undefined,
  preco_medio: 0,
});

const buildProdutoPayload = (data: FormState, categorias: CategoriaProduto[]) => {
  const payload = Object.fromEntries(
    Object.entries(data).filter(([, v]) => v !== "" && v !== undefined)
  ) as Record<string, unknown>;

  const principioAtivo =
    typeof data.principio_ativo === "string" ? data.principio_ativo.trim() : "";

  delete payload.principio_ativo;

  if (isCategoriaAgricola(data.categoria_id, categorias)) {
    payload.detalhe_agricola = { principio_ativo: principioAtivo };
  }

  return payload;
};

const labelEmbalagem = (p: Produto) => {
  if (!p.qtd_conteudo) return p.unidade_medida;
  const unidade = UNIDADES.find((u) => u.value === p.unidade_conteudo)?.label || p.unidade_conteudo;
  return `${p.qtd_conteudo} ${unidade}`;
};

const formatPrecoMedio = (value: number) => (
  value > 0
    ? value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
    : "—"
);

const createProdutoColumns = (openEdit: (p: Produto) => void, confirmarExclusao: (p: Produto) => void): ColumnDef<Produto>[] => [
  {
    id: "nome",
    header: "Nome / Marca · Modelo",
    accessorFn: (row) => row.nome,
    sortable: true,
    filterable: true,
    cell: (value: string, row: Produto) => (
      <div>
        <div className="font-medium text-sm">{value}</div>
        {(row.marca_nome || row.modelo_nome) && (
          <div className="text-[11px] text-muted-foreground">
            {[row.marca_nome, row.modelo_nome].filter(Boolean).join(" · ")}
          </div>
        )}
      </div>
    ),
  },
  {
    id: "categoria",
    header: "Categoria",
    accessorFn: (row) => row.categoria_nome || "",
    sortable: true,
    cell: (value: string) => (
      value ? (
        <Badge variant="outline" className="text-xs">{value}</Badge>
      ) : (
        <span className="text-muted-foreground text-xs">Sem categoria</span>
      )
    ),
  },
  {
    id: "embalagem",
    header: "Embalagem",
    accessorFn: (row) => labelEmbalagem(row),
    sortable: false,
    cell: (value) => <span className="text-muted-foreground text-xs">{value}</span>,
  },
  {
    id: "codigo_interno",
    header: "Código",
    accessorKey: "codigo_interno",
    sortable: false,
    cell: (value) => <span className="text-muted-foreground text-xs">{value || "—"}</span>,
  },
  {
    id: "preco_medio",
    header: "Preço Médio",
    accessorKey: "preco_medio",
    sortable: true,
    cell: (value: number) => (
      <span className="text-muted-foreground text-xs tabular-nums">
        {formatPrecoMedio(value ?? 0)}
      </span>
    ),
  },
  {
    id: "principio_ativo",
    header: "Princípio Ativo",
    accessorFn: (row) => row.principio_ativo || row.detalhe_agricola?.principio_ativo || "",
    sortable: false,
    cell: (value: string) => (
      <span className="text-muted-foreground text-xs">{value || "—"}</span>
    ),
  },
  {
    id: "status",
    header: "Status",
    accessorKey: "ativo",
    sortable: false,
    cell: (value: boolean) => (
      <StatusBadge status={value ? "ativo" : "inativo"} />
    ),
  },
  {
    id: "origem",
    header: "Origem",
    accessorFn: (row) => (row.tenant_id ? "TENANT" : "SISTEMA"),
    sortable: false,
    cell: (_value: string, row: Produto) => (
      <Badge variant="outline" className="text-[11px]">
        {row.tenant_id ? "Tenant" : "Sistema"}
      </Badge>
    ),
  },
  {
    id: "acoes",
    header: "",
    accessorKey: "id",
    sortable: false,
    filterable: false,
    exportable: false,
    cell: (id: string, row: Produto) => (
      <div className="flex items-center gap-0 justify-end">
        {row.tenant_id ? (
          <>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-primary hover:text-primary"
              onClick={() => openEdit(row)}
            >
              <Pencil className="size-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive"
              onClick={() => confirmarExclusao(row)}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </>
        ) : null}
      </div>
    ),
  },
];

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

export function ProdutosClient({
  initialProdutos,
  initialMarcas,
  initialModelos,
  initialCategorias,
}: {
  initialProdutos?: Produto[];
  initialMarcas?: Marca[];
  initialModelos?: ModeloProduto[];
  initialCategorias?: CategoriaProduto[];
}) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; produto?: Produto }>({ open: false });
  const [excluindo, setExcluindo] = useState<Produto | null>(null);
  const [incluirProdutosSistema, setIncluirProdutosSistema] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem(STORAGE_KEY_INCLUIR_PRODUTOS_SISTEMA) !== "false";
  });
  const formMethods = useForm<FormState>({
    defaultValues: emptyForm(),
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      STORAGE_KEY_INCLUIR_PRODUTOS_SISTEMA,
      incluirProdutosSistema ? "true" : "false",
    );
  }, [incluirProdutosSistema]);

  // Queries
  const { data: produtos = [], isLoading } = useQuery<Produto[]>({
    queryKey: ["cadastros-produtos", incluirProdutosSistema],
    queryFn: () => apiFetch("/cadastros/produtos", {
      params: {
        incluir_sistema: incluirProdutosSistema,
        ativo: true,
      },
    }),
    initialData: initialProdutos,
  });

  const produtosVisiveis = incluirProdutosSistema
    ? produtos
    : produtos.filter((produto) => hasTenantOwnership(produto.tenant_id));

  // Catálogo de produtos padrão (tenant_id NULL) para o fluxo "criar a partir de padrão".
  const { data: produtosSistema = [] } = useQuery<Produto[]>({
    queryKey: ["cadastros-produtos-sistema"],
    queryFn: () => apiFetch("/cadastros/produtos", {
      params: { incluir_sistema: true, ativo: true },
    }),
    select: (data) => data.filter((p) => !hasTenantOwnership(p.tenant_id)),
  });

  const { data: marcas = [] } = useQuery<Marca[]>({
    queryKey: ["cadastros-marcas"],
    queryFn: () => apiFetch("/cadastros/marcas?ativo=true"),
    initialData: initialMarcas,
  });

  const { data: modelos = [] } = useQuery<ModeloProduto[]>({
    queryKey: ["cadastros-modelos-produto"],
    queryFn: () => apiFetch("/cadastros/modelos-produto?ativo=true"),
    initialData: initialModelos,
  });

  const { data: categorias = [] } = useQuery<CategoriaProduto[]>({
    queryKey: ["cadastros-categorias-produto"],
    queryFn: () => apiFetch("/cadastros/categorias-produto?ativo=true"),
    initialData: initialCategorias,
  });

  // Mutations
  const save = useMutation<Produto, Error, FormState>({
    mutationFn: (data: FormState) => {
      const payload = buildProdutoPayload(data, categorias);
      return dialog.produto
        ? apiFetch(`/cadastros/produtos/${dialog.produto.id}`, { method: "PATCH", body: JSON.stringify(payload) })
        : apiFetch("/cadastros/produtos", { method: "POST", body: JSON.stringify(payload) });
    },
    onSuccess: (savedProduto) => {
      qc.setQueriesData<Produto[]>(
        { queryKey: ["cadastros-produtos"] },
        (current) => {
          if (!current) return [savedProduto];
          const existingIndex = current.findIndex((produto) => produto.id === savedProduto.id);
          if (existingIndex === -1) return [savedProduto, ...current];
          return current.map((produto) => (produto.id === savedProduto.id ? savedProduto : produto));
        },
      );
      qc.invalidateQueries({ queryKey: ["cadastros-produtos"] });
      toast.success(dialog.produto ? "Produto atualizado com sucesso" : "Produto cadastrado com sucesso");
      setDialog({ open: false });
    },
    onError: () => toast.error(dialog.produto ? "Erro ao atualizar produto" : "Erro ao cadastrar produto"),
  });

  const remover = useMutation<void, Error, string>({
    mutationFn: (produtoId: string) => apiFetch(`/cadastros/produtos/${produtoId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cadastros-produtos"] });
      toast.success("Produto excluído com sucesso");
      setExcluindo(null);
    },
    onError: () => toast.error("Erro ao excluir produto"),
  });

  const openCreate = () => {
    formMethods.reset(emptyForm());
    setDialog({ open: true });
  };
  const aplicarProdutoReferencia = (referenciaId: string) => {
    if (referenciaId === "none") {
      formMethods.reset(emptyForm());
      return;
    }
    const base = produtosSistema.find((p) => p.id === referenciaId);
    if (!base) return;
    formMethods.reset({
      ...emptyForm(),
      nome: base.nome, unidade_medida: base.unidade_medida,
      descricao: base.descricao ?? "",
      categoria_id: base.categoria_id,
      fabricante: base.fabricante ?? "",
      referencia_fabricante: base.referencia_fabricante ?? "",
      qtd_conteudo: base.qtd_conteudo, unidade_conteudo: base.unidade_conteudo,
      principio_ativo: base.principio_ativo ?? base.detalhe_agricola?.principio_ativo ?? "",
      produto_referencia_id: base.id,
    });
  };
  const openEdit = (p: Produto) => {
    formMethods.reset({
      nome: p.nome, unidade_medida: p.unidade_medida, ativo: p.ativo,
      codigo_interno: p.codigo_interno ?? "", sku: p.sku ?? "",
      codigo_barras: p.codigo_barras ?? "", descricao: p.descricao ?? "",
      marca_id: p.marca_id, modelo_id: p.modelo_id,
      marca: p.marca ?? "", fabricante: p.fabricante ?? "",
      referencia_fabricante: p.referencia_fabricante ?? "",
      categoria_id: p.categoria_id, principio_ativo: p.principio_ativo ?? p.detalhe_agricola?.principio_ativo ?? "",
      qtd_conteudo: p.qtd_conteudo, unidade_conteudo: p.unidade_conteudo,
      preco_medio: p.preco_medio,
      preco_ultima_compra: p.preco_ultima_compra,
    });
    setDialog({ open: true, produto: p });
  };

  const watchedForm = useWatch({
    control: formMethods.control,
  });

  const modelosFiltrados = watchedForm.marca_id
    ? modelos.filter((m) => m.marca_id === watchedForm.marca_id)
    : modelos;

  const categoriasHierarquia = buildCategoriaHierarquia(categorias);

  // Display texts for selects
  const categoriaSelecionada = categorias.find((c) => c.id === watchedForm.categoria_id);
  const marcaSelecionada = marcas.find((m) => m.id === watchedForm.marca_id);
  const modeloSelecionado = modelosFiltrados.find((m) => m.id === watchedForm.modelo_id);

  const catDisplay = categoriaSelecionada?.nome || "";
  const marcaDisplay = marcaSelecionada?.nome || "";
  const modeloDisplay = modeloSelecionado?.nome || "";


  return (
    <div className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6 min-h-0">
      <div className="shrink-0">
        <PageHeader
        title="Catálogo de Produtos"
        description="Dados mestres de insumos, almoxarifado, EPIs e serviços."
        icon={<Package className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Cadastros", href: "/cadastros" }, { label: "Produtos" }]}
        actions={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-sm border border-border bg-muted/20 px-3 py-1.5">
              <Switch
                checked={incluirProdutosSistema}
                onCheckedChange={(checked) => setIncluirProdutosSistema(checked === true)}
              />
              <div className="flex flex-col leading-none">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Produtos padrão
                </span>
                <span className="text-xs text-foreground">Listar itens do sistema</span>
              </div>
            </div>
            <Button size="sm" onClick={openCreate}>
              <Plus className="size-4 mr-2" /> Novo Produto
            </Button>
          </div>
        }
      />
      </div>

      {/* DataTable */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground flex-1 min-h-0 flex items-center justify-center">Carregando...</div>
      ) : (
        <DataTable
          className="flex-1 min-h-0"
          key={incluirProdutosSistema ? "produtos-com-sistema" : "produtos-sem-sistema"}
          data={produtosVisiveis}
          columns={createProdutoColumns(openEdit, setExcluindo)}
          searchable={true}
          searchPlaceholder="Buscar por nome, código, marca..."
          exportable={true}
          exportFileName="produtos-catalogo"
          emptyMessage="Nenhum produto encontrado"
        />
      )}

      {/* Dialog Criar / Editar */}
      <Dialog open={dialog.open} onOpenChange={(o) => {
        setDialog({ open: o, produto: o ? dialog.produto : undefined });
        if (!o) formMethods.reset(emptyForm());
      }}>
        <DialogContent className="sm:max-w-3xl p-0 flex flex-col">
          <DialogHeader className="shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Package className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.produto ? "Editar Produto" : "Novo Produto"}</DialogTitle>
            </div>
          </DialogHeader>

          <Form {...formMethods}>
            <form onSubmit={formMethods.handleSubmit((data) => save.mutate(data))}>
              <DialogBody className="space-y-4 overflow-y-auto max-h-[85vh] pb-3">

                {!dialog.produto && produtosSistema.length > 0 && (
                  <FormItem className="space-y-1.5">
                    <FormLabel className="text-xs font-medium flex items-center gap-1.5">
                      <Copy className="size-3.5" /> Criar a partir de um produto padrão
                    </FormLabel>
                    <Select
                      value={watchedForm.produto_referencia_id ?? "none"}
                      onValueChange={aplicarProdutoReferencia}
                    >
                      <SelectTrigger className="h-8 rounded-sm text-xs">
                        <SelectValue placeholder="Começar do zero" />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        <SelectItem value="none" className="text-xs">Começar do zero</SelectItem>
                        {produtosSistema.map((p) => (
                          <SelectItem key={p.id} value={p.id} className="text-xs">{p.nome}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}

                {/* Identificação */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="col-span-2">
                    <FormField
                      control={formMethods.control}
                      name="nome"
                      render={({ field }) => (
                        <FormItem className="space-y-1.5">
                          <FormLabel className="text-xs font-medium">Nome *</FormLabel>
                          <FormControl>
                            <Input {...field} className="h-8 rounded-sm text-xs" value={field.value ?? ""} placeholder="Ex: Semente de soja" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <FormField
                    control={formMethods.control}
                    name="categoria_id"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Categoria</FormLabel>
                        <Select value={field.value ?? "none"} onValueChange={(v: string) => field.onChange(v === "none" ? undefined : v)}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder={catDisplay || "Sem categoria"} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            <SelectItem value="none" className="text-xs">Sem categoria</SelectItem>
                            {categoriasHierarquia.map((c) => (
                              <SelectItem key={c.id} value={c.id} className="text-xs">
                                <span style={{ paddingLeft: c.depth * 14 }}>
                                  {c.depth > 0 ? "↳ " : ""}{c.nome}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {isCategoriaAgricola(watchedForm.categoria_id, categorias) ? (
                    <FormField
                      control={formMethods.control}
                      name="principio_ativo"
                      render={({ field }) => (
                        <FormItem className="space-y-1.5">
                          <FormLabel className="text-xs font-medium">Princípio Ativo</FormLabel>
                          <FormControl>
                            <Input {...field} maxLength={30} placeholder="Ex: Glifosato" className="h-8 rounded-sm text-xs" value={field.value ?? ""} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  ) : (
                    <FormField
                      control={formMethods.control}
                      name="referencia_fabricante"
                      render={({ field }) => (
                        <FormItem className="space-y-1.5">
                          <FormLabel className="text-xs font-medium">Referência do Fabr.</FormLabel>
                          <FormControl>
                            <Input {...field} placeholder="Part number" className="h-8 rounded-sm text-xs" value={field.value ?? ""} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}
                </div>

                <FormField
                  control={formMethods.control}
                  name="descricao"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <FormLabel className="text-xs font-medium">Descrição</FormLabel>
                      <FormControl>
                        <Input {...field} value={field.value ?? ""} className="h-8 rounded-sm text-xs" placeholder="Descrição opcional do produto" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Marca & Modelo */}
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide pt-2 border-t">Marca & Modelo</p>
                <div className="grid grid-cols-4 gap-3">
                  <FormField
                    control={formMethods.control}
                    name="marca_id"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Marca cadastrada</FormLabel>
                        <Select
                          value={field.value ?? "none"}
                          onValueChange={(v: string) => {
                            field.onChange(v === "none" ? undefined : v);
                            formMethods.setValue("modelo_id", undefined);
                          }}
                        >
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder={marcaDisplay || "Selecionar marca…"} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            <SelectItem value="none" className="text-xs">— Nenhuma —</SelectItem>
                            {marcas.map((m) => <SelectItem key={m.id} value={m.id} className="text-xs">{m.nome}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="modelo_id"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Modelo</FormLabel>
                        <Select
                          value={field.value ?? "none"}
                          onValueChange={(v: string) => field.onChange(v === "none" ? undefined : v)}
                          disabled={!watchedForm.marca_id}
                        >
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder={modeloDisplay || (watchedForm.marca_id ? "Selecionar modelo…" : "Selecione a marca")} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            <SelectItem value="none" className="text-xs">— Nenhum —</SelectItem>
                            {modelosFiltrados.map((m) => <SelectItem key={m.id} value={m.id} className="text-xs">{m.nome}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="marca"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Marca (texto livre)</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Se não cadastrada" className="h-8 rounded-sm text-xs" value={field.value ?? ""} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="fabricante"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Fabricante</FormLabel>
                        <FormControl>
                          <Input {...field} className="h-8 rounded-sm text-xs" value={field.value ?? ""} placeholder="Ex: Bayer" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Logística & Códigos */}
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide pt-2 border-t">Logística & Códigos</p>
                <div className="grid grid-cols-5 gap-3">
                  <FormField
                    control={formMethods.control}
                    name="unidade_medida"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Unidade Estoque</FormLabel>
                        <Select value={field.value ?? "UN"} onValueChange={field.onChange} disabled={!!dialog.produto}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder={UNIDADES.find(u => u.value === (field.value ?? "UN"))?.label || "Selecione..."} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            {UNIDADES.map((u) => <SelectItem key={u.value} value={u.value} className="text-xs">{u.label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="qtd_conteudo"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Cont. / Emb.</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={0}
                            step={0.001}
                            placeholder="ex: 3"
                            className="h-8 rounded-sm text-xs"
                            value={field.value ?? ""}
                            onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                            disabled={!!dialog.produto}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="unidade_conteudo"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Unid. Conteúdo</FormLabel>
                        <Select value={field.value ?? "none"} onValueChange={(v: string) => field.onChange(v === "none" ? undefined : v)} disabled={!!dialog.produto}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs">
                              <SelectValue placeholder={field.value ? UNIDADES.find(u => u.value === field.value)?.label || "—" : "—"} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent className="rounded-sm">
                            <SelectItem value="none" className="text-xs">—</SelectItem>
                            {UNIDADES.map((u) => <SelectItem key={u.value} value={u.value} className="text-xs">{u.label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="codigo_interno"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">SKU</FormLabel>
                        <FormControl>
                          <Input {...field} className="h-8 rounded-sm text-xs" value={field.value ?? ""} disabled={!!dialog.produto} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={formMethods.control}
                    name="preco_medio"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <FormLabel className="text-xs font-medium">Preço Médio (R$)</FormLabel>
                        <FormControl>
                          <Input
                            className="h-8 rounded-sm text-xs"
                            type="number"
                            min={0}
                            step="any"
                            value={field.value ?? 0}
                            onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                {watchedForm.qtd_conteudo && watchedForm.unidade_conteudo && (
                  <p className="text-[10px] text-muted-foreground italic -mt-2">
                    Conversão: 1 {watchedForm.unidade_medida} = {watchedForm.qtd_conteudo} {watchedForm.unidade_conteudo}
                  </p>
                )}

              </DialogBody>

              <DialogFooter className="shrink-0">
                <div className="flex items-center gap-4 mr-auto px-4">
                  <FormField
                    control={formMethods.control}
                    name="ativo"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-2 space-y-0">
                        <FormControl>
                          <Switch
                            id="produto-ativo"
                            checked={field.value ?? true}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel
                          htmlFor="produto-ativo"
                          className="text-[11px] font-medium text-muted-foreground uppercase"
                        >
                          Ativo
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                </div>
                <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
                  <XCircle className="size-3.5 mr-1.5" />
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  className="rounded-sm border-primary/50 text-primary hover:bg-primary/5"
                  disabled={!watchedForm.nome || save.isPending}
                >
                  <Save className="size-3.5 mr-1.5" />
                  {save.isPending ? "Salvando…" : "Salvar Produto"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!excluindo} onOpenChange={(o) => !o && setExcluindo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir produto?</AlertDialogTitle>
            <AlertDialogDescription>
              {excluindo && (
                <>
                  Tem certeza que deseja excluir <strong>{excluindo.nome}</strong>? Se o produto já
                  tiver sido usado em alguma solicitação, pedido, estoque ou operação, ele será apenas
                  desativado em vez de excluído, para preservar o histórico.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={remover.isPending}
              onClick={() => excluindo && remover.mutate(excluindo.id)}
            >
              {remover.isPending ? "Excluindo…" : "Excluir"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
