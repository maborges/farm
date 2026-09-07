"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody } from "@/components/ui/dialog";
import { ArrowRight, Calculator } from "lucide-react";
import { UnidadeMedidaCombobox } from "@/components/shared/unidade-medida-combobox";

interface ConversaoResponse {
  valor_original: number;
  unidade_origem_id: string;
  valor_convertido: number;
  unidade_destino_id: string;
}

export function UnidadeConversorDialog() {
  const [open, setOpen] = useState(false);
  const [valor, setValor] = useState("1");
  const [origemId, setOrigemId] = useState<string | null>(null);
  const [origemLabel, setOrigemLabel] = useState<string>("");
  const [destinoId, setDestinoId] = useState<string | null>(null);
  const [destinoLabel, setDestinoLabel] = useState<string>("");
  const [resultado, setResultado] = useState<ConversaoResponse | null>(null);

  const converter = useMutation({
    mutationFn: () =>
      apiFetch<ConversaoResponse>("/unidades-medida/converter", {
        method: "POST",
        body: {
          valor: Number(valor),
          unidade_origem_id: origemId,
          unidade_destino_id: destinoId,
        },
      }),
    onSuccess: (data) => setResultado(data),
    onError: (err: any) => {
      setResultado(null);
      toast.error(err?.message || "Não foi possível converter — verifique se existe fator/conversão entre essas unidades.");
    },
  });

  function reset() {
    setValor("1");
    setOrigemId(null);
    setOrigemLabel("");
    setDestinoId(null);
    setDestinoLabel("");
    setResultado(null);
  }

  return (
    <>
      <Button size="sm" variant="outline" className="h-8 rounded-sm text-xs" onClick={() => setOpen(true)}>
        <Calculator className="mr-2 size-3.5" />
        Converter Unidades
      </Button>

      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) reset(); }}>
        <DialogContent className="max-w-md rounded-sm">
          <DialogHeader>
            <DialogTitle>Conversor de Unidades</DialogTitle>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Valor</Label>
              <Input
                type="number"
                step="any"
                value={valor}
                onChange={(e) => { setValor(e.target.value); setResultado(null); }}
              />
            </div>

            <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-2">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">De</Label>
                <UnidadeMedidaCombobox
                  value={origemId}
                  fallbackLabel={origemLabel}
                  onChange={(id, unidade) => {
                    setOrigemId(id);
                    setOrigemLabel(unidade?.nome || "");
                    setResultado(null);
                  }}
                />
              </div>
              <ArrowRight className="size-4 text-muted-foreground mb-2" />
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-muted-foreground">Para</Label>
                <UnidadeMedidaCombobox
                  value={destinoId}
                  fallbackLabel={destinoLabel}
                  onChange={(id, unidade) => {
                    setDestinoId(id);
                    setDestinoLabel(unidade?.nome || "");
                    setResultado(null);
                  }}
                />
              </div>
            </div>

            {resultado && (
              <div className="rounded-sm border bg-muted/30 p-3 text-center">
                <p className="text-lg font-semibold tabular-nums">
                  {resultado.valor_original} {origemLabel} = {resultado.valor_convertido} {destinoLabel}
                </p>
              </div>
            )}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setOpen(false)}>Fechar</Button>
            <Button
              size="sm"
              disabled={!valor || !origemId || !destinoId || converter.isPending}
              onClick={() => converter.mutate()}
            >
              <Calculator className="size-3.5 mr-1.5" />
              Converter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
