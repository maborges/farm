"use client";

import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AlertTriangle } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
  isPending?: boolean;
}

export function DeleteEntradaDialog({ open, onClose, onConfirm, isPending }: Props) {
  const [motivo, setMotivo] = useState("");
  const error = motivo.length > 0 && motivo.length < 10;

  const handleConfirm = () => {
    if (motivo.length < 10) return;
    onConfirm(motivo);
    setMotivo("");
  };

  const handleClose = () => {
    setMotivo("");
    onClose();
  };

  return (
    <AlertDialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <AlertDialogContent className="rounded-sm max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive text-base font-semibold">
            <AlertTriangle className="size-4" />
            Excluir registro do caderno
          </AlertDialogTitle>
          <AlertDialogDescription className="text-xs text-muted-foreground">
            Esta ação não remove permanentemente o registro. Ele será mantido para auditoria
            com status de &quot;excluído&quot; e o motivo informado será registrado.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-1 py-2">
          <Label htmlFor="motivo" className="text-xs font-medium">
            Motivo da exclusão <span className="text-destructive">*</span>
          </Label>
          <Textarea
            id="motivo"
            rows={3}
            placeholder="Descreva o motivo da exclusão (mínimo 10 caracteres)..."
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className={`rounded-sm text-sm ${error ? "border-destructive" : ""}`}
          />
          {error && (
            <p className="text-[11px] text-destructive">
              O motivo deve ter pelo menos 10 caracteres.
            </p>
          )}
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending} className="rounded-sm h-8 text-xs">
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction
            asChild
            disabled={isPending || motivo.length < 10}
          >
            <Button
              variant="destructive"
              size="sm"
              onClick={handleConfirm}
              disabled={isPending || motivo.length < 10}
              className="rounded-sm"
            >
              {isPending ? "Excluindo..." : "Excluir registro"}
            </Button>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
