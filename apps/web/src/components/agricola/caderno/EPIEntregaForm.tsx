"use client";

import { useForm, Controller } from "react-hook-form";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { HardHat, Check, Loader2 } from "lucide-react";
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
      <DialogContent className="max-w-lg p-0">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
              <HardHat className="size-4 text-primary" />
            </div>
            <div>
              <DialogTitle>Registrar Entrega de EPI</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Registro de fornecimento de EPI aos colaboradores conforme NR-6 e NR-31.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit(onFormSubmit)}>
          <DialogBody className="space-y-4 max-h-[70vh]">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Nome do Trabalhador <span className="text-destructive">*</span></Label>
              <Input placeholder="Nome completo" {...register("nome_trabalhador", { required: true })} className="h-8 text-xs rounded-sm" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Tipo de EPI <span className="text-destructive">*</span></Label>
                <Controller
                  name="epi_tipo"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value || ""}>
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue placeholder="Selecionar..." />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        {EPI_TIPOS.map((t) => (
                          <SelectItem key={t.value} value={t.value} className="text-xs">{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Quantidade</Label>
                <Input type="number" min={1} {...register("quantidade", { valueAsNumber: true, min: 1 })} className="h-8 text-xs rounded-sm" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Data de Entrega</Label>
                <Input type="date" {...register("data_entrega", { required: true })} className="h-8 text-xs rounded-sm" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Validade do EPI</Label>
                <Input type="date" {...register("validade")} className="h-8 text-xs rounded-sm" />
              </div>
            </div>

            {epiTipo && (
              <div className="rounded-sm bg-primary/5 border border-primary/20 p-3">
                <p className="text-xs text-primary font-medium">
                  EPI: {EPI_TIPOS.find(t => t.value === epiTipo)?.label}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Conforme normas regulamentadoras, o empregador deve fornecer EPI adequado e fiscalizar o uso correto.
                </p>
              </div>
            )}
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
                  Registrar Entrega
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
