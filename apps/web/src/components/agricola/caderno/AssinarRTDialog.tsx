"use client";

import { useState } from "react";
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
import { PenTool, AlertTriangle, AlertOctagon, Loader2 } from "lucide-react";
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
      <DialogContent className="max-w-lg p-0">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
              <PenTool className="size-4 text-primary" />
            </div>
            <div>
              <DialogTitle>Assinar Caderno de Campo</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Validação formal do caderno para auditoria, rastreabilidade e certificações.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogBody className="space-y-4 max-h-[70vh]">
          <div className="space-y-1.5">
            <Label htmlFor="rt-nome" className="text-xs font-medium">Nome do Responsável Técnico <span className="text-destructive">*</span></Label>
            <Input
              id="rt-nome"
              placeholder="Ex: João da Silva"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="h-8 text-xs rounded-sm"
            />
            {!nomeValido && nome.length > 0 && (
              <p className="text-[11px] text-destructive">Mínimo 3 caracteres.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="rt-crea" className="text-xs font-medium">Número do CREA <span className="text-destructive">*</span></Label>
              <Input
                id="rt-crea"
                placeholder="Ex: 123456/UF"
                value={crea}
                onChange={(e) => setCrea(e.target.value.toUpperCase())}
                className="h-8 text-xs rounded-sm"
              />
              {!creaValido && crea.length > 0 && (
                <p className="text-[11px] text-destructive">Mínimo 4 caracteres.</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rt-crea-validade" className="text-xs font-medium">Validade do CREA</Label>
              <Input
                id="rt-crea-validade"
                type="date"
                value={creaValidade}
                onChange={(e) => setCreaValidade(e.target.value)}
                className="h-8 text-xs rounded-sm"
              />
            </div>
          </div>

          {creaValidadeDate && creaVencido && (
            <div className="flex items-start gap-2 rounded-sm border border-red-500/20 bg-red-500/10 p-3">
              <AlertOctagon className="size-4 shrink-0 text-red-500 mt-0.5" />
              <p className="text-xs text-red-600">
                CREA vencido em {format(creaValidadeDate, "dd/MM/yyyy")}. Renove antes de assinar.
              </p>
            </div>
          )}
          {creaValidadeDate && creaVencendoEmBreve && !creaVencido && (
            <div className="flex items-start gap-2 rounded-sm border border-amber-500/20 bg-amber-500/10 p-3">
              <AlertTriangle className="size-4 shrink-0 text-amber-500 mt-0.5" />
              <p className="text-xs text-amber-600">
                CREA vence em {format(creaValidadeDate, "dd/MM/yyyy")}. Considere renovar.
              </p>
            </div>
          )}

          <div className="rounded-sm border border-amber-500/20 bg-amber-500/5 p-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="size-4 shrink-0 text-amber-500 mt-0.5" />
              <div className="space-y-0.5">
                <h4 className="text-xs font-semibold text-amber-900 dark:text-amber-300">Validação e responsabilidade</h4>
                <p className="text-[11px] text-muted-foreground">
                  Ao assinar, você declara que as informações registradas neste caderno de campo
                  são verdadeiras e foram verificadas pelo responsável técnico.
                </p>
              </div>
            </div>
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" className="rounded-sm" onClick={handleClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button size="sm" className="rounded-sm gap-1.5" onClick={handleConfirm} disabled={isPending || !podeAssinar}>
            {isPending ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                Assinando...
              </>
            ) : (
              <>
                <PenTool className="size-3.5" />
                Assinar
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
