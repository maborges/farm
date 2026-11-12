"use client";

import { useEffect } from "react";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, UserCheck, Check, Loader2 } from "lucide-react";
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
      <DialogContent className="max-w-lg p-0">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
              <UserCheck className="size-4 text-primary" />
            </div>
            <div>
              <DialogTitle>Registrar Visita Técnica</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Apontamento técnico do responsável agronômico no talhão.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onFormSubmit)}>
          <DialogBody className="space-y-4 max-h-[70vh]">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Talhão <span className="text-destructive">*</span></Label>
                <Controller
                  name="talhao_id"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value || ""}>
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue placeholder="Selecionar..." />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        {talhoes.length === 0 ? (
                          <SelectItem value="__empty" disabled>Nenhum talhão vinculado</SelectItem>
                        ) : (
                          talhoes.map((t) => (
                            <SelectItem key={t.id} value={t.id} className="text-xs">
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
                <Label className="text-xs font-medium">Data da Visita</Label>
                <Input type="date" {...register("data_visita", { required: true })} className="h-8 text-xs rounded-sm" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Nome do RT <span className="text-destructive">*</span></Label>
                <Input placeholder="Ex: João da Silva" {...register("nome_rt", { required: true, minLength: 3 })} className="h-8 text-xs rounded-sm" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">CREA <span className="text-destructive">*</span></Label>
                <Input placeholder="Ex: 123456/UF" {...register("crea", { required: true, minLength: 4 })} className="h-8 text-xs rounded-sm" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Observações</Label>
              <Textarea rows={3} placeholder="Constatações gerais da visita..." {...register("observacoes")} className="text-xs rounded-sm" />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Recomendações</Label>
              <Textarea rows={3} placeholder="Orientações ao produtor..." {...register("recomendacoes")} className="text-xs rounded-sm" />
            </div>

            {/* Constatações dinâmicas */}
            <div className="space-y-2 pt-2 border-t border-border/50">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">Constatações Detalhadas</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm gap-1 h-7 text-xs"
                  onClick={() => append({ descricao: "" })}
                >
                  <Plus className="size-3" />
                  Adicionar
                </Button>
              </div>
              {fields.map((field, index) => (
                <div key={field.id} className="flex gap-2 items-center">
                  <Input
                    placeholder={`Constatação ${index + 1}`}
                    {...register(`constatacoes.${index}.descricao`)}
                    className="flex-1 h-8 text-xs rounded-sm"
                  />
                  {fields.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="size-8 p-0 text-destructive hover:text-destructive"
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" size="sm" type="button" className="rounded-sm" onClick={handleClose} disabled={isLoading}>
              Cancelar
            </Button>
            <Button size="sm" type="submit" className="rounded-sm gap-1.5" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Registrando...
                </>
              ) : (
                <>
                  <Check className="size-3.5" />
                  Registrar Visita
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
