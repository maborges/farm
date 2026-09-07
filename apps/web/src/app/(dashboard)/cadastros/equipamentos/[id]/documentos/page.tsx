"use client";

import { useCallback, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, useWatch } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { differenceInDays, format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileText,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { PageHeader } from "@/components/shared/page-header";

const TIPOS_DOC_COMPLETOS = [
  { value: "RENAGRO", label: "RENAGRO" },
  { value: "CRLV", label: "CRLV - Licenciamento" },
  { value: "SEGURO", label: "Seguro Agricola/Patrimonial" },
  { value: "LAUDO_VISTORIA", label: "Laudo de Vistoria" },
  { value: "ART", label: "ART" },
  { value: "MANUAL", label: "Manual do Fabricante" },
  { value: "CONTRATO_LEASING", label: "Leasing / Financiamento" },
  { value: "OUTRO", label: "Outro" },
] as const;

const ORGANOS_EMISSORES = [
  { value: "DETRAN", label: "DETRAN" },
  { value: "MAPA", label: "MAPA - Ministerio da Agricultura" },
  { value: "SEFA", label: "SEFA / SEFAZ" },
  { value: "INCRA", label: "INCRA" },
  { value: "IBAMA", label: "IBAMA" },
  { value: "ANA", label: "ANA - Agencia Nacional de Aguas" },
  { value: "ANTT", label: "ANTT" },
  { value: "CREA", label: "CREA" },
  { value: "SEGURADORA", label: "Seguradora" },
  { value: "FABRICANTE", label: "Fabricante" },
  { value: "OUTRO", label: "Outro" },
] as const;

type DocumentoTipo = (typeof TIPOS_DOC_COMPLETOS)[number]["value"];
type StatusFiltro = "todos" | "validos" | "vencendo" | "vencidos";

type DocumentoFormValues = {
  tipo: DocumentoTipo;
  descricao: string;
  numero: string;
  orgao_emissor: string;
  data_emissao: string;
  data_vencimento: string;
  arquivo_url: string;
  observacoes: string;
};

const EMPTY_FORM: DocumentoFormValues = {
  tipo: "CRLV",
  descricao: "",
  numero: "",
  orgao_emissor: "",
  data_emissao: "",
  data_vencimento: "",
  arquivo_url: "",
  observacoes: "",
};

interface Documento {
  id: string;
  tipo: string;
  descricao?: string;
  numero?: string;
  orgao_emissor?: string;
  data_emissao?: string;
  data_vencimento?: string;
  arquivo_url?: string;
  observacoes?: string;
  ativo: boolean;
}

interface Equipamento {
  id: string;
  nome: string;
  tipo: string;
  marca?: string;
  modelo?: string;
}

function tipoLabel(tipo: string) {
  return TIPOS_DOC_COMPLETOS.find((t) => t.value === tipo)?.label ?? tipo;
}

function orgaoLabel(orgao?: string) {
  if (!orgao) return "Sem órgão";
  return ORGANOS_EMISSORES.find((o) => o.value === orgao)?.label ?? orgao;
}

function getVencimentoInfo(dataVencimento?: string) {
  if (!dataVencimento) {
    return {
      kind: "sem_vencimento" as const,
      label: "Sem vencimento",
      icon: null,
      className: "border-border/70 bg-muted/30 text-muted-foreground",
    };
  }

  const dias = differenceInDays(parseISO(dataVencimento), new Date());

  if (dias < 0) {
    return {
      kind: "vencido" as const,
      label: "Vencido",
      icon: <AlertTriangle className="size-3" />,
      className: "border-destructive/20 bg-destructive/5 text-destructive",
    };
  }

  if (dias <= 30) {
    return {
      kind: "vencendo" as const,
      label: `Vence em ${dias}d`,
      icon: <Clock className="size-3" />,
      className: "border-amber-200 bg-amber-50 text-amber-700",
    };
  }

  return {
    kind: "valido" as const,
    label: "Válido",
    icon: <CheckCircle2 className="size-3" />,
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
}

function vencimentoBadge(dataVencimento?: string) {
  const info = getVencimentoInfo(dataVencimento);
  return (
    <Badge variant="outline" className={cn("gap-1 text-xs", info.className)}>
      {info.icon}
      {info.label}
    </Badge>
  );
}

function statusFromDocumento(doc: Documento): StatusFiltro {
  if (!doc.data_vencimento) return "validos";
  const dias = differenceInDays(parseISO(doc.data_vencimento), new Date());
  if (dias < 0) return "vencidos";
  if (dias <= 30) return "vencendo";
  return "validos";
}

export default function DocumentosEquipamentoPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; docId?: string }>({ open: false });
  const [statusFilter, setStatusFilter] = useState<StatusFiltro>("todos");

  const form = useForm<DocumentoFormValues>({
    defaultValues: EMPTY_FORM,
  });
  const watchedForm = (useWatch({ control: form.control }) ?? EMPTY_FORM) as DocumentoFormValues;
  const isSaving = form.formState.isSubmitting;

  const { data: equipamento } = useQuery<Equipamento>({
    queryKey: ["equipamento", id],
    queryFn: () => apiFetch(`/cadastros/equipamentos/${id}`),
    enabled: !!id,
  });

  const { data: documentos = [], isLoading } = useQuery<Documento[]>({
    queryKey: ["documentos-equipamento", id],
    queryFn: () => apiFetch(`/frota/documentos/?equipamento_id=${id}&apenas_ativos=true`),
    enabled: !!id,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) =>
      apiFetch("/frota/documentos/", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentos-equipamento", id] });
      toast.success("Documento cadastrado");
      setOpen(false);
      setEditId(null);
      form.reset(EMPTY_FORM);
    },
    onError: () => toast.error("Erro ao salvar documento"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ docId, data }: { docId: string; data: any }) =>
      apiFetch(`/frota/documentos/${docId}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentos-equipamento", id] });
      toast.success("Documento atualizado");
      setOpen(false);
      setEditId(null);
      form.reset(EMPTY_FORM);
    },
    onError: () => toast.error("Erro ao atualizar documento"),
  });

  const removerMutation = useMutation({
    mutationFn: (docId: string) =>
      apiFetch(`/frota/documentos/${docId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documentos-equipamento", id] });
      toast.success("Documento removido");
    },
    onError: () => toast.error("Erro ao remover documento"),
  });

  const openNovo = () => {
    setEditId(null);
    form.reset(EMPTY_FORM);
    setOpen(true);
  };

  const openEditar = useCallback((doc: Documento) => {
    setEditId(doc.id);
    form.reset({
      tipo: doc.tipo as DocumentoTipo,
      descricao: doc.descricao ?? "",
      numero: doc.numero ?? "",
      orgao_emissor: doc.orgao_emissor ?? "",
      data_emissao: doc.data_emissao?.slice(0, 10) ?? "",
      data_vencimento: doc.data_vencimento?.slice(0, 10) ?? "",
      arquivo_url: doc.arquivo_url ?? "",
      observacoes: doc.observacoes ?? "",
    });
    setOpen(true);
  }, [form]);

  const handleSave = form.handleSubmit((values) => {
    const payload = {
      equipamento_id: id,
      tipo: values.tipo,
      descricao: values.descricao || undefined,
      numero: values.numero || undefined,
      orgao_emissor: values.orgao_emissor || undefined,
      data_emissao: values.data_emissao || undefined,
      data_vencimento: values.data_vencimento || undefined,
      arquivo_url: values.arquivo_url || undefined,
      observacoes: values.observacoes || undefined,
    };

    if (editId) {
      updateMutation.mutate({ docId: editId, data: payload });
      return;
    }

    createMutation.mutate(payload);
  });

  const documentosVisiveis = useMemo(() => {
    if (statusFilter === "todos") return documentos;
    return documentos.filter((doc) => statusFromDocumento(doc) === statusFilter);
  }, [documentos, statusFilter]);

  const resumo = useMemo(() => {
    const totais = documentos.reduce(
      (acc, doc) => {
        const status = statusFromDocumento(doc);
        acc.total += 1;
        if (status === "validos") acc.validos += 1;
        if (status === "vencendo") acc.vencendo += 1;
        if (status === "vencidos") acc.vencidos += 1;
        return acc;
      },
      { total: 0, validos: 0, vencendo: 0, vencidos: 0 }
    );

    return totais;
  }, [documentos]);

  const columns = useMemo<ColumnDef<Documento>[]>(() => [
    {
      id: "tipo",
      header: "Documento",
      accessorFn: (row) => `${tipoLabel(row.tipo)} ${row.descricao ?? ""}`,
      sortable: true,
      filterable: true,
      cell: (_value, row) => (
        <div className="flex flex-col gap-1">
          <div className="font-medium text-sm">{tipoLabel(row.tipo)}</div>
          {row.descricao ? <div className="text-xs text-muted-foreground">{row.descricao}</div> : null}
        </div>
      ),
    },
    {
      id: "numero",
      header: "Número / Código",
      accessorKey: "numero",
      sortable: true,
      filterable: true,
      cell: (value) => <span className="font-mono text-xs text-muted-foreground">{value || "—"}</span>,
    },
    {
      id: "orgao_emissor",
      header: "Órgão / Observação",
      accessorFn: (row) => `${orgaoLabel(row.orgao_emissor)} ${row.observacoes ?? ""}`,
      sortable: true,
      filterable: true,
      cell: (_value, row) => (
        <div className="flex flex-col gap-1">
          <span className="text-sm">{orgaoLabel(row.orgao_emissor)}</span>
          {row.observacoes ? <span className="text-xs text-muted-foreground">{row.observacoes}</span> : null}
        </div>
      ),
    },
    {
      id: "data_emissao",
      header: "Emissão",
      accessorFn: (row) => (row.data_emissao ? format(parseISO(row.data_emissao), "dd/MM/yyyy", { locale: ptBR }) : ""),
      sortable: true,
      filterable: false,
      cell: (_value, row) => (
        <span className="text-xs text-muted-foreground">
          {row.data_emissao ? format(parseISO(row.data_emissao), "dd/MM/yyyy", { locale: ptBR }) : "—"}
        </span>
      ),
    },
    {
      id: "data_vencimento",
      header: "Vencimento",
      accessorFn: (row) => (row.data_vencimento ? format(parseISO(row.data_vencimento), "dd/MM/yyyy", { locale: ptBR }) : ""),
      sortable: true,
      filterable: false,
      cell: (_value, row) => (
        <div className="flex flex-col gap-1">
          <span className="text-xs">{row.data_vencimento ? format(parseISO(row.data_vencimento), "dd/MM/yyyy", { locale: ptBR }) : "—"}</span>
          {row.data_vencimento ? (
            <span className="text-[11px] text-muted-foreground">
              {differenceInDays(parseISO(row.data_vencimento), new Date()) < 0
                ? `${Math.abs(differenceInDays(parseISO(row.data_vencimento), new Date()))} dias em atraso`
                : `${differenceInDays(parseISO(row.data_vencimento), new Date())} dias restantes`}
            </span>
          ) : null}
        </div>
      ),
    },
    {
      id: "status",
      header: "Status",
      accessorFn: (row) => getVencimentoInfo(row.data_vencimento).label,
      sortable: true,
      filterable: true,
      filterOptions: [
        { label: "Sem vencimento", value: "Sem vencimento" },
        { label: "Válido", value: "Válido" },
        { label: "Vence em 30d", value: "Vence em 30d" },
        { label: "Vencido", value: "Vencido" },
      ],
      cell: (_value, row) => vencimentoBadge(row.data_vencimento),
    },
    {
      id: "acoes",
      header: "",
      accessorKey: "id",
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_value, row) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
              <MoreHorizontal className="size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuItem onClick={() => openEditar(row)} className="gap-2">
              <Pencil className="size-3.5" />
              Editar
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="gap-2 text-destructive focus:text-destructive"
              onClick={() => setDeleteDialog({ open: true, docId: row.id })}
            >
              <Trash2 className="size-3.5" />
              Remover
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ], [openEditar]);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/cadastros/equipamentos" className="hover:text-foreground transition-colors">
          Equipamentos
        </Link>
        <span>/</span>
        <span className="truncate text-foreground font-medium">
          {equipamento ? equipamento.nome : "..."}
        </span>
        <span>/</span>
        <span className="text-foreground">Documentos</span>
      </div>

      <PageHeader
        title="Documentos"
        description={equipamento ? `${equipamento.marca ?? ""} ${equipamento.modelo ?? ""} - validade, rastreio e registros do equipamento` : "Carregando..."}
        icon={<FileText className="text-primary" size={22} />}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="size-4" data-icon="inline-start" />
              Voltar
            </Button>
            <Button size="sm" onClick={openNovo}>
              <Plus className="size-4" data-icon="inline-start" />
              Novo Documento
            </Button>
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-4">
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <CardDescription>Total</CardDescription>
            <CardTitle className="text-xl">{resumo.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <CardDescription>Válidos</CardDescription>
            <CardTitle className="text-xl text-emerald-700">{resumo.validos}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <CardDescription>Vencendo em 30 dias</CardDescription>
            <CardTitle className="text-xl text-amber-700">{resumo.vencendo}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="border-border/60 shadow-sm">
          <CardHeader className="pb-1">
            <CardDescription>Vencidos</CardDescription>
            <CardTitle className="text-xl text-destructive">{resumo.vencidos}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Documentos do equipamento</CardTitle>
              <CardDescription>Busque por tipo, número, órgão emissor ou observações.</CardDescription>
            </div>
            <ToggleGroup
              type="single"
              value={statusFilter}
              onValueChange={(value) => setStatusFilter((value as StatusFiltro) || "todos")}
              className="flex flex-wrap gap-1"
            >
              <ToggleGroupItem value="todos">Todos</ToggleGroupItem>
              <ToggleGroupItem value="validos">Válidos</ToggleGroupItem>
              <ToggleGroupItem value="vencendo">Vencendo</ToggleGroupItem>
              <ToggleGroupItem value="vencidos">Vencidos</ToggleGroupItem>
            </ToggleGroup>
          </div>
        </CardHeader>
      </Card>

      <DataTable
        data={documentosVisiveis}
        columns={columns}
        searchable
        searchPlaceholder="Buscar documentos..."
        exportable
        exportFileName="documentos-equipamento"
        emptyMessage={
          statusFilter === "todos"
            ? "Nenhum documento cadastrado para este equipamento"
            : "Nenhum documento encontrado para este filtro"
        }
        rowClassName={(row) => {
          const status = statusFromDocumento(row);
          if (status === "vencidos") return "bg-destructive/5";
          if (status === "vencendo") return "bg-amber-500/5";
          return "";
        }}
      />

      <Dialog open={open} onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) {
          setEditId(null);
          form.reset(EMPTY_FORM);
        }
      }}>
        <DialogContent className="max-w-3xl p-0">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Documento" : "Novo Documento"}</DialogTitle>
            <div className="text-sm text-muted-foreground">
              {equipamento ? `${equipamento.nome} - ${tipoLabel(watchedForm.tipo)}` : "Cadastre o documento do equipamento."}
            </div>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={handleSave}>
              <DialogBody className="max-h-[70vh] overflow-y-auto pb-3">
                <div className="grid gap-4">
                  <div className="grid gap-3 md:grid-cols-3">
                    <FormField
                      control={form.control}
                      name="tipo"
                      render={({ field }) => (
                        <FormItem className="md:col-span-2">
                          <FormLabel>Tipo *</FormLabel>
                          <Select value={field.value} onValueChange={field.onChange}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Selecione o tipo" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {TIPOS_DOC_COMPLETOS.map((tipo) => (
                                <SelectItem key={tipo.value} value={tipo.value}>
                                  {tipo.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="numero"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Número / Código</FormLabel>
                          <FormControl>
                            <Input {...field} value={field.value ?? ""} placeholder="Ex: 123456-7" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="grid gap-3 md:grid-cols-3">
                    <FormField
                      control={form.control}
                      name="orgao_emissor"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Órgão Emissor</FormLabel>
                          <Select value={field.value} onValueChange={field.onChange}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Selecione..." />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {ORGANOS_EMISSORES.map((orgao) => (
                                <SelectItem key={orgao.value} value={orgao.value}>
                                  {orgao.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="data_emissao"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Data de Emissão</FormLabel>
                          <FormControl>
                            <Input {...field} type="date" value={field.value ?? ""} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="data_vencimento"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Data de Vencimento</FormLabel>
                          <FormControl>
                            <Input {...field} type="date" value={field.value ?? ""} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <Separator />

                  <div className="grid gap-3">
                    <FormField
                      control={form.control}
                      name="descricao"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Descrição</FormLabel>
                          <FormControl>
                            <Textarea {...field} value={field.value ?? ""} rows={3} placeholder="Nome curto do documento ou finalidade" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="observacoes"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Observações</FormLabel>
                          <FormControl>
                            <Textarea {...field} value={field.value ?? ""} rows={3} placeholder="Detalhes adicionais, restrições ou contexto" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="arquivo_url"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>URL do arquivo</FormLabel>
                          <FormControl>
                            <Input {...field} value={field.value ?? ""} placeholder="https://..." />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
              </DialogBody>

              <DialogFooter className="gap-2 sm:gap-0">
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={isSaving || createMutation.isPending || updateMutation.isPending}>
                  {(isSaving || createMutation.isPending || updateMutation.isPending) ? "Salvando..." : editId ? "Salvar" : "Cadastrar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteDialog.open}
        title="Remover Documento"
        description="Tem certeza que deseja remover este documento? Esta ação não pode ser desfeita."
        confirmText="Remover"
        cancelText="Cancelar"
        destructive
        onConfirm={() => deleteDialog.docId && removerMutation.mutate(deleteDialog.docId)}
        onCancel={() => setDeleteDialog({ open: false })}
      />
    </div>
  );
}
