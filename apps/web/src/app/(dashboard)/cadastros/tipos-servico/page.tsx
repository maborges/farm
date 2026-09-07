"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import { Wrench, Plus, Pencil, PowerOff, Power, Loader2, XCircle, Save } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";

const UNIDADES = [
  { value: "UN", label: "Unidade" },
  { value: "HA", label: "Hectare (ha)" },
  { value: "H", label: "Hora (h)" },
  { value: "DIA", label: "Diária" },
  { value: "KM", label: "Quilômetro (km)" },
  { value: "SC", label: "Saca (sc)" },
];

const tipoServicoSchema = z.object({
  ativo: z.boolean(),
  nome: z.string().min(2, "Mínimo 2 caracteres").max(200),
  unidade_medida: z.string().min(1, "Unidade é obrigatória"),
  custo_referencia: z.coerce.number().optional(),
  observacoes: z.string().optional(),
});

type TipoServicoFormValues = z.infer<typeof tipoServicoSchema>;

interface TipoServico {
  id: string;
  nome: string;
  unidade_medida: string;
  custo_referencia?: number | null;
  observacoes?: string | null;
  ativo: boolean;
  is_global: boolean;
}

interface TipoServicoPayload {
  nome: string;
  unidade_medida: string;
  custo_referencia?: number;
  observacoes?: string;
  ativo?: boolean;
}

const EMPTY_FORM: TipoServicoFormValues = {
  ativo: true,
  nome: "",
  unidade_medida: "UN",
  custo_referencia: undefined,
  observacoes: "",
};

export default function TiposServicoPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const form = useForm<TipoServicoFormValues>({
    resolver: zodResolver(tipoServicoSchema) as Resolver<TipoServicoFormValues>,
    defaultValues: EMPTY_FORM,
  });

  const resetForm = () => {
    form.reset(EMPTY_FORM);
    setEditId(null);
  };

  const { data: tiposServico = [], isLoading } = useQuery<TipoServico[]>({
    queryKey: ["tipos-servico"],
    queryFn: () => apiFetch<TipoServico[]>("/cadastros/tipos-servico?q="),
  });

  const createMutation = useMutation({
    mutationFn: (data: TipoServicoPayload) =>
      apiFetch("/cadastros/tipos-servico", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tipos-servico"] });
      toast.success("Tipo de serviço cadastrado com sucesso");
      setOpen(false);
      resetForm();
    },
    onError: () => toast.error("Erro ao cadastrar tipo de serviço"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TipoServicoPayload }) =>
      apiFetch(`/cadastros/tipos-servico/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tipos-servico"] });
      toast.success("Tipo de serviço atualizado");
      setOpen(false);
      resetForm();
    },
    onError: () => toast.error("Erro ao atualizar tipo de serviço"),
  });

  const toggleAtivoMutation = useMutation({
    mutationFn: ({ id, ativo }: { id: string; ativo: boolean }) =>
      apiFetch(`/cadastros/tipos-servico/${id}`, { method: "PATCH", body: JSON.stringify({ ativo }) }),
    onSuccess: (_, { ativo }) => {
      queryClient.invalidateQueries({ queryKey: ["tipos-servico"] });
      toast.success(ativo ? "Tipo de serviço ativado" : "Tipo de serviço desativado");
    },
    onError: () => toast.error("Erro ao alterar status"),
  });

  const openEditar = (t: TipoServico) => {
    setEditId(t.id);
    form.reset({
      ativo: t.ativo,
      nome: t.nome,
      unidade_medida: t.unidade_medida,
      custo_referencia: t.custo_referencia ?? undefined,
      observacoes: t.observacoes ?? "",
    });
    setOpen(true);
  };

  const handleSave = (data: TipoServicoFormValues) => {
    const payload: TipoServicoPayload = {
      nome: data.nome.trim(),
      unidade_medida: data.unidade_medida,
      custo_referencia: data.custo_referencia || undefined,
      observacoes: data.observacoes || undefined,
      ativo: data.ativo,
    };
    if (editId) {
      updateMutation.mutate({ id: editId, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleNovo = () => {
    setEditId(null);
    form.reset(EMPTY_FORM);
    setOpen(true);
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  const columns: ColumnDef<TipoServico>[] = [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value, row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{value}</span>
          {row.is_global && (
            <Badge variant="outline" className="text-[10px] bg-cyan-50 text-cyan-700">Padrão</Badge>
          )}
        </div>
      ),
    },
    {
      id: "unidade_medida",
      header: "Unidade",
      accessorKey: "unidade_medida",
      cell: (value) => (
        <Badge variant="outline" className="text-xs">
          {UNIDADES.find((u) => u.value === value)?.label ?? value}
        </Badge>
      ),
    },
    {
      id: "custo_referencia",
      header: "Custo de Referência",
      accessorKey: "custo_referencia",
      cell: (value) => (
        <span className="text-muted-foreground">
          {value != null ? Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}
        </span>
      ),
    },
    {
      id: "ativo",
      header: "Status",
      accessorKey: "ativo",
      cell: (value) => (
        <Badge variant="outline" className={value ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}>
          {value ? "Ativo" : "Inativo"}
        </Badge>
      ),
      exportFormat: (value) => (value ? "Ativo" : "Inativo"),
    },
    {
      id: "acoes",
      header: "",
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={`Editar ${row.nome}`}
            title={row.is_global ? "Registro padrão do sistema — somente leitura" : "Editar"}
            onClick={() => openEditar(row)}
            disabled={row.is_global}
          >
            <Pencil />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={row.ativo ? `Desativar ${row.nome}` : `Ativar ${row.nome}`}
            title={row.is_global ? "Registro padrão do sistema — somente leitura" : row.ativo ? "Desativar" : "Ativar"}
            onClick={() => toggleAtivoMutation.mutate({ id: row.id, ativo: !row.ativo })}
            disabled={toggleAtivoMutation.isPending || row.is_global}
            className={row.ativo ? "text-destructive hover:text-destructive" : "text-emerald-600 hover:text-emerald-600"}
          >
            {row.ativo ? <PowerOff /> : <Power />}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Tipos de Serviço"
        description="Serviços terceirizados (aplicação, colheita, transporte) com custo de referência — usado no orçamento de safra."
        icon={<Wrench className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Cadastros", href: "/cadastros" }, { label: "Tipos de Serviço" }]}
        actions={
          <Button size="sm" variant="outline" className="rounded-sm border-primary/50 text-primary hover:bg-primary/5" onClick={handleNovo}>
            <Plus className="size-4 mr-2" />
            Novo Tipo de Serviço
          </Button>
        }
      />

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Carregando...</div>
      ) : (
        <DataTable
          data={tiposServico}
          columns={columns}
          searchPlaceholder="Buscar por nome..."
          exportFileName="tipos-servico"
          emptyMessage="Nenhum tipo de serviço cadastrado"
        />
      )}

      <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
        <DialogContent className="max-w-md p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Wrench className="size-4 text-primary" />
              </div>
              <DialogTitle>{editId ? "Editar Tipo de Serviço" : "Novo Tipo de Serviço"}</DialogTitle>
            </div>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSave)}>
              <DialogBody className="space-y-4">
                <FormField
                  control={form.control}
                  name="nome"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nome *</FormLabel>
                      <FormControl>
                        <Input {...field} className="h-8 rounded-sm text-xs"
                          placeholder="Ex: Aplicação terceirizada de defensivo"
                          disabled={isPending} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="grid grid-cols-2 gap-3">
                  <FormField
                    control={form.control}
                    name="unidade_medida"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Unidade *</FormLabel>
                        <Select onValueChange={field.onChange} value={field.value} disabled={isPending}>
                          <FormControl>
                            <SelectTrigger className="h-8 rounded-sm text-xs"><SelectValue /></SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {UNIDADES.map((u) => <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField control={form.control} name="custo_referencia" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Custo de Referência</FormLabel>
                      <FormControl>
                        <Input type="number" min="0" step="0.01" {...field} value={field.value ?? ""} className="h-8 rounded-sm text-xs" placeholder="85,50" disabled={isPending} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )} />
                </div>
                <FormField control={form.control} name="observacoes" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observações</FormLabel>
                    <FormControl>
                      <Textarea {...field} className="rounded-sm text-xs" rows={3} placeholder="Detalhes do serviço, fornecedor de referência, etc." disabled={isPending} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </DialogBody>

              <DialogFooter>
                <FormField
                  control={form.control}
                  name="ativo"
                  render={({ field }) => (
                    <div className="flex items-center gap-2 mr-auto">
                      <Switch checked={field.value} onCheckedChange={field.onChange} disabled={isPending} />
                      <span className="text-xs text-muted-foreground font-medium">Ativo</span>
                    </div>
                  )}
                />
                <Button type="button" variant="outline" size="sm" className="rounded-sm"
                  onClick={() => { setOpen(false); resetForm(); }}
                  disabled={isPending}>
                  <XCircle className="size-3.5 mr-1.5" /> Cancelar
                </Button>
                <Button type="submit" size="sm" className="rounded-sm" disabled={isPending}>
                  {isPending ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Save className="size-3.5 mr-1.5" />}
                  {isPending ? "Salvando..." : editId ? "Salvar Alterações" : "Cadastrar"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
