"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Plus, Pencil, Trash2, ArrowLeft, ShieldCheck, ClipboardList, Settings2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge } from "@/components/ui/status-badge";

const FASE_DESCRIPTIONS: Record<string, string> = {
  PLANEJAMENTO: "Planejamento",
  PLANEJADA: "Planejada",
  PREPARO_SOLO: "Preparo de Solo",
  PLANTIO: "Plantio",
  DESENVOLVIMENTO: "Desenvolvimento Vegetativo",
  COLHEITA: "Colheita",
  POS_COLHEITA: "Pós-Colheita",
  ENCERRADA: "Encerrada",
};

// --- Types ---
interface PhaseTemplate {
  id: string;
  cultura?: string;
  fase: string;
  titulo: string;
  descricao?: string;
  ativo: boolean;
  is_system_default: boolean;
}

interface OperationTemplate {
  id: string;
  cultura?: string;
  fase?: string;
  titulo: string;
  descricao?: string;
  ativo: boolean;
}

export default function BackofficeAgroTemplatesPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState("phase");
  const [dialog, setDialog] = useState<{ open: boolean; type: "phase" | "ops"; item?: any }>({ open: false, type: "phase" });
  const [form, setForm] = useState<any>({ titulo: "", ativo: true });
  const [templateToDelete, setTemplateToDelete] = useState<{ type: "phase" | "ops"; id: string; titulo: string } | null>(null);

  // --- Queries ---
  const { data: phases = [], isLoading: loadingPhases } = useQuery<PhaseTemplate[]>({
    queryKey: ["bo-agro-templates-phase"],
    queryFn: () => apiFetch("/backoffice/tabelas/agro-templates/phase"),
  });

  const { data: operations = [], isLoading: loadingOps } = useQuery<OperationTemplate[]>({
    queryKey: ["bo-agro-templates-ops"],
    queryFn: () => apiFetch("/backoffice/tabelas/agro-templates/operations"),
  });

  const save = useMutation({
    mutationFn: async (dados: any) => {
      const isEdit = !!dados.id;
      const baseUrl = dialog.type === "phase" ? "/backoffice/tabelas/agro-templates/phase" : "/backoffice/tabelas/agro-templates/operations";
      const path = isEdit ? `${baseUrl}/${dados.id}` : baseUrl;
      return apiFetch(path, {
        method: isEdit ? "PUT" : "POST",
        body: JSON.stringify(dados)
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bo-agro-templates-phase"] });
      qc.invalidateQueries({ queryKey: ["bo-agro-templates-ops"] });
      setDialog({ ...dialog, open: false });
      toast.success(form.id ? "Template atualizado com sucesso!" : "Template criado com sucesso!");
    },
    onError: (e: any) => toast.error(e?.message || "Erro ao salvar template"),
  });

  const remove = useMutation({
    mutationFn: async ({ id, type }: { id: string; type: "phase" | "ops" }) => {
      const baseUrl = type === "phase" ? "/backoffice/tabelas/agro-templates/phase" : "/backoffice/tabelas/agro-templates/operations";
      return apiFetch(`${baseUrl}/${id}`, { method: "DELETE" });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bo-agro-templates-phase"] });
      qc.invalidateQueries({ queryKey: ["bo-agro-templates-ops"] });
      toast.success("Template removido com sucesso!");
    },
    onError: (e: any) => toast.error(e?.message || "Erro ao remover template"),
  });

  const openNew = (type: "phase" | "ops") => {
    setForm({ titulo: "", ativo: true, cultura: "", fase: type === "phase" ? "PLANEJAMENTO" : "", descricao: "" });
    setDialog({ open: true, type });
  };

  const openEdit = (type: "phase" | "ops", item: any) => {
    setForm({ ...item });
    setDialog({ open: true, type, item });
  };

  const confirmDelete = (type: "phase" | "ops", id: string, titulo: string) => {
    setTemplateToDelete({ type, id, titulo });
  };

  // --- Columns ---
  const phaseColumns: ColumnDef<PhaseTemplate>[] = [
    {
      id: "titulo",
      header: "Título",
      accessorKey: "titulo",
      cell: (v, row) => (
        <div className="flex flex-col">
          <span className="font-medium text-sm">{v}</span>
          {row.is_system_default && (
            <div className="flex items-center gap-1 text-[10px] text-primary font-bold uppercase mt-0.5">
              <ShieldCheck className="size-2.5" /> Sistema
            </div>
          )}
        </div>
      )
    },
    { id: "cultura", header: "Cultura", accessorKey: "cultura", cell: (v) => v ? <Badge variant="outline" className="text-[10px] rounded-sm">{v}</Badge> : <span className="text-muted-foreground text-xs">Todas</span> },
    { id: "fase", header: "Fase", accessorKey: "fase", cell: (v) => <Badge variant="secondary" className="text-[10px] rounded-sm">{FASE_DESCRIPTIONS[v] || v}</Badge> },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativo",
      cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} />
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Link href={`/backoffice/tabelas/agro-templates/${row.id}?type=phase`}>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-muted-foreground hover:text-primary"
              title="Gerenciar Itens e Regras"
            >
              <Settings2 className="size-3.5" />
            </Button>
          </Link>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-muted-foreground hover:text-primary"
            onClick={(e) => { e.stopPropagation(); openEdit("phase", row); }}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.stopPropagation(); confirmDelete("phase", row.id, row.titulo); }}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      )
    }
  ];

  const opColumns: ColumnDef<OperationTemplate>[] = [
    {
      id: "titulo",
      header: "Título",
      accessorKey: "titulo",
      cell: (v) => <span className="font-medium text-sm">{v}</span>
    },
    { id: "cultura", header: "Cultura", accessorKey: "cultura", cell: (v) => v ? <Badge variant="outline" className="text-[10px] rounded-sm">{v}</Badge> : <span className="text-muted-foreground text-xs">Todas</span> },
    { id: "fase", header: "Fase", accessorKey: "fase", cell: (v) => v ? <Badge variant="secondary" className="text-[10px] rounded-sm">{FASE_DESCRIPTIONS[v] || v}</Badge> : "—" },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativo",
      cell: (v) => <StatusBadge status={v ? "ativo" : "inativo"} />
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Link href={`/backoffice/tabelas/agro-templates/${row.id}?type=ops`}>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-muted-foreground hover:text-primary"
              title="Gerenciar Itens Operacionais"
            >
              <Settings2 className="size-3.5" />
            </Button>
          </Link>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-muted-foreground hover:text-primary"
            onClick={(e) => { e.stopPropagation(); openEdit("ops", row); }}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.stopPropagation(); confirmDelete("ops", row.id, row.titulo); }}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/backoffice/tabelas">
            <Button variant="outline" size="sm" className="size-8 rounded-sm">
              <ArrowLeft className="size-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground/90">Templates Agrícolas</h1>
            <p className="text-xs text-muted-foreground">Modelos globais de governança e operação para o ecossistema AgroSaaS</p>
          </div>
        </div>
        <Button size="sm" variant="outline" className="h-8 rounded-sm" onClick={() => openNew(activeTab as any)}>
          <Plus className="size-3.5 mr-1.5" />
          Novo Template
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="phase">
            <ShieldCheck />
            Fases e Governança
          </TabsTrigger>
          <TabsTrigger value="ops">
            <ClipboardList />
            Operações Padrão (OS)
          </TabsTrigger>
        </TabsList>

        <TabsContent value="phase" className="mt-0 space-y-4">
          <div className="rounded-sm border bg-card">
            <DataTable
              data={phases}
              columns={phaseColumns}
              searchPlaceholder="Filtrar fases..."
              emptyMessage="Nenhum template de fase encontrado."
              isLoading={loadingPhases}
            />
          </div>
        </TabsContent>

        <TabsContent value="ops" className="mt-0 space-y-4">
          <div className="rounded-sm border bg-card">
            <DataTable
              data={operations}
              columns={opColumns}
              searchPlaceholder="Filtrar operações..."
              emptyMessage="Nenhum template operacional encontrado."
              isLoading={loadingOps}
            />
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={dialog.open} onOpenChange={(open) => setDialog({ ...dialog, open })}>
        <DialogContent className="max-w-lg rounded-sm">
          <DialogHeader>
            <DialogTitle className="text-lg">
              {dialog.item ? "Editar " : "Novo "}
              {dialog.type === "phase" ? "Template de Governança" : "Template Operacional"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label className="text-xs">Título do Template *</Label>
              <Input
                className="h-8 text-sm rounded-sm"
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                placeholder="Ex: Soja - Alta Tecnologia"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Cultura (Opcional)</Label>
                <Input
                  className="h-8 text-sm uppercase rounded-sm"
                  value={form.cultura}
                  onChange={(e) => setForm({ ...form, cultura: e.target.value.toUpperCase() })}
                  placeholder="SOJA"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Fase {dialog.type === "phase" && "*"}</Label>
                <Select value={form.fase} onValueChange={(v: string) => setForm({ ...form, fase: v })}>
                  <SelectTrigger className="h-8 text-xs rounded-sm">
                    <SelectValue placeholder={FASE_DESCRIPTIONS[form.fase] || "Selecione a fase"} />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {Object.entries(FASE_DESCRIPTIONS).map(([id, label]) => (
                      <SelectItem key={id} value={id} className="text-xs">{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Descrição</Label>
              <Input
                className="h-8 text-sm rounded-sm"
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <Switch checked={form.ativo} onCheckedChange={(v) => setForm({ ...form, ativo: v })} />
              <Label className="text-xs">Template Ativo</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" className="h-8 rounded-sm text-xs" onClick={() => setDialog({ ...dialog, open: false })}>
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 rounded-sm text-xs border-primary text-primary hover:bg-primary/5"
              disabled={!form.titulo || save.isPending}
              onClick={() => save.mutate(form)}
            >
              {save.isPending ? "Salvando..." : (form.id ? "Atualizar" : "Criar Template")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!templateToDelete}
        title="Remover template?"
        description={templateToDelete ? `O template "${templateToDelete.titulo}" será removido permanentemente.` : undefined}
        confirmText="Remover"
        destructive
        onCancel={() => setTemplateToDelete(null)}
        onConfirm={() => {
          if (!templateToDelete) return;
          remove.mutate(
            { id: templateToDelete.id, type: templateToDelete.type },
            { onSettled: () => setTemplateToDelete(null) }
          );
        }}
      />
    </div>
  );
}
