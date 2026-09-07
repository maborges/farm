"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PenTool, AlertTriangle, AlertOctagon } from "lucide-react";
import { format, parseISO, isPast, isWithinInterval, addDays } from "date-fns";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (nome: string, crea: string, creaValidade?: string) => void;
  isPending?: boolean;
  exportaId?: string;
}

export function AssinarRTDialog({ open, onClose, onConfirm, isPending }: Props) {
  const [nome, setNome] = useState("");
  const [crea, setCrea] = useState("");
  const [creaValidade, setCreaValidade] = useState("");

  const nomeValido = nome.trim().length >= 3;
  const creaValido = crea.trim().length >= 4;

  // Validação da data de validade do CREA
  const creaValidadeDate = creaValidade ? (() => {
    try { return parseISO(creaValidade); } catch { return null; }
  })() : null;

  const creaVencido = creaValidadeDate ? isPast(creaValidadeDate) : false;
  const creaVencendoEmBreve = creaValidadeDate
    ? isWithinInterval(creaValidadeDate, { start: new Date(), end: addDays(new Date(), 30) })
    : false;

  const podeAssinar = nomeValido && creaValido && !creaVencido;

  const handleConfirm = () => {
    if (!podeAssinar) return;
    onConfirm(
      nome.trim(),
      crea.trim(),
      creaValidade || undefined,
    );
    setNome("");
    setCrea("");
    setCreaValidade("");
  };

  const handleClose = () => {
    setNome("");
    setCrea("");
    setCreaValidade("");
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="sm:max-w-[560px] p-0 gap-0 overflow-hidden">
        <DialogHeader className="border-b px-6 py-5">
          <DialogTitle className="flex items-center gap-2">
            <PenTool />
            Assinar Caderno de Campo
          </DialogTitle>
          <DialogDescription>
            A assinatura do responsável técnico valida o caderno para auditoria, rastreabilidade
            e certificações.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="min-h-0 max-h-[70vh]">
          <div className="px-6 py-5">
            <div className="flex flex-col gap-5">
              <section className="rounded-sm border bg-muted/30 p-4">
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-foreground">Identificação do responsável</h3>
                  <p className="text-xs text-muted-foreground">
                    Informe quem está validando o caderno e o registro profissional correspondente.
                  </p>
                </div>

                <div className="flex flex-col gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="rt-nome">Nome do Responsável Técnico</Label>
                    <Input
                      id="rt-nome"
                      placeholder="Ex: João da Silva"
                      value={nome}
                      onChange={(e) => setNome(e.target.value)}
                    />
                    {!nomeValido && nome.length > 0 && (
                      <p className="text-xs text-destructive">Mínimo 3 caracteres.</p>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="rt-crea">Número do CREA</Label>
                    <Input
                      id="rt-crea"
                      placeholder="Ex: 123456/UF"
                      value={crea}
                      onChange={(e) => setCrea(e.target.value.toUpperCase())}
                    />
                    {!creaValido && crea.length > 0 && (
                      <p className="text-xs text-destructive">Mínimo 4 caracteres.</p>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="rt-crea-validade">Validade do CREA</Label>
                    <Input
                      id="rt-crea-validade"
                      type="date"
                      value={creaValidade}
                      onChange={(e) => setCreaValidade(e.target.value)}
                    />
                    {creaValidadeDate && creaVencido && (
                      <div className="flex items-start gap-2 rounded-sm border border-red-500/20 bg-red-500/10 p-3">
                        <AlertOctagon className="flex-shrink-0 text-red-500" />
                        <p className="text-xs text-red-600">
                          CREA vencido em {format(creaValidadeDate, "dd/MM/yyyy")}. Renove antes de assinar.
                        </p>
                      </div>
                    )}
                    {creaValidadeDate && creaVencendoEmBreve && !creaVencido && (
                      <div className="flex items-start gap-2 rounded-sm border border-amber-500/20 bg-amber-500/10 p-3">
                        <AlertTriangle className="flex-shrink-0 text-amber-500" />
                        <p className="text-xs text-amber-600">
                          CREA vence em {format(creaValidadeDate, "dd/MM/yyyy")}. Considere renovar.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </section>

              <section className="rounded-sm border border-amber-500/20 bg-amber-500/5 p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="flex-shrink-0 text-amber-500" />
                  <div className="space-y-1">
                    <h4 className="text-sm font-medium text-foreground">Validação e responsabilidade</h4>
                    <p className="text-xs text-muted-foreground">
                      Ao assinar, você declara que as informações registradas neste caderno de campo
                      são verdadeiras e foram verificadas pelo responsável técnico.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={isPending || !podeAssinar}>
            <PenTool />
            {isPending ? "Assinando..." : "Assinar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
