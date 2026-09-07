"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  fetchBackofficeModelos, 
  createBackofficeModelo, 
  updateBackofficeModelo, 
  deleteBackofficeModelo,
  ModeloFitossanitario,
  fetchCulturas,
} from "@/lib/agricola/clima-api";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Pencil, Trash2, Plus, Target, XCircle, Save, Copy } from "lucide-react";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { PageHeader } from "@/components/shared/page-header";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";
import { Card, CardContent } from "@/components/ui/card";

const condicaoSchema = z.object({
  variavel: z.string().min(1, "Obrigatório"),
  operador: z.enum([">=", "<=", ">", "<", "between"]),
  valor: z.number().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  peso: z.number().min(0.1, "Obrigatório"),
});

const schema = z.object({
  cultura: z.string().min(2, "Cultura obrigatória"),
  doenca: z.string().min(2, "Doença obrigatória"),
  condicoes: z.array(condicaoSchema).min(1, "Adicione pelo menos uma condição"),
  nivel_critico_pct: z.number().min(0).max(100),
  nivel_alto_pct: z.number().min(0).max(100),
  nivel_medio_pct: z.number().min(0).max(100),
});

type FormData = z.infer<typeof schema>;

const VARIAVEIS = [
  { value: "temp_media_c", label: "Temperatura Média (°C)" },
  { value: "temp_max_c", label: "Temperatura Máxima (°C)" },
  { value: "temp_min_c", label: "Temperatura Mínima (°C)" },
  { value: "umidade_rel_pct", label: "Umidade Relativa (%)" },
  { value: "precipitacao_mm", label: "Precipitação (mm)" },
];

const OPERADORES = [
  { value: ">=", label: "Maior ou igual (>=)" },
  { value: "<=", label: "Menor ou igual (<=)" },
  { value: ">", label: "Maior que (>)" },
  { value: "<", label: "Menor que (<)" },
  { value: "between", label: "Entre (min e max)" },
];

export default function ModelosBackofficeClient() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingModelo, setEditingModelo] = useState<ModeloFitossanitario | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      cultura: "",
      doenca: "",
      condicoes: [{ variavel: "temp_media_c", operador: ">=", valor: 20, peso: 1 }],
      nivel_critico_pct: 80,
      nivel_alto_pct: 60,
      nivel_medio_pct: 35,
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "condicoes",
  });

  const { data: modelos = [], isLoading } = useQuery({
    queryKey: ["backoffice-modelos-fitossanitarios"],
    queryFn: fetchBackofficeModelos,
  });

  const { data: culturas = [] } = useQuery({
    queryKey: ["culturas", "backoffice"],
    queryFn: () => fetchCulturas(true),
  });

  const createMutation = useMutation({
    mutationFn: createBackofficeModelo,
    onSuccess: () => {
      toast({ title: "Modelo global criado com sucesso", variant: "default" });
      queryClient.invalidateQueries({ queryKey: ["backoffice-modelos-fitossanitarios"] });
      setIsModalOpen(false);
    },
    onError: () => toast({ title: "Erro ao criar modelo", variant: "destructive" })
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: string, payload: any }) => updateBackofficeModelo(data.id, data.payload),
    onSuccess: () => {
      toast({ title: "Modelo global atualizado com sucesso", variant: "default" });
      queryClient.invalidateQueries({ queryKey: ["backoffice-modelos-fitossanitarios"] });
      setIsModalOpen(false);
    },
    onError: () => toast({ title: "Erro ao atualizar modelo", variant: "destructive" })
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBackofficeModelo,
    onSuccess: () => {
      toast({ title: "Modelo global removido com sucesso", variant: "default" });
      queryClient.invalidateQueries({ queryKey: ["backoffice-modelos-fitossanitarios"] });
    },
    onError: () => toast({ title: "Erro ao remover modelo", variant: "destructive" })
  });

  const handleOpenModal = (modelo?: ModeloFitossanitario) => {
    if (modelo) {
      setEditingModelo(modelo);
      const regras = modelo.regras_risco;
      form.reset({
        cultura: modelo.cultura,
        doenca: modelo.doenca,
        condicoes: regras?.condicoes || [],
        nivel_critico_pct: regras?.nivel_critico_pct ?? 80,
        nivel_alto_pct: regras?.nivel_alto_pct ?? 60,
        nivel_medio_pct: regras?.nivel_medio_pct ?? 35,
      });
    } else {
      setEditingModelo(null);
      form.reset({
        cultura: "",
        doenca: "",
        condicoes: [{ variavel: "umidade_rel_pct", operador: ">=", valor: 85, peso: 2 }],
        nivel_critico_pct: 80,
        nivel_alto_pct: 60,
        nivel_medio_pct: 35,
      });
    }
    setIsModalOpen(true);
  };

  const onSubmit = (data: FormData) => {
    const payload = {
      cultura: data.cultura,
      doenca: data.doenca,
      regras_risco: {
        condicoes: data.condicoes,
        nivel_critico_pct: data.nivel_critico_pct,
        nivel_alto_pct: data.nivel_alto_pct,
        nivel_medio_pct: data.nivel_medio_pct,
      }
    };
    
    if (editingModelo) {
      updateMutation.mutate({ id: editingModelo.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleDelete = (id: string) => {
    setDeleteId(id);
  };

  const columns: ColumnDef<ModeloFitossanitario>[] = [
    {
      id: "cultura",
      header: "Cultura",
      accessorKey: "cultura",
      cell: (value) => <span className="font-medium">{value as string}</span>,
    },
    {
      id: "doenca",
      header: "Doença",
      accessorKey: "doenca",
    },
    {
      id: "condicoes",
      header: "Regras",
      accessorFn: (row) => row.regras_risco?.condicoes?.length || 0,
      cell: (value) => <span className="text-muted-foreground">{value as number} condições</span>,
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button size="icon" variant="ghost" onClick={() => handleOpenModal(row)} className="size-7 text-primary hover:text-primary">
            <Pencil className="size-3.5" />
          </Button>
          <Button size="icon" variant="ghost" onClick={() => handleDelete(row.id)} className="size-7 text-destructive hover:text-destructive">
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Modelos Fitossanitários Globais"
        description="Gestão de modelos base da plataforma SaaS."
        icon={<Target className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Backoffice" }, { label: "Modelos Fitossanitários" }]}
        actions={
          <Button size="sm" variant="outline" onClick={() => handleOpenModal()} className="rounded-sm">
            <Plus className="size-4 mr-2" />
            Novo Modelo Global
          </Button>
        }
      />

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Carregando...</div>
      ) : (
        <DataTable
          data={modelos}
          columns={columns}
          searchPlaceholder="Buscar por cultura ou doença..."
          exportFileName="modelos-fitossanitarios"
          emptyMessage="Nenhum modelo cadastrado"
        />
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-xl p-0">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2.5">
              <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                <Target className="size-4 text-primary" />
              </div>
              {editingModelo ? "Editar Modelo Fitossanitário" : "Novo Modelo Fitossanitário"}
            </DialogTitle>
          </DialogHeader>
          
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
              <DialogBody className="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
                {/* Identificação */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Identificação</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <FormField control={form.control} name="cultura" render={({ field }) => (
                      <div className="space-y-1">
                      <label className="text-xs font-medium">Cultura</label>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue placeholder="Selecione a cultura" />
                        </SelectTrigger>
                        <SelectContent>
                          {culturas.map((c) => (
                            <SelectItem key={c.id} value={c.nome}>
                              {c.nome}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {form.formState.errors.cultura && (
                        <p className="text-xs text-destructive">{form.formState.errors.cultura.message}</p>
                      )}
                    </div>
                    )} />
                    <FormField control={form.control} name="doenca" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Doença</FormLabel>
                        <FormControl><Input {...field} placeholder="Ex: Ferrugem Asiática" className="h-8 rounded-sm text-sm" /></FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />
                  </div>
                </div>

                {/* Limiares de Risco */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Limiares de Alerta (%)</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <FormField control={form.control} name="nivel_critico_pct" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Risco Crítico (≥)</FormLabel>
                        <FormControl><Input type="number" {...field} onChange={e => field.onChange(Number(e.target.value))} className="h-8 rounded-sm text-sm" /></FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />
                    <FormField control={form.control} name="nivel_alto_pct" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Risco Alto (≥)</FormLabel>
                        <FormControl><Input type="number" {...field} onChange={e => field.onChange(Number(e.target.value))} className="h-8 rounded-sm text-sm" /></FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />
                    <FormField control={form.control} name="nivel_medio_pct" render={({ field }) => (
                      <FormItem>
                        <FormLabel>Risco Médio (≥)</FormLabel>
                        <FormControl><Input type="number" {...field} onChange={e => field.onChange(Number(e.target.value))} className="h-8 rounded-sm text-sm" /></FormControl>
                        <FormMessage />
                      </FormItem>
                    )} />
                  </div>
                </div>

                {/* Condições Climáticas */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Condições Climáticas</h4>
                    <Button type="button" variant="outline" size="sm" onClick={() => append({ variavel: "temp_media_c", operador: ">=", valor: 20, peso: 1 })} className="rounded-sm h-7 text-xs">
                      <Plus className="size-3 mr-1" /> Adicionar
                    </Button>
                  </div>
                  
                  <div className="space-y-3">
                    {fields.map((field, index) => {
                      const operador = form.watch(`condicoes.${index}.operador`);
                      const isBetween = operador === "between";
                      return (
                        <Card key={field.id} className="border bg-muted/20 relative shadow-sm">
                          <Button 
                            type="button" 
                            variant="ghost" 
                            size="icon" 
                            onClick={() => remove(index)} 
                            className="absolute top-2 right-2 size-6 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title="Remover Condição"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                          
                          <CardContent className="p-4 pt-5 space-y-3">
                            <div className="grid grid-cols-[3fr_2fr] gap-3">
                              <FormField control={form.control} name={`condicoes.${index}.variavel`} render={({ field: f }) => (
                                <FormItem>
                                  <FormLabel className="text-[10px] uppercase text-muted-foreground">Variável Climática</FormLabel>
                                  <Select onValueChange={f.onChange} defaultValue={f.value}>
                                    <FormControl><SelectTrigger className="h-8 rounded-sm text-xs bg-background"><SelectValue placeholder="Selecione" /></SelectTrigger></FormControl>
                                    <SelectContent>
                                      {VARIAVEIS.map(v => <SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}
                                    </SelectContent>
                                  </Select>
                                </FormItem>
                              )} />
                              
                              <FormField control={form.control} name={`condicoes.${index}.operador`} render={({ field: f }) => (
                                <FormItem>
                                  <FormLabel className="text-[10px] uppercase text-muted-foreground">Operador</FormLabel>
                                  <Select onValueChange={f.onChange} defaultValue={f.value}>
                                    <FormControl><SelectTrigger className="h-8 rounded-sm text-xs bg-background"><SelectValue placeholder="Selecione" /></SelectTrigger></FormControl>
                                    <SelectContent>
                                      {OPERADORES.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                    </SelectContent>
                                  </Select>
                                </FormItem>
                              )} />
                            </div>

                            <div className="grid grid-cols-[3fr_2fr] gap-3">
                              {isBetween ? (
                                <div className="grid grid-cols-2 gap-2">
                                  <FormField control={form.control} name={`condicoes.${index}.min`} render={({ field: f }) => (
                                    <FormItem>
                                      <FormLabel className="text-[10px] uppercase text-muted-foreground">Valor Mínimo</FormLabel>
                                      <FormControl><Input type="number" step="0.1" placeholder="Ex: 15" {...f} onChange={e => f.onChange(e.target.value ? Number(e.target.value) : undefined)} className="h-8 rounded-sm text-xs bg-background" /></FormControl>
                                    </FormItem>
                                  )} />
                                  <FormField control={form.control} name={`condicoes.${index}.max`} render={({ field: f }) => (
                                    <FormItem>
                                      <FormLabel className="text-[10px] uppercase text-muted-foreground">Valor Máximo</FormLabel>
                                      <FormControl><Input type="number" step="0.1" placeholder="Ex: 25" {...f} onChange={e => f.onChange(e.target.value ? Number(e.target.value) : undefined)} className="h-8 rounded-sm text-xs bg-background" /></FormControl>
                                    </FormItem>
                                  )} />
                                </div>
                              ) : (
                                <FormField control={form.control} name={`condicoes.${index}.valor`} render={({ field: f }) => (
                                  <FormItem>
                                    <FormLabel className="text-[10px] uppercase text-muted-foreground">Valor Limite</FormLabel>
                                    <FormControl><Input type="number" step="0.1" placeholder="Valor" {...f} onChange={e => f.onChange(e.target.value ? Number(e.target.value) : undefined)} className="h-8 rounded-sm text-xs bg-background" /></FormControl>
                                  </FormItem>
                                )} />
                              )}

                              <FormField control={form.control} name={`condicoes.${index}.peso`} render={({ field: f }) => (
                                <FormItem>
                                  <FormLabel className="text-[10px] uppercase text-muted-foreground">Peso (Impacto)</FormLabel>
                                  <FormControl><Input type="number" step="0.1" placeholder="Ex: 1 ou 2" {...f} onChange={e => f.onChange(e.target.value ? Number(e.target.value) : undefined)} className="h-8 rounded-sm text-xs bg-background" /></FormControl>
                                </FormItem>
                              )} />
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                    {form.formState.errors.condicoes?.root?.message && (
                      <p className="text-sm font-medium text-destructive">{form.formState.errors.condicoes.root.message}</p>
                    )}
                  </div>
                </div>
              </DialogBody>

              <DialogFooter>
                <Button type="button" variant="outline" size="sm" className="rounded-sm" onClick={() => setIsModalOpen(false)} disabled={createMutation.isPending || updateMutation.isPending}>
                  <XCircle className="size-3.5 mr-1.5" /> Cancelar
                </Button>
                <Button type="submit" variant="outline" size="sm" className="rounded-sm border-primary/50 text-primary hover:bg-primary/5" disabled={createMutation.isPending || updateMutation.isPending}>
                  <Save className="size-3.5 mr-1.5" /> {createMutation.isPending || updateMutation.isPending ? "Salvando..." : "Salvar Modelo"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteId}
        title="Remover Modelo Global"
        description="Tem certeza que deseja remover este modelo fitossanitário global? Isso afetará novos produtores. Ação irreversível."
        destructive
        onCancel={() => setDeleteId(null)}
        onConfirm={() => {
          if (deleteId) {
            deleteMutation.mutate(deleteId);
            setDeleteId(null);
          }
        }}
      />
    </div>
  );
}
