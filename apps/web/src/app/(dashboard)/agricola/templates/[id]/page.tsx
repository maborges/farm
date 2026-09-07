"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Pencil, Trash2, Lock, Globe, Settings, ClipboardList, ListTodo, LayoutTemplate } from "lucide-react";
import {
  templateService,
  type OperationTemplateItemPayload,
  type PhaseTemplateChecklistItemPayload,
  type PhaseTemplateTaskPayload,
} from "@/services/agro/template-service";
import { UnidadeMedidaCombobox } from "@/components/shared/unidade-medida-combobox";
import { ProdutoCombobox } from "@/components/shared/produto-combobox";
import type {
  PhaseTemplateDetail, OperationTemplateDetail, OperationTemplateItem,
  PhaseTemplateChecklistItem, PhaseTemplateTask,
} from "@/types/agro/templates";

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

const TIPO_ITEM_LABELS: Record<string, string> = {
  SEMENTE: "Semente",
  FERTILIZANTE: "Fertilizante",
  DEFENSIVO: "Defensivo",
  MATERIAL: "Material",
  MAQUINARIO: "Maquinário",
  COMBUSTIVEL: "Combustível",
  MAO_DE_OBRA: "Mão de obra",
  SERVICO: "Serviço",
  OUTROS: "Outros",
};
const TIPO_ITEM_OPTIONS = Object.keys(TIPO_ITEM_LABELS);

type ItemFormState = {
  tipo: string;
  titulo: string;
  descricao: string;
  dose_sugerida: string;
  unidade: string;
  unidade_medida_id: string | null;
  can_generate_task: boolean;
};

const EMPTY_ITEM: ItemFormState = { tipo: "OUTROS", titulo: "", descricao: "", dose_sugerida: "", unidade: "", unidade_medida_id: null, can_generate_task: true };

type ChecklistFormState = {
  titulo: string; descricao: string; obrigatorio: boolean; ordem: string;
  tipo_resultado: "TAREFA_CAMPO" | "SOLICITACAO_ESTOQUE" | "MANUAL";
  produto_id_padrao: string; quantidade_minima: string;
};
const EMPTY_CHECKLIST_ITEM: ChecklistFormState = {
  titulo: "", descricao: "", obrigatorio: false, ordem: "0",
  tipo_resultado: "MANUAL", produto_id_padrao: "", quantidade_minima: "",
};
const TIPO_RESULTADO_LABEL: Record<ChecklistFormState["tipo_resultado"], string> = {
  TAREFA_CAMPO: "Gera OS (tarefa de campo)",
  SOLICITACAO_ESTOQUE: "Verifica estoque (reserva/compra)",
  MANUAL: "Manual (só checkbox)",
};

type TaskFormState = { tipo: string; titulo: string; descricao: string; criticidade: string; ordem: string };
const EMPTY_TASK: TaskFormState = { tipo: "COLHEITA", titulo: "", descricao: "", criticidade: "NORMAL", ordem: "0" };
const CRITICIDADE_OPTIONS = ["CRITICA", "NORMAL", "OPCIONAL"];

export default function TemplateDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const id = params.id as string;
  const type = (searchParams.get("type") || "operations") as "phase" | "operations";

  const [itemDialog, setItemDialog] = useState<{ open: boolean; item?: OperationTemplateItem }>({ open: false });
  const [itemForm, setItemForm] = useState<ItemFormState>(EMPTY_ITEM);
  const [itemDeleteId, setItemDeleteId] = useState<string | null>(null);

  const [checklistDialog, setChecklistDialog] = useState<{ open: boolean; item?: PhaseTemplateChecklistItem }>({ open: false });
  const [checklistForm, setChecklistForm] = useState<ChecklistFormState>(EMPTY_CHECKLIST_ITEM);
  const [checklistDeleteId, setChecklistDeleteId] = useState<string | null>(null);

  const [taskDialog, setTaskDialog] = useState<{ open: boolean; task?: PhaseTemplateTask }>({ open: false });
  const [taskForm, setTaskForm] = useState<TaskFormState>(EMPTY_TASK);
  const [taskDeleteId, setTaskDeleteId] = useState<string | null>(null);

  const { data: phaseTemplate, isLoading: loadingPhase } = useQuery<PhaseTemplateDetail>({
    queryKey: ["agro-template-detail", id, "phase"],
    queryFn: () => templateService.getPhaseTemplate(id),
    enabled: type === "phase",
  });

  const { data: opTemplate, isLoading: loadingOp } = useQuery<OperationTemplateDetail>({
    queryKey: ["agro-template-detail", id, "operations"],
    queryFn: () => templateService.getOperationTemplate(id),
    enabled: type === "operations",
  });

  const template = type === "phase" ? phaseTemplate : opTemplate;
  const isLoading = type === "phase" ? loadingPhase : loadingOp;
  const isOwn = !!template?.tenant_id;

  const invalidate = () => qc.invalidateQueries({ queryKey: ["agro-template-detail", id, type] });

  const saveItem = useMutation({
    mutationFn: (payload: OperationTemplateItemPayload) =>
      itemDialog.item
        ? templateService.updateOperationTemplateItem(id, itemDialog.item.id, payload)
        : templateService.createOperationTemplateItem(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success(itemDialog.item ? "Item atualizado." : "Item adicionado.");
      setItemDialog({ open: false });
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível salvar o item."),
  });

  const deleteItem = useMutation({
    mutationFn: (itemId: string) => templateService.deleteOperationTemplateItem(id, itemId),
    onSuccess: () => {
      invalidate();
      toast.success("Item excluído.");
      setItemDeleteId(null);
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível excluir o item."),
  });

  function openItemDialog(item?: OperationTemplateItem) {
    setItemForm(
      item
        ? {
            tipo: item.tipo,
            titulo: item.titulo,
            descricao: item.descricao || "",
            dose_sugerida: item.dose_sugerida != null ? String(item.dose_sugerida) : "",
            unidade: item.unidade || "",
            unidade_medida_id: item.unidade_medida_id ?? null,
            can_generate_task: item.can_generate_task,
          }
        : EMPTY_ITEM
    );
    setItemDialog({ open: true, item });
  }

  const saveChecklistItem = useMutation({
    mutationFn: (payload: PhaseTemplateChecklistItemPayload) =>
      checklistDialog.item
        ? templateService.updatePhaseChecklistItem(id, checklistDialog.item.id, payload)
        : templateService.createPhaseChecklistItem(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success(checklistDialog.item ? "Item atualizado." : "Item adicionado.");
      setChecklistDialog({ open: false });
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível salvar o item."),
  });

  const deleteChecklistItem = useMutation({
    mutationFn: (itemId: string) => templateService.deletePhaseChecklistItem(id, itemId),
    onSuccess: () => {
      invalidate();
      toast.success("Item excluído.");
      setChecklistDeleteId(null);
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível excluir o item."),
  });

  const saveTask = useMutation({
    mutationFn: (payload: PhaseTemplateTaskPayload) =>
      taskDialog.task
        ? templateService.updatePhaseTask(id, taskDialog.task.id, payload)
        : templateService.createPhaseTask(id, payload),
    onSuccess: () => {
      invalidate();
      toast.success(taskDialog.task ? "Tarefa atualizada." : "Tarefa adicionada.");
      setTaskDialog({ open: false });
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível salvar a tarefa."),
  });

  const deleteTask = useMutation({
    mutationFn: (taskId: string) => templateService.deletePhaseTask(id, taskId),
    onSuccess: () => {
      invalidate();
      toast.success("Tarefa excluída.");
      setTaskDeleteId(null);
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível excluir a tarefa."),
  });

  function openChecklistDialog(item?: PhaseTemplateChecklistItem) {
    setChecklistForm(
      item
        ? {
            titulo: item.titulo, descricao: item.descricao || "", obrigatorio: item.obrigatorio, ordem: String(item.ordem),
            tipo_resultado: item.tipo_resultado ?? "MANUAL",
            produto_id_padrao: item.produto_id_padrao || "",
            quantidade_minima: item.quantidade_minima != null ? String(item.quantidade_minima) : "",
          }
        : EMPTY_CHECKLIST_ITEM
    );
    setChecklistDialog({ open: true, item });
  }

  function handleSaveChecklistItem() {
    saveChecklistItem.mutate({
      titulo: checklistForm.titulo,
      descricao: checklistForm.descricao || null,
      obrigatorio: checklistForm.obrigatorio,
      ordem: Number(checklistForm.ordem) || 0,
      tipo_resultado: checklistForm.tipo_resultado,
      produto_id_padrao: checklistForm.tipo_resultado === "SOLICITACAO_ESTOQUE" && checklistForm.produto_id_padrao ? checklistForm.produto_id_padrao : null,
      quantidade_minima: checklistForm.tipo_resultado === "SOLICITACAO_ESTOQUE" && checklistForm.quantidade_minima ? Number(checklistForm.quantidade_minima) : null,
    });
  }

  function openTaskDialog(task?: PhaseTemplateTask) {
    setTaskForm(
      task
        ? { tipo: task.tipo, titulo: task.titulo, descricao: task.descricao || "", criticidade: task.criticidade, ordem: String(task.ordem) }
        : EMPTY_TASK
    );
    setTaskDialog({ open: true, task });
  }

  function handleSaveTask() {
    saveTask.mutate({
      tipo: taskForm.tipo,
      titulo: taskForm.titulo,
      descricao: taskForm.descricao || null,
      criticidade: taskForm.criticidade,
      ordem: Number(taskForm.ordem) || 0,
    });
  }

  function handleSaveItem() {
    saveItem.mutate({
      tipo: itemForm.tipo,
      titulo: itemForm.titulo,
      descricao: itemForm.descricao || null,
      dose_sugerida: itemForm.dose_sugerida ? Number(itemForm.dose_sugerida) : null,
      unidade: itemForm.unidade || null,
      unidade_medida_id: itemForm.unidade_medida_id,
      can_generate_task: itemForm.can_generate_task,
    });
  }

  const itemColumns: ColumnDef<OperationTemplateItem>[] = [
    { id: "tipo", header: "Tipo", accessorKey: "tipo", cell: (v) => <Badge variant="outline">{TIPO_ITEM_LABELS[v as string] ?? v}</Badge> },
    { id: "titulo", header: "Título", accessorKey: "titulo", sortable: true, filterable: true },
    { id: "dose_sugerida", header: "Dose sugerida", cell: (_, row) => (row.dose_sugerida != null ? `${row.dose_sugerida} ${row.unidade || ""}` : "—") },
    { id: "can_generate_task", header: "Gera tarefa", cell: (v) => (v ? <Badge>Sim</Badge> : <Badge variant="outline">Não</Badge>), accessorKey: "can_generate_task" },
    {
      id: "acoes",
      header: "",
      exportable: false,
      cell: (_, row) =>
        isOwn ? (
          <div className="flex items-center gap-0 justify-end">
            <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Editar" onClick={() => openItemDialog(row)}>
              <Pencil className="size-3.5" />
            </Button>
            <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label="Excluir" onClick={() => setItemDeleteId(row.id)}>
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        ) : (
          <div className="flex justify-end">
            <Lock className="size-3.5 text-muted-foreground" aria-label="Template global — somente leitura" />
          </div>
        ),
    },
  ];

  if (isLoading) {
    return (
      <div className="p-6 space-y-6 max-w-5xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px] w-full rounded-sm" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="p-6 max-w-5xl">
        <EmptyState
          icon={<LayoutTemplate />}
          title="Template não encontrado"
          description="O template pode ter sido excluído ou o link está incorreto."
          action={{ label: "Voltar para Templates", href: "/agricola/templates" }}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <PageHeader
        title={template.titulo}
        description={template.descricao || undefined}
        icon={<LayoutTemplate className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Agricultura", href: "/agricola" },
          { label: "Templates", href: "/agricola/templates" },
          { label: template.titulo },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={template.ativo ? "ativo" : "inativo"} />
            {isOwn ? (
              <Badge variant="outline" className="gap-1"><Pencil className="size-3" /> Customizado</Badge>
            ) : (
              <Badge variant="secondary" className="gap-1"><Globe className="size-3" /> Global</Badge>
            )}
            {template.fase && <Badge variant="secondary">{FASE_DESCRIPTIONS[template.fase] || template.fase}</Badge>}
            {type === "operations" && isOwn && (
              <Button size="sm" onClick={() => openItemDialog()}>
                <Plus className="size-4 mr-1" /> Novo Item
              </Button>
            )}
          </div>
        }
      />

      {type === "operations" ? (
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 space-y-0">
            <Settings className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm font-semibold">Itens da Operação</CardTitle>
          </CardHeader>
          <CardContent>
            {opTemplate?.items?.length ? (
              <DataTable
                data={opTemplate.items}
                columns={itemColumns}
                searchable
                searchPlaceholder="Buscar item..."
                emptyMessage="Nenhum item encontrado."
              />
            ) : (
              <EmptyState
                icon={<Settings />}
                title="Nenhum item cadastrado"
                description={
                  isOwn
                    ? "Adicione os insumos, mão de obra e recursos que esta operação consome por hectare."
                    : "Este template global ainda não tem itens configurados."
                }
                action={isOwn ? { label: "Novo Item", onClick: () => openItemDialog() } : undefined}
              />
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
              <div className="flex items-center gap-2">
                <ClipboardList className="size-4 text-muted-foreground" />
                <CardTitle className="text-sm font-semibold">Checklist</CardTitle>
              </div>
              {isOwn && (
                <Button size="sm" variant="outline" onClick={() => openChecklistDialog()}>
                  <Plus className="size-4 mr-1" /> Novo Item
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <DataTable
                data={[...(phaseTemplate?.checklist_items || [])].sort((a, b) => a.ordem - b.ordem)}
                columns={[
                  { id: "ordem", header: "Ordem", accessorKey: "ordem", cell: (v) => <Badge variant="outline">{v as number}</Badge> },
                  { id: "titulo", header: "Título", accessorKey: "titulo" },
                  { id: "obrigatorio", header: "Obrigatório", cell: (v) => (v ? <Badge>Sim</Badge> : <Badge variant="outline">Não</Badge>), accessorKey: "obrigatorio" },
                  {
                    id: "acoes",
                    header: "",
                    exportable: false,
                    cell: (_, row) =>
                      isOwn ? (
                        <div className="flex items-center gap-0 justify-end">
                          <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Editar" onClick={() => openChecklistDialog(row)}>
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label="Excluir" onClick={() => setChecklistDeleteId(row.id)}>
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex justify-end">
                          <Lock className="size-3.5 text-muted-foreground" aria-label="Template global — somente leitura" />
                        </div>
                      ),
                  },
                ]}
                emptyMessage="Nenhum item de checklist configurado."
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
              <div className="flex items-center gap-2">
                <ListTodo className="size-4 text-muted-foreground" />
                <CardTitle className="text-sm font-semibold">Tarefas Padrão</CardTitle>
              </div>
              {isOwn && (
                <Button size="sm" variant="outline" onClick={() => openTaskDialog()}>
                  <Plus className="size-4 mr-1" /> Nova Tarefa
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <DataTable
                data={[...(phaseTemplate?.tasks || [])].sort((a, b) => a.ordem - b.ordem)}
                columns={[
                  { id: "ordem", header: "Ordem", accessorKey: "ordem", cell: (v) => <Badge variant="outline">{v as number}</Badge> },
                  { id: "titulo", header: "Título", accessorKey: "titulo" },
                  { id: "criticidade", header: "Criticidade", accessorKey: "criticidade" },
                  {
                    id: "acoes",
                    header: "",
                    exportable: false,
                    cell: (_, row) =>
                      isOwn ? (
                        <div className="flex items-center gap-0 justify-end">
                          <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Editar" onClick={() => openTaskDialog(row)}>
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label="Excluir" onClick={() => setTaskDeleteId(row.id)}>
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex justify-end">
                          <Lock className="size-3.5 text-muted-foreground" aria-label="Template global — somente leitura" />
                        </div>
                      ),
                  },
                ]}
                emptyMessage="Nenhuma tarefa padrão configurada."
              />
            </CardContent>
          </Card>
          {!isOwn && (
            <p className="text-xs text-muted-foreground text-pretty">
              Este é um template global do sistema — duplique-o para poder editar checklist e tarefas padrão.
            </p>
          )}
        </div>
      )}

      <Dialog open={itemDialog.open} onOpenChange={(open) => !open && setItemDialog({ open: false })}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>{itemDialog.item ? "Editar Item" : "Novo Item"}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Título *</Label>
              <Input value={itemForm.titulo} onChange={(e) => setItemForm((f) => ({ ...f, titulo: e.target.value }))} placeholder="Ex: Ureia em cobertura" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Tipo *</Label>
              <Select value={itemForm.tipo} onValueChange={(v) => setItemForm((f) => ({ ...f, tipo: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o tipo" />
                </SelectTrigger>
                <SelectContent>
                  {TIPO_ITEM_OPTIONS.map((t) => (
                    <SelectItem key={t} value={t}>{TIPO_ITEM_LABELS[t]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Dose sugerida (por ha)</Label>
              <Input type="number" step="0.01" value={itemForm.dose_sugerida} onChange={(e) => setItemForm((f) => ({ ...f, dose_sugerida: e.target.value }))} placeholder="Ex: 2,5" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Unidade</Label>
              <UnidadeMedidaCombobox
                value={itemForm.unidade_medida_id}
                fallbackLabel={itemForm.unidade || undefined}
                onChange={(unidadeId, unidade) =>
                  setItemForm((f) => ({ ...f, unidade_medida_id: unidadeId, unidade: unidade?.codigo || f.unidade }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Descrição</Label>
              <Textarea value={itemForm.descricao} onChange={(e) => setItemForm((f) => ({ ...f, descricao: e.target.value }))} rows={2} className="resize-none text-sm" />
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={itemForm.can_generate_task} onCheckedChange={(v) => setItemForm((f) => ({ ...f, can_generate_task: v }))} />
              <Label className="text-xs font-medium text-muted-foreground">Gera necessidade de tarefa ao aplicar</Label>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setItemDialog({ open: false })}>Cancelar</Button>
            <Button size="sm" disabled={!itemForm.titulo || !itemForm.tipo || saveItem.isPending} onClick={handleSaveItem}>
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!itemDeleteId}
        title="Excluir item"
        description="Esta ação não pode ser desfeita."
        destructive
        confirmText="Excluir"
        onConfirm={() => itemDeleteId && deleteItem.mutate(itemDeleteId)}
        onCancel={() => setItemDeleteId(null)}
      />

      <Dialog open={checklistDialog.open} onOpenChange={(open) => !open && setChecklistDialog({ open: false })}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>{checklistDialog.item ? "Editar Item de Checklist" : "Novo Item de Checklist"}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Título *</Label>
              <Input value={checklistForm.titulo} onChange={(e) => setChecklistForm((f) => ({ ...f, titulo: e.target.value }))} placeholder="Ex: Verificar maturação dos frutos" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Ordem *</Label>
              <Input type="number" value={checklistForm.ordem} onChange={(e) => setChecklistForm((f) => ({ ...f, ordem: e.target.value }))} placeholder="Ex: 1" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Descrição</Label>
              <Textarea value={checklistForm.descricao} onChange={(e) => setChecklistForm((f) => ({ ...f, descricao: e.target.value }))} rows={2} className="resize-none text-sm" />
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={checklistForm.obrigatorio} onCheckedChange={(v) => setChecklistForm((f) => ({ ...f, obrigatorio: v }))} />
              <Label className="text-xs font-medium text-muted-foreground">Obrigatório</Label>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">O que este item gera ao entrar na fase?</Label>
              <Select
                value={checklistForm.tipo_resultado}
                onValueChange={(v) => setChecklistForm((f) => ({ ...f, tipo_resultado: v as ChecklistFormState["tipo_resultado"] }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(Object.keys(TIPO_RESULTADO_LABEL) as ChecklistFormState["tipo_resultado"][]).map((v) => (
                    <SelectItem key={v} value={v}>{TIPO_RESULTADO_LABEL[v]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {checklistForm.tipo_resultado === "SOLICITACAO_ESTOQUE" && (
              <>
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium text-muted-foreground">Produto a verificar</Label>
                  <ProdutoCombobox
                    value={checklistForm.produto_id_padrao}
                    onChange={(produtoId) => setChecklistForm((f) => ({ ...f, produto_id_padrao: produtoId }))}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium text-muted-foreground">Quantidade mínima exigida</Label>
                  <Input
                    type="number"
                    value={checklistForm.quantidade_minima}
                    onChange={(e) => setChecklistForm((f) => ({ ...f, quantidade_minima: e.target.value }))}
                    placeholder="Ex: 10"
                  />
                </div>
              </>
            )}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setChecklistDialog({ open: false })}>Cancelar</Button>
            <Button size="sm" disabled={!checklistForm.titulo || saveChecklistItem.isPending} onClick={handleSaveChecklistItem}>
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!checklistDeleteId}
        title="Excluir item de checklist"
        description="Esta ação não pode ser desfeita."
        destructive
        confirmText="Excluir"
        onConfirm={() => checklistDeleteId && deleteChecklistItem.mutate(checklistDeleteId)}
        onCancel={() => setChecklistDeleteId(null)}
      />

      <Dialog open={taskDialog.open} onOpenChange={(open) => !open && setTaskDialog({ open: false })}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>{taskDialog.task ? "Editar Tarefa Padrão" : "Nova Tarefa Padrão"}</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Título *</Label>
              <Input value={taskForm.titulo} onChange={(e) => setTaskForm((f) => ({ ...f, titulo: e.target.value }))} placeholder="Ex: Colher cachos maduros por talhão" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Ordem *</Label>
              <Input type="number" value={taskForm.ordem} onChange={(e) => setTaskForm((f) => ({ ...f, ordem: e.target.value }))} placeholder="Ex: 1" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Criticidade *</Label>
              <Select value={taskForm.criticidade} onValueChange={(v) => setTaskForm((f) => ({ ...f, criticidade: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a criticidade" />
                </SelectTrigger>
                <SelectContent>
                  {CRITICIDADE_OPTIONS.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Descrição</Label>
              <Textarea value={taskForm.descricao} onChange={(e) => setTaskForm((f) => ({ ...f, descricao: e.target.value }))} rows={2} className="resize-none text-sm" />
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setTaskDialog({ open: false })}>Cancelar</Button>
            <Button size="sm" disabled={!taskForm.titulo || saveTask.isPending} onClick={handleSaveTask}>
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!taskDeleteId}
        title="Excluir tarefa padrão"
        description="Esta ação não pode ser desfeita."
        destructive
        confirmText="Excluir"
        onConfirm={() => taskDeleteId && deleteTask.mutate(taskDeleteId)}
        onCancel={() => setTaskDeleteId(null)}
      />
    </div>
  );
}
