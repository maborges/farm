"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/shared/page-header";
import { Plus, Pencil, Trash2, Cpu, Save, XCircle, Layers } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";

interface Marca { id: string; nome: string; }
interface Modelo {
  id: string;
  nome: string;
  referencia?: string;
  marca_id: string;
  marca_nome?: string;
  ativo: boolean;
  tenant_id?: string | null;
  sistema?: boolean;
}

type FormState = Partial<Modelo>;
const EMPTY: FormState = { nome: "", referencia: "", marca_id: undefined, ativo: true };

interface ModelosReusableProps {
  mode: "subscriber" | "backoffice";
}

export function ModelosReusable({ mode }: ModelosReusableProps) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; modelo?: Modelo }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [filterMarca, setFilterMarca] = useState<string>("all");
  const [modeloToDelete, setModeloToDelete] = useState<Modelo | null>(null);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const isBackoffice = mode === "backoffice";
  const baseUrl = isBackoffice ? "/backoffice/tabelas/modelos" : "/cadastros/modelos-produto";
  const marcasUrl = isBackoffice ? "/backoffice/tabelas/marcas" : "/cadastros/marcas";
  const queryKey = isBackoffice ? ["backoffice-modelos", filterMarca] : ["tabelas-modelos", filterMarca];
  const marcasQueryKey = isBackoffice ? ["backoffice-marcas"] : ["tabelas-marcas"];

  const { data: marcas = [] } = useQuery<Marca[]>({
    queryKey: marcasQueryKey,
    queryFn: () => apiFetch(marcasUrl),
  });

  const { data: modelos = [] } = useQuery<Modelo[]>({
    queryKey,
    queryFn: () => {
      const qs = filterMarca !== "all" ? `?marca_id=${filterMarca}` : "";
      return apiFetch(`${baseUrl}${qs}`);
    },
  });

  const save = useMutation({
    mutationFn: (f: FormState) =>
      dialog.modelo
        ? apiFetch(`${baseUrl}/${dialog.modelo.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch(baseUrl, { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { 
      qc.invalidateQueries({ queryKey }); 
      setDialog({ open: false });
      toast.success("Modelo salvo com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao salvar modelo");
    }
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`${baseUrl}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Modelo excluído com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao excluir modelo");
    }
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(m: Modelo) { setForm(m); setDialog({ open: true, modelo: m }); }

  const columns: ColumnDef<Modelo>[] = [
    {
      id: "nome",
      header: "Modelo",
      accessorKey: "nome",
      cell: (value) => <span className="font-medium">{value}</span>,
    },
    {
      id: "marca",
      header: "Marca",
      accessorKey: "marca_nome",
      cell: (value) => value ?? "—",
    },
    {
      id: "referencia",
      header: "Referência",
      accessorKey: "referencia",
      cell: (value) => value ?? "—",
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativo",
      cell: (value) => <StatusBadge status={value ? "ativo" : "inativo"} />,
      exportFormat: (value) => (value ? "Ativo" : "Inativo"),
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => {
        const canEdit = isBackoffice || (!row.sistema && row.tenant_id);

        return (
          <div className="flex items-center gap-0 justify-end">
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-primary hover:text-primary disabled:opacity-30"
              onClick={() => openEdit(row)}
              disabled={!canEdit}
              title={!canEdit ? "Registros do sistema não podem ser alterados" : "Editar"}
            >
              <Pencil className="size-3.5" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-destructive hover:text-destructive disabled:opacity-30"
              onClick={() => setModeloToDelete(row)}
              disabled={!canEdit}
              title={!canEdit ? "Registros do sistema não podem ser excluídos" : "Excluir"}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="w-full space-y-4 p-6">
      {!isBackoffice && (
        <PageHeader
          title="Modelos"
          description="Modelos de produtos por marca."
          icon={<Layers className="text-primary" size={20} />}
          breadcrumbs={[
            { label: "Cadastros", href: "/cadastros" },
            { label: "Tabelas", href: "/cadastros/tabelas" },
            { label: "Modelos" },
          ]}
          actions={(
            <Button size="sm" variant="outline" className="w-full rounded-sm sm:w-auto" onClick={openNew}>
              <Plus data-icon="inline-start" />
              Novo Modelo
            </Button>
          )}
        />
      )}

      {isBackoffice && (
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Modelos Disponíveis</h2>
          <Button size="sm" variant="outline" className="h-8 rounded-sm" onClick={openNew}>
            <Plus className="size-3.5 mr-1.5" /> Novo Modelo
          </Button>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Label className="text-sm shrink-0">Filtrar por marca:</Label>
        <Select value={filterMarca} onValueChange={setFilterMarca}>
          <SelectTrigger className="w-52 h-8 text-xs"><SelectValue placeholder="Todas as marcas" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as marcas</SelectItem>
            {marcas.map((m) => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        data={modelos}
        columns={columns}
        searchPlaceholder="Buscar modelos..."
        exportFileName="modelos"
        emptyMessage="Nenhum modelo cadastrado"
      />

      <ConfirmDialog
        open={!!modeloToDelete}
        title="Excluir modelo?"
        description={modeloToDelete ? `O modelo "${modeloToDelete.nome}" será removido permanentemente.` : undefined}
        confirmText="Excluir"
        destructive
        onCancel={() => setModeloToDelete(null)}
        onConfirm={() => {
          if (!modeloToDelete) return;
          remove.mutate(modeloToDelete.id, {
            onSettled: () => setModeloToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Cpu className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.modelo ? "Editar Modelo" : "Novo Modelo"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Marca *</Label>
              <Select value={form.marca_id ?? "none"} onValueChange={(v: string) => set({ marca_id: v === "none" ? undefined : v })}>
                <SelectTrigger className="h-8 text-xs rounded-sm">
                  <SelectValue placeholder={form.marca_id ? (marcas.find(m => m.id === form.marca_id)?.nome ?? form.marca_nome ?? "Selecionar marca…") : "Selecionar marca…"} />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="none" className="text-xs">— Selecionar —</SelectItem>
                  {marcas.map((m) => <SelectItem key={m.id} value={m.id} className="text-xs">{m.nome}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome *</Label>
              <Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} className="h-8 text-xs rounded-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Referência</Label>
              <Input placeholder="Código / part number" value={form.referencia ?? ""} onChange={(e) => set({ referencia: e.target.value })} className="h-8 text-xs rounded-sm" />
            </div>
            <div className="flex items-center gap-2 pt-2">
              <Switch checked={form.ativo} onCheckedChange={(checked: boolean) => set({ ativo: checked })} />
              <Label className="text-xs font-medium">Ativo</Label>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="size-3.5 mr-1.5" />
              Cancelar
            </Button>
            <Button 
              variant="default" 
              size="sm" 
              className="rounded-sm"
              onClick={() => save.mutate(form)} 
              disabled={!form.nome || !form.marca_id || save.isPending}
            >
              <Save className="size-3.5 mr-1.5" />
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
