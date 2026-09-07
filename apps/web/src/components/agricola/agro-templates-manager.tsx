"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CulturaCombobox } from "@/components/shared/cultura-combobox";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Plus, Pencil, Trash2, Lock, Globe, Save, ListChecks } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { templateService } from "@/services/agro/template-service";
import type { PhaseTemplate, OperationTemplate } from "@/types/agro/templates";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { PhaseTemplateCreateSchema, OperationTemplateCreateSchema, type PhaseTemplateCreate, type OperationTemplateCreate } from "@farm/zod-schemas";



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

function OrigemBadge({ tenantId }: { tenantId?: string | null }) {
  return tenantId ? (
    <Badge variant="outline" className="gap-1"><Pencil className="size-3" /> Customizado</Badge>
  ) : (
    <Badge variant="secondary" className="gap-1"><Globe className="size-3" /> Global</Badge>
  );
}

export function AgroTemplatesManager() {
  const qc = useQueryClient();
  const router = useRouter();

  // --- Phase templates state ---
  const [phaseDialog, setPhaseDialog] = useState<{ open: boolean; item?: PhaseTemplate }>({ open: false });
  const [phaseDeleteId, setPhaseDeleteId] = useState<string | null>(null);

  const phaseForm = useForm<PhaseTemplateCreate>({
    resolver: zodResolver(PhaseTemplateCreateSchema) as unknown as Resolver<PhaseTemplateCreate>,
    defaultValues: { cultura: "", fase: "PLANEJAMENTO", titulo: "", descricao: "", ativo: true },
  });

  const [showSystemPhase, setShowSystemPhase] = useState(true);

  const { data: phaseTemplates = [], isLoading: loadingPhase } = useQuery<PhaseTemplate[]>({
    queryKey: ["agro-templates-phase"],
    queryFn: () => templateService.listPhaseTemplates(),
  });

  const visiblePhaseTemplates = showSystemPhase ? phaseTemplates : phaseTemplates.filter((t) => t.tenant_id);

  const savePhase = useMutation({
    mutationFn: (payload: PhaseTemplateCreate) =>
      phaseDialog.item
        ? templateService.updatePhaseTemplate(phaseDialog.item.id, {
            ...payload,
            cultura: payload.cultura || null,
            descricao: payload.descricao || null,
          })
        : templateService.createPhaseTemplate({
            ...payload,
            cultura: payload.cultura || null,
            descricao: payload.descricao || null,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-templates-phase"] });
      toast.success(phaseDialog.item ? "Template de fase atualizado." : "Template de fase criado.");
      setPhaseDialog({ open: false });
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível salvar o template."),
  });

  const deletePhase = useMutation({
    mutationFn: (id: string) => templateService.deletePhaseTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-templates-phase"] });
      toast.success("Template de fase excluído.");
      setPhaseDeleteId(null);
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível excluir o template."),
  });

  function openPhaseDialog(item?: PhaseTemplate) {
    if (item) {
      phaseForm.reset({ cultura: item.cultura || "", fase: item.fase as PhaseTemplateCreate["fase"], titulo: item.titulo, descricao: item.descricao || "", ativo: item.ativo });
    } else {
      phaseForm.reset({ cultura: "", fase: "PLANEJAMENTO", titulo: "", descricao: "", ativo: true });
    }
    setPhaseDialog({ open: true, item });
  }

  const phaseColumns: ColumnDef<PhaseTemplate>[] = [
    { id: "titulo", header: "Título", accessorKey: "titulo", sortable: true, filterable: true },
    { id: "fase", header: "Fase", accessorKey: "fase", sortable: true, filterable: true, cell: (v) => typeof v === "string" ? (FASE_DESCRIPTIONS[v] || v) : "—" },
    { id: "cultura", header: "Cultura", accessorKey: "cultura", cell: (v) => v || "—" },
    { id: "origem", header: "Origem", cell: (_, row) => <OrigemBadge tenantId={row.tenant_id} /> },
    { id: "ativo", header: "Ativo", cell: (v) => (v ? <Badge>Ativo</Badge> : <Badge variant="outline">Inativo</Badge>), accessorKey: "ativo" },
    {
      id: "acoes",
      header: "",
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Gerenciar itens" asChild>
            <Link href={`/agricola/templates/${row.id}?type=phase`} onClick={(e) => e.stopPropagation()}>
              <ListChecks className="size-3.5" />
            </Link>
          </Button>
          {row.tenant_id ? (
            <>
              <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Editar" onClick={(e) => { e.stopPropagation(); openPhaseDialog(row); }}>
                <Pencil className="size-3.5" />
              </Button>
              <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label="Excluir" onClick={(e) => { e.stopPropagation(); setPhaseDeleteId(row.id); }}>
                <Trash2 className="size-3.5" />
              </Button>
            </>
          ) : (
            <Button size="icon" variant="ghost" className="size-7 text-muted-foreground" aria-label="Template global — somente leitura" disabled>
              <Lock className="size-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  // --- Operation templates state ---
  const [opDialog, setOpDialog] = useState<{ open: boolean; item?: OperationTemplate }>({ open: false });
  const [opDeleteId, setOpDeleteId] = useState<string | null>(null);

  const opForm = useForm<OperationTemplateCreate>({
    resolver: zodResolver(OperationTemplateCreateSchema) as unknown as Resolver<OperationTemplateCreate>,
    defaultValues: { cultura: "", fase: null, titulo: "", descricao: "", ativo: true },
  });

  const [showSystemOp, setShowSystemOp] = useState(true);

  const { data: operationTemplates = [], isLoading: loadingOp } = useQuery<OperationTemplate[]>({
    queryKey: ["agro-templates-operations"],
    queryFn: () => templateService.listOperationTemplates(),
  });

  const visibleOperationTemplates = showSystemOp ? operationTemplates : operationTemplates.filter((t) => t.tenant_id);

  const saveOp = useMutation({
    mutationFn: (payload: OperationTemplateCreate) =>
      opDialog.item
        ? templateService.updateOperationTemplate(opDialog.item.id, {
            ...payload,
            cultura: payload.cultura || null,
            fase: payload.fase || null,
            descricao: payload.descricao || null,
          })
        : templateService.createOperationTemplate({
            ...payload,
            cultura: payload.cultura || null,
            fase: payload.fase || null,
            descricao: payload.descricao || null,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-templates-operations"] });
      toast.success(opDialog.item ? "Template de operação atualizado." : "Template de operação criado.");
      setOpDialog({ open: false });
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível salvar o template."),
  });

  const deleteOp = useMutation({
    mutationFn: (id: string) => templateService.deleteOperationTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agro-templates-operations"] });
      toast.success("Template de operação excluído.");
      setOpDeleteId(null);
    },
    onError: (err: any) => toast.error(err?.message || "Não foi possível excluir o template."),
  });

  function openOpDialog(item?: OperationTemplate) {
    if (item) {
      opForm.reset({ cultura: item.cultura || "", fase: (item.fase as OperationTemplateCreate["fase"]) || null, titulo: item.titulo, descricao: item.descricao || "", ativo: item.ativo });
    } else {
      opForm.reset({ cultura: "", fase: null, titulo: "", descricao: "", ativo: true });
    }
    setOpDialog({ open: true, item });
  }

  const opColumns: ColumnDef<OperationTemplate>[] = [
    { id: "titulo", header: "Título", accessorKey: "titulo", sortable: true, filterable: true },
    { id: "fase", header: "Fase", accessorKey: "fase", cell: (v) => typeof v === "string" ? (FASE_DESCRIPTIONS[v] || v) : "—" },
    { id: "cultura", header: "Cultura", accessorKey: "cultura", cell: (v) => v || "—" },
    { id: "origem", header: "Origem", cell: (_, row) => <OrigemBadge tenantId={row.tenant_id} /> },
    { id: "ativo", header: "Ativo", cell: (v) => (v ? <Badge>Ativo</Badge> : <Badge variant="outline">Inativo</Badge>), accessorKey: "ativo" },
    {
      id: "acoes",
      header: "",
      exportable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Gerenciar itens" asChild>
            <Link href={`/agricola/templates/${row.id}?type=operations`} onClick={(e) => e.stopPropagation()}>
              <ListChecks className="size-3.5" />
            </Link>
          </Button>
          {row.tenant_id ? (
            <>
              <Button size="icon" variant="ghost" className="size-7 text-primary hover:text-primary" aria-label="Editar" onClick={(e) => { e.stopPropagation(); openOpDialog(row); }}>
                <Pencil className="size-3.5" />
              </Button>
              <Button size="icon" variant="ghost" className="size-7 text-destructive hover:text-destructive" aria-label="Excluir" onClick={(e) => { e.stopPropagation(); setOpDeleteId(row.id); }}>
                <Trash2 className="size-3.5" />
              </Button>
            </>
          ) : (
            <Button size="icon" variant="ghost" className="size-7 text-muted-foreground" aria-label="Template global — somente leitura" disabled>
              <Lock className="size-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <Tabs defaultValue="fase" className="space-y-4">
      <TabsList>
        <TabsTrigger value="fase">Templates de Fase</TabsTrigger>
        <TabsTrigger value="operacao">Templates de Operação</TabsTrigger>
      </TabsList>

      <TabsContent value="fase" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Switch checked={showSystemPhase} onCheckedChange={setShowSystemPhase} id="show-system-phase" />
            <Label htmlFor="show-system-phase" className="text-sm font-normal text-muted-foreground">
              Mostrar templates do sistema
            </Label>
          </div>
          <Button size="sm" onClick={() => openPhaseDialog()}>
            <Plus className="size-4 mr-1" /> Novo Template de Fase
          </Button>
        </div>
        <DataTable
          data={visiblePhaseTemplates}
          columns={phaseColumns}
          isLoading={loadingPhase}
          searchable
          searchPlaceholder="Buscar template de fase..."
          emptyMessage="Nenhum template de fase encontrado."
          onRowClick={(row) => router.push(`/agricola/templates/${row.id}?type=phase`)}
        />
      </TabsContent>

      <TabsContent value="operacao" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Switch checked={showSystemOp} onCheckedChange={setShowSystemOp} id="show-system-op" />
            <Label htmlFor="show-system-op" className="text-sm font-normal text-muted-foreground">
              Mostrar templates do sistema
            </Label>
          </div>
          <Button size="sm" onClick={() => openOpDialog()}>
            <Plus className="size-4 mr-1" /> Novo Template de Operação
          </Button>
        </div>
        <DataTable
          data={visibleOperationTemplates}
          columns={opColumns}
          isLoading={loadingOp}
          searchable
          searchPlaceholder="Buscar template de operação..."
          emptyMessage="Nenhum template de operação encontrado."
          onRowClick={(row) => router.push(`/agricola/templates/${row.id}?type=operations`)}
        />
      </TabsContent>

      {/* Dialog: Phase Template */}
      <Dialog open={phaseDialog.open} onOpenChange={(open) => !open && setPhaseDialog({ open: false })}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>{phaseDialog.item ? "Editar Template de Fase" : "Novo Template de Fase"}</DialogTitle>
          </DialogHeader>
          <Form {...phaseForm}>
            <form onSubmit={phaseForm.handleSubmit((data) => savePhase.mutate(data))}>
              <DialogBody className="space-y-4">
                <FormField control={phaseForm.control} name="titulo" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Título *</FormLabel>
                    <FormControl><Input {...field} placeholder="Ex: Checklist de Plantio" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={phaseForm.control} name="fase" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fase *</FormLabel>
                    <FormControl>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger className="h-9 rounded-sm text-xs"><SelectValue placeholder="Selecione a fase" /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(FASE_DESCRIPTIONS).map(([valor, label]) => (
                            <SelectItem key={valor} value={valor}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={phaseForm.control} name="cultura" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cultura (opcional)</FormLabel>
                    <FormControl><CulturaCombobox value={field.value || ""} onChange={field.onChange} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={phaseForm.control} name="descricao" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição</FormLabel>
                    <FormControl><Textarea {...field} value={field.value || ""} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={phaseForm.control} name="ativo" render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
                    <FormLabel className="m-0 cursor-pointer">Ativo</FormLabel>
                  </FormItem>
                )} />
              </DialogBody>
              <DialogFooter>
                <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setPhaseDialog({ open: false })}>Cancelar</Button>
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  className="rounded-sm border-primary text-primary hover:bg-primary/5"
                  disabled={savePhase.isPending}
                >
                  <Save className="size-3.5 mr-1.5" />
                  Salvar
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Dialog: Operation Template */}
      <Dialog open={opDialog.open} onOpenChange={(open) => !open && setOpDialog({ open: false })}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>{opDialog.item ? "Editar Template de Operação" : "Novo Template de Operação"}</DialogTitle>
          </DialogHeader>
          <Form {...opForm}>
            <form onSubmit={opForm.handleSubmit((data) => saveOp.mutate(data))}>
              <DialogBody className="space-y-4">
                <FormField control={opForm.control} name="titulo" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Título *</FormLabel>
                    <FormControl><Input {...field} placeholder="Ex: Plano de Ação — Pulverização" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={opForm.control} name="fase" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fase (opcional)</FormLabel>
                    <FormControl>
                      <Select value={field.value || ""} onValueChange={field.onChange}>
                        <SelectTrigger className="h-9 rounded-sm text-xs"><SelectValue placeholder="Todas as fases" /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(FASE_DESCRIPTIONS).map(([valor, label]) => (
                            <SelectItem key={valor} value={valor}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={opForm.control} name="cultura" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cultura (opcional)</FormLabel>
                    <FormControl><CulturaCombobox value={field.value || ""} onChange={field.onChange} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={opForm.control} name="descricao" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição</FormLabel>
                    <FormControl><Textarea {...field} value={field.value || ""} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={opForm.control} name="ativo" render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl><Switch checked={field.value} onCheckedChange={field.onChange} /></FormControl>
                    <FormLabel className="m-0 cursor-pointer">Ativo</FormLabel>
                  </FormItem>
                )} />
                {opDialog.item && (
                  <p className="text-xs text-muted-foreground">
                    Os itens (operações e doses sugeridas) deste template podem ser gerenciados na tela de detalhe do template.
                  </p>
                )}
              </DialogBody>
              <DialogFooter>
                <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setOpDialog({ open: false })}>Cancelar</Button>
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  className="rounded-sm border-primary text-primary hover:bg-primary/5"
                  disabled={saveOp.isPending}
                >
                  <Save className="size-3.5 mr-1.5" />
                  Salvar
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!phaseDeleteId}
        title="Excluir template de fase"
        description="Esta ação não pode ser desfeita. O template deixará de estar disponível para novas safras."
        destructive
        confirmText="Excluir"
        onConfirm={() => phaseDeleteId && deletePhase.mutate(phaseDeleteId)}
        onCancel={() => setPhaseDeleteId(null)}
      />

      <ConfirmDialog
        open={!!opDeleteId}
        title="Excluir template de operação"
        description="Esta ação não pode ser desfeita. O template deixará de estar disponível para novas safras."
        destructive
        confirmText="Excluir"
        onConfirm={() => opDeleteId && deleteOp.mutate(opDeleteId)}
        onCancel={() => setOpDeleteId(null)}
      />
    </Tabs>
  );
}
