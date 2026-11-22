"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { PageHeader } from "@/components/shared/page-header";
import { CotacoesRegionaisSection } from "@/components/cadastros/cotacoes-regionais-section";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogClose,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Eye, Trash2, Loader2, Package, Sprout } from "lucide-react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  COMMODITY_TIPOS,
  COMMODITY_UNIDADES,
  type CommodityType,
} from "@farm/zod-schemas";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Mapa de cores para tipos de commodity (mesmo estilo do StatusBadge)
// ---------------------------------------------------------------------------

const TIPO_BADGE_STYLES: Record<string, string> = {
  AGRICOLA:
    "bg-emerald-500/10 text-emerald-700 border-emerald-500/20 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-400/30",
  PECUARIA:
    "bg-amber-500/10 text-amber-700 border-amber-500/20 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-400/30",
  FLORESTAL:
    "bg-blue-500/10 text-blue-700 border-blue-500/20 dark:bg-blue-500/20 dark:text-blue-300 dark:border-blue-400/30",
};

// ---------------------------------------------------------------------------
// FieldView — padrao de label/valor para detail views
// ---------------------------------------------------------------------------

function FieldView({ label, value, className }: { label: string; value?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
      <div className="text-sm">{value ?? <span className="text-muted-foreground/50">—</span>}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

const TIPO_LABELS: Record<string, string> = {
  AGRICOLA: "Agrícola",
  PECUARIA: "Pecuária",
  FLORESTAL: "Florestal",
};

const UNIDADE_LABELS: Record<string, string> = {
  SACA_60KG: "Saca (60 kg)",
  TONELADA: "Tonelada (t)",
  KG: "Quilograma (kg)",
  ARROBA: "Arroba (@)",
  CABECA: "Cabeça",
  LITRO: "Litro (L)",
  M3: "Metro Cúbico (m³)",
  UNIDADE: "Unidade (un)",
};

function formatUnidadeCommodity(unidade?: string | null) {
  if (!unidade) return "—";
  return UNIDADE_LABELS[unidade] ?? unidade;
}

const commoditySchema = z.object({
  nome: z.string().min(1, "Obrigatório"),
  codigo: z.string().min(1, "Obrigatório"),
  descricao: z.string().optional(),
  tipo: z.enum(["AGRICOLA", "PECUARIA", "FLORESTAL"]),
  unidade_padrao: z.string().min(1, "Obrigatório"),
  peso_unidade: z.coerce.number().positive("Deve ser positivo").nullable().optional(),
  umidade_padrao_pct: z.coerce.number().min(0).max(100).nullable().optional(),
  impureza_padrao_pct: z.coerce.number().min(0).max(100).nullable().optional(),
  possui_cotacao: z.boolean().default(false),
  bolsa_referencia: z.string().optional(),
  codigo_bolsa: z.string().optional(),
  ativo: z.boolean().default(true),
});
type CommodityFormData = z.infer<typeof commoditySchema>;
type CommodityFormInput = z.input<typeof commoditySchema>;
type CommodityFormOutput = z.output<typeof commoditySchema>;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CommoditiesPage() {
  const queryClient = useQueryClient();
  const hasHydrated = useAppStore((state) => state._hasHydrated);
  const [dialog, setDialog] = useState<{ open: boolean; editing: CommodityType | null }>({
    open: false,
    editing: null,
  });
  const [detail, setDetail] = useState<{ open: boolean; item: CommodityType | null }>({
    open: false,
    item: null,
  });
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; item?: CommodityType }>({ open: false });

  const rhForm = useForm<CommodityFormInput, unknown, CommodityFormOutput>({
    resolver: zodResolver(commoditySchema),
    defaultValues: {
      nome: "", codigo: "", descricao: "", tipo: "AGRICOLA",
      unidade_padrao: "SACA_60KG", peso_unidade: null,
      umidade_padrao_pct: null, impureza_padrao_pct: null,
      possui_cotacao: false, bolsa_referencia: "", codigo_bolsa: "", ativo: true,
    },
  });
  const possuiCotacao = useWatch({ control: rhForm.control, name: "possui_cotacao" });

  // ── Query ──
  const { data: commodities, isLoading } = useQuery<CommodityType[]>({
    queryKey: ["commodities"],
    enabled: hasHydrated,
    queryFn: () => apiFetch<CommodityType[]>("/cadastros/commodities"),
  });

  // ── Mutations ──
  const createMutation = useMutation({
    mutationFn: (d: CommodityFormData) =>
      apiFetch("/cadastros/commodities", { method: "POST", body: JSON.stringify(d) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commodities"] });
      toast.success("Commodity criada com sucesso!");
      setDialog({ open: false, editing: null });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CommodityFormData }) =>
      apiFetch(`/cadastros/commodities/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commodities"] });
      toast.success("Commodity atualizada!");
      setDialog({ open: false, editing: null });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/cadastros/commodities/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commodities"] });
      toast.success("Commodity desativada!");
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const isSaving = createMutation.isPending || updateMutation.isPending;

  // ── Handlers ──
  const openCreate = () => {
    rhForm.reset({
      nome: "", codigo: "", descricao: "", tipo: "AGRICOLA",
      unidade_padrao: "SACA_60KG", peso_unidade: null,
      umidade_padrao_pct: null, impureza_padrao_pct: null,
      possui_cotacao: false, bolsa_referencia: "", codigo_bolsa: "", ativo: true,
    });
    setDialog({ open: true, editing: null });
  };

  const openEdit = (item: CommodityType) => {
    rhForm.reset({
      nome: item.nome, codigo: item.codigo, descricao: item.descricao ?? "",
      tipo: item.tipo as "AGRICOLA" | "PECUARIA" | "FLORESTAL",
      unidade_padrao: item.unidade_padrao, peso_unidade: item.peso_unidade ?? null,
      umidade_padrao_pct: item.umidade_padrao_pct ?? null,
      impureza_padrao_pct: item.impureza_padrao_pct ?? null,
      possui_cotacao: item.possui_cotacao ?? false,
      bolsa_referencia: item.bolsa_referencia ?? "",
      codigo_bolsa: item.codigo_bolsa ?? "",
      ativo: item.ativo ?? true,
    });
    setDialog({ open: true, editing: item });
  };

  const openDetail = (item: CommodityType) => setDetail({ open: true, item });

  const handleDelete = (item: CommodityType) => {
    if (item.sistema) {
      toast.error("Commodities do sistema não podem ser excluídas");
      return;
    }
    setDeleteDialog({ open: true, item });
  };

  const onSubmit = (data: CommodityFormData) => {
    const payload = { ...data, codigo: data.codigo.toUpperCase().replace(/\s+/g, "_") };
    if (dialog.editing?.id) {
      updateMutation.mutate({ id: dialog.editing.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  // ── Columns ──
  const columns: ColumnDef<CommodityType>[] = [
    {
      id: "nome",
      header: "Commodity",
      accessorKey: "nome",
      sortable: true,
      filterable: true,
      cell: (v: string, row) => (
        <div>
          <p className="font-medium">{v}</p>
          <p className="text-xs text-muted-foreground">{row.codigo}</p>
        </div>
      ),
    },
    {
      id: "tipo",
      header: "Tipo",
      accessorKey: "tipo",
      sortable: true,
      filterable: true,
      cell: (v: string) => (
        <Badge variant="outline" className={cn("rounded-sm text-xs font-medium", TIPO_BADGE_STYLES[v])}>
          {TIPO_LABELS[v] || v}
        </Badge>
      ),
    },
    {
      id: "unidade",
      header: "Unidade",
      accessorKey: "unidade_padrao",
      cell: (v: string) => formatUnidadeCommodity(v),
    },
    {
      id: "peso",
      header: "Peso (kg)",
      accessorFn: (r) => (r.peso_unidade ? `${r.peso_unidade}` : "—"),
    },
    {
      id: "cotacao",
      header: "Cotação",
      accessorFn: (r) => (r.possui_cotacao ? r.bolsa_referencia || "Ativa" : "—"),
      cell: (v: string | null, r) =>
        r.possui_cotacao ? (
          <Badge variant="outline" className="rounded-sm text-xs">
            {r.bolsa_referencia || "Ativa"}
          </Badge>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      id: "status",
      header: "Status",
      accessorFn: (r) => (r.sistema ? "Sistema" : r.ativo ? "Ativo" : "Inativo"),
      cell: (_v, r) => {
        if (r.sistema) return <StatusBadge status="inativo" label="🔒 Sistema" />;
        return <StatusBadge status={r.ativo ? "ativo" : "inativo"} />;
      },
    },
    {
      id: "acoes",
      header: "",
      accessorKey: "id",
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_v, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            onClick={() => openDetail(row)}
            aria-label={`Ver detalhes de ${row.nome}`}
            title="Ver detalhes"
          >
            <Eye className="size-3.5" />
          </Button>
          {!row.sistema && (
            <>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 text-primary hover:text-primary"
                onClick={() => openEdit(row)}
                aria-label={`Editar ${row.nome}`}
                title="Editar"
              >
                <Pencil className="size-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 text-destructive hover:text-destructive"
                onClick={() => handleDelete(row)}
                aria-label={`Desativar ${row.nome}`}
                title="Desativar"
              >
                <Trash2 className="size-3.5" />
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  // ── Render ──
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Commodities"
        description="Categorias padronizadas de mercado para comercialização."
        icon={<Sprout className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Cadastros", href: "/cadastros" },
          { label: "Commodities" },
        ]}
        actions={
          <Button size="sm" variant="outline" onClick={openCreate}>
            <Plus className="size-4 mr-2" /> Nova Commodity
          </Button>
        }
      />

      {isLoading ? (
        <div className="rounded-sm border bg-card p-6 space-y-3">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : (
        <DataTable
          data={commodities ?? []}
          columns={columns}
          searchable
          searchPlaceholder="Buscar por nome ou código..."
          exportable
          exportFileName="commodities"
          emptyMessage="Nenhuma commodity cadastrada"
        />
      )}

      <CotacoesRegionaisSection />

      {/* ── Create/Edit Dialog ── */}
      <Dialog open={dialog.open} onOpenChange={(o) => { if (!o && !isSaving) setDialog({ open: false, editing: null }); }}>
        <DialogContent className="max-w-xl p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Sprout className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.editing ? "Editar" : "Nova"} Commodity</DialogTitle>
            </div>
          </DialogHeader>

          <Form {...rhForm}>
            <form onSubmit={rhForm.handleSubmit(onSubmit)}>
              <DialogBody className="space-y-4">

                {/* Nome + Código + Tipo + Unidade */}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_120px]">
                  <FormField
                    control={rhForm.control}
                    name="nome"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nome</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Soja" className="h-8 rounded-sm" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={rhForm.control}
                    name="codigo"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Código</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            placeholder="SOJA"
                            className="h-8 rounded-sm"
                            onChange={(e) => field.onChange(e.target.value.toUpperCase().replace(/\s+/g, "_"))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <FormField
                    control={rhForm.control}
                    name="tipo"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tipo</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {COMMODITY_TIPOS.map((t) => (
                              <SelectItem key={t} value={t}>{TIPO_LABELS[t]}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={rhForm.control}
                    name="unidade_padrao"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Unidade Padrão</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm"><SelectValue /></SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {COMMODITY_UNIDADES.map((u) => (
                              <SelectItem key={u} value={u}>{u.replace(/_/g, " ")}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={rhForm.control}
                  name="descricao"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Descrição <span className="text-muted-foreground font-normal">(opcional)</span></FormLabel>
                      <FormControl>
                        <Textarea {...field} placeholder="Grão de soja (Glycine max)" rows={2} className="rounded-sm resize-none text-sm" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Separator />

                {/* Peso & Qualidade */}
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Peso & Qualidade</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <FormField
                    control={rhForm.control}
                    name="peso_unidade"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Peso (kg)</FormLabel>
                        <FormControl>
                          <Input
                            type="number" step="0.01" placeholder="60"
                            className="h-8 rounded-sm"
                            value={(field.value ?? "") as string | number | readonly string[]}
                            onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={rhForm.control}
                    name="umidade_padrao_pct"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Umidade (%)</FormLabel>
                        <FormControl>
                          <Input
                            type="number" step="0.1" placeholder="14,0"
                            className="h-8 rounded-sm"
                            value={(field.value ?? "") as string | number | readonly string[]}
                            onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={rhForm.control}
                    name="impureza_padrao_pct"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Impureza (%)</FormLabel>
                        <FormControl>
                          <Input
                            type="number" step="0.1" placeholder="1,0"
                            className="h-8 rounded-sm"
                            value={(field.value ?? "") as string | number | readonly string[]}
                            onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : null)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <Separator />

                {/* Cotação */}
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Cotação de Mercado</p>
                <FormField
                  control={rhForm.control}
                  name="possui_cotacao"
                  render={({ field }) => (
                    <FormItem>
                      <div className="flex items-center gap-2">
                        <FormControl>
                          <Switch checked={field.value} onCheckedChange={field.onChange} />
                        </FormControl>
                        <FormLabel className="font-normal cursor-pointer">Possui cotação de mercado</FormLabel>
                      </div>
                    </FormItem>
                  )}
                />
                {possuiCotacao && (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                    <FormField
                      control={rhForm.control}
                      name="bolsa_referencia"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Bolsa de Referência</FormLabel>
                          <FormControl>
                            <Input {...field} placeholder="CBOT" className="h-8 rounded-sm" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={rhForm.control}
                      name="codigo_bolsa"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Código na Bolsa</FormLabel>
                          <FormControl>
                            <Input {...field} placeholder="ZS" className="h-8 rounded-sm" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                )}

              </DialogBody>

              <DialogFooter>
                <FormField
                  control={rhForm.control}
                  name="ativo"
                  render={({ field }) => (
                    <div className="flex items-center gap-2 mr-auto">
                      <Switch id="dialog-ativo" checked={field.value} onCheckedChange={field.onChange} />
                      <FormLabel htmlFor="dialog-ativo" className="font-normal cursor-pointer">Ativo</FormLabel>
                    </div>
                  )}
                />
                <Button variant="outline" type="button" disabled={isSaving} onClick={() => setDialog({ open: false, editing: null })}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={isSaving}>
                  {isSaving && <Loader2 className="mr-2 size-4 animate-spin" />}
                  {dialog.editing ? "Salvar alterações" : "Criar Commodity"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* ── Detail Dialog ── */}
      <Dialog open={detail.open} onOpenChange={(o) => { if (!o) setDetail({ open: false, item: null }); }}>
        <DialogContent className="max-w-lg p-0">
          <DialogHeader>
            <div className="flex items-start gap-3 pr-8">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Package />
              </div>
              <div className="min-w-0">
                <DialogTitle className="truncate">{detail.item?.nome ?? "Commodity"}</DialogTitle>
                <DialogDescription className="mt-1">
                  Cadastro de commodity para comercialização e controle operacional.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          {detail.item && (
            <DialogBody className="flex flex-col gap-4">
              <Card size="sm" className="shadow-none">
                <CardHeader>
                  <CardTitle>Identificação</CardTitle>
                  <CardDescription>Código, classificação e situação do cadastro.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                  <FieldView label="Código" value={<span className="font-medium">{detail.item.codigo}</span>} />
                  <FieldView
                    label="Tipo"
                    value={
                      <Badge variant="outline" className={cn("rounded-sm text-xs font-medium", TIPO_BADGE_STYLES[detail.item.tipo])}>
                        {TIPO_LABELS[detail.item.tipo] || detail.item.tipo}
                      </Badge>
                    }
                  />
                  <FieldView
                    label="Status"
                    value={
                      detail.item.sistema ? (
                        <StatusBadge status="inativo" label="🔒 Sistema" />
                      ) : (
                        <StatusBadge status={detail.item.ativo ? "ativo" : "inativo"} />
                      )
                    }
                  />
                  <FieldView
                    label="Origem"
                    value={detail.item.sistema ? "Tabela padrão do sistema" : "Cadastro do produtor"}
                  />
                </CardContent>
              </Card>

              <Card size="sm" className="shadow-none">
                <CardHeader>
                  <CardTitle>Parâmetros Operacionais</CardTitle>
                  <CardDescription>Unidade de controle, peso e padrões de qualidade.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                  <FieldView label="Unidade Padrão" value={formatUnidadeCommodity(detail.item.unidade_padrao)} />
                  <FieldView
                    label="Peso da Unidade"
                    value={detail.item.peso_unidade ? `${detail.item.peso_unidade} kg` : undefined}
                  />
                  <FieldView
                    label="Umidade Padrão"
                    value={detail.item.umidade_padrao_pct != null ? `${detail.item.umidade_padrao_pct}%` : undefined}
                  />
                  <FieldView
                    label="Impureza Padrão"
                    value={detail.item.impureza_padrao_pct != null ? `${detail.item.impureza_padrao_pct}%` : undefined}
                  />
                </CardContent>
              </Card>

              <Card size="sm" className="shadow-none">
                <CardHeader>
                  <CardTitle>Cotação de Mercado</CardTitle>
                  <CardDescription>Referência utilizada para acompanhamento comercial.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                  <FieldView
                    label="Cotação"
                    value={
                      detail.item.possui_cotacao ? (
                        <Badge variant="outline" className="rounded-sm text-xs">Configurada</Badge>
                      ) : (
                        "Não configurada"
                      )
                    }
                  />
                  <FieldView label="Bolsa de Referência" value={detail.item.bolsa_referencia} />
                  <FieldView label="Código na Bolsa" value={detail.item.codigo_bolsa} />
                </CardContent>
              </Card>

              {detail.item.descricao && (
                <>
                  <Separator />
                  <FieldView
                    label="Descrição"
                    value={<p className="leading-relaxed text-muted-foreground">{detail.item.descricao}</p>}
                  />
                </>
              )}
            </DialogBody>
          )}
          <DialogFooter>
            <DialogClose render={<Button variant="outline" type="button" />}>
              Fechar
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteDialog.open}
        title="Desativar Commodity"
        description={`Deseja desativar "${deleteDialog.item?.nome}"? A commodity deixará de aparecer como ativa.`}
        confirmText="Desativar"
        cancelText="Cancelar"
        destructive
        onConfirm={() => deleteDialog.item?.id && deleteMutation.mutate(deleteDialog.item.id)}
        onCancel={() => setDeleteDialog({ open: false })}
      />
    </div>
  );
}
