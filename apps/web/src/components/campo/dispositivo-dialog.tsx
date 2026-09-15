"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Copy, CheckCheck, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { FazendaSelector } from "@/components/shared/fazendas-selector";

const schema = z.object({
  nome: z.string().min(2, "Nome obrigatório"),
  user_id: z.string().min(1, "Operador obrigatório"),
  fazenda_ids: z.array(z.string().uuid()).min(1, "Selecione ao menos uma fazenda"),
  expires_days: z.number().min(1).max(365),
});

type FormData = z.infer<typeof schema>;

interface ActivationResult {
  id: string;
  nome: string;
  activation_code: string;
  activation_code_expires_at: string;
  expires_at: string;
  status: string;
}

interface Usuario {
  id: string;
  usuario_id: string;
  nome: string;
  email: string;
}

interface DispositivoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DispositivoDialog({ open, onOpenChange }: DispositivoDialogProps) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ActivationResult | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: usuarios = [] } = useQuery<Usuario[]>({
    queryKey: ["usuarios-campo"],
    queryFn: () => apiFetch("/team/users"),
    enabled: open,
  });

  const {
    register,
    handleSubmit,
    setValue,
    control,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { nome: "", user_id: "", fazenda_ids: [], expires_days: 30 },
  });

  const criar = useMutation({
    mutationFn: (data: FormData) =>
      apiFetch("/campo/devices", {
        method: "POST",
        body: JSON.stringify({ ...data, modulos: ["agricola"] }),
      }),
    onSuccess: (data: ActivationResult) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["campo-dispositivos"] });
      toast.success("Código de ativação gerado!");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleClose() {
    setResult(null);
    setCopied(false);
    reset();
    onOpenChange(false);
  }

  async function copiarCodigo() {
    if (!result) return;
    await navigator.clipboard.writeText(result.activation_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast.success("Código copiado para a área de transferência.");
  }

  const expiresAt = result
    ? new Date(result.activation_code_expires_at).toLocaleString("pt-BR")
    : null;

  const userId = useWatch({ control, name: "user_id" });
  const selectedFazendas = useWatch({ control, name: "fazenda_ids" }) ?? [];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-2xl rounded-sm border shadow-xl">
        <DialogHeader className="space-y-1 border-b border-border/60 px-6 pb-5">
          <DialogTitle className="text-lg font-bold tracking-tight">
            {result ? "Dispositivo Criado" : "Novo Dispositivo"}
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            {result
              ? "Repasse o código de ativação ao operador responsável."
              : "Cadastre um tablet ou celular e gere um código de ativação."}
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="space-y-5 px-6 pb-6 pt-5">
            <div className="flex flex-col items-center gap-3 rounded-sm border bg-muted/30 p-7 text-center">
              <span className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">
                Código de Ativação
              </span>
              <span className="font-mono text-4xl font-black tracking-[0.3em] text-primary select-all">
                {result.activation_code}
              </span>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={copiarCodigo} 
                className="mt-2 h-8 gap-1.5 rounded-sm"
              >
                {copied
                  ? <CheckCheck className="size-3.5 text-emerald-500" />
                  : <Copy className="size-3.5" />}
                {copied ? "Copiado!" : "Copiar código"}
              </Button>
            </div>
            
            <div className="overflow-hidden rounded-sm border bg-background text-xs">
              <div className="flex justify-between border-b px-4 py-2.5">
                <span className="text-muted-foreground">Nome Identificador</span>
                <span className="font-semibold">{result.nome}</span>
              </div>
              <div className="flex justify-between px-4 py-2.5">
                <span className="text-muted-foreground">O código expira em</span>
                <span className="font-semibold text-orange-600">{expiresAt}</span>
              </div>
            </div>

            <DialogFooter>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleClose} 
                className="w-full rounded-sm"
              >
                Concluído
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-6 px-6 pb-6 pt-5">
            <form
              id="dispositivo-form"
              onSubmit={handleSubmit((d) => criar.mutate(d))}
              className="space-y-5"
            >
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Nome do Dispositivo *</label>
                <Input
                  placeholder="Ex: Tablet Operador João"
                  className="rounded-sm"
                  {...register("nome")}
                />
                {errors.nome && <p className="text-[10px] text-destructive">{errors.nome.message}</p>}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Operador Responsável *</label>
                <Select value={userId} onValueChange={(val) => setValue("user_id", val)}>
                  <SelectTrigger className="rounded-sm">
                    <SelectValue placeholder="Selecione o operador..." />
                  </SelectTrigger>
                  <SelectContent className="rounded-sm">
                    {usuarios.map((u) => (
                      <SelectItem key={u.id} value={u.usuario_id}>
                        {u.nome}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.user_id && <p className="text-[10px] text-destructive">{errors.user_id.message}</p>}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Validade do Dispositivo (dias)</label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  className="rounded-sm"
                  {...register("expires_days", { valueAsNumber: true })}
                />
                {errors.expires_days && <p className="text-[10px] text-destructive">{errors.expires_days.message}</p>}
              </div>

              <div className="space-y-2 rounded-sm border bg-muted/20 p-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold">Fazendas do dispositivo *</label>
                  <p className="text-[10px] text-muted-foreground">
                    Marque abaixo as fazendas que este dispositivo pode acessar.
                  </p>
                </div>
                <FazendaSelector
                  selectedIds={selectedFazendas}
                  onChange={(fazendaIds) =>
                    setValue("fazenda_ids", fazendaIds, {
                      shouldDirty: true,
                      shouldTouch: true,
                      shouldValidate: true,
                    })
                  }
                  maxHeight="240px"
                />
                {errors.fazenda_ids && (
                  <p className="text-[10px] text-destructive">{errors.fazenda_ids.message}</p>
                )}
              </div>
            </form>
            
            <DialogFooter className="gap-2 sm:gap-0">
              <Button 
                type="button" 
                variant="outline" 
                size="sm" 
                onClick={handleClose}
                className="rounded-sm"
              >
                Cancelar
              </Button>
              <Button 
                type="submit" 
                form="dispositivo-form" 
                variant="default"
                size="sm" 
                className="rounded-sm"
                disabled={criar.isPending}
              >
                {criar.isPending ? (
                  <>
                    <Loader2 className="size-3.5 mr-1.5 animate-spin" />
                    Gerando...
                  </>
                ) : (
                  "Gerar Código de Ativação"
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
