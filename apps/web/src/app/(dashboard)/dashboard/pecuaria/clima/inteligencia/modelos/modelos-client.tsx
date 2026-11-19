"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  fetchModelosZoosanitarios,
  createModeloZoosanitario,
  updateModeloZoosanitario,
  deleteModeloZoosanitario,
  copiarModeloZoosanitario,
  ModeloZoosanitario,
} from "@/lib/pecuaria/clima-api";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Check, Target, Plus, Pencil, Trash2, Copy, AlertTriangle, Eye } from "lucide-react";
import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { PageHeader } from "@/components/shared/page-header";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormMessage,
} from "@/components/ui/form";
import { Card, CardContent } from "@/components/ui/card";

const schema = z.object({
  especie: z.string().min(2, "Espécie obrigatória"),
  tipo_risco: z.string().min(2, "Tipo de risco obrigatório"),
  nivel_critico: z.coerce.number().min(0).max(100),
  nivel_alto: z.coerce.number().min(0).max(100),
  nivel_medio: z.coerce.number().min(0).max(100),
});

const PADROES_ESPECIE: Record<string, { nivel_critico: number; nivel_alto: number; nivel_medio: number }> = {
  "Bovino de Leite": { nivel_critico: 82, nivel_alto: 78, nivel_medio: 72 },
  "Bovino de Corte": { nivel_critico: 84, nivel_alto: 79, nivel_medio: 75 },
  "Ovino": { nivel_critico: 85, nivel_alto: 81, nivel_medio: 78 },
  "Caprino": { nivel_critico: 85, nivel_alto: 81, nivel_medio: 78 },
  "Suíno": { nivel_critico: 78, nivel_alto: 74, nivel_medio: 68 },
  "Aves de Corte": { nivel_critico: 83, nivel_alto: 80, nivel_medio: 76 },
  "Aves de Postura": { nivel_critico: 83, nivel_alto: 80, nivel_medio: 76 },
  "Bubalino": { nivel_critico: 85, nivel_alto: 80, nivel_medio: 75 },
  "Asinino": { nivel_critico: 83, nivel_alto: 78, nivel_medio: 72 },
};

type FormData = z.infer<typeof schema>;

export default function ModelosZoosanitariosClient() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingModelo, setEditingModelo] = useState<ModeloZoosanitario | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [incluirModelosSistema, setIncluirModelosSistema] = useState(false);
  const [isViewing, setIsViewing] = useState(false);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      especie: "Bovino de Leite",
      tipo_risco: "Estresse Térmico",
      nivel_critico: 82,
      nivel_alto: 78,
      nivel_medio: 72,
    },
  });

  const { data: modelos = [], isLoading } = useQuery({
    queryKey: ["modelos-zoosanitarios"],
    queryFn: fetchModelosZoosanitarios,
  });

  const saveMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const payload = {
        especie: data.especie,
        tipo_risco: data.tipo_risco,
        regras_risco: {
          nivel_critico: data.nivel_critico,
          nivel_alto: data.nivel_alto,
          nivel_medio: data.nivel_medio,
        }
      };

      if (editingModelo) {
        return updateModeloZoosanitario(editingModelo.id, payload);
      }
      return createModeloZoosanitario(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modelos-zoosanitarios"] });
      setIsModalOpen(false);
      toast({ title: "Sucesso", description: "Modelo salvo com sucesso" });
    },
    onError: () => {
      toast({ title: "Erro", description: "Não foi possível salvar o modelo", variant: "destructive" });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteModeloZoosanitario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["modelos-zoosanitarios"] });
      setDeleteId(null);
      toast({ title: "Sucesso", description: "Modelo excluído" });
    }
  });

  const copyMutation = useMutation({
    mutationFn: copiarModeloZoosanitario,
    onSuccess: (copiedModel) => {
      queryClient.invalidateQueries({ queryKey: ["modelos-zoosanitarios"] });
      openEditModal(copiedModel);
      toast({ title: "Modelo copiado", description: "Você agora pode personalizá-lo para sua fazenda." });
    },
    onError: (error: unknown) => {
      const msg = error instanceof Error ? error.message : "Não foi possível copiar o modelo";
      toast({ title: "Erro ao copiar", description: msg, variant: "destructive" });
    }
  });

  const openNewModal = () => {
    setIsViewing(false);
    setEditingModelo(null);
    form.reset({
      especie: "Bovino de Leite",
      tipo_risco: "Estresse Térmico",
      nivel_critico: 82,
      nivel_alto: 78,
      nivel_medio: 72,
    });
    setIsModalOpen(true);
  };

  const openEditModal = (modelo: ModeloZoosanitario) => {
    if (modelo.is_global) {
      copyMutation.mutate(modelo.id);
      return;
    }
    setIsViewing(false);
    setEditingModelo(modelo);
    form.reset({
      especie: modelo.especie,
      tipo_risco: modelo.tipo_risco,
      nivel_critico: modelo.regras_risco.nivel_critico || 82,
      nivel_alto: modelo.regras_risco.nivel_alto || 78,
      nivel_medio: modelo.regras_risco.nivel_medio || 72,
    });
    setIsModalOpen(true);
  };

  const openViewModal = (modelo: ModeloZoosanitario) => {
    setIsViewing(true);
    setEditingModelo(modelo);
    form.reset({
      especie: modelo.especie,
      tipo_risco: modelo.tipo_risco,
      nivel_critico: modelo.regras_risco.nivel_critico || 82,
      nivel_alto: modelo.regras_risco.nivel_alto || 78,
      nivel_medio: modelo.regras_risco.nivel_medio || 72,
    });
    setIsModalOpen(true);
  };

  const columns: ColumnDef<ModeloZoosanitario>[] = [
    {
      id: "especie",
      accessorKey: "especie",
      header: "Espécie",
    },
    {
      id: "tipo_risco",
      accessorKey: "tipo_risco",
      header: "Tipo de Risco",
    },
    {
      id: "is_global",
      accessorKey: "is_global",
      header: "Origem",
      cell: (value, row) => (
        <Badge variant={row.is_global ? "secondary" : "default"}>
          {row.is_global ? "Padrão do Sistema" : "Personalizado"}
        </Badge>
      ),
    },
    {
      id: "actions",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (value, row) => {
        const modelo = row;
        return (
          <div className="flex items-center gap-0 justify-end">
            {modelo.is_global ? (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openViewModal(modelo)}
                  className="size-7 text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  title="Visualizar Padrão"
                >
                  <Eye className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openEditModal(modelo)}
                  className="size-7 text-primary hover:text-primary hover:bg-primary/10"
                  title="Personalizar (Copiar)"
                >
                  <Copy className="size-4" />
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => openEditModal(modelo)}
                  className="size-7 text-primary hover:text-primary hover:bg-primary/10"
                  title="Editar"
                >
                  <Pencil className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setDeleteId(modelo.id)}
                  className="size-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                  title="Excluir"
                >
                  <Trash2 className="size-4" />
                </Button>
              </>
            )}
          </div>
        );
      },
    }
  ];

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Modelos Zoossanitários"
        description="Parâmetros de predição e gestão de risco (Estresse Térmico, ITH)"
        icon={<Target className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Clima", href: "/dashboard/pecuaria/clima/monitoramento" },
          { label: "Bem-Estar Animal", href: "/dashboard/pecuaria/clima/inteligencia" },
          { label: "Modelos" }
        ]}
        actions={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-sm border border-border bg-muted/20 px-3 py-1.5">
              <Switch
                checked={incluirModelosSistema}
                onCheckedChange={(checked) => setIncluirModelosSistema(checked === true)}
              />
              <div className="flex flex-col leading-none text-left">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Modelos padrão
                </span>
                <span className="text-xs text-foreground">Listar itens do sistema</span>
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={openNewModal} className="rounded-sm">
              <Plus className="size-4 mr-2" />
              Novo Modelo
            </Button>
          </div>
        }
      />

      <Card variant="warning">
        <CardContent className="flex items-start gap-3 px-4 py-3 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-alert-warning-icon" />
          <p className="text-card-description">
            <span className="font-semibold text-card-title">Atenção:</span> somente modelos personalizados são apresentados na inteligência pecuária. Os modelos padrão do sistema são referências e precisam ser copiados e ajustados para a fazenda.
          </p>
        </CardContent>
      </Card>

      <DataTable
        columns={columns}
        data={modelos.filter((m) => incluirModelosSistema ? true : !m.is_global)}
        isLoading={isLoading}
        searchable={true}
      />

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {isViewing ? "Visualizar Modelo Padrão" : editingModelo ? "Editar Modelo Zoossanitário" : "Novo Modelo"}
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Form {...form}>
              <form onSubmit={form.handleSubmit((d) => saveMutation.mutate(d))} className="space-y-6">

                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="especie"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Espécie</FormLabel>
                        <Select
                          onValueChange={(value) => {
                            field.onChange(value);
                            if (!editingModelo && PADROES_ESPECIE[value]) {
                              form.reset({ especie: value, tipo_risco: "Estresse Térmico", ...PADROES_ESPECIE[value] });
                            }
                          }}
                          defaultValue={field.value}
                          disabled={isViewing}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Selecione..." />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="Bovino de Leite">Bovino de Leite</SelectItem>
                            <SelectItem value="Bovino de Corte">Bovino de Corte</SelectItem>
                            <SelectItem value="Ovino">Ovinos</SelectItem>
                            <SelectItem value="Caprino">Caprinos</SelectItem>
                            <SelectItem value="Suíno">Suínos</SelectItem>
                            <SelectItem value="Aves de Corte">Aves de Corte</SelectItem>
                            <SelectItem value="Aves de Postura">Aves de Postura</SelectItem>
                            <SelectItem value="Bubalino">Bubalinos</SelectItem>
                            <SelectItem value="Asinino">Asininos</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="tipo_risco"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tipo de Risco</FormLabel>
                        <FormControl>
                          <Input {...field} placeholder="Ex: Estresse Térmico" disabled={isViewing} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="border rounded-md p-4 space-y-4">
                  <h4 className="font-medium text-sm">Gatilhos do Índice (ITH)</h4>

                  <div className="grid grid-cols-3 gap-4">
                    <FormField
                      control={form.control}
                      name="nivel_critico"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-destructive">Risco Crítico (&gt;=)</FormLabel>
                          <FormControl>
                            <Input type="number" {...field} disabled={isViewing} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="nivel_alto"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-orange-500">Risco Alto (&gt;=)</FormLabel>
                          <FormControl>
                            <Input type="number" {...field} disabled={isViewing} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="nivel_medio"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-yellow-500">Risco Médio (&gt;=)</FormLabel>
                          <FormControl>
                            <Input type="number" {...field} disabled={isViewing} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                <DialogFooter className="mt-8">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                    {isViewing ? "Fechar" : "Cancelar"}
                  </Button>
                  {!isViewing && (
                    <Button type="submit" disabled={saveMutation.isPending} size="sm">
                      {saveMutation.isPending && <span className="animate-spin mr-2">⟳</span>}
                      Salvar
                    </Button>
                  )}
                </DialogFooter>
              </form>
            </Form>
          </DialogBody>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteId}
        onCancel={() => setDeleteId(null)}
        title="Excluir Modelo"
        description="Tem certeza que deseja excluir esta personalização? O sistema voltará a utilizar o modelo padrão global."
        onConfirm={() => {
          if (deleteId) deleteMutation.mutate(deleteId);
        }}
        confirmText="Excluir"
        destructive={true}
      />
    </div>
  );
}
