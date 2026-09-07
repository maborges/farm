"use client";

import { useState, useMemo } from "react";
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
import { Plus, Pencil, Trash2, ChevronRight, Save, XCircle, FolderTree } from "lucide-react";
import { toast } from "sonner";

interface CategoriaProduto {
  id: string;
  nome: string;
  descricao?: string;
  parent_id?: string;
  cor?: string;
  ordem: number;
  ativo: boolean;
  tenant_id?: string | null;
  sistema?: boolean;
}

type FormState = Partial<CategoriaProduto>;
const EMPTY: FormState = { nome: "", descricao: "", parent_id: undefined, cor: "#6366f1", ordem: 0, ativo: true };

interface CategoriasReusableProps {
  mode: "subscriber" | "backoffice";
}

export function CategoriasReusable({ mode }: CategoriasReusableProps) {
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<{ open: boolean; cat?: CategoriaProduto }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [catToDelete, setCatToDelete] = useState<CategoriaProduto | null>(null);
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const isBackoffice = mode === "backoffice";
  const baseUrl = isBackoffice ? "/backoffice/tabelas/categorias-produto" : "/cadastros/categorias-produto";
  const queryKey = isBackoffice ? ["backoffice-categorias-produto"] : ["tabelas-categorias-produto"];

  const { data: categorias = [] } = useQuery<CategoriaProduto[]>({
    queryKey,
    queryFn: () => apiFetch(baseUrl),
  });

  const save = useMutation({
    mutationFn: (f: FormState) =>
      dialog.cat
        ? apiFetch(`${baseUrl}/${dialog.cat.id}`, { method: "PATCH", body: JSON.stringify(f) })
        : apiFetch(baseUrl, { method: "POST", body: JSON.stringify(f) }),
    onSuccess: () => { 
      qc.invalidateQueries({ queryKey }); 
      setDialog({ open: false });
      toast.success("Categoria salva com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao salvar categoria");
    }
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch(`${baseUrl}/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Categoria excluída com sucesso!");
    },
    onError: (error: any) => {
      toast.error(error?.message || "Erro ao excluir categoria");
    }
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(c: CategoriaProduto) { setForm(c); setDialog({ open: true, cat: c }); }

  // Flatten hierarchy for DataTable: root categories followed by their children
  const flatCategorias = useMemo(() => {
    const raizes = categorias.filter((c) => !c.parent_id).sort((a, b) => a.ordem - b.ordem);
    const result: CategoriaProduto[] = [];
    raizes.forEach((raiz) => {
      result.push(raiz);
      const filhos = categorias
        .filter((c) => c.parent_id === raiz.id)
        .sort((a, b) => a.ordem - b.ordem);
      result.push(...filhos);
    });
    return result;
  }, [categorias]);

  const columns: ColumnDef<CategoriaProduto>[] = [
    {
      id: "nome",
      header: "Nome",
      accessorKey: "nome",
      cell: (value, row) => (
        row.parent_id ? (
          <span className="flex items-center gap-1 text-sm text-muted-foreground pl-5">
            <ChevronRight className="size-3" />
            {value}
          </span>
        ) : (
          <span className="font-medium">{value}</span>
        )
      ),
      exportFormat: (value, row) => row.parent_id ? `  → ${value}` : value,
    },
    {
      id: "descricao",
      header: "Descrição",
      accessorKey: "descricao",
      cell: (value) => <span className="text-sm text-muted-foreground">{value ?? "—"}</span>,
    },
    {
      id: "parent",
      header: "Categoria Pai",
      accessorKey: "parent_id",
      cell: (value) => {
        if (!value) return "—";
        const parent = categorias.find((c) => String(c.id) === String(value));
        return parent ? parent.nome : <span className="text-destructive font-mono text-[10px]">{value}</span>;
      },
    },
    {
      id: "cor",
      header: "Cor",
      accessorKey: "cor",
      cell: (value) =>
        value ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="size-3 rounded-full border" style={{ background: value }} />
            {value}
          </span>
        ) : (
          "—"
        ),
    },
    {
      id: "ordem",
      header: "Ordem",
      accessorKey: "ordem",
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
              onClick={() => setCatToDelete(row)}
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
          title="Categorias de Produto"
          description="Organização hierárquica dos produtos do catálogo."
          icon={<FolderTree className="text-primary" size={20} />}
          breadcrumbs={[
            { label: "Cadastros", href: "/cadastros" },
            { label: "Tabelas", href: "/cadastros/tabelas" },
            { label: "Categorias de Produto" },
          ]}
          actions={(
            <Button size="sm" variant="outline" className="w-full rounded-sm sm:w-auto" onClick={openNew}>
              <Plus data-icon="inline-start" />
              Nova Categoria
            </Button>
          )}
        />
      )}

      {isBackoffice && (
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Categorias Disponíveis</h2>
          <Button size="sm" variant="outline" className="h-8 rounded-sm" onClick={openNew}>
            <Plus className="size-3.5 mr-1.5" /> Nova Categoria
          </Button>
        </div>
      )}

      <DataTable
        data={flatCategorias}
        columns={columns}
        searchPlaceholder="Buscar categorias..."
        exportFileName="categorias-produto"
        emptyMessage="Nenhuma categoria cadastrada"
        rowClassName={(row) => row.parent_id ? "bg-muted/30" : ""}
      />

      <ConfirmDialog
        open={!!catToDelete}
        title="Excluir categoria?"
        description={catToDelete ? `A categoria "${catToDelete.nome}" será removida permanentemente.` : undefined}
        confirmText="Excluir"
        destructive
        onCancel={() => setCatToDelete(null)}
        onConfirm={() => {
          if (!catToDelete) return;
          remove.mutate(catToDelete.id, {
            onSettled: () => setCatToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => setDialog({ open: o })}>
        <DialogContent className="max-w-md p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <Plus className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.cat ? "Editar Categoria" : "Nova Categoria"}</DialogTitle>
            </div>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label>Nome *</Label>
              <Input value={form.nome ?? ""} onChange={(e) => set({ nome: e.target.value })} className="h-8 rounded-sm text-xs" />
            </div>
            <div className="space-y-1.5">
              <Label>Categoria Pai</Label>
              <Select
                value={form.parent_id ? String(form.parent_id) : "none"}
                onValueChange={(v: string) => set({ parent_id: v === "none" ? undefined : v })}
              >
                <SelectTrigger className="h-8 text-xs rounded-sm">
                  <SelectValue placeholder={form.parent_id ? (categorias.find(c => String(c.id) === String(form.parent_id))?.nome || form.parent_id) : "Nenhuma (categoria raiz)"} />
                </SelectTrigger>
                <SelectContent className="rounded-sm">
                  <SelectItem value="none" className="text-xs">— Nenhuma (raiz) —</SelectItem>
                  {categorias
                    .filter((c) => c.id !== dialog.cat?.id)
                    .map((c) => (
                      <SelectItem key={c.id} value={String(c.id)} className="text-xs">
                        {`${c.parent_id ? "  " : ""}${c.nome}`}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Descrição</Label>
              <Input value={form.descricao ?? ""} onChange={(e) => set({ descricao: e.target.value })} className="h-8 rounded-sm text-xs" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Cor</Label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={form.cor ?? "#6366f1"}
                    onChange={(e) => set({ cor: e.target.value })}
                    className="size-8 rounded-sm border cursor-pointer bg-transparent"
                  />
                  <Input value={form.cor ?? ""} onChange={(e) => set({ cor: e.target.value })} className="h-8 font-mono text-xs rounded-sm" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Ordem</Label>
                <Input
                  type="number" min={0}
                  value={form.ordem ?? 0}
                  onChange={(e) => set({ ordem: parseInt(e.target.value) || 0 })}
                  className="h-8 rounded-sm text-xs"
                />
              </div>
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
              disabled={!form.nome || save.isPending}
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
