"use client";

import { useEffect } from "react";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface Talhao {
  id: string;
  nome: string;
  codigo: string | null;
  principal: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  safraId: string;
  talhoes: Talhao[];
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

export function VisitaTecnicaForm({ open, onClose, safraId, talhoes, onSubmit, isLoading }: Props) {
  const { register, handleSubmit, control, reset, setValue } = useForm({
    defaultValues: {
      safra_id: safraId,
      nome_rt: "",
      crea: "",
      data_visita: new Date().toISOString().split("T")[0],
      talhao_id: "",
      observacoes: "",
      recomendacoes: "",
      constatacoes: [{ descricao: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "constatacoes",
  });

  useEffect(() => {
    if (open) {
      setValue("safra_id", safraId);
    }
  }, [open, safraId, setValue]);

  const handleClose = () => {
    reset();
    onClose();
  };

  const onFormSubmit = async (data: any) => {
    if (!data.talhao_id) {
      toast.error("Selecione um talhão.");
      return;
    }
    if (data.nome_rt.trim().length < 3) {
      toast.error("Informe o nome do responsável técnico.");
      return;
    }
    await onSubmit(data);
    handleClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-[540px] max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit(onFormSubmit)}>
          <DialogHeader>
            <DialogTitle>Registrar Visita Técnica</DialogTitle>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Talhão <span className="text-destructive">*</span></Label>
                <Controller
                  name="talhao_id"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value || ""}>
                      <SelectTrigger><SelectValue placeholder="Selecionar..." /></SelectTrigger>
                      <SelectContent>
                        {talhoes.length === 0 ? (
                          <SelectItem value="__empty" disabled>Nenhum talhão vinculado</SelectItem>
                        ) : (
                          talhoes.map((t) => (
                            <SelectItem key={t.id} value={t.id}>
                              {t.nome}{t.codigo ? ` (${t.codigo})` : ""}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Data da Visita</Label>
                <Input type="date" {...register("data_visita", { required: true })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Nome do RT <span className="text-destructive">*</span></Label>
                <Input placeholder="Ex: João da Silva" {...register("nome_rt", { required: true, minLength: 3 })} />
              </div>
              <div className="space-y-1.5">
                <Label>CREA <span className="text-destructive">*</span></Label>
                <Input placeholder="Ex: 123456/UF" {...register("crea", { required: true, minLength: 4 })} />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Observações</Label>
              <Textarea rows={3} placeholder="Constatações gerais da visita..." {...register("observacoes")} />
            </div>

            <div className="space-y-1.5">
              <Label>Recomendações</Label>
              <Textarea rows={3} placeholder="Orientações ao produtor..." {...register("recomendacoes")} />
            </div>

            {/* Constatações dinâmicas */}
            <div className="space-y-2">
              <Label>Constatações Detalhadas</Label>
              {fields.map((field, index) => (
                <div key={field.id} className="flex gap-2 items-start">
                  <Input
                    placeholder={`Constatação ${index + 1}`}
                    {...register(`constatacoes.${index}.descricao`)}
                    className="flex-1"
                  />
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  )}
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => append({ descricao: "" })}
              >
                <Plus className="size-3.5" />
                Adicionar constatação
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose}>Cancelar</Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Registrando..." : "Registrar Visita"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
