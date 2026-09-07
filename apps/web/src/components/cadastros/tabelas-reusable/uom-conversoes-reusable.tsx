"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Pencil, Trash2, Save, ArrowRight, ArrowRightLeft, XCircle } from "lucide-react";
import { toast } from "sonner";

interface Uom {
  id: string;
  codigo: string;
  nome: string;
  dimensao: string;
  ativo: boolean;
}

interface Conversao {
  id: string;
  unidade_origem_id: string;
  unidade_destino_id: string;
  fator: number;
  cultura: string | null;
  observacoes: string | null;
  tenant_id: string | null;
  created_at: string;
}

type FormState = Partial<Conversao>;
const EMPTY: FormState = {
  unidade_origem_id: "",
  unidade_destino_id: "",
  fator: undefined,
  cultura: "",
  observacoes: "",
};

export function UomConversoesReusable() {
  const qc = useQueryClient();
  const canWrite = usePermission("backoffice:uom:create");
  const [dialog, setDialog] = useState<{ open: boolean; item?: Conversao }>({ open: false });
  const [form, setForm] = useState<FormState>(EMPTY);
  const [conversaoToDelete, setConversaoToDelete] = useState<Conversao | null>(null);

  const queryKey = ["bo-uom-conversoes"];

  const { data: conversoes = [], isLoading } = useQuery<Conversao[]>({
    queryKey,
    queryFn: () => apiFetch("/backoffice/uom/conversoes/"),
  });

  const { data: uoms = [] } = useQuery<Uom[]>({
    queryKey: ["bo-uom"],
    queryFn: () => apiFetch("/backoffice/uom/"),
  });

  const uomMap = Object.fromEntries(uoms.map((u) => [u.id, u]));
  const renderUomNome = (id?: string | null) => {
    if (!id) return null;
    return uomMap[id]?.nome ?? null;
  };

  const save = useMutation({
    mutationFn: (payload: FormState) =>
      dialog.item
        ? apiFetch(`/backoffice/uom/conversoes/${dialog.item.id}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          })
        : apiFetch("/backoffice/uom/conversoes/", {
            method: "POST",
            body: JSON.stringify(payload),
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      setDialog({ open: false });
      toast.success(dialog.item ? "Conversão atualizada" : "Conversão cadastrada");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao salvar"),
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/backoffice/uom/conversoes/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      toast.success("Conversão removida");
    },
    onError: (e: any) => toast.error(e.message || "Erro ao remover"),
  });

  function openNew() { setForm(EMPTY); setDialog({ open: true }); }
  function openEdit(item: Conversao) { setForm(item); setDialog({ open: true, item }); }
  const set = (p: Partial<FormState>) => setForm((f) => ({ ...f, ...p }));

  const origemUom = uomMap[form.unidade_origem_id ?? ""];
  const destinoUom = uomMap[form.unidade_destino_id ?? ""];
  const preview =
    origemUom && destinoUom && form.fator && form.fator > 0
      ? `1 ${origemUom.nome} = ${form.fator.toLocaleString("pt-BR", { maximumSignificantDigits: 6 })} ${destinoUom.nome}`
      : null;

  const isValid =
    form.unidade_origem_id &&
    form.unidade_destino_id &&
    form.unidade_origem_id !== form.unidade_destino_id &&
    form.fator &&
    form.fator > 0;

  const columns: ColumnDef<Conversao>[] = [
    {
      id: "origem",
      header: "Origem",
      accessorKey: "unidade_origem_id",
      cell: (v) => {
        const u = uomMap[v];
        return u ? (
          <span className="font-mono font-semibold">{u.codigo}</span>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        );
      },
      filterable: true,
    },
    {
      id: "seta",
      header: "",
      accessorKey: "unidade_destino_id",
      cell: () => <ArrowRight className="size-3.5 text-muted-foreground" />,
    },
    {
      id: "destino",
      header: "Destino",
      accessorKey: "unidade_destino_id",
      cell: (v) => {
        const u = uomMap[v];
        return u ? (
          <span className="font-mono font-semibold">{u.codigo}</span>
        ) : (
          <span className="text-muted-foreground text-xs">—</span>
        );
      },
      filterable: true,
    },
    {
      id: "fator",
      header: "Fator",
      accessorKey: "fator",
      cell: (v) => (
        <span className="font-mono text-xs">
          {(v as number).toLocaleString("pt-BR", { maximumSignificantDigits: 8 })}
        </span>
      ),
      sortable: true,
    },
    {
      id: "cultura",
      header: "Cultura",
      accessorKey: "cultura",
      cell: (v) =>
        v ? (
          <span className="text-xs">{v as string}</span>
        ) : (
          <span className="text-[10px] text-muted-foreground italic">qualquer</span>
        ),
      filterable: true,
    },
    {
      id: "actions",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          {canWrite && (
            <>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 text-primary"
                onClick={() => openEdit(row)}
              >
                <Pencil className="size-3.5" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="size-7 text-destructive"
                onClick={() => setConversaoToDelete(row)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Conversões de Unidade</h2>
        {canWrite && (
          <Button variant="outline" size="sm" className="h-8 rounded-sm" onClick={openNew}>
            <Plus className="mr-1.5 size-3.5" />
            Nova Conversão
          </Button>
        )}
      </div>

      <DataTable
        data={conversoes}
        columns={columns}
        isLoading={isLoading}
        searchPlaceholder="Buscar por código ou cultura..."
        emptyMessage="Nenhuma conversão cadastrada"
      />

      <ConfirmDialog
        open={!!conversaoToDelete}
        title="Remover conversão?"
        description={
          conversaoToDelete
            ? `A conversão ${uomMap[conversaoToDelete.unidade_origem_id]?.codigo ?? "?"} → ${uomMap[conversaoToDelete.unidade_destino_id]?.codigo ?? "?"} será removida.`
            : undefined
        }
        confirmText="Remover"
        destructive
        onCancel={() => setConversaoToDelete(null)}
        onConfirm={() => {
          if (!conversaoToDelete) return;
          remove.mutate(conversaoToDelete.id, {
            onSettled: () => setConversaoToDelete(null),
          });
        }}
      />

      <Dialog open={dialog.open} onOpenChange={(o) => !o && setDialog({ open: false })}>
        <DialogContent className="max-w-lg p-0">
          <DialogHeader>
            <div className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                <ArrowRightLeft className="size-4 text-primary" />
              </div>
              <DialogTitle>{dialog.item ? "Editar Conversão" : "Nova Conversão"}</DialogTitle>
            </div>
          </DialogHeader>

          <DialogBody className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Unidade de Origem *</Label>
                <Select
                  value={form.unidade_origem_id ?? ""}
                  onValueChange={(v: string) => set({ unidade_origem_id: v })}
                >
                  <SelectTrigger className="h-8 rounded-sm text-xs">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {uoms.map((u) => (
                      <SelectItem key={u.id} value={u.id} className="text-xs">
                        {u.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Unidade de Destino *</Label>
                <Select
                  value={form.unidade_destino_id ?? ""}
                  onValueChange={(v: string) => set({ unidade_destino_id: v })}
                >
                  <SelectTrigger className="h-8 rounded-sm text-xs">
                    <SelectValue placeholder="Selecione..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {uoms.map((u) => (
                      <SelectItem
                        key={u.id}
                        value={u.id}
                        disabled={u.id === form.unidade_origem_id}
                        className="text-xs"
                      >
                        {u.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {form.unidade_origem_id &&
                  form.unidade_destino_id &&
                  form.unidade_origem_id === form.unidade_destino_id && (
                    <p className="text-[10px] text-destructive">Origem e destino não podem ser iguais</p>
                  )}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Fator de Conversão *</Label>
              <Input
                type="number"
                step="any"
                value={form.fator ?? ""}
                onChange={(e) => set({ fator: e.target.value ? +e.target.value : undefined })}
                placeholder="Ex: 60"
                className="h-8 rounded-sm text-xs"
              />
              {preview && (
                <p className="text-[10px] text-muted-foreground font-mono">{preview}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Cultura (opcional)</Label>
              <Input
                value={form.cultura ?? ""}
                onChange={(e) => set({ cultura: e.target.value || null })}
                placeholder="Ex: soja, milho, cafe — vazio = universal"
                className="h-8 rounded-sm text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Observações (opcional)</Label>
              <Input
                value={form.observacoes ?? ""}
                onChange={(e) => set({ observacoes: e.target.value || null })}
                className="h-8 rounded-sm text-xs"
              />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setDialog({ open: false })}>
              <XCircle className="mr-1.5 size-3.5" />
              Cancelar
            </Button>
            <Button
              size="sm"
              className="rounded-sm"
              onClick={() => save.mutate(form)}
              disabled={!isValid || save.isPending}
            >
              <Save className="mr-1.5 size-3.5" />
              {save.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
