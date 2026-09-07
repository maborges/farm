"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

const EPI_TIPOS = [
  { value: "LUVA", label: "Luva" },
  { value: "MASCARA", label: "Máscara" },
  { value: "OCULOS", label: "Óculos de Proteção" },
  { value: "AVENTAL", label: "Avental" },
  { value: "BOTA", label: "Bota" },
  { value: "CAPACETE", label: "Capacete" },
  { value: "PROTETOR_AUDITIVO", label: "Protetor Auditivo" },
  { value: "OUTRO", label: "Outro" },
];

export function EPIEntregaForm({ open, onClose, onSubmit, isLoading }: Props) {
  const { register, handleSubmit, control, reset, watch } = useForm({
    defaultValues: {
      nome_trabalhador: "",
      epi_tipo: "",
      quantidade: 1,
      data_entrega: new Date().toISOString().split("T")[0],
      validade: "",
    },
  });

  const epiTipo = watch("epi_tipo");

  const handleClose = () => {
    reset();
    onClose();
  };

  const onFormSubmit = async (data: any) => {
    if (!data.nome_trabalhador.trim()) {
      toast.error("Informe o nome do trabalhador.");
      return;
    }
    if (!data.epi_tipo) {
      toast.error("Selecione o tipo de EPI.");
      return;
    }
    await onSubmit(data);
    handleClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-[480px]">
        <form onSubmit={handleSubmit(onFormSubmit)}>
          <DialogHeader>
            <DialogTitle>Registrar Entrega de EPI</DialogTitle>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="space-y-1.5">
              <Label>Nome do Trabalhador <span className="text-destructive">*</span></Label>
              <Input placeholder="Nome completo" {...register("nome_trabalhador", { required: true })} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Tipo de EPI <span className="text-destructive">*</span></Label>
                <Controller
                  name="epi_tipo"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value || ""}>
                      <SelectTrigger><SelectValue placeholder="Selecionar..." /></SelectTrigger>
                      <SelectContent>
                        {EPI_TIPOS.map((t) => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Quantidade</Label>
                <Input type="number" min={1} {...register("quantidade", { valueAsNumber: true, min: 1 })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Data de Entrega</Label>
                <Input type="date" {...register("data_entrega", { required: true })} />
              </div>
              <div className="space-y-1.5">
                <Label>Validade do EPI</Label>
                <Input type="date" {...register("validade")} />
              </div>
            </div>

            {epiTipo && (
              <div className="rounded-md bg-blue-500/10 border border-blue-500/20 p-3">
                <p className="text-xs text-blue-600">
                  EPI: <strong>{EPI_TIPOS.find(t => t.value === epiTipo)?.label}</strong>
                  <br />
                  Conforme NR-6, o empregador deve fornecer EPI adequado gratuitamente
                  e fiscalizar o uso correto.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose}>Cancelar</Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Registrando..." : "Registrar Entrega"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
