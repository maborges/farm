"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "@/components/ui/status-badge";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/shared/page-header";
import { Plus, Pencil, Trash2, Globe, Save, XCircle, BookmarkCheck } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";

interface Marca {
  id: string;
  nome: string;
  nome_fantasia?: string;
  pais_origem?: string;
  website?: string;
  ativo: boolean;
  tenant_id?: string | null;
  sistema?: boolean;
}

type FormState = Partial<Marca>;
const EMPTY: FormState = { nome: "", nome_fantasia: "", website: "", pais_origem: "Brasil", ativo: true };

interface MarcasReusableProps {
  mode: "subscriber" | "backoffice";
}

export function MarcasReusable({ mode }: MarcasReusableProps) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; marca?: Marca }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [marcaToDelete, setMarcaToDelete] = useState<Marca | null>(null);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const isBackoffice = mode === "backoffice";
  const baseUrl = isBackoffice ? "/backoffice/tabelas/marcas" : "/cadastros/marcas";
  const queryKey = isBackoffice ? ["backoffice-marcas"] : ["tabelas-marcas"];

  const { data = [], isLoading } = useQuery<Marca[]>({
    queryKey,
    queryFn: () => apiFetch(baseUrl),
  });

  const save = useMutation({
    mutationFn: (f: FormState) =>
      dialog.marca
        ? apiFetch(`${baseUrl}/${dialog.marca.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch(baseUrl, { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { 
      qc.invalidateQueries({ queryKey }); 
      setDialog({ open: false });
      toast.success("Marca salva com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao salvar marca");
    }
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`${baseUrl}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Marca excluída com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao excluir marca");
    },
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(m: Marca) { setForm(m); setDialog({ open: true, marca: m }); }

  const columns: ColumnDef<Marca>[] = [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value) => <span className="font-medium">{value}</span>,
    },
    {
      id: "nome_fantasia",
      header: "Nome Fantasia",
      accessorKey: "nome_fantasia",
      cell: (value) => value ?? "—",
    },
    {
      id: "pais_origem",
      header: "País",
      accessorKey: "pais_origem",
      cell: (value) => (
        <Badge variant="outline" className="text-[10px] rounded-sm font-normal">
          {value || "Brasil"}
        </Badge>
      ),
    },
    {
      id: "website",
      header: "Website",
      accessorKey: "website",
      cell: (value) =>
        value ? (
          <a
            href={value}
            target="_blank"
            rel="noreferrer"
            className="block max-w-[240px] truncate text-primary underline-offset-2 hover:underline"
            title={value}
          >
            {value}
          </a>
        ) : (
          "—"
        ),
      exportFormat: (value) => value ?? "",
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
              onClick={() => setMarcaToDelete(row)}
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
    <div className="flex w-full flex-col gap-4 p-6">
      {!isBackoffice && (
        <PageHeader
          title="Marcas"
          description="Fabricantes e marcas dos produtos do catálogo."
          icon={<BookmarkCheck className="text-primary" size={20} />}
          breadcrumbs={[
            { label: "Cadastros", href: "/cadastros" },
            { label: "Tabelas", href: "/cadastros/tabelas" },
            { label: "Marcas" },
          ]}
          actions={(
            <Button size="sm" variant="outline" className="w-full rounded-sm sm:w-auto" onClick={openNew}>
              <Plus data-icon="inline-start" />
              Nova Marca
            </Button>
          )}
        />
      )}

      {isBackoffice && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Marcas Disponíveis</h2>
          <Button size="sm" variant="outline" className="w-full rounded-sm sm:w-auto" onClick={openNew}>
            <Plus data-icon="inline-start" />
            Nova Marca
          </Button>
        </div>
      )}

      <DataTable
        data={data}
        columns={columns}
        searchPlaceholder="Buscar marcas..."
        exportFileName="marcas"
        emptyMessage="Nenhuma marca cadastrada"
        isLoading={isLoading}
      />

      <ConfirmDialog
        open={!!marcaToDelete}
        title="Excluir marca?"
        description={marcaToDelete ? `A marca "${marcaToDelete.nome}" será removida permanentemente.` : undefined}
        confirmText="Excluir"
        destructive
        onCancel={() => setMarcaToDelete(null)}
        onConfirm={() => {
          if (!marcaToDelete) return;
          remove.mutate(marcaToDelete.id, {
            onSettled: () => setMarcaToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Globe className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.marca ? "Editar Marca" : "Nova Marca"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome / Razão Social *</Label>
              <Input 
                value={form.nome ?? ""} 
                onChange={(e) => set({ nome: e.target.value })} 
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome Fantasia</Label>
              <Input 
                value={form.nome_fantasia ?? ""} 
                onChange={(e) => set({ nome_fantasia: e.target.value })} 
                className="h-8 text-xs rounded-sm"
              />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">País de Origem</Label>
                <Input 
                  placeholder="Ex: Brasil, EUA..." 
                  value={form.pais_origem ?? ""} 
                  onChange={(e) => set({ pais_origem: e.target.value })} 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Website</Label>
                <Input 
                  placeholder="https://..." 
                  value={form.website ?? ""} 
                  onChange={(e) => set({ website: e.target.value })} 
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 rounded-sm border bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs font-medium">Status do Registro</Label>
                <p className="text-[10px] text-muted-foreground">Define se a marca estará visível para seleção</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("text-[10px] font-bold uppercase", form.ativo ? "text-emerald-600" : "text-muted-foreground")}>
                  {form.ativo ? "Ativo" : "Inativo"}
                </span>
                <Switch 
                  checked={form.ativo} 
                  onCheckedChange={(checked) => set({ ativo: checked })} 
                />
              </div>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle data-icon="inline-start" />
              Cancelar
            </Button>
            <Button
              size="sm"
              className="rounded-sm"
              onClick={() => save.mutate(form)}
              disabled={!form.nome || save.isPending}
            >
              <Save data-icon="inline-start" />
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
